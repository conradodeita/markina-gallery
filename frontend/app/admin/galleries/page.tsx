"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

type PrivateGallery = { id: string; name: string; cover_preview_url: string | null; frozen: boolean; blocked: boolean; payment_pending: boolean; selection_in_progress: boolean };
type SourceGallery = { id: string; name: string; event_name: string; cover_preview_url: string | null; private_gallery_count: number; registration_count: number; frozen_gallery_count: number };

export default function GalleriesPage() {
  const [view, setView] = useState<"sources" | "private">("sources");
  const [tab, setTab] = useState<"active" | "frozen">("active");
  const [query, setQuery] = useState("");
  const [state, setState] = useState("");
  const [privateGalleries, setPrivateGalleries] = useState<PrivateGallery[]>([]);
  const [sources, setSources] = useState<SourceGallery[]>([]);
  const [failed, setFailed] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const path = view === "sources" ? "/api/admin/parent-galleries/overview" : "/api/admin/derived-galleries";
    const params = new URLSearchParams(view === "sources" ? {} : { tab });
    if (query) params.set("query", query);
    if (view === "private" && state) params.set("state", state);
    queueMicrotask(() => setLoading(true));
    fetch(`${path}?${params}`, { credentials: "same-origin" })
      .then(async (response) => {
        if (!response.ok) throw new Error("Falha ao carregar galerias");
        const data = await response.json();
        if (view === "sources") setSources(data.parent_galleries);
        else setPrivateGalleries(data.galleries);
        setFailed(false);
      })
      .catch(() => setFailed(true))
      .finally(() => setLoading(false));
  }, [query, state, tab, view]);

  const empty = view === "sources" ? !sources.length : !privateGalleries.length;
  return (
    <main className="admin-shell">
      <div className="section-heading gallery-list-heading">
        <div><p className="eyebrow">Markina Gallery · Fotógrafo</p><h1>Galerias</h1><p className="intro">Cada pasta nasce dentro de uma galeria-mãe. Cada responsável recebe uma galeria privada e um histórico independente.</p></div>
        <Link className="mk-button mk-button--primary" href="/admin/galleries/new">＋ Criar galeria</Link>
      </div>
      <div className="context-tabs" role="tablist" aria-label="Tipo de galeria">
        <button role="tab" aria-selected={view === "sources"} className={view === "sources" ? "selected" : ""} onClick={() => setView("sources")}>Galerias-mãe</button>
        <button role="tab" aria-selected={view === "private"} className={view === "private" ? "selected" : ""} onClick={() => setView("private")}>Galerias privadas</button>
      </div>
      {view === "private" ? <><div className="context-tabs" role="tablist" aria-label="Estado da galeria privada"><button role="tab" aria-selected={tab === "active"} className={tab === "active" ? "selected" : ""} onClick={() => setTab("active")}>Ativas</button><button role="tab" aria-selected={tab === "frozen"} className={tab === "frozen" ? "selected" : ""} onClick={() => setTab("frozen")}>Congeladas</button></div><label className="gallery-search">Filtrar por situação<select aria-label="Filtrar por situação" value={state} onChange={(event) => setState(event.target.value)}><option value="">Todas as situações</option><option value="selection_in_progress">Seleção em andamento</option><option value="payment_pending">Pagamento pendente</option><option value="selection_finalized">Seleção finalizada</option><option value="blocked">Acesso bloqueado</option></select></label></> : null}
      <label className="gallery-search">Buscar por galeria, nome ou telefone<input value={query} onChange={(event) => setQuery(event.target.value)} /></label>
      {loading ? <p className="form-message" role="status">Carregando galerias…</p> : null}
      {!loading && failed ? <p className="notice" role="alert">Não foi possível carregar as galerias.</p> : null}
      {!loading && !failed && empty ? <p className="notice">Nenhum resultado nesta visão.</p> : null}
      {!loading && !failed && !empty && view === "sources" ? <section className="gallery-admin-list" aria-label="Galerias do evento">{sources.map((source) => <Link key={source.id} href={`/admin/galleries/sources/${source.id}`}><div className="gallery-cover">{source.cover_preview_url ? <img src={`/api${source.cover_preview_url}`} alt="" /> : "Sem capa"}</div><div><strong>{source.name}</strong><small>{source.event_name || "Evento sem nome"}</small><span>{source.registration_count} pessoas registradas · {source.private_gallery_count} galerias privadas · {source.frozen_gallery_count} congeladas</span></div></Link>)}</section> : null}
      {!loading && !failed && !empty && view === "private" ? <section className="gallery-admin-list" aria-label="Galerias privadas">{privateGalleries.map((gallery) => <Link key={gallery.id} href={`/admin/galleries/${gallery.id}`}><div className="gallery-cover">{gallery.cover_preview_url ? <img src={`/api${gallery.cover_preview_url}`} alt="" /> : "Sem capa"}</div><div><strong>{gallery.name}</strong><small>1 responsável · histórico independente</small><span>{gallery.frozen ? "Prazo expirado" : gallery.blocked ? "Acesso bloqueado" : gallery.payment_pending ? "Pagamento pendente" : gallery.selection_in_progress ? "Seleção em andamento" : "Disponível"}</span></div></Link>)}</section> : null}
    </main>
  );
}
