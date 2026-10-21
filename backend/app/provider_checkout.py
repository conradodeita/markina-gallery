"""Reserva local de seleções para checkout externo; não faz chamada HTTP."""

from urllib.parse import urlsplit
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.acervo_context import client_tenant_id, require_active_owner
from app.auth import (
    Client,
    GalleryClientState,
    InfinitePaySettings,
    PaymentGroup,
    PhotoSelection,
    ProviderPayment,
    ProviderPaymentAttempt,
    SaleOrder,
    now,
)
from app.checkout import CheckoutError, _synchronize_order
from app.infinitepay_binding import api_key_configured
from app.infinitepay_settings import configuration_payload
from app.payment_availability import lock_payment_account
from app.payment_provider import CheckoutItem, CheckoutRequest, ProviderTransportError
from app.unified_checkout import (
    _fingerprint,
    _gallery_key,
    _materials,
    _valid_materials,
)

MAX_PROVIDER_CENTS = 2_147_483_647


def prepare_provider_payment(
    db: Session,
    client: Client,
    *,
    cart_revision: str,
    checkout_key: str,
) -> ProviderPayment:
    """Congele/reserve o carrinho numa transação do chamador antes da rede.

    Perfil de configuração ativa não é criado por APIs do produto. Os testes
    podem inserir somente um perfil sintético e continuar sem dinheiro real.
    """
    tenant_id = client_tenant_id(db, client.id)
    require_active_owner(db, tenant_id)
    lock_payment_account(db, tenant_id)
    if not checkout_key or len(checkout_key) > 128:
        raise CheckoutError("Chave de compra inválida.")
    db.scalar(select(Client.id).where(Client.id == client.id, Client.tenant_id == tenant_id).with_for_update())
    existing = db.scalar(select(ProviderPayment).where(
        ProviderPayment.tenant_id == tenant_id, ProviderPayment.client_id == client.id,
        ProviderPayment.checkout_key == checkout_key,
    ).with_for_update())
    if existing:
        if existing.cart_revision != cart_revision:
            raise CheckoutError("A chave já foi usada para outra revisão do carrinho.")
        return existing

    # Trave as galerias canônicas antes de cotar/fixar fotos; a ordem evita deadlock.
    parent_ids = sorted({
        gallery.parent_gallery_id
        for gallery, _parent, _material, _error in _materials(db, client)
        if gallery.parent_gallery_id is not None
    }, key=str)
    from app.auth import ParentGallery

    for parent_id in parent_ids:
        parent = db.scalar(select(ParentGallery).where(
            ParentGallery.id == parent_id, ParentGallery.tenant_id == tenant_id,
        ).with_for_update())
        if parent is None:
            raise CheckoutError("Carrinho indisponível neste contexto.")

    materials = _valid_materials(db, client)
    revision = _fingerprint(materials)
    if revision != cart_revision:
        raise CheckoutError("O carrinho mudou. Atualize a revisão antes de pagar.")
    settings = db.scalar(select(InfinitePaySettings).where(
        InfinitePaySettings.tenant_id == tenant_id,
    ).with_for_update())
    if not configuration_payload(
        settings, api_key_configured=api_key_configured(tenant_id, db=db),
    )["checkout_available"]:
        raise CheckoutError("Cartão indisponível para esta conta.")

    eligible = [(gallery, parent, material, error) for gallery, parent, material, error in materials
                if parent.payment_required]
    if not eligible or any(error or material is None for _, _, material, error in eligible):
        raise CheckoutError("Confira as galerias pagas antes de preparar o cartão.")
    count = sum(len(material[1]) for _, _, material, _ in eligible)
    amounts = [parcel.unit_price_cents
               for _, _, material, _ in eligible
               for parcel in material[3].quote.parcels
               for _ in range(parcel.quantity)]
    total = sum(amounts)
    if (not 1 <= count <= 100_000 or len(amounts) != count
            or not 0 < total <= MAX_PROVIDER_CENTS or any(not 0 < price <= MAX_PROVIDER_CENTS for price in amounts)):
        raise CheckoutError("Valores ou quantidade indisponíveis para checkout.")
    key = str(UUID(checkout_key)) if _is_uuid(checkout_key) else checkout_key
    new_payment = ProviderPayment(
        tenant_id=tenant_id, client_id=client.id, checkout_key=key,
        cart_revision=revision, total_cents=total, handle_snapshot=settings.handle,
        credential_id=settings.credential_id,
        configuration_version=settings.version, verification_profile=settings.verification_profile,
        state="creating", revision_number=0,
    )
    db.add(new_payment)
    db.flush()

    # Local PIX rascunhos ainda não foram comunicados. Feche somente esses grupos
    # sob o lock do cliente e conserve sua identificação e payloads históricas.
    draft_groups = list(db.scalars(select(PaymentGroup).where(
        PaymentGroup.tenant_id == tenant_id, PaymentGroup.client_id == client.id,
        PaymentGroup.state == "draft",
    ).with_for_update()))
    for group in draft_groups:
        group.state = "unavailable"

    by_key: dict[tuple[str, UUID], SaleOrder] = {}
    drafts = list(db.scalars(select(SaleOrder).where(
        SaleOrder.tenant_id == tenant_id, SaleOrder.client_id == client.id,
        SaleOrder.payment_status == "pending", SaleOrder.frozen_at.is_(None),
        SaleOrder.assets_removed_at.is_(None), SaleOrder.checkout_key.is_not(None),
    ).order_by(SaleOrder.id).with_for_update()))
    for order in drafts:
        order.payment_group_id = None
        order.checkout_key = None
        if order.payment_status == "pending" and order.frozen_at is None:
            by_key[("canonical", order.parent_gallery_id) if order.parent_gallery_id
                   else ("legacy", order.derived_gallery_id)] = order

    for gallery, _parent, material, _error in eligible:
        order = by_key.get(_gallery_key(gallery)) or SaleOrder(
            parent_gallery_id=gallery.parent_gallery_id if isinstance(gallery, GalleryClientState) else None,
            derived_gallery_id=None if isinstance(gallery, GalleryClientState) else gallery.id,
            client_id=client.id, total_cents=0, checkout_key=str(UUID(checkout_key)) if _is_uuid(checkout_key) else checkout_key,
            tenant_id=tenant_id,
        )
        _synchronize_order(db, order=order, gallery=gallery, client=client, material=material)
        order.payment_group_id = None
        order.checkout_key = str(UUID(checkout_key)) if _is_uuid(checkout_key) else checkout_key
        order.pix_copy_paste_snapshot = None
        order.pix_qr_code_snapshot = None
        order.pix_instructions_snapshot = None
        order.pix_configuration_snapshot = None
        order.frozen_at = now()
        order.provider_payment_id = new_payment.id
        db.execute(delete(PhotoSelection).where(
            PhotoSelection.tenant_id == tenant_id,
            PhotoSelection.client_id == client.id,
            PhotoSelection.id.in_([selection.id for selection in material[0]]),
        ))
    attempt = ProviderPaymentAttempt(tenant_id=tenant_id, client_id=client.id,
                                     payment_id=new_payment.id, state="started")
    db.add(attempt)
    db.flush()
    return new_payment


