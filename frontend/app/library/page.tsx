"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";

import { MarkinaButton, MarkinaLink, StatusBadge, SystemState } from "../ui-kit";
import { GalleryCardPreview, galleryCoverUrl } from "../gallery-card-preview";
import { SelectionDeadline } from "../selection-deadline";
import styles from "./library.module.css";

type Journey = {
  id: string;
  name: string;
  event_name: string;
  status: "active" | "pending_review" | "blocked" | "expired" | "origin_removed" | "unavailable";
  browse_url: string | null;
  cover_preview_url?: string | null;
  selection_deadlines?: Array<{ folder_id: string; folder_name: string; expires_at: string }>;
  orders?: Array<{ commercial_state: "awaiting_payment" | "payment_reported" | "purchased" | "selection_finalized" | "cancelled" }>;
  actions: {
    continue_url: string | null;
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

const galleryFilters = [
  { value: "all", label: "Todas" },
  { value: "active", label: "Ativas" },
  { value: "expired", label: "Expiradas" },
] as const;

function JourneyCard({ journey, hidden, revalidateLibrary }: { journey: Journey; hidden: boolean; revalidateLibrary: () => void }) {
  const status = journeyStatus[journey.status] ?? journeyStatus.unavailable;
  const latestOrder = journey.orders?.find((order) => order.commercial_state !== "awaiting_payment");
  const browse = journey.actions.continue_url ?? journey.actions.prepared_url ?? journey.actions.fallback_url ?? journey.browse_url;
  const primaryAction = browse ? { href: browse, label: "Ver fotos" } : latestOrder ? { href: "/library/purchases", label: latestOrder.commercial_state === "selection_finalized" ? "Ver seleção" : "Ver compra" } : null;
  const deadlines = journey.selection_deadlines ?? [];
  return (
    <article className={styles.card} hidden={hidden}>
      <div className={styles.cover}>
        {browse ? <Link href={browse} aria-label={`Abrir galeria ${journey.name}`}><GalleryCardPreview src={galleryCoverUrl(journey.cover_preview_url)} name={journey.name} protectedPhoto /></Link> : <GalleryCardPreview src={null} name={journey.name} />}
        <StatusBadge className={styles.status} tone={status.tone}>{status.label}</StatusBadge>
      </div>
      <div className={styles.details}>
        <h2>{journey.name}</h2>
        {journey.event_name ? <p>{journey.event_name}</p> : null}
        {latestOrder ? <StatusBadge tone={latestOrder.commercial_state === "purchased" ? "success" : latestOrder.commercial_state === "payment_reported" ? "warning" : "neutral"}>{latestOrder.commercial_state === "selection_finalized" ? "Seleção finalizada" : latestOrder.commercial_state === "purchased" ? "Pagamento confirmado" : latestOrder.commercial_state === "payment_reported" ? "Pagamento informado" : "Pagamento não localizado"}</StatusBadge> : null}
        {deadlines.length ? <section className={styles.deadlines} aria-label={"Prazos de seleção: " + journey.name}>
          <h3>Prazo para novas seleções</h3>
          {deadlines.map((deadline) => <div
            className={styles.deadline}
            key={deadline.folder_id}
            role="group"
            aria-label={"Prazo na pasta " + deadline.folder_name}
          >
            <strong>{deadline.folder_name}</strong>
            <SelectionDeadline
              expiresAt={deadline.expires_at}
                onRevalidate={revalidateLibrary}
            />
          </div>)}
        </section> : null}
        <div className={styles.actions}>
          {primaryAction ? <MarkinaLink href={primaryAction.href} prefetch>{primaryAction.label}</MarkinaLink> : <p>Indisponível</p>}
        </div>
      </div>
    </article>
  );
}

export default function LibraryPage() {
  const [journeys, setJourneys] = useState<Journey[] | null>(null);
  const [journeysFailed, setJourneysFailed] = useState(false);
  const [libraryRequest, setLibraryRequest] = useState(0);
  const [filter, setFilter] = useState<(typeof galleryFilters)[number]["value"]>("all");
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
        if (controller.signal.aborted) return;
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

  const includesJourney = (journey: Journey) => filter === "all" || journey.status === filter;
  const hasVisibleJourneys = journeys?.some(includesJourney);

  return (
    <div className={styles.library}>
      <header className={styles.heading}>
        <h1>Suas galerias</h1>
        <p>Acesse seus ensaios e retome suas seleções de fotos.</p>
      </header>

      <section className={styles.content} aria-label="Galerias">
        {journeysFailed ? <div className={styles.error}>
          <SystemState tone="error" title="Biblioteca indisponível" detail="Não foi possível consultar suas galerias." />
          <MarkinaButton type="button" variant="secondary" onClick={() => {
            setJourneysFailed(false);
            setJourneys(null);
            revalidateLibrary();
          }}>Tentar novamente</MarkinaButton>
        </div> : !journeys ? <SystemState tone="loading" title="Carregando sua biblioteca" detail="Consultando suas galerias e seleções." /> : journeys.length === 0
          ? <SystemState title="Nenhuma galeria disponível" detail="Links e convites autorizados aparecerão aqui." />
          : <>
          <div className={styles.filters} role="group" aria-label="Filtrar galerias">
            {galleryFilters.map(({ value, label }) => <button key={value} type="button" aria-pressed={filter === value} onClick={() => setFilter(value)}>
              {label}{value === "all" ? ` (${journeys.length})` : ""}
            </button>)}
          </div>
          <div className={styles.grid} hidden={!hasVisibleJourneys}>
            {journeys.map((journey) => (
              <JourneyCard key={journey.id} journey={journey} hidden={!includesJourney(journey)} revalidateLibrary={revalidateLibrary} />
            ))}
          </div>
          {hasVisibleJourneys ? null : <SystemState title="Nenhuma galeria neste filtro" detail="Selecione Todas para ver as galerias disponíveis." />}
        </>}
      </section>

    </div>
  );
}
