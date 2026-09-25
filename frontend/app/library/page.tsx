"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { MarkinaLink, PageHeading, StatusBadge, SystemState } from "../ui-kit";
import { EmptyState } from "../validation-ui";
import { SelectionDeadline } from "../selection-deadline";
import Link from "next/link";
import { GalleryCardPreview, galleryCoverUrl } from "../gallery-card-preview";

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
  cover_preview_url?: string | null;
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
const journeyStatus = {
  active: { label: "Acesso ativo", tone: "success" as const },
  pending_review: { label: "Aguardando liberação", tone: "warning" as const },
  blocked: { label: "Acesso bloqueado", tone: "neutral" as const },
  expired: { label: "Prazo expirado", tone: "warning" as const },
  origin_removed: { label: "Origem indisponível", tone: "warning" as const },
  unavailable: { label: "Indisponível", tone: "neutral" as const },
};

export default function LibraryPage() {
  const [journeys, setJourneys] = useState<Journey[] | null>(null);
  const [journeysFailed, setJourneysFailed] = useState(false);
  const [libraryRequest, setLibraryRequest] = useState(0);
  const refreshTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const revalidateLibrary = useCallback(() => {
    if (refreshTimer.current !== null) clearTimeout(refreshTimer.current);
    refreshTimer.current = setTimeout(() => setLibraryRequest((value) => value + 1), 50);
  }, []);

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
  }, [libraryRequest]);

  useEffect(() => {
    window.addEventListener("focus", revalidateLibrary);
    return () => { window.removeEventListener("focus", revalidateLibrary); if (refreshTimer.current !== null) clearTimeout(refreshTimer.current); };
  }, [revalidateLibrary]);

  useEffect(() => {
    const destination = window.location.hash === "#cart" ? "/library/cart" : window.location.hash === "#purchases" ? "/library/purchases" : null;
    if (destination) window.location.replace(destination);
  }, []);

  if (!journeys) return <SystemState tone="loading" title="Carregando sua biblioteca" detail="Consultando suas galerias e seleções." />;
  if (journeysFailed) return <main className="admin-shell"><h1>Biblioteca indisponível</h1><p className="intro">Não foi possível consultar suas galerias. Tente novamente.</p></main>;

  return (
    <main className="admin-shell library-shell">
      <PageHeading title="Galerias" />

      <section className="library-section" aria-labelledby="journey-library-title">
        <div className="section-heading"><h2 id="journey-library-title">Galerias</h2><StatusBadge>{journeys.length}</StatusBadge></div>
        {journeys.length ? <div className="library-card-grid">{journeys.map((journey) => {
          const status = journeyStatus[journey.status] ?? journeyStatus.unavailable;
          const latestOrder = journey.orders?.find((order) => order.commercial_state !== "awaiting_payment");
          const browse = journey.actions.continue_url ?? journey.actions.prepared_url ?? journey.actions.fallback_url ?? journey.browse_url;
          const primaryAction = browse ? { href: browse, label: "Ver fotos" } : latestOrder ? { href: "/library/purchases", label: "Ver compra" } : null;
          return (
            <article className={`library-card journey-card journey-card--${journey.status}`} key={journey.id}>
              {browse ? <Link href={browse} className="library-cover-link" aria-label={`Abrir galeria ${journey.name}`}><GalleryCardPreview src={galleryCoverUrl(journey.cover_preview_url)} name={journey.name} /></Link> : <GalleryCardPreview src={null} name={journey.name} />}
              <header><StatusBadge tone={status.tone}>{status.label}</StatusBadge></header>
              <strong>{journey.name}</strong>
              {journey.event_name ? <small>{journey.event_name}</small> : null}
              <SelectionDeadline expiresAt={journey.private_gallery?.selection_expires_at} onRevalidate={revalidateLibrary} />
              {latestOrder ? <StatusBadge tone={latestOrder.commercial_state === "purchased" ? "success" : latestOrder.commercial_state === "payment_reported" ? "warning" : "neutral"}>{latestOrder.commercial_state === "purchased" ? "Pagamento confirmado" : latestOrder.commercial_state === "payment_reported" ? "Pagamento informado" : "Pagamento não localizado"}</StatusBadge> : null}
              <div className="library-card-actions">
                {primaryAction ? <MarkinaLink href={primaryAction.href} prefetch>{primaryAction.label}</MarkinaLink> : <span>Indisponível</span>}
              </div>
            </article>
          );
        })}</div> : <EmptyState title="Nenhuma galeria disponível" detail="Links e convites autorizados aparecerão aqui como uma única jornada por evento." />}
      </section>

    </main>
  );
}
