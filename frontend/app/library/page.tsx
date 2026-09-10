"use client";

import { useEffect, useRef, useState } from "react";

import { MarkinaLink, PageHeading, StatusBadge, SurfaceCard, SystemState } from "../ui-kit";
import { EmptyState } from "../validation-ui";

type PublicGallery = {
  id: string;
  name: string;
  event_name: string;
  access_mode: "standard" | "invite_only" | "collective_protected";
  gallery_status: "active" | "pending_review";
  browse_url: string | null;
};
type PrivateGallery = {
  id: string;
  name: string;
  message: string;
  selection_expires_at: string | null;
  gallery_status: "active" | "expired" | "origin_removed";
  origin_removed: boolean;
  origin: { id: string; name: string; available: boolean; browse_url: string | null };
  folders: Array<{ id: string; name: string }>;
};
type Journey = {
  id: string;
  name: string;
  event_name: string;
  status: "active" | "pending_review" | "blocked" | "expired" | "origin_removed" | "unavailable";
  primary_surface: "public" | "private" | "unavailable";
  browse_url: string | null;
  public_gallery: PublicGallery | null;
  private_gallery: PrivateGallery | null;
  selection: {
    quantity: number;
    total_cents?: number;
    savings_cents?: number;
    pricing_error?: string;
  };
  orders?: Array<{ order_id: string; commercial_state: "awaiting_payment" | "payment_reported" | "purchased" | "cancelled"; total_cents: number }>;
  has_prepared_photos: boolean;
  actions: {
    continue_url: string | null;
    review_url: string | null;
    orders_url?: string | null;
    prepared_url: string | null;
    fallback_url: string | null;
  };
};
type Order = {
  id: string;
  gallery_name: string;
  parent_gallery_name: string;
  gallery_status_label: string;
  gallery_removed: boolean;
  confirmed_at: string | null;
  commercial_state?: "awaiting_payment" | "payment_reported" | "purchased" | "cancelled";
  communication_status?: "pending_review" | "confirmed" | "refused" | null;
  total_cents: number;
  items: Array<{ photo_id: string; name: string; preview_url: string | null; delivery_url: string | null; delivery_reference_available: boolean }>;
};

const journeyStatus = {
  active: { label: "Acesso ativo", tone: "success" as const },
  pending_review: { label: "Aguardando liberação", tone: "warning" as const },
  blocked: { label: "Acesso bloqueado", tone: "neutral" as const },
  expired: { label: "Prazo expirado", tone: "warning" as const },
  origin_removed: { label: "Origem indisponível", tone: "warning" as const },
  unavailable: { label: "Indisponível", tone: "neutral" as const },
};

