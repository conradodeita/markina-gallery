"use client";
import { useEffect, useRef, useState } from "react";
import { StatusBadge } from "../ui-kit";
import { PurchasePreview } from "../purchase-preview";
export type Order = {
  id: string;
  gallery_name: string;
  parent_gallery_name: string;
  gallery_status_label: string;
  gallery_removed: boolean;
  communicated_at?: string | null;
  confirmed_at: string | null;
  commercial_state?: "awaiting_payment" | "payment_reported" | "purchased" | "cancelled";
  communication_status?: "pending_review" | "confirmed" | "refused" | null;
  total_cents: number;
  items: Array<{ photo_id: string; name: string; preview_url: string | null; delivery_url: string | null; delivery_reference_available: boolean }>;
};

function money(cents: number) {
  return (cents / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function orderState(order: Order) {
  return order.commercial_state ?? "purchased";
}

function orderLabel(order: Order) {
  const state = orderState(order);
  return state === "payment_reported" ? "Pagamento informado" : state === "cancelled" ? "Pagamento não localizado" : state === "awaiting_payment" ? "Aguardando pagamento" : "Pagamento confirmado";
}

export function LibraryOrderCard({ order }: { order: Order }) {
  const [open, setOpen] = useState(false);
  const [expandedPhoto, setExpandedPhoto] = useState<Order["items"][number] | null>(null);
  const dialog = useRef<HTMLDivElement>(null);
  const previewTrigger = useRef<HTMLButtonElement | null>(null);
  const photos = order.items;
  const state = orderState(order).replaceAll("_", "-");
  const activityAt = order.confirmed_at ?? order.communicated_at;
  const activityLabel = order.confirmed_at ? "Confirmada" : "Informada";
  const gridId = `library-order-${order.id}-photos`;

  useEffect(() => {
    if (!expandedPhoto) return;
    const trigger = previewTrigger.current;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    dialog.current?.querySelector<HTMLButtonElement>("button")?.focus();
    return () => { document.body.style.overflow = previousOverflow; trigger?.focus(); };
  }, [expandedPhoto]);

  return (
    <article aria-label={`Compra de ${order.gallery_name}`} className={`library-order library-order--${state}`}>
      <div className="library-order-summary"><strong>{order.gallery_name}</strong><small>{order.parent_gallery_name}{order.gallery_removed ? " · Galeria removida" : ""}</small><span>{order.items.length} foto(s) · {money(order.total_cents)}</span><StatusBadge tone={order.commercial_state === "purchased" || !order.commercial_state ? "success" : order.commercial_state === "payment_reported" ? "warning" : "neutral"}>{orderLabel(order)}</StatusBadge>{activityAt ? <time dateTime={activityAt}>{activityLabel} em {new Date(activityAt).toLocaleDateString("pt-BR")}</time> : null}</div>
      <button className="secondary" type="button" aria-expanded={open} aria-controls={gridId} onClick={() => setOpen((current) => !current)} disabled={!photos.length}>{open ? "Ocultar fotos" : `Ver fotos (${photos.length})`}</button>
      {open ? <div className="library-order-photo-grid" id={gridId} role="region" aria-label={`Fotos da compra de ${order.gallery_name}`}>
        {photos.map((photo) => <figure key={photo.photo_id}>
          <button type="button" aria-label={`Ampliar prévia protegida de ${photo.name}`} onClick={(event) => { previewTrigger.current = event.currentTarget; setExpandedPhoto(photo); }} onContextMenu={(event) => event.preventDefault()}>
            <PurchasePreview path={photo.preview_url} name={photo.name} />
          </button>
          <figcaption>{photo.name}</figcaption>
        </figure>)}
      </div> : null}
      {expandedPhoto ? <div className="library-photo-dialog-backdrop" role="presentation" onMouseDown={() => setExpandedPhoto(null)}>
        <div ref={dialog} className="library-photo-dialog" role="dialog" aria-modal="true" aria-label={`Prévia ampliada de ${expandedPhoto.name}`} tabIndex={-1} onMouseDown={(event) => event.stopPropagation()} onKeyDown={(event) => { if (event.key === "Escape") setExpandedPhoto(null); if (event.key === "Tab") { event.preventDefault(); dialog.current?.querySelector<HTMLButtonElement>("button")?.focus(); } }}>
          <button type="button" className="library-photo-dialog-close" onClick={() => setExpandedPhoto(null)}>Fechar</button>
          <PurchasePreview key={expandedPhoto.photo_id} path={expandedPhoto.preview_url} name={expandedPhoto.name} expanded />
          <strong>{expandedPhoto.name}</strong>
        </div>
      </div> : null}
    </article>
  );
}