def checkout_request_for(db: Session, payment: ProviderPayment) -> CheckoutRequest:
    """Reconstrua descrição/valores do snapshot gravado, sem nomes de fotos."""
    orders = list(db.scalars(select(SaleOrder).where(
        SaleOrder.tenant_id == payment.tenant_id,
        SaleOrder.client_id == payment.client_id,
        SaleOrder.provider_payment_id == payment.id,
    ).order_by(SaleOrder.id)))
    if not orders:
        raise CheckoutError("Snapshot de compra indisponível.")
    from app.auth import SaleOrderItem

    order_ids = [order.id for order in orders]
    units = list(db.scalars(select(SaleOrderItem.unit_price_cents).where(
        SaleOrderItem.tenant_id == payment.tenant_id,
        SaleOrderItem.sale_order_id.in_(order_ids),
    )))
    grouped: dict[int, int] = {}
    for price in units:
        grouped[price] = grouped.get(price, 0) + 1
    if not units or sum(units) != payment.total_cents or len(grouped) > 1000:
        raise CheckoutError("Snapshot de valores indisponível para checkout.")
    try:
        items = tuple(CheckoutItem(quantity=quantity, price=price)
                      for price, quantity in sorted(grouped.items()))
        return CheckoutRequest(payment_id=payment.id, tenant_id=payment.tenant_id,
                               handle=payment.handle_snapshot, items=items)
    except ValueError as exc:
        raise CheckoutError("Valores indisponíveis para checkout.") from exc


