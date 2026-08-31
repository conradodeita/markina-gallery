"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ProtectedPhoto, ProtectedPhotoViewer } from "../protected-photo-viewer";
import { PageHeading, StatusBadge, SurfaceCard, SystemState } from "../ui-kit";
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
type Order = {
  id: string;
  gallery_name: string;
  parent_gallery_name: string;
  gallery_status_label: string;
  gallery_removed: boolean;
  confirmed_at: string | null;
  total_cents: number;
  items: Array<{ photo_id: string; name: string; preview_url: string | null; delivery_url: string | null; delivery_reference_available: boolean }>;
};

const accessModeLabel = {
  standard: "Acesso por link",
  invite_only: "Somente convite",
  collective_protected: "Acesso coletivo protegido",
};

export default function LibraryPage() {
  const [publicGalleries, setPublicGalleries] = useState<PublicGallery[] | null>(null);
  const [privateGalleries, setPrivateGalleries] = useState<PrivateGallery[] | null>(null);
  const [orders, setOrders] = useState<Order[] | null>(null);
  const [selected, setSelected] = useState<ProtectedPhoto[]>([]);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    Promise.all([
      fetch("/api/library", { credentials: "same-origin" }),
      fetch("/api/library/purchases", { credentials: "same-origin" }),
    ])
      .then(async ([libraryResponse, purchasesResponse]) => {
        if (!libraryResponse.ok || !purchasesResponse.ok) throw new Error();
        const library = await libraryResponse.json();
        const purchases = await purchasesResponse.json();
        setPublicGalleries(library.public_galleries ?? []);
        setPrivateGalleries(library.private_galleries ?? library.galleries ?? []);
        setOrders(purchases.orders ?? []);
      })
      .catch(() => {
        setFailed(true);
        setPublicGalleries([]);
        setPrivateGalleries([]);
        setOrders([]);
      });
  }, []);

  if (!publicGalleries || !privateGalleries || !orders) return <SystemState tone="loading" title="Carregando sua biblioteca" detail="Consultando Galerias públicas, galerias privadas e compras." />;
  if (failed) return <main className="admin-shell"><h1>Biblioteca indisponível</h1><p className="intro">Não foi possível consultar suas galerias. Tente novamente.</p></main>;

  return (
    <main className="admin-shell library-shell">
      <PageHeading eyebrow="Sua área privada" title="Suas galerias" detail="Continue escolhendo fotos nas Galerias públicas autorizadas, revise suas galerias privadas e consulte compras preservadas." />

      <section className="library-section" aria-labelledby="public-library-title">
        <div className="section-heading"><div><p className="eyebrow">Para continuar escolhendo</p><h2 id="public-library-title">Galerias públicas abertas</h2></div><StatusBadge>{publicGalleries.length}</StatusBadge></div>
        {publicGalleries.length ? <div className="library-card-grid">{publicGalleries.map((gallery) => {
          const content = <><header><span>Galeria pública</span><StatusBadge tone={gallery.gallery_status === "active" ? "success" : "warning"}>{gallery.gallery_status === "active" ? "Acesso ativo" : "Aguardando liberação"}</StatusBadge></header><strong>{gallery.name}</strong><small>{gallery.event_name || "Evento sem nome"}</small><p>{accessModeLabel[gallery.access_mode]}</p>{gallery.browse_url ? <b>Ver fotos e escolher mais →</b> : <b>A grade de fotos ainda não está disponível</b>}</>;
          return gallery.browse_url ? <Link className="library-card" href={gallery.browse_url} key={gallery.id}>{content}</Link> : <article className="library-card" key={gallery.id}>{content}</article>;
        })}</div> : <EmptyState title="Nenhuma Galeria pública aberta" detail="Links e convites autorizados aparecerão aqui enquanto a origem estiver disponível." />}
      </section>

      <section className="library-section" aria-labelledby="private-library-title">
        <div className="section-heading"><div><p className="eyebrow">Suas escolhas e fotos disponíveis</p><h2 id="private-library-title">Galerias privadas</h2></div><StatusBadge>{privateGalleries.length}</StatusBadge></div>
        {privateGalleries.length ? <div className="library-card-grid">{privateGalleries.map((gallery) => (
          <article className={`library-card private-library-card private-library-card--${gallery.gallery_status}`} key={gallery.id}>
            <header><span>Galeria privada</span><StatusBadge tone={gallery.gallery_status === "active" ? "success" : "warning"}>{gallery.gallery_status === "active" ? "Ativa" : gallery.gallery_status === "expired" ? "Prazo expirado" : "Origem removida"}</StatusBadge></header>
            <strong>{gallery.name}</strong>
            <small>{gallery.message || "Revise as fotos disponíveis para você"}</small>
            <div className="gallery-folder-badges">{gallery.folders.map((folder) => <StatusBadge key={folder.id} tone="success">{folder.name}</StatusBadge>)}{!gallery.folders.length ? <StatusBadge tone="warning">Aguardando fotos</StatusBadge> : null}</div>
            {gallery.selection_expires_at ? <small>Seleção até {new Date(gallery.selection_expires_at).toLocaleDateString("pt-BR")}</small> : null}
            <div className="library-card-actions"><Link href={`/gallery/${gallery.id}`}>Abrir galeria privada</Link>{gallery.origin.available && gallery.origin.browse_url ? <Link href={gallery.origin.browse_url}>Voltar à Galeria pública</Link> : <span>{gallery.origin_removed ? "A Galeria pública de origem foi removida; suas fotos privadas permanecem." : "O retorno à origem não está autorizado."}</span>}</div>
          </article>
        ))}</div> : <EmptyState title="Nenhuma galeria privada ativa" detail="Uma galeria privada aparece após sua primeira seleção ou quando o fotógrafo disponibiliza fotos para você." />}
      </section>

      <SurfaceCard className="client-order-history library-history" >
        <div className="section-heading"><div><p className="eyebrow">Preservado independentemente</p><h2>Histórico de compras</h2></div><StatusBadge>{orders.length}</StatusBadge></div>
        {orders.length ? orders.map((order) => (
          <article className="library-order" key={order.id}>
            <div><strong>{order.gallery_name}</strong><small>{order.parent_gallery_name} · {order.gallery_status_label}</small><span>{order.items.length} foto(s) · {(order.total_cents / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}</span>{order.confirmed_at ? <time dateTime={order.confirmed_at}>Confirmada em {new Date(order.confirmed_at).toLocaleDateString("pt-BR")}</time> : null}</div>
            <button className="secondary" onClick={() => setSelected(order.items.filter((item) => item.preview_url).map((item) => ({ id: item.photo_id, name: item.name, previewUrl: item.preview_url! })))} disabled={!order.items.some((item) => item.preview_url)}>Ver prévias</button>
          </article>
        )) : <EmptyState title="Nenhuma compra confirmada" detail="Suas compras futuras ficarão disponíveis mesmo que uma galeria seja encerrada ou removida." />}
      </SurfaceCard>
      {selected.length > 0 ? <ProtectedPhotoViewer label="Fotos compradas" photos={selected} /> : null}
    </main>
  );
}
