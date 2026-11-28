"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";

import { MarkinaLink, MetricCard, PageHeading, StatusBadge, SystemState } from "../../ui-kit";
import { OverviewIcon } from "../overview-icon";
import styles from "../catalog.module.css";

type SourceGallery = {
  id: string;
  name: string;
  event_name: string;
  active?: boolean;
  cover_preview_url: string | null;
  private_gallery_count?: number;
  registration_count: number;
};

type GalleryResponse = {
  total: number;
  parent_galleries: SourceGallery[];
};

export default function GalleriesPage() {
  const [query, setQuery] = useState("");
  const [sources, setSources] = useState<SourceGallery[]>([]);
  const [total, setTotal] = useState(0);
  const [failed, setFailed] = useState(false);
  const [loading, setLoading] = useState(true);
  const [presentation, setPresentation] = useState<"grid" | "list">("grid");

  useEffect(() => {
    const controller = new AbortController();
    const params = new URLSearchParams();
    if (query) params.set("query", query);
    queueMicrotask(() => {
      if (!controller.signal.aborted) setLoading(true);
    });
    fetch(`/api/admin/parent-galleries/overview?${params}`, { credentials: "same-origin", signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error("Falha ao carregar galerias");
        const data = await response.json() as GalleryResponse;
        if (controller.signal.aborted) return;
        setSources(data.parent_galleries);
        setTotal(data.total ?? data.parent_galleries.length);
        setFailed(false);
      })
      .catch(() => {
        if (!controller.signal.aborted) setFailed(true);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [query]);

  return (
    <div className={styles.catalog}>
      <PageHeading
        title="Galerias"
        detail="Cada pasta nasce dentro de uma galeria pública. Abra a galeria para gerenciar os acervos das clientes."
        actions={<MarkinaLink href="/admin/galleries/new"><OverviewIcon name="add" /> Criar galeria</MarkinaLink>}
      />
      {!loading && !failed && total > 0 && (
        <section className={styles.metrics} aria-label="Resumo das galerias">
          <MetricCard icon={<OverviewIcon name="photo_library" />} label="Galerias públicas" value={total} detail={query ? "correspondentes à busca" : "no catálogo da sua conta"} />
          <MetricCard icon={<OverviewIcon name="folder_shared" />} label="Galerias privadas vinculadas" value={sources.reduce((count, source) => count + (source.private_gallery_count ?? 0), 0)} detail="nas galerias públicas exibidas" />
          <MetricCard icon={<OverviewIcon name="group" />} label="Pessoas registradas" value={sources.reduce((count, source) => count + source.registration_count, 0)} detail="inscrições nas galerias exibidas" />
        </section>
      )}
      <section className={styles.catalogPanel} aria-labelledby="gallery-catalog-title">
        <div className={styles.panelHeading}>
          <h2 id="gallery-catalog-title"><OverviewIcon name="public" /> Galerias públicas</h2>
          <div className={styles.viewControl} role="group" aria-label="Exibição das galerias">
            <button type="button" aria-label="Grade" aria-pressed={presentation === "grid"} onClick={() => setPresentation("grid")}><OverviewIcon name="grid_view" /></button>
            <button type="button" aria-label="Lista" aria-pressed={presentation === "list"} onClick={() => setPresentation("list")}><OverviewIcon name="menu" /></button>
          </div>
        </div>
        <label className={styles.search}>
          Buscar galeria por nome, evento, cliente ou telefone
          <span className={styles.searchField}><OverviewIcon name="search" /><input id="gallery-search" type="search" value={query} onChange={(event) => setQuery(event.target.value)} /></span>
        </label>
        {loading ? (
          <SystemState tone="loading" title="Carregando galerias…" detail="Consultando o catálogo da sua conta." />
        ) : failed ? (
          <SystemState tone="error" title="Não foi possível carregar as galerias." detail="Recarregue a página para tentar de novo." />
        ) : !sources.length ? (
          <SystemState title="Nenhum resultado nesta visão." detail={query ? "Revise o termo de busca." : "Crie uma galeria para começar."} />
        ) : (
          <>
            {total > sources.length && <p className={styles.count}>Exibindo {sources.length} de {total} galerias.</p>}
            <ul className={`${styles.galleries} ${presentation === "list" ? styles.galleryList : ""}`}>
              {sources.map((source) => (
                <li key={source.id}>
                  <Link className={styles.galleryCard} href={`/admin/galleries/sources/${source.id}`}>
                    <div className={styles.cover}>
                      {source.cover_preview_url ? (
                        <Image src={`/api${source.cover_preview_url}`} alt="" fill unoptimized />
                      ) : <span><OverviewIcon name="collections" /><span>Sem capa</span></span>}
                    </div>
                    <div className={styles.galleryCardBody}>
                      <div className={styles.galleryCardHeading}>
                        <h3>{source.name}</h3>
                        {typeof source.active === "boolean" && <StatusBadge tone={source.active ? "success" : "danger"}>{source.active ? "Ativa" : "Bloqueada"}</StatusBadge>}
                      </div>
                      <p>{source.event_name || "Evento sem nome"}</p>
                      <div className={styles.galleryCardFooter}>
                        <span><OverviewIcon name="group" /> <span>{source.registration_count} pessoas registradas</span></span>
                        <OverviewIcon name="arrow_forward" />
                      </div>
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          </>
        )}
      </section>
    </div>
  );
}