def issue_provider_payment(db: Session, payment_id: UUID, provider) -> ProviderPayment:
    """Faça uma única chamada depois de gravar incerteza recuperável.

    Uma tentativa marcada unknown nunca é chamada novamente. O perfil sintético
    é permitido apenas para evidência local; o fluxo real usa retorno e payment_check.
    """
    payment = db.scalar(select(ProviderPayment).where(ProviderPayment.id == payment_id).with_for_update())
    if not payment or payment.state != "creating":
        raise CheckoutError("Compra indisponível para emissão.")
    attempt = db.scalar(select(ProviderPaymentAttempt).where(
        ProviderPaymentAttempt.tenant_id == payment.tenant_id,
        ProviderPaymentAttempt.payment_id == payment.id,
    ).with_for_update())
    if not attempt or attempt.state != "started":
        raise CheckoutError("Tentativa já utilizada; conciliação necessária.")
    capabilities = provider.capabilities
    if (capabilities.profile != "synthetic-only"
            and not all((capabilities.operational, capabilities.credit_only,
                         capabilities.payment_binding_verified))):
        raise CheckoutError("Perfil do provedor não atende ao fluxo documentado de cartão.")
    request = checkout_request_for(db, payment)
    if request.total_cents != payment.total_cents:
        raise CheckoutError("Valor do snapshot diverge do total congelado.")
    attempt.state = "unknown"
    attempt.error_category = "transport_unknown"
    attempt.completed_at = now()
    payment.state = "verification_required"
    payment.revision_number += 1
    db.commit()

    # A marca durable unknown precede o efeito. Falha, exceção ou timeout nunca
    # causa reemissão automática; um processo posterior concilia esta tentativa.
    try:
        result = provider.create_checkout(request)
    except ProviderTransportError:
        return payment
    db.refresh(payment)
    if result.outcome == "accepted" and _allowed_checkout_url(result.url, synthetic=capabilities.profile == "synthetic-only"):
        payment.checkout_url = result.url
        payment.state = "awaiting_payment"
        payment.revision_number += 1
        attempt.state = "accepted"
        attempt.error_category = None
        db.commit()
    elif result.outcome == "refused" and result.error_category == "not_created":
        payment.state = "failed_before_issue"
        payment.revision_number += 1
        attempt.state = "refused"
        attempt.error_category = "not_created"
        payment.checkout_url = None
        _restore_local_selection(db, payment)
        db.commit()
    else:
        attempt.error_category = result.error_category or "invalid_response"
        db.commit()
    return payment


def _allowed_checkout_url(value: str | None, *, synthetic: bool) -> bool:
    if not value or len(value) > 8192:
        return False
    try:
        parsed = urlsplit(value)
        return (parsed.scheme == "https" and parsed.username is None and parsed.password is None
                and parsed.port in (None, 443) and
                (parsed.hostname in {"checkout.infinitepay.io", "checkout.infinitepay.com.br"}
                 or synthetic and parsed.hostname == "checkout.example.invalid"))
    except ValueError:
        return False


def _restore_local_selection(db: Session, payment: ProviderPayment) -> None:
    from app.auth import SaleOrderItem

    orders = list(db.scalars(select(SaleOrder).where(
        SaleOrder.tenant_id == payment.tenant_id,
        SaleOrder.provider_payment_id == payment.id,
    ).with_for_update()))
    for order in orders:
        items = list(db.scalars(select(SaleOrderItem).where(
            SaleOrderItem.tenant_id == payment.tenant_id,
            SaleOrderItem.sale_order_id == order.id,
        )))
        for item in items:
            gallery_filter = (PhotoSelection.parent_gallery_id == order.parent_gallery_id
                              if order.parent_gallery_id else PhotoSelection.derived_gallery_id == order.derived_gallery_id)
            exists = db.scalar(select(PhotoSelection.id).where(
                PhotoSelection.tenant_id == payment.tenant_id,
                PhotoSelection.client_id == payment.client_id,
                gallery_filter, PhotoSelection.photo_asset_id == item.photo_asset_id_snapshot,
            ))
            if not exists:
                db.add(PhotoSelection(tenant_id=payment.tenant_id, client_id=payment.client_id,
                    parent_gallery_id=order.parent_gallery_id, derived_gallery_id=order.derived_gallery_id,
                    photo_asset_id=item.photo_asset_id_snapshot))
        order.provider_payment_id = None
        order.frozen_at = None
        order.checkout_key = None


def _is_uuid(value: str) -> bool:
    try:
        UUID(value)
    except (ValueError, TypeError, AttributeError):
        return False
    return True
