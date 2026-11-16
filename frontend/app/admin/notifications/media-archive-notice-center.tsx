"use client";

import { useState } from "react";
import Link from "next/link";
import { MarkinaButton, StatusBadge, SurfaceCard, SystemState } from "../../ui-kit";
import styles from "./media-archive-notice-center.module.css";

export type MediaArchiveNotice = {
  id: string;
  notice_type: string;
  title: string;
  body: string;
  cycle_id: string;
  folder_id: string;
  parent_gallery_id: string;
  deadline_at: string | null;
  created_at: string;
  read_at: string | null;
  superseded_at: string | null;
};

type NoticePayload = { items: MediaArchiveNotice[]; unread_count: number; detail?: unknown };

function dateLabel(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Data indisponível" : date.toLocaleString("pt-BR");
}

async function responseJson<T>(response: Response): Promise<T> {
  const payload = await response.json().catch(() => null) as { detail?: unknown } | null;
  if (!response.ok) {
    throw new Error(typeof payload?.detail === "string" ? payload.detail : "Não foi possível consultar os avisos.");
  }
  return payload as T;
}

export function MediaArchiveNoticeCenter() {
  const [items, setItems] = useState<MediaArchiveNotice[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loaded, setLoaded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState("");

  async function load() {
    if (loading) return;
    setLoading(true);
    setError("");
    try {
      const result = await responseJson<NoticePayload>(await fetch(
        "/api/admin/media-archive/notices?limit=50",
        { credentials: "same-origin", cache: "no-store" },
      ));
      setItems(Array.isArray(result.items) ? result.items : []);
      setUnreadCount(Number.isSafeInteger(result.unread_count) ? result.unread_count : 0);
      setLoaded(true);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Não foi possível consultar os avisos.");
    } finally {
      setLoading(false);
    }
  }

  async function markRead(id: string) {
    if (busyId) return;
    const wasUnreadCurrent = items.some((item) => item.id === id && !item.read_at && !item.superseded_at);
    setBusyId(id);
    setError("");
    try {
      const result = await responseJson<{ id: string; read_at: string | null }>(await fetch(
        `/api/admin/media-archive/notices/${encodeURIComponent(id)}/read`,
        { method: "POST", credentials: "same-origin", cache: "no-store" },
      ));
      setItems((current) => current.map((item) => item.id === id
        ? { ...item, read_at: result.read_at }
        : item));
      if (wasUnreadCurrent) setUnreadCount((current) => Math.max(0, current - 1));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Não foi possível marcar o aviso como lido.");
    } finally {
      setBusyId(null);
    }
  }

  return <SurfaceCard className={styles.card}>
    <div className={styles.heading}>
      <div>
        <p className="eyebrow">Arquivo frio</p>
        <h2>Avisos ao fotógrafo</h2>
        <p>Consulte prazos, bloqueios por pedido e o andamento das transferências.</p>
      </div>
      {loaded && unreadCount > 0 ? <StatusBadge tone="warning">{unreadCount} não lido(s)</StatusBadge> : null}
      <MarkinaButton type="button" disabled={loading} onClick={() => void load()}>
        {loading ? "Consultando…" : loaded ? "Atualizar avisos" : "Ver avisos"}
      </MarkinaButton>
    </div>

    {error ? <p className={styles.error} role="alert">{error}</p> : null}
    {loading && !loaded ? <SystemState tone="loading" title="Consultando avisos" detail="Buscando atualizações do arquivo frio da sua conta." /> : null}
    {loaded && items.length === 0 ? <SystemState title="Nenhum aviso de arquivo frio" detail="Quando houver um prazo, bloqueio ou mudança de transferência, o aviso aparecerá aqui." /> : null}
    {loaded && items.length > 0 ? <ol className={styles.list} aria-label="Avisos de arquivo frio">
      {items.map((item) => (
        <li className={styles.item} key={item.id}>
          <div className={styles.itemHeading}>
            <h3>{item.title}</h3>
            {item.superseded_at
              ? <StatusBadge tone="neutral">Prazo alterado</StatusBadge>
              : item.read_at
                ? <StatusBadge tone="neutral">Lido</StatusBadge>
                : <StatusBadge tone="warning">Novo</StatusBadge>}
          </div>
          <p>{item.body}</p>
          {item.deadline_at && !item.superseded_at
            ? <p className={styles.deadline}>Elegível para arquivo após {dateLabel(item.deadline_at)}.</p>
            : null}
          {item.superseded_at ? <p className={styles.deadline}>A reabertura mais recente alterou a data deste aviso.</p> : null}
          <div className={styles.actions}>
            <time dateTime={item.created_at}>{dateLabel(item.created_at)}</time>
            <Link href={`/admin/galleries/sources/${encodeURIComponent(item.parent_gallery_id)}`}>Abrir galeria</Link>
            {item.read_at ? null : <MarkinaButton
              type="button"
              disabled={busyId !== null}
              onClick={() => void markRead(item.id)}
            >{busyId === item.id ? "Salvando…" : "Marcar como lido"}</MarkinaButton>}
          </div>
        </li>
      ))}
    </ol> : null}
  </SurfaceCard>;
}