function money(cents: number) {
  return (cents / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function orderState(order: Order) {
  return order.commercial_state ?? "purchased";
}

function orderLabel(order: Order) {
  const state = orderState(order);
  return state === "payment_reported" ? "Pagamento informado" : state === "cancelled" ? "Pagamento não localizado" : state === "awaiting_payment" ? "Aguardando pagamento" : "Comprado";
}

function LibraryOrderCard({ order }: { order: Order }) {
  const [open, setOpen] = useState(false);
  const [expandedPhoto, setExpandedPhoto] = useState<Order["items"][number] | null>(null);
  const dialog = useRef<HTMLDivElement>(null);
  const photos = order.items.filter((item) => item.preview_url);
  const state = orderState(order).replaceAll("_", "-");
  const gridId = `library-order-${order.id}-photos`;

  useEffect(() => {
    if (expandedPhoto) dialog.current?.focus();
  }, [expandedPhoto]);

  return (
    <article aria-label={`Pedido de ${order.gallery_name}`} className={`library-order library-order--${state}`}>
      <div className="library-order-summary"><strong>{order.gallery_name}</strong><small>{order.parent_gallery_name} · {order.gallery_status_label}</small><span>{order.items.length} foto(s) · {money(order.total_cents)}</span><StatusBadge tone={order.commercial_state === "purchased" || !order.commercial_state ? "success" : order.commercial_state === "payment_reported" ? "warning" : "neutral"}>{orderLabel(order)}</StatusBadge>{order.confirmed_at ? <time dateTime={order.confirmed_at}>Confirmada em {new Date(order.confirmed_at).toLocaleDateString("pt-BR")}</time> : null}</div>
      <button className="secondary" type="button" aria-expanded={open} aria-controls={gridId} onClick={() => setOpen((current) => !current)} disabled={!photos.length}>{open ? "Ocultar fotos" : `Ver fotos (${photos.length})`}</button>
      {open ? <div className="library-order-photo-grid" id={gridId} role="region" aria-label={`Fotos do pedido de ${order.gallery_name}`}>
        {photos.map((photo) => <figure key={photo.photo_id}>
          <button type="button" aria-label={`Ampliar prévia protegida de ${photo.name}`} onClick={() => setExpandedPhoto(photo)} onContextMenu={(event) => event.preventDefault()}>
            <img src={photo.preview_url!} alt={`Prévia protegida de ${photo.name}`} loading="lazy" draggable={false} />
          </button>
          <figcaption>{photo.name}</figcaption>
        </figure>)}
      </div> : null}
      {expandedPhoto ? <div className="library-photo-dialog-backdrop" role="presentation" onMouseDown={() => setExpandedPhoto(null)}>
        <div ref={dialog} className="library-photo-dialog" role="dialog" aria-modal="true" aria-label={`Prévia ampliada de ${expandedPhoto.name}`} tabIndex={-1} onMouseDown={(event) => event.stopPropagation()} onKeyDown={(event) => { if (event.key === "Escape") setExpandedPhoto(null); }}>
          <button type="button" className="library-photo-dialog-close" onClick={() => setExpandedPhoto(null)}>Fechar</button>
          <img src={expandedPhoto.preview_url!} alt={`Prévia protegida ampliada de ${expandedPhoto.name}`} draggable={false} onContextMenu={(event) => event.preventDefault()} />
          <strong>{expandedPhoto.name}</strong>
        </div>
      </div> : null}
    </article>
  );
}

export default function LibraryPage() {
  const [journeys, setJourneys] = useState<Journey[] | null>(null);
  const [orders, setOrders] = useState<Order[] | null>(null);
  const [journeysFailed, setJourneysFailed] = useState(false);
  const [ordersFailed, setOrdersFailed] = useState(false);
  const [ordersRequest, setOrdersRequest] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/library", { credentials: "same-origin", signal: controller.signal })
      .then(async (libraryResponse) => {
        if (!libraryResponse.ok) throw new Error();
        const library = await libraryResponse.json();
        setJourneys(library.journeys ?? []);
        setJourneysFailed(false);
      })
      .catch(() => {
        if (controller.signal.aborted) return;
        setJourneysFailed(true);
        setJourneys([]);
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/library/purchases", { credentials: "same-origin", signal: controller.signal })
      .then(async (purchasesResponse) => {
        if (!purchasesResponse.ok) throw new Error();
        const purchases = await purchasesResponse.json();
        setOrders(purchases.orders ?? []);
      })
      .catch(() => {
        if (controller.signal.aborted) return;
        setOrdersFailed(true);
        setOrders([]);
      });
    return () => controller.abort();
  }, [ordersRequest]);

  if (!journeys) return <SystemState tone="loading" title="Carregando sua biblioteca" detail="Consultando suas galerias e seleções." />;
  if (journeysFailed) return <main className="admin-shell"><h1>Biblioteca indisponível</h1><p className="intro">Não foi possível consultar suas galerias. Tente novamente.</p></main>;

  return (
    <main className="admin-shell library-shell">
      <PageHeading title="Minhas fotos" />

      <section className="library-section" aria-labelledby="journey-library-title">
        <div className="section-heading"><h2 id="journey-library-title">Galerias e seleções</h2><StatusBadge>{journeys.length}</StatusBadge></div>
        {journeys.length ? <div className="library-card-grid">{journeys.map((journey) => {
          const status = journeyStatus[journey.status] ?? journeyStatus.unavailable;
          const latestOrder = journey.orders?.[0];
          const primaryAction = journey.selection.quantity > 0 && journey.actions.review_url
            ? { href: `${journey.actions.review_url}?mode=review`, label: `Carrinho (${journey.selection.quantity})` }
            : latestOrder && journey.actions.orders_url
              ? { href: journey.actions.orders_url, label: "Ver pedido" }
            : journey.actions.continue_url
              ? { href: journey.actions.continue_url, label: "Ver fotos" }
              : journey.actions.prepared_url
                ? { href: journey.actions.prepared_url, label: "Ver fotos" }
                : journey.actions.fallback_url
                  ? { href: journey.actions.fallback_url, label: "Ver fotos" }
                  : null;
          return (
            <article className={`library-card journey-card journey-card--${journey.status}`} key={journey.id}>
              <header><StatusBadge tone={status.tone}>{status.label}</StatusBadge></header>
              <strong>{journey.name}</strong>
              {journey.event_name ? <small>{journey.event_name}</small> : null}
              {journey.selection.quantity > 0 ? <div className="journey-selection-summary" aria-label="Resumo da seleção"><span><strong>{journey.selection.quantity}</strong> foto(s) selecionada(s)</span>{typeof journey.selection.total_cents === "number" ? <span><strong>{money(journey.selection.total_cents)}</strong> no total</span> : null}{typeof journey.selection.savings_cents === "number" && journey.selection.savings_cents > 0 ? <small>Economia de {money(journey.selection.savings_cents)}</small> : null}</div> : null}
              {latestOrder ? <StatusBadge tone={latestOrder.commercial_state === "purchased" ? "success" : latestOrder.commercial_state === "payment_reported" ? "warning" : "neutral"}>{latestOrder.commercial_state === "purchased" ? "Comprado" : latestOrder.commercial_state === "payment_reported" ? "Pagamento informado" : latestOrder.commercial_state === "cancelled" ? "Pagamento não localizado" : "Aguardando pagamento"}</StatusBadge> : null}
              {journey.private_gallery?.selection_expires_at ? <small>Seleção até {new Date(journey.private_gallery.selection_expires_at).toLocaleDateString("pt-BR")}</small> : null}
              <div className="library-card-actions">
                {primaryAction ? <MarkinaLink href={primaryAction.href} prefetch>{primaryAction.label}</MarkinaLink> : <span>Indisponível</span>}
              </div>
            </article>
          );
        })}</div> : <EmptyState title="Nenhuma galeria disponível" detail="Links e convites autorizados aparecerão aqui como uma única jornada por evento." />}
      </section>

      <SurfaceCard className="client-order-history library-history" >
        <div className="section-heading"><h2>Pedidos</h2><StatusBadge>{orders?.length ?? 0}</StatusBadge></div>
        {ordersFailed ? <SystemState tone="error" title="Não foi possível carregar os pedidos" detail="Suas galerias continuam disponíveis. Tente carregar o histórico novamente." /> : orders === null ? <SystemState tone="loading" title="Carregando pedidos" detail="Buscando seu histórico comercial." /> : orders.length ? orders.map((order) => <LibraryOrderCard order={order} key={order.id} />) : <EmptyState title="Nenhum pedido" detail="" />}
        {ordersFailed ? <button type="button" className="secondary library-history-retry" onClick={() => { setOrders(null); setOrdersFailed(false); setOrdersRequest((request) => request + 1); }}>Tentar novamente</button> : null}
      </SurfaceCard>
    </main>
  );
}
