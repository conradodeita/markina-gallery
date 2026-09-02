"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";

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
  width: number | null;
  height: number | null;
};
type ReleasedFolder = { id: string; name: string; position: number; photo_count: number };
type Comment = { id: string; photo_id: string; body: string };
type Cart = {
  quantity: number;
  total_cents?: number;
  base_total_cents?: number;
  savings_cents?: number;
  unit_price_cents?: number;
  tier?: { minimum_quantity: number; maximum_quantity: number | null };
  parcels?: Array<{ minimum_quantity: number; maximum_quantity: number | null; quantity: number; unit_price_cents: number; subtotal_cents: number }>;
  pricing_error?: string;
  items?: { id: string; name: string }[];
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
  communication: { id: string; status: "pending_review" | "confirmed" | "refused" } | null;
  notification: { status: "queued" | "processing" | "sent" | "failed"; last_error: string | null } | null;
};
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
  const [review, setReview] = useState<Review | null>(null);
  const [loadFailed, setLoadFailed] = useState(false);
  const [comments, setComments] = useState<Comment[]>([]);
  const [cart, setCart] = useState<Cart>({ quantity: 0 });
  const [pendingOrder, setPendingOrder] = useState<PendingOrder | null>(null);
  const [paymentOrders, setPaymentOrders] = useState<PaymentOrder[]>([]);
  const [releasedFolders, setReleasedFolders] = useState<ReleasedFolder[]>([]);
  const [activePhotoId, setActivePhotoId] = useState("");
  const [message, setMessage] = useState("");
  const [closedGallery, setClosedGallery] = useState<{ publicGalleryUrl: string | null } | null>(null);
  const [filter, setFilter] = useState<"all" | "nova" | "visualizada mas não comprada" | "já comprada">("all");
  const [checkoutBusy, setCheckoutBusy] = useState(false);
  const [paymentBusy, setPaymentBusy] = useState("");
  const [pixCopied, setPixCopied] = useState(false);
  const checkoutKey = useRef("");
  const paymentKeys = useRef<Record<string, string>>({});
  function load() {
    Promise.all([
      fetch(`/api/gallery/${galleryId}/review`, { credentials: "same-origin" }),
      fetch(`/api/gallery/${galleryId}/folders`, { credentials: "same-origin" }),
    ])
      .then(async ([response, foldersResponse]) => {
        if (!response.ok || !foldersResponse.ok) throw new Error();
        const [result, folderResult] = await Promise.all([response.json(), foldersResponse.json()]);
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
              width: photo.width,
              height: photo.height,
            }),
          ),
        });
        setLoadFailed(false);
        setReleasedFolders(folderResult.folders ?? []);
        setActivePhotoId((current) => current || result.photos[0]?.id || "");
      })
      .catch(() => {
        setReview(null);
        setLoadFailed(true);
      });
  }
  function loadComments() {
    fetch(`/api/gallery/${galleryId}/comments`, { credentials: "same-origin" })
      .then(async (response) => {
        if (!response.ok) throw new Error();
        setComments((await response.json()).comments);
      })
      .catch(() => setComments([]));
  }
  function loadCart() {
    fetch(`/api/gallery/${galleryId}/cart`, { credentials: "same-origin" })
      .then(async (response) => {
        if (!response.ok) throw new Error();
        const result = await response.json();
        setCart(typeof result.quantity === "number" ? result : { quantity: 0 });
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
  useEffect(() => {
    load();
    loadComments();
    loadCart();
    loadPaymentOrders();
  }, [galleryId]); // eslint-disable-line react-hooks/exhaustive-deps
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
      checkoutKey.current = "";
      if (response.headers.get("X-Markina-Gallery-Closed") === "true") {
        setClosedGallery({ publicGalleryUrl: response.headers.get("X-Markina-Public-Gallery-Url") });
        return;
      }
      load();
      loadCart();
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
  async function removeFromCart(photoId: string) {
    const response = await fetch(`/api/gallery/${galleryId}/photos/${photoId}/selection`, {
      method: "DELETE",
      credentials: "same-origin",
    });
    setMessage(response.ok ? "Foto removida do carrinho." : "Não foi possível remover esta foto do carrinho.");
    if (response.ok) {
      if (response.headers.get("X-Markina-Gallery-Closed") === "true") {
        setClosedGallery({ publicGalleryUrl: response.headers.get("X-Markina-Public-Gallery-Url") });
        return;
      }
      load();
      loadCart();
    }
  }
  async function addComment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const body = new FormData(event.currentTarget).get("body");
    const response = await fetch(
      `/api/gallery/${galleryId}/photos/${activePhotoId}/comments`,
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
      event.currentTarget.reset();
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
  if (!review.photos.length)
    return (
      <SystemState title="Nenhuma foto liberada ainda" detail="Quando o fotógrafo concluir uma rodada, ela aparecerá aqui." />
    );
  const activeComments = comments.filter(
    (comment) => comment.photo_id === activePhotoId,
  );
  const counts = review.photos.reduce(
    (result, photo) => ({ ...result, [photo.purchaseState]: (result[photo.purchaseState] ?? 0) + 1 }),
    {} as Record<string, number>,
  );
  const visiblePhotos = filter === "all" ? review.photos : review.photos.filter((photo) => photo.purchaseState === filter);
  const presentationFolders = releasedFolders.map((folder) => ({ id: folder.id, name: folder.name, photos: visiblePhotos.filter((photo) => photo.folderId === folder.id) })).filter((folder) => folder.photos.length);
  return (
    <main className="admin-shell">
      {!review.gallery.selection_open && (
        <p className="notice">
          O prazo para novas seleções terminou. Seu histórico continua
          disponível.
        </p>
      )}
      {review.gallery.selection_expires_at && review.gallery.selection_open && (
        <p className="form-message">
          Seleções até{" "}
          {new Date(review.gallery.selection_expires_at).toLocaleDateString(
            "pt-BR",
          )}
        </p>
      )}
      <nav className="gallery-photo-filters" aria-label="Filtrar fotos">
        {(["all", "nova", "visualizada mas não comprada", "já comprada"] as const).map((value) => (
          <button key={value} type="button" className={filter === value ? "selected" : ""} aria-pressed={filter === value} onClick={() => setFilter(value)}>
            {value === "all" ? "Todas" : value === "nova" ? "Novas fotos" : value === "visualizada mas não comprada" ? "Vistas, não compradas" : "Já compradas"}
            <span>{value === "all" ? review.photos.length : counts[value] ?? 0}</span>
          </button>
        ))}
      </nav>
      {!visiblePhotos.length && <p className="notice">Nenhuma foto nesta categoria.</p>}
      <GalleryPresentation galleryName={review.gallery.name} context={review.gallery.message ? <p>{review.gallery.message}</p> : null} coverUrl={review.gallery.cover_preview_url ? `/api${review.gallery.cover_preview_url}` : null} folders={(presentationFolders.length ? presentationFolders : [{ id: "authorized-photos", name: "Fotos liberadas", photos: visiblePhotos }]) as GalleryPresentationFolder<ReviewPhoto>[]} folderDisplayMode={review.gallery.folder_display_mode ?? "individual"} titleStyle={{ color: review.gallery.cover_title_color, fontFamily: galleryFontFamily(review.gallery.cover_title_font), fontSize: review.gallery.cover_title_size, position: review.gallery.cover_title_position }} emptyDetail="Nenhuma foto desta categoria está disponível neste momento." renderPhotoMarkers={(photo) => <>
        <StatusBadge tone={photo.purchaseState === "já comprada" ? "success" : photo.purchaseState === "visualizada mas não comprada" ? "warning" : "neutral"}>{photo.purchaseState}</StatusBadge>
        {photo.purchaseState === "já comprada" ? <span className="gallery-presentation-marker is-purchased">Comprada</span> : <button type="button" className="gallery-presentation-marker" aria-pressed={photo.selected} disabled={!review.gallery.selection_open} onClick={() => interaction(photo, "selection")}>{photo.selected ? "✓ Selecionada" : "Selecionar"}</button>}
        {review.gallery.favorites_enabled ? <button type="button" className="gallery-presentation-marker" aria-pressed={photo.favorited} onClick={() => interaction(photo, "favorite")}>{photo.favorited ? "★ Favorita" : "☆ Favoritar"}</button> : null}
      </>} />
      {cart.quantity > 0 ? <aside className="selection-summary selection-summary--floating" aria-live="polite" aria-label="Resumo da seleção">
        <div><span>Sua seleção</span><strong>{cart.quantity} foto{cart.quantity === 1 ? "" : "s"}</strong></div>
        <div className="selection-summary__commercial"><span>Total <strong>{cart.total_cents !== undefined ? (cart.total_cents / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" }) : "A calcular"}</strong></span>{cart.savings_cents ? <span className="selection-summary__savings">Você economiza {(cart.savings_cents / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}</span> : null}</div>
        {cart.items?.length ? <details><summary>Revisar seleção</summary><ul className="photo-list" aria-label="Fotos no carrinho">{cart.items.map((item) => <li key={item.id}>{item.name}<button type="button" className="link-button" onClick={() => removeFromCart(item.id)}>Remover do carrinho</button></li>)}</ul></details> : null}
        {cart.parcels?.length ? <details><summary>Ver cálculo por faixas</summary><ul>{cart.parcels.map((parcel) => <li key={`${parcel.minimum_quantity}-${parcel.maximum_quantity ?? "mais"}`}>{parcel.quantity} × {(parcel.unit_price_cents / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" })} = {(parcel.subtotal_cents / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}</li>)}</ul></details> : null}
        {cart.pricing_error ? <p className="notice">{cart.pricing_error}</p> : null}
        <button type="button" className="primary" disabled={!review.gallery.selection_open || cart.total_cents === undefined || checkoutBusy} onClick={checkout}>{checkoutBusy ? "Preparando…" : "Prosseguir"}</button>
      </aside> : null}
      {pendingOrder && !paymentOrders.some((order) => order.order_id === pendingOrder.id && order.communication) && <section className="admin-card client-checkout-review" aria-live="polite"><div className="section-heading"><div><p className="eyebrow">Conferência do pedido</p><h2>Revise suas fotos e faça o PIX</h2></div><StatusBadge tone="warning">Aguardando pagamento</StatusBadge></div>{pendingOrder.items?.length ? <div className="client-checkout-items">{pendingOrder.items.map((item) => <figure key={item.photo_id}><img src={`/api${item.preview_url}`} alt={`Miniatura protegida de ${item.name}`} draggable={false} /><figcaption><strong>{item.name}</strong><span>{(item.unit_price_cents / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}</span></figcaption></figure>)}</div> : null}<div className="client-checkout-total"><span>{pendingOrder.items?.length ?? 0} foto(s)</span><strong>{(pendingOrder.total_cents / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}</strong>{pendingOrder.price_rule?.savings_cents ? <span>Economia de {(pendingOrder.price_rule.savings_cents / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}</span> : null}</div>{pendingOrder.sales_message ? <p>{pendingOrder.sales_message}</p> : null}{pendingOrder.pix?.qr_png_data_url ? <img className="client-checkout-qr" src={pendingOrder.pix.qr_png_data_url} alt="QR Code PIX do pedido" /> : null}{pendingOrder.pix?.copy_paste ? <label className="client-checkout-pix">PIX copia e cola<textarea readOnly value={pendingOrder.pix.copy_paste} /><button className="secondary" type="button" onClick={copyPix}>{pixCopied ? "Código copiado" : "Copiar código PIX"}</button></label> : <p className="notice">O fotógrafo ainda não configurou um código PIX para esta galeria.</p>}{pendingOrder.pix?.instructions ? <p>{pendingOrder.pix.instructions}</p> : null}<p>O pagamento estará sujeito a análise e você será informada após a conferência do fotógrafo.</p><button className="primary" type="button" disabled={paymentBusy === pendingOrder.id} onClick={() => reportPayment(pendingOrder.id)}>{paymentBusy === pendingOrder.id ? "Informando…" : "Informar pagamento"}</button></section>}
      {paymentOrders.length > 0 && <section className="admin-card" aria-live="polite"><h2>Acompanhamento do pagamento</h2>{paymentOrders.map((order) => {
        const status = order.communication?.status;
        return <article className="upload-status" key={order.order_id}>
          <strong>Pedido {order.order_id.slice(0, 8)} · R$ {(order.total_cents / 100).toFixed(2).replace(".", ",")}</strong>
          <span>{status === "confirmed" ? "Pagamento confirmado" : status === "refused" ? "Pagamento não localizado" : status === "pending_review" ? "Pagamento informado · aguardando revisão" : "Pagamento ainda não comunicado"}</span>
          {order.notification?.status === "failed" && <span>A resposta por WhatsApp falhou. O status acima continua válido.</span>}
          {order.payment_status === "pending" && (!status || status === "refused") && <button className="primary" type="button" disabled={paymentBusy === order.order_id} onClick={() => reportPayment(order.order_id)}>{paymentBusy === order.order_id ? "Informando…" : "Informar pagamento"}</button>}
        </article>;
      })}</section>}
      {review.gallery.comments_enabled && (
        <section className="admin-card">
          <h2>Comentários</h2>
          <label>
            Foto
            <select
              value={activePhotoId}
              onChange={(event) => setActivePhotoId(event.target.value)}
            >
              {review.photos.map((photo) => (
                <option key={photo.id} value={photo.id}>
                  {photo.name}
                </option>
              ))}
            </select>
          </label>
          <form className="auth-form" onSubmit={addComment}>
            <label>
              Comentário
              <input name="body" maxLength={2000} required />
            </label>
            <button className="primary">Enviar comentário</button>
          </form>
          <ul className="photo-list">
            {activeComments.map((comment) => (
              <li key={comment.id}>
                {comment.body}
                <button
                  className="link-button"
                  onClick={() => removeComment(comment.id)}
                >
                  Remover
                </button>
              </li>
            ))}
          </ul>
          {!activeComments.length && (
            <p className="form-message">Nenhum comentário nesta foto.</p>
          )}
        </section>
      )}
      {message && (
        <p className="form-message" role="status">
          {message}
        </p>
      )}
    </main>
  );
}
