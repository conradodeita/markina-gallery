"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { PRODUCT_NAME } from "../../product-brand";

type SourceGallery = {
  id: string;
  name: string;
  event_name: string;
  cover_preview_url: string | null;
  registration_count: number;
};

export default function GalleriesPage() {
  const [query, setQuery] = useState("");
  const [sources, setSources] = useState<SourceGallery[]>([]);
  const [failed, setFailed] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const params = new URLSearchParams();
    if (query) params.set("query", query);
    queueMicrotask(() => setLoading(true));
    fetch(`/api/admin/parent-galleries/overview?${params}`, { credentials: "same-origin" })
      .then(async (response) => {
        if (!response.ok) throw new Error("Falha ao carregar galerias");
        const data = await response.json();
        setSources(data.parent_galleries);
        setFailed(false);
      })
      .catch(() => setFailed(true))
      .finally(() => setLoading(false));
  }, [query]);

  return (
    <main className="admin-shell">
      <div className="section-heading gallery-list-heading">
        <div>
          <p className="eyebrow">{PRODUCT_NAME} · Fotógrafo</p>
          <h1>Galerias</h1>
          <p className="intro">Cada pasta nasce dentro de uma galeria. O acervo de cada cliente fica no card dela.</p>
        </div>
        <Link className="mk-button mk-button--primary" href="/admin/galleries/new">
          ＋ Criar galeria
        </Link>
      </div>
      <label className="gallery-search">
        Buscar galeria por nome, evento, cliente ou telefone
        <input value={query} onChange={(event) => setQuery(event.target.value)} />
      </label>
      {loading ? <p className="form-message" role="status">Carregando galerias…</p> : null}
      {!loading && failed ? <p className="notice" role="alert">Não foi possível carregar as galerias.</p> : null}
      {!loading && !failed && !sources.length ? <p className="notice">Nenhum resultado nesta visão.</p> : null}
      {!loading && !failed && sources.length ? (
        <section className="gallery-admin-list" aria-label="Galerias do evento">
          {sources.map((source) => (
            <Link key={source.id} href={`/admin/galleries/sources/${source.id}`}>
              <div className="gallery-cover">
                {source.cover_preview_url ? <img src={`/api${source.cover_preview_url}`} alt="" /> : "Sem capa"}
              </div>
              <div>
                <strong>{source.name}</strong>
                <small>{source.event_name || "Evento sem nome"}</small>
                <span>{source.registration_count} pessoas registradas</span>
              </div>
            </Link>
          ))}
        </section>
      ) : null}
    </main>
  );
}
