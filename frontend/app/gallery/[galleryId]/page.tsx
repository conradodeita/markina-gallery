"use client";

import { FormEvent, useEffect, useState } from "react";
import { useParams } from "next/navigation";

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
};
type ReleasedFolder = { id: string; name: string; position: number; photo_count: number };
type Comment = { id: string; photo_id: string; body: string };
type Cart = {
  quantity: number;
  total_cents?: number;
  unit_price_cents?: number;
  tier?: { minimum_quantity: number; maximum_quantity: number | null };
  items?: { id: string; name: string }[];
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
  };
  photos: ReviewPhoto[];
};

export default function GalleryPage() {
  const { galleryId } = useParams<{ galleryId: string }>();
  const [review, setReview] = useState<Review | null>(null);
  const [loadFailed, setLoadFailed] = useState(false);
  const [comments, setComments] = useState<Comment[]>([]);
  const [cart, setCart] = useState<Cart>({ quantity: 0 });
  const [pendingOrder, setPendingOrder] = useState<{ id: string; total_cents: number } | null>(null);
  const [paymentOrders, setPaymentOrders] = useState<PaymentOrder[]>([]);
  const [releasedFolders, setReleasedFolders] = useState<ReleasedFolder[]>([]);
  const [activePhotoId, setActivePhotoId] = useState("");
  const [message, setMessage] = useState("");
  const [closedGallery, setClosedGallery] = useState<{ publicGalleryUrl: string | null } | null>(null);
  const [filter, setFilter] = useState<"all" | "nova" | "visualizada mas não comprada" | "já comprada">("all");
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
            }) => ({
              id: photo.id,
              name: photo.name,
              folderId: photo.folder_id,
              previewUrl: `/api${photo.preview_url}`,
              selected: photo.selected,
              favorited: photo.favorited,
              purchaseState: photo.purchase_state,
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
      if (response.headers.get("X-Markina-Gallery-Closed") === "true") {
        setClosedGallery({ publicGalleryUrl: response.headers.get("X-Markina-Public-Gallery-Url") });
        return;
      }
      load();
      loadCart();
    }
  }
  async function checkout() {
    const idempotencyKey = globalThis.crypto?.randomUUID?.() ?? `checkout-${Date.now()}-${galleryId}`;
    const response = await fetch(`/api/gallery/${galleryId}/checkout`, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ idempotency_key: idempotencyKey }),
    });
    if (!response.ok) {
      setMessage("Não foi possível finalizar o pedido. Revise sua seleção e tente novamente.");
      return;
    }
    const order = await response.json();
    setPendingOrder({ id: order.id, total_cents: order.total_cents });
    setMessage("Pedido criado. O pagamento será confirmado manualmente pelo fotógrafo.");
    load();
    loadCart();
    loadPaymentOrders();
  }
  async function reportPayment(orderId: string) {
    const idempotencyKey = globalThis.crypto?.randomUUID?.() ?? `payment-report-${Date.now()}-${orderId}`;
    const response = await fetch(`/api/gallery/${galleryId}/orders/${orderId}/payment-communications`, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ idempotency_key: idempotencyKey }),
    });
    setMessage(response.ok ? "Pagamento comunicado. Aguarde a revisão do fotógrafo." : "Não foi possível comunicar o pagamento.");
    if (response.ok) {
      setPendingOrder(null);
      loadPaymentOrders();
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
  const selectedPhotos = review.photos.filter((photo) => photo.selected);
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
      <GalleryPresentation galleryName={review.gallery.name} context={review.gallery.message ? <p>{review.gallery.message}</p> : null} coverUrl={review.gallery.cover_preview_url ? `/api${review.gallery.cover_preview_url}` : null} folders={(presentationFolders.length ? presentationFolders : [{ id: "authorized-photos", name: "Fotos liberadas", photos: visiblePhotos }]) as GalleryPresentationFolder<ReviewPhoto>[]} emptyDetail="Nenhuma foto desta categoria está disponível neste momento." renderPhotoDetails={(photo) => <>
            <StatusBadge
              tone={
                photo.purchaseState === "já comprada"
                  ? "success"
                  : photo.purchaseState === "visualizada mas não comprada"
                    ? "warning"
                    : "neutral"
              }
            >
              {photo.purchaseState}
            </StatusBadge>
            <small>
              {photo.selected
                ? "Selecionada"
                : photo.favorited
                  ? "Favorita"
                  : "Disponível para revisão"}
            </small>
            <div className="gallery-presentation-actions">
              <button
                type="button"
                className="secondary"
                disabled={
                  !review.gallery.selection_open ||
                  photo.purchaseState === "já comprada"
                }
                onClick={() => interaction(photo, "selection")}
              >
                {photo.selected ? "Desfazer" : "Selecionar"}
              </button>
              {review.gallery.favorites_enabled && (
                <button
                  type="button"
                  className="secondary"
                  aria-pressed={photo.favorited}
                  onClick={() => interaction(photo, "favorite")}
                >
                  {photo.favorited ? "★ Favorita" : "☆ Favoritar"}
                </button>
              )}
            </div>
          </>} />
      <section className="selection-summary" aria-live="polite" aria-label="Resumo da seleção">
        <div><span>Sua seleção</span><strong>{selectedPhotos.length} foto{selectedPhotos.length === 1 ? "" : "s"}</strong></div>
        <p>{review.gallery.selection_open ? "Use Selecionar em cada prévia. Suas escolhas ficam salvas nesta galeria." : "O prazo de novas seleções terminou; suas escolhas continuam identificadas abaixo."}</p>
        {cart.total_cents !== undefined && <p>Faixa aplicada: R$ {(cart.unit_price_cents! / 100).toFixed(2).replace(".", ",")} por foto · total estimado R$ {(cart.total_cents / 100).toFixed(2).replace(".", ",")}.</p>}
        {cart.items?.length ? <ul className="photo-list" aria-label="Fotos no carrinho">{cart.items.map((item) => <li key={item.id}>{item.name}<button type="button" className="link-button" onClick={() => removeFromCart(item.id)}>Remover do carrinho</button></li>)}</ul> : null}
        <button type="button" className="primary" disabled={!review.gallery.selection_open || cart.quantity === 0} onClick={checkout}>Finalizar {cart.quantity} foto{cart.quantity === 1 ? "" : "s"} por PIX</button>
      </section>
      {pendingOrder && !paymentOrders.some((order) => order.order_id === pendingOrder.id) && <section className="admin-card" aria-live="polite"><h2>Pedido pendente de confirmação</h2><p>Pedido criado no valor de R$ {(pendingOrder.total_cents / 100).toFixed(2).replace(".", ",")}.</p><p>Envie o PIX conforme as instruções do fotógrafo. A confirmação não é automática.</p><button className="primary" type="button" onClick={() => reportPayment(pendingOrder.id)}>Já fiz o PIX</button></section>}
      {paymentOrders.length > 0 && <section className="admin-card" aria-live="polite"><h2>Acompanhamento do pagamento</h2>{paymentOrders.map((order) => {
        const status = order.communication?.status;
        return <article className="upload-status" key={order.order_id}>
          <strong>Pedido {order.order_id.slice(0, 8)} · R$ {(order.total_cents / 100).toFixed(2).replace(".", ",")}</strong>
          <span>{status === "confirmed" ? "Pagamento confirmado" : status === "refused" ? "Pagamento não localizado" : status === "pending_review" ? "Pagamento informado · aguardando revisão" : "Pagamento ainda não comunicado"}</span>
          {order.notification?.status === "failed" && <span>A resposta por WhatsApp falhou. O status acima continua válido.</span>}
          {order.payment_status === "pending" && (!status || status === "refused") && <button className="primary" type="button" onClick={() => reportPayment(order.order_id)}>Já fiz o PIX</button>}
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
