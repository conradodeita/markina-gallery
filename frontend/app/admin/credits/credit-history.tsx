"use client";

import { useEffect, useRef, useState } from "react";

import { MarkinaButton, StatusBadge, SystemState } from "../../ui-kit";
import styles from "./credit-history.module.css";

export type HistoryEntry = {
  id: string;
  type: string;
  delta: number;
  source_reference: string | null;
  description: string | null;
  created_at: string;
  photo_count?: number;
  folder_id?: string | null;
  gallery_name?: string | null;
  first_at?: string;
  last_at?: string;
  folder_unidentified?: boolean;
  related_folder_name?: string | null;
};

export type HistoryPage = { items: HistoryEntry[]; has_more: boolean; as_of?: string };

function movementLabel(type: string) {
  return {
    owner_grant: "Créditos concedidos", grant_revocation: "Créditos revogados",
    purchase: "Compra de créditos", purchase_reversal: "Estorno de compra",
    upload_consumption: "Upload de foto", archive_recovery: "Recuperação de arquivo frio",
    correction: "Correção de saldo",
  }[type] ?? "Movimentação de créditos";
}

function dateLabel(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Data indisponível" : date.toLocaleString("pt-BR");
}

async function readPage(endpoint: string, limit: number, offset: number, asOf: string | undefined, signal: AbortSignal) {
  const query = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  if (asOf) query.set("as_of", asOf);
  const response = await fetch(`${endpoint}?${query}`, { credentials: "same-origin", cache: "no-store", signal });
  const payload = await response.json().catch(() => null) as HistoryPage | null;
  if (!response.ok || !payload || !Array.isArray(payload.items) || typeof payload.has_more !== "boolean") {
    throw new Error("Não foi possível consultar as movimentações.");
  }
  return payload;
}

function useHistoryPage(endpoint: string, limit: number, initialPage?: HistoryPage) {
  const [page, setPage] = useState<HistoryPage>(initialPage ?? { items: [], has_more: false });
  const [state, setState] = useState<"loading" | "ready" | "failed">(initialPage ? "ready" : "loading");
  const [moreState, setMoreState] = useState<"idle" | "loading" | "failed">("idle");
  const generation = useRef(0);
  const moreController = useRef<AbortController | null>(null);
  useEffect(() => {
    const current = ++generation.current;
    const controller = new AbortController();
    if (!initialPage) {
      readPage(endpoint, limit, 0, undefined, controller.signal).then((result) => {
        if (controller.signal.aborted || current !== generation.current) return;
        setPage(result);
        setState("ready");
      }).catch(() => {
        if (!controller.signal.aborted && current === generation.current) setState("failed");
      });
    }
    return () => { controller.abort(); moreController.current?.abort(); };
  }, [endpoint, limit, initialPage]);

  async function loadMore() {
    if (moreState === "loading") return;
    const current = generation.current;
    const controller = new AbortController();
    moreController.current = controller;
    setMoreState("loading");
    try {
      const result = await readPage(endpoint, limit, page.items.length, page.as_of, controller.signal);
      if (controller.signal.aborted || current !== generation.current) return;
      setPage((previous) => {
        const seen = new Set(previous.items.map((item) => item.id));
        return { ...result, items: [...previous.items, ...result.items.filter((item) => !seen.has(item.id))] };
      });
      setMoreState("idle");
    } catch {
      if (!controller.signal.aborted && current === generation.current) setMoreState("failed");
    }
  }
  return { page, state, moreState, loadMore };
}

function Amount({ value }: { value: number }) {
  return <strong className={value < 0 ? styles.debit : styles.credit}>
    {value > 0 ? "+" : ""}{new Intl.NumberFormat("pt-BR").format(value)}
  </strong>;
}

function HistoryRow({ item }: { item: HistoryEntry }) {
  const isFolder = item.type === "folder_upload" && Boolean(item.folder_id);
  const isRecovery = item.type === "archive_recovery";
  return <li className={styles.row}>
    <div className={styles.info}>
      <strong>{isFolder ? `Uploads · ${item.description || "Pasta removida"}`
        : isRecovery ? `Recuperação · ${item.related_folder_name || item.description || "Pasta arquivada"}`
          : item.description || movementLabel(item.type)}</strong>
      {isFolder ? <>
        {item.gallery_name ? <span>{item.gallery_name}</span> : null}
        <span className={styles.photoCount}>{new Intl.NumberFormat("pt-BR").format(item.photo_count ?? 0)} {(item.photo_count ?? 0) === 1 ? "foto cobrada" : "fotos cobradas"}</span>
        <span>Último envio: <time dateTime={item.created_at}>{dateLabel(item.created_at)}</time></span>
      </> : <span>{movementLabel(item.type)} · <time dateTime={item.created_at}>{dateLabel(item.created_at)}</time></span>}
      {item.source_reference ? <small className={styles.reference}>{isFolder ? "Referência da pasta" : "Referência"}: {item.source_reference}</small> : null}
    </div>
    <div className={styles.amount}><Amount value={item.delta} /><small>créditos</small></div>
  </li>;
}

type Props = { endpoint: string; title?: string; label?: string; initialPage?: HistoryPage; refreshKey?: string; level?: 2 | 3; className?: string };

function HistoryContent({ endpoint, title = "Histórico recente", label = "Histórico de créditos", initialPage, level = 2, className = "" }: Props) {
  const { page, state, moreState, loadMore } = useHistoryPage(endpoint, 30, initialPage);
  const Heading = level === 3 ? "h3" : "h2";
  const summaries = page.items.filter((item) => item.type !== "upload_consumption");
  const hasIndividualLegacy = summaries.length !== page.items.length;
  return <section className={`${styles.section} ${className}`} aria-label={label}>
    <div className={styles.heading}><div><p className="eyebrow">Movimentações por pasta</p><Heading>{title}</Heading></div>
      {state === "ready" ? <StatusBadge>{summaries.length} {summaries.length === 1 ? "resumo exibido" : "resumos exibidos"}</StatusBadge> : null}</div>
    {state === "loading" ? <SystemState tone="loading" title="Consultando movimentações" detail="Preparando os resumos por pasta." />
      : state === "failed" ? <SystemState tone="error" title="Histórico indisponível" detail="Não foi possível consultar as movimentações. O saldo não foi alterado." />
        : page.items.length ? <>
          {hasIndividualLegacy ? <SystemState title="Consumos anteriores preservados"
            detail="Há consumos anteriores sem pasta identificável. Os registros individuais permanecem preservados para rastreabilidade interna." /> : null}
          {summaries.length ? <ol className={styles.list}>{summaries.map((item) => <HistoryRow key={item.id} item={item} />)}</ol> : null}
          {page.has_more ? <MarkinaButton type="button" variant="secondary" disabled={moreState === "loading"}
            onClick={() => void loadMore()}>{moreState === "loading" ? "Carregando…" : "Carregar mais movimentações"}</MarkinaButton> : null}
          {moreState === "failed" ? <p role="alert">Não foi possível carregar mais movimentações. Tente novamente.</p> : null}
        </> : <SystemState title="Nenhuma movimentação" detail="Compras, concessões e consumos aparecerão aqui." />}
  </section>;
}

export default function CreditHistory(props: Props) {
  // Troca de tenant ou refresh invalida páginas e requisições anteriores.
  return <HistoryContent key={`${props.endpoint}:${props.refreshKey ?? props.initialPage?.as_of ?? ""}`} {...props} />;
}
