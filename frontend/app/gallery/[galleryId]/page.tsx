"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";

import { ClientCartLink } from "../../client-cart";
import { galleryFontFamily } from "../../gallery-fonts";
import { GalleryPresentation, type GalleryPresentationFolder } from "../../gallery-presentation";
import { MarkinaLink, StatusBadge, SystemState } from "../../ui-kit";

type ReviewPhoto = {
  id: string;
  name: string;
  previewUrl: string;
  folderId: string;
  selected: boolean;
  favorited: boolean;
  purchaseState: string;
  commercialState: "available" | "selected" | "awaiting_payment" | "payment_reported" | "purchased";
  width: number | null;
  height: number | null;
};
type ReleasedFolder = { id: string; name: string; position: number; photo_count: number };
type Comment = { id: string; photo_id: string; body: string };
type Cart = {
  quantity: number;
  draft_order_id?: string | null;
  total_cents?: number;
  base_total_cents?: number;
  savings_cents?: number;
  unit_price_cents?: number;
  tier?: { minimum_quantity: number; maximum_quantity: number | null };
  parcels?: Array<{ minimum_quantity: number; maximum_quantity: number | null; quantity: number; unit_price_cents: number; subtotal_cents: number }>;
  pricing_error?: string;
  items?: { id: string; name: string; preview_url?: string | null }[];
};
type PendingOrder = {
  id: string;
  total_cents: number;
  price_rule?: { savings_cents?: number; parcels?: Cart["parcels"] };
  sales_message?: string | null;
  pix?: { copy_paste: string | null; qr_png_data_url: string | null; instructions: string | null; confirmation: string };
  items?: Array<{ photo_id: string; name: string; unit_price_cents: number; preview_url: string }>;
};
type PaymentOrder = {
  order_id: string;
  total_cents: number;
  payment_status: "pending" | "confirmed" | "cancelled";
  commercial_state?: "draft" | "awaiting_payment" | "payment_reported" | "purchased" | "cancelled";
  frozen_at?: string | null;
  communication: { id: string; status: "pending_review" | "confirmed" | "refused" } | null;
  notification: { status: "queued" | "processing" | "sent" | "failed"; last_error: string | null } | null;
  items?: Array<{ photo_id: string; name: string; preview_url: string | null; unit_price_cents: number }>;
};
type CommercialFilter = "all" | "selected" | "awaiting_payment" | "payment_reported" | "purchased";
type ReopeningRequest = { id: string; status: "pending" | "approved" | "refused"; approved_until: string | null; created_at: string };
type Review = {
  gallery: {
    name: string;
    message: string;
    selection_expires_at: string | null;
    selection_open: boolean;
    favorites_enabled: boolean;
    comments_enabled: boolean;
    cover_preview_url: string | null;
    folder_display_mode: "individual" | "sequential";
    cover_title_font: string;
    cover_title_color: string;
    cover_title_size: number;
    cover_title_position: string;
  };
  photos: ReviewPhoto[];
};

export default function GalleryPage() {
  const { galleryId } = useParams<{ galleryId: string }>();
  const searchParams = useSearchParams();
  const selectionReviewMode = searchParams.get("mode") === "review";
  const [review, setReview] = useState<Review | null>(null);
  const [loadFailed, setLoadFailed] = useState(false);
  const [comments, setComments] = useState<Comment[]>([]);
  const [cart, setCart] = useState<Cart>({ quantity: 0 });
  const [pendingOrder, setPendingOrder] = useState<PendingOrder | null>(null);
  const [paymentOrders, setPaymentOrders] = useState<PaymentOrder[]>([]);
  const [reopening, setReopening] = useState<ReopeningRequest | null>(null);
  const [releasedFolders, setReleasedFolders] = useState<ReleasedFolder[]>([]);
  const [message, setMessage] = useState("");
  const [closedGallery, setClosedGallery] = useState<{ publicGalleryUrl: string | null } | null>(null);
  const [filter, setFilter] = useState<CommercialFilter>("all");
  const [checkoutBusy, setCheckoutBusy] = useState(false);
  const [paymentBusy, setPaymentBusy] = useState("");
  const [pixCopied, setPixCopied] = useState(false);
  const checkoutKey = useRef("");
  const paymentKeys = useRef<Record<string, string>>({});
  const reopeningKey = useRef("");
  function load() {
    fetch(`/api/gallery/${galleryId}/review`, { credentials: "same-origin" })
      .then(async (response) => {
        if (!response.ok) throw new Error();
        const result = await response.json();
        setReview({
          ...result,
          photos: result.photos.map(
            (photo: {
              id: string;
              name: string;
              folder_id: string;
              preview_url: string;
              selected: boolean;
              favorited: boolean;
              purchase_state: string;
              commercial_state?: ReviewPhoto["commercialState"];
              width: number | null;
              height: number | null;
            }) => ({
              id: photo.id,
              name: photo.name,
              folderId: photo.folder_id,
              previewUrl: `/api${photo.preview_url}`,
              selected: photo.selected,
              favorited: photo.favorited,
              purchaseState: photo.purchase_state,
              commercialState: photo.commercial_state ?? (photo.purchase_state === "já comprada" ? "purchased" : photo.purchase_state === "pagamento informado" ? "payment_reported" : photo.selected ? "selected" : "available"),
              width: photo.width,
              height: photo.height,
            }),
          ),
        });
        setLoadFailed(false);
      })
      .catch(() => {
        setReview(null);
        setLoadFailed(true);
      });
    fetch(`/api/gallery/${galleryId}/folders`, { credentials: "same-origin" })
      .then(async (response) => {
        if (!response.ok) throw new Error();
        const result = await response.json();
        setReleasedFolders(result.folders ?? []);
      })
      .catch(() => setReleasedFolders([]));
  }
  function loadComments() {
    fetch(`/api/gallery/${galleryId}/comments`, { credentials: "same-origin" })
      .then(async (response) => {
        if (!response.ok) throw new Error();
        setComments((await response.json()).comments);
      })
      .catch(() => setComments([]));
  }
  function loadCart(restoreDraft = true) {
    fetch(`/api/gallery/${galleryId}/cart`, { credentials: "same-origin" })
      .then(async (response) => {
        if (!response.ok) throw new Error();
        const result = await response.json();
        setCart(typeof result.quantity === "number" ? result : { quantity: 0 });
        if (restoreDraft && result.draft_order_id) {
          const detailResponse = await fetch(`/api/gallery/${galleryId}/orders/${result.draft_order_id}`, { credentials: "same-origin" });
          if (detailResponse.ok) setPendingOrder(await detailResponse.json());
        }
      })
      .catch(() => setCart({ quantity: 0 }));
  }
  function loadPaymentOrders() {
    fetch(`/api/gallery/${galleryId}/payment-communications`, { credentials: "same-origin" })
      .then(async (response) => {
        if (!response.ok) throw new Error();
        const result = await response.json();
        setPaymentOrders(Array.isArray(result.orders) ? result.orders : []);
      })
      .catch(() => setPaymentOrders([]));
  }
  function loadReopening() {
    fetch(`/api/gallery/${galleryId}/reopening-requests`, { credentials: "same-origin" })
      .then(async (response) => { if (!response.ok) throw new Error(); setReopening((await response.json()).request ?? null); })
      .catch(() => setReopening(null));
  }
  useEffect(() => {
    load();
    loadComments();
    loadCart();
    loadPaymentOrders();
    loadReopening();
  }, [galleryId]); // eslint-disable-line react-hooks/exhaustive-deps
  async function requestReopening() {
    if (paymentBusy || reopening?.status === "pending") return;
    setPaymentBusy("reopening");
    reopeningKey.current ||= globalThis.crypto?.randomUUID?.() ?? `reopening-${Date.now()}-${galleryId}`;
    const response = await fetch(`/api/gallery/${galleryId}/reopening-requests`, { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ idempotency_key: reopeningKey.current }) });
    setMessage(response.ok ? "Solicitação enviada ao fotógrafo. Esta galeria continua congelada até a aprovação." : "Não foi possível solicitar a reabertura.");
    if (response.ok) loadReopening();
    setPaymentBusy("");
  }
  async function interaction(
    photo: ReviewPhoto,
    kind: "selection" | "favorite",
  ) {
    const active = kind === "selection" ? photo.selected : photo.favorited;
    const response = await fetch(
      `/api/gallery/${galleryId}/photos/${photo.id}/${kind}`,
      { method: active ? "DELETE" : "POST", credentials: "same-origin" },
    );
    setMessage(
      response.ok
        ? "Alteração salva."
        : "Não foi possível salvar esta alteração.",
    );
    if (response.ok) {
      if (kind === "selection") {
        checkoutKey.current = "";
        setPendingOrder(null);
      }
      if (response.headers.get("X-Markina-Gallery-Closed") === "true") {
        setClosedGallery({ publicGalleryUrl: response.headers.get("X-Markina-Public-Gallery-Url") });
        return;
      }
      load();
      loadCart(kind !== "selection");
    }
  }
  async function checkout() {
    if (checkoutBusy || !cart.quantity) return;
    setCheckoutBusy(true);
    checkoutKey.current ||= globalThis.crypto?.randomUUID?.() ?? `checkout-${Date.now()}-${galleryId}`;
    try {
      const response = await fetch(`/api/gallery/${galleryId}/checkout`, {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ idempotency_key: checkoutKey.current }),
      });
      if (!response.ok) throw new Error();
      const order = await response.json();
      const detailResponse = await fetch(`/api/gallery/${galleryId}/orders/${order.id}`, { credentials: "same-origin" });
      const detail = detailResponse.ok ? await detailResponse.json() : order;
      setPendingOrder(detail);
      setPixCopied(false);
      setMessage("Confira as fotos e os dados do PIX antes de informar o pagamento.");
      load();
      loadCart();
      loadPaymentOrders();
    } catch {
      setMessage("Não foi possível finalizar o pedido. Revise sua seleção e tente novamente.");
    } finally {
      setCheckoutBusy(false);
    }
  }
  async function reportPayment(orderId: string) {
    if (paymentBusy) return;
    setPaymentBusy(orderId);
    paymentKeys.current[orderId] ||= globalThis.crypto?.randomUUID?.() ?? `payment-report-${Date.now()}-${orderId}`;
    const response = await fetch(`/api/gallery/${galleryId}/orders/${orderId}/payment-communications`, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ idempotency_key: paymentKeys.current[orderId] }),
    });
    setMessage(response.ok ? "O pagamento está em análise." : "Não foi possível comunicar o pagamento.");
    if (response.ok) {
      setPendingOrder(null);
      load();
      loadCart(false);
      loadPaymentOrders();
    }
    setPaymentBusy("");
  }
  async function copyPix() {
    if (!pendingOrder?.pix?.copy_paste) return;
    try {
      await navigator.clipboard.writeText(pendingOrder.pix.copy_paste);
      setPixCopied(true);
    } catch {
      setMessage("Não foi possível copiar automaticamente. Selecione o código PIX abaixo.");
    }
  }
  async function addComment(event: FormEvent<HTMLFormElement>, photoId: string) {
    event.preventDefault();
    const form = event.currentTarget;
    const body = new FormData(form).get("body");
    const response = await fetch(
      `/api/gallery/${galleryId}/photos/${photoId}/comments`,
      {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ body }),
      },
    );
    setMessage(
      response.ok
        ? "Comentário enviado."
        : "Não foi possível enviar o comentário.",
    );
    if (response.ok) {
      form.reset();
      loadComments();
    }
  }
  async function removeComment(id: string) {
    const response = await fetch(`/api/gallery/${galleryId}/comments/${id}`, {
      method: "DELETE",
      credentials: "same-origin",
    });
    if (response.ok) loadComments();
  }
  if (closedGallery)
    return (
      <main className="admin-shell private-gallery-closed">
        <SystemState
          title="Esta galeria privada foi encerrada"
          detail="Você removeu a última foto disponível. Seu cadastro e seu histórico de compras continuam preservados."
        />
        <div className="private-gallery-closed__actions">
          {closedGallery.publicGalleryUrl ? (
            <MarkinaLink href={closedGallery.publicGalleryUrl}>Voltar à Galeria pública</MarkinaLink>
          ) : null}
          <MarkinaLink href="/library" variant={closedGallery.publicGalleryUrl ? "secondary" : "primary"}>
            Ver minha biblioteca
          </MarkinaLink>
        </div>
      </main>
    );
  if (loadFailed)
    return (
      <SystemState
        tone="error"
        title="Não foi possível abrir esta galeria"
        detail="Verifique se você entrou com a conta correta e atualize a página."
      />
    );
  if (review === null)
    return (
      <SystemState
        tone="loading"
        title="Abrindo sua galeria"
        detail="Carregando prévias protegidas."
      />
    );
  if (!review.photos.length && review.gallery.selection_open)
    return (
      <SystemState title="Nenhuma foto liberada ainda" detail="Quando o fotógrafo concluir uma rodada, ela aparecerá aqui." />
    );
  const reviewPhotos = selectionReviewMode ? review.photos.filter((photo) => photo.selected) : review.photos;
  const counts = reviewPhotos.reduce(
    (result, photo) => ({ ...result, [photo.commercialState]: (result[photo.commercialState] ?? 0) + 1 }),
    {} as Record<string, number>,
  );
  const visiblePhotos = filter === "all" ? reviewPhotos : reviewPhotos.filter((photo) => photo.commercialState === filter);
  const filterOptions: Array<{ value: CommercialFilter; label: string }> = [
    { value: "all", label: "Todas" },
    { value: "selected", label: "Carrinho" },
    { value: "awaiting_payment", label: "Aguardando pagamento" },
    { value: "payment_reported", label: "Pagamento informado" },
    { value: "purchased", label: "Compradas" },
  ];
  const presentationFolders = releasedFolders.map((folder) => ({ id: folder.id, name: folder.name, photos: visiblePhotos.filter((photo) => photo.folderId === folder.id) })).filter((folder) => folder.photos.length);
  const activePendingOrder = pendingOrder && !paymentOrders.some((order) => order.order_id === pendingOrder.id && order.communication) ? pendingOrder : null;
  const selectionOpen = review.gallery.selection_open;
  const favoritesEnabled = review.gallery.favorites_enabled;
  const checkoutPhotos = (activePendingOrder?.items ?? []).map((item) => {
    const currentPhoto = review.photos.find((photo) => photo.id === item.photo_id);
    return currentPhoto
      ? { ...currentPhoto, name: item.name, previewUrl: `/api${item.preview_url}` }
      : {
          id: item.photo_id,
          name: item.name,
          previewUrl: `/api${item.preview_url}`,
          folderId: "checkout",
          selected: true,
          favorited: false,
          purchaseState: "selected",
          commercialState: "selected" as const,
          width: null,
          height: null,
        };
  });
  function renderPhotoMarkers(photo: ReviewPhoto) {
    return <>
      {!["available", "selected"].includes(photo.commercialState) ? <span className="gallery-presentation-marker gallery-presentation-marker--status is-purchased">{photo.commercialState === "purchased" ? "Comprada" : photo.commercialState === "payment_reported" ? "Pagamento informado" : "Aguardando pagamento"}</span> : <button type="button" className="gallery-presentation-marker" aria-pressed={photo.selected} disabled={!selectionOpen} onClick={() => interaction(photo, "selection")}>{photo.selected ? "✓ Desmarcar" : "Selecionar"}</button>}
      {favoritesEnabled ? <button type="button" className="gallery-presentation-marker gallery-presentation-marker--favorite" aria-label={photo.favorited ? "Remover dos favoritos" : "Favoritar"} title={photo.favorited ? "Remover dos favoritos" : "Favoritar"} aria-pressed={photo.favorited} onClick={() => interaction(photo, "favorite")}>{photo.favorited ? "♥" : "♡"}</button> : null}
    </>;
  }
  function renderPhotoComments(photo: ReviewPhoto) {
    const photoComments = comments.filter((comment) => comment.photo_id === photo.id);
    return (
      <section className="gallery-photo-comments" aria-label={`Comentários de ${photo.name}`}>
        <h2>Comentários</h2>
        <form className="auth-form" onSubmit={(event) => addComment(event, photo.id)}>
          <label>
            Comentário sobre {photo.name}
            <input name="body" maxLength={2000} required />
          </label>
          <button type="submit" className="primary">Enviar comentário</button>
        </form>
        <ul className="photo-list">
          {photoComments.map((comment) => (
            <li key={comment.id}>
              {comment.body}
              <button type="button" className="link-button" onClick={() => removeComment(comment.id)}>Remover</button>
            </li>
          ))}
        </ul>
        {!photoComments.length ? <p className="form-message">Nenhum comentário nesta foto.</p> : null}
      </section>
    );
  }
  return (
    <main className="admin-shell">
      {!activePendingOrder ? <ClientCartLink count={cart.quantity} href="/library#cart" /> : null}
      {!review.gallery.selection_open && (
        <section className="admin-card gallery-reopening" aria-live="polite">
          <h2>Solicitar novo prazo para seleção das fotos</h2>
          <p>O prazo para novas seleções terminou e esta galeria está congelada. Você ainda pode consultar fotos, pedidos e pagamentos, mas não pode alterar ou finalizar a seleção.</p>
          {reopening?.status === "pending" ? <StatusBadge tone="warning">Reabertura solicitada</StatusBadge> : reopening?.status === "refused" ? <><StatusBadge tone="danger">Solicitação recusada</StatusBadge><button className="primary" type="button" disabled={paymentBusy === "reopening"} onClick={requestReopening}>Solicitar reabertura da galeria</button></> : <button className="primary" type="button" disabled={paymentBusy === "reopening"} onClick={requestReopening}>{paymentBusy === "reopening" ? "Solicitando…" : "Solicitar reabertura da galeria"}</button>}
        </section>
      )}
      {!activePendingOrder && review.gallery.selection_expires_at && review.gallery.selection_open && cart.quantity > 0 && (
        <p className="form-message">
          Seleções até{" "}
          {new Date(review.gallery.selection_expires_at).toLocaleDateString(
            "pt-BR",
          )}
        </p>
      )}
      {!activePendingOrder ? <><nav className="gallery-photo-filters" aria-label="Filtrar fotos">
        {filterOptions.map(({ value, label }) => (
          <button key={value} type="button" className={filter === value ? "selected" : ""} aria-pressed={filter === value} onClick={() => setFilter(value)}>
            {label}
            <span>{value === "all" ? reviewPhotos.length : counts[value] ?? 0}</span>
          </button>
        ))}
      </nav>
      {!visiblePhotos.length && <p className="notice">Nenhuma foto nesta categoria.</p>}
      <GalleryPresentation galleryName={review.gallery.name} context={review.gallery.message ? <p>{review.gallery.message}</p> : null} folders={(presentationFolders.length ? presentationFolders : [{ id: "authorized-photos", name: selectionReviewMode ? "Fotos selecionadas" : "Fotos liberadas", photos: visiblePhotos }]) as GalleryPresentationFolder<ReviewPhoto>[]} folderDisplayMode={review.gallery.folder_display_mode ?? "individual"} titleStyle={{ color: review.gallery.cover_title_color, fontFamily: galleryFontFamily(review.gallery.cover_title_font), fontSize: review.gallery.cover_title_size, position: review.gallery.cover_title_position }} emptyDetail={selectionReviewMode ? "Nenhuma foto permanece selecionada. Volte à galeria pública para escolher suas fotos." : "Nenhuma foto desta categoria está disponível neste momento."} showHero={false} showCopyrightProtectionDialog renderExpandedPhotoContent={review.gallery.comments_enabled ? renderPhotoComments : undefined} renderPhotoMarkers={renderPhotoMarkers} />
      {cart.quantity > 0 && review.gallery.selection_open ? <aside className="selection-summary selection-summary--floating" aria-live="polite" aria-label="Resumo da seleção">
        <div><span>Sua seleção</span><strong>{cart.quantity} foto{cart.quantity === 1 ? "" : "s"}</strong></div>
        <div className="selection-summary__commercial"><span>Total <strong>{cart.total_cents !== undefined ? (cart.total_cents / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" }) : "A calcular"}</strong></span>{cart.savings_cents ? <span className="selection-summary__savings">Você economiza {(cart.savings_cents / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}</span> : null}</div>
        {cart.parcels?.length ? <details><summary>Ver cálculo por faixas</summary><ul>{cart.parcels.map((parcel) => <li key={`${parcel.minimum_quantity}-${parcel.maximum_quantity ?? "mais"}`}>{parcel.quantity} × {(parcel.unit_price_cents / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" })} = {(parcel.subtotal_cents / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}</li>)}</ul></details> : null}
        {cart.pricing_error ? <p className="notice">{cart.pricing_error}</p> : null}
        <button type="button" className="primary" disabled={!review.gallery.selection_open || cart.total_cents === undefined || checkoutBusy} onClick={checkout}>{checkoutBusy ? "Preparando…" : "Continuar para o PIX"}</button>
      </aside> : null}</> : null}
      {activePendingOrder ? <section className="admin-card client-checkout-review" aria-live="polite"><GalleryPresentation galleryName="Revise suas fotos e faça o PIX" eyebrow="Conferência do pedido" modeLabel={<StatusBadge tone="warning">Aguardando pagamento</StatusBadge>} folders={[{ id: "checkout", name: "Fotos do pedido", photos: checkoutPhotos }]} folderDisplayMode="sequential" showHero={false} showCopyrightProtectionDialog renderExpandedPhotoContent={review.gallery.comments_enabled ? renderPhotoComments : undefined} renderPhotoMarkers={renderPhotoMarkers} /><div className="client-checkout-total"><span>{activePendingOrder.items?.length ?? 0} foto(s)</span><strong>{(activePendingOrder.total_cents / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}</strong>{activePendingOrder.price_rule?.savings_cents ? <span>Economia de {(activePendingOrder.price_rule.savings_cents / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}</span> : null}</div>{activePendingOrder.sales_message ? <p>{activePendingOrder.sales_message}</p> : null}{activePendingOrder.pix?.qr_png_data_url ? <img className="client-checkout-qr" src={activePendingOrder.pix.qr_png_data_url} alt="QR Code PIX do pedido" /> : null}{activePendingOrder.pix?.copy_paste ? <label className="client-checkout-pix">PIX copia e cola<textarea readOnly value={activePendingOrder.pix.copy_paste} /><button className="secondary" type="button" onClick={copyPix}>{pixCopied ? "Código copiado" : "Copiar código PIX"}</button></label> : <p className="notice">O fotógrafo ainda não configurou um código PIX para esta galeria.</p>}{activePendingOrder.pix?.instructions ? <p>{activePendingOrder.pix.instructions}</p> : null}<p>O pagamento estará sujeito a análise e você será informada após a conferência do fotógrafo.</p><button className="primary" type="button" disabled={paymentBusy === activePendingOrder.id} onClick={() => reportPayment(activePendingOrder.id)}>{paymentBusy === activePendingOrder.id ? "Informando…" : "Informar pagamento"}</button></section> : null}
      {paymentOrders.length > 0 && <section className="admin-card client-payment-orders" aria-live="polite"><h2>Acompanhamento do pagamento</h2>{paymentOrders.map((order) => {
        const status = order.communication?.status;
        const visualState = order.commercial_state === "purchased" || status === "confirmed" ? "purchased" : order.commercial_state === "payment_reported" || status === "pending_review" ? "payment-reported" : order.commercial_state === "cancelled" || status === "refused" ? "cancelled" : "awaiting-payment";
        return <article aria-label={`Pedido ${order.order_id}`} className={`upload-status client-order-resume client-order-resume--${visualState}`} key={order.order_id}>
          <strong>Pedido {order.order_id.slice(0, 8)} · R$ {(order.total_cents / 100).toFixed(2).replace(".", ",")}</strong>
          <StatusBadge tone={status === "confirmed" ? "success" : status === "pending_review" ? "warning" : "neutral"}>{status === "confirmed" ? "Pagamento confirmado" : status === "refused" ? "Pagamento não localizado" : status === "pending_review" ? "Pagamento informado" : "Aguardando pagamento"}</StatusBadge>
          {order.items?.length ? <div className="client-checkout-items">{order.items.map((item) => item.preview_url ? <figure key={item.photo_id}><img src={`/api${item.preview_url}`} alt={`Miniatura protegida de ${item.name}`} draggable={false} /><figcaption>{item.name}</figcaption></figure> : null)}</div> : null}
          {order.payment_status === "pending" && (!status || status === "refused") && <button className="primary" type="button" disabled={paymentBusy === order.order_id} onClick={() => reportPayment(order.order_id)}>{paymentBusy === order.order_id ? "Informando…" : "Informar pagamento"}</button>}
        </article>;
      })}</section>}
      {message && (
        <p className="form-message" role="status">
          {message}
        </p>
      )}
    </main>
  );
}
