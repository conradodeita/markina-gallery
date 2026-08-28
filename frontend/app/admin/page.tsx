"use client";


import { useEffect, useState } from "react";

import { MarkinaLink, StatusBadge, SurfaceCard, SystemState } from "../ui-kit";

type Summary = {
  environment: string;
  version: string;
  counts: {
    clients: number;
    parent_galleries: number;
    derived_galleries: number;
    imports: Record<string, number>;
    folders_preparing?: number;
    folders_released?: number;
  };
  recent_galleries: Array<{
    id: string;
    name: string;
    access_enabled: boolean;
    selection_expires_at?: string | null;
  }>;
};

export default function AdminPage() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    fetch("/api/admin/validation-summary", { credentials: "same-origin" })
      .then(async (response) => {
        if (!response.ok) throw new Error();
        setSummary(await response.json());
      })
      .catch(() => setFailed(true));
  }, []);
  if (failed) return <SystemState tone="error" title="Acesso administrativo indisponível" detail="Entre novamente ou atualize a página." />;
  if (!summary) return <SystemState tone="loading" title="Preparando seu painel" detail="Consultando suas galerias e operações." />;
  const processing = (summary.counts.imports.queued ?? 0) + (summary.counts.imports.processing ?? 0);
  return (
    <div className="admin-dashboard">
      <section className="dashboard-hero">
        <div>
          <p className="eyebrow">Área do fotógrafo</p>
          <h1>Seu trabalho, organizado por galerias.</h1>
          <p>Crie a galeria, configure suas etapas e prepare cada pasta de fotos dentro dela.</p>
          <div className="dashboard-actions">
            <MarkinaLink href="/admin/galleries/new">Nova galeria</MarkinaLink>
            <MarkinaLink href="/admin/galleries" variant="secondary">Ver galerias</MarkinaLink>
          </div>
        </div>
        <aside><span>Ambiente</span><strong>{summary.environment}</strong><small>versão {summary.version}</small></aside>
      </section>
      <section className="dashboard-metrics">
        <SurfaceCard><span>Galerias-mãe</span><strong>{summary.counts.parent_galleries}</strong><small>eventos sob seu controle</small></SurfaceCard>
        <SurfaceCard><span>Galerias privadas</span><strong>{summary.counts.derived_galleries}</strong><small>históricos independentes</small></SurfaceCard>
        <SurfaceCard><span>Pastas em preparação</span><strong>{summary.counts.folders_preparing ?? 0}</strong><small>{processing} importação(ões) em andamento</small></SurfaceCard>
        <SurfaceCard><span>Pastas liberadas</span><strong>{summary.counts.folders_released ?? 0}</strong><small>visíveis apenas às clientes autorizadas</small></SurfaceCard>
      </section>
      <section className="dashboard-columns">
        <SurfaceCard>
          <div className="section-heading"><div><p className="eyebrow">Atenção agora</p><h2>Próximos passos</h2></div></div>
          <ol className="task-steps">
            <li><b>1</b><div><strong>Abra uma galeria</strong><small>Revise ajustes e contexto do evento.</small></div></li>
            <li><b>2</b><div><strong>Prepare uma pasta</strong><small>Envie JPEGs pela etapa Imagens.</small></div></li>
            <li><b>3</b><div><strong>Vincule clientes</strong><small>Libere somente a rodada completa.</small></div></li>
          </ol>
        </SurfaceCard>
        <SurfaceCard>
          <div className="section-heading"><div><p className="eyebrow">Acesso recente</p><h2>Galerias privadas</h2></div><MarkinaLink href="/admin/galleries" variant="quiet">Todas →</MarkinaLink></div>
          {summary.recent_galleries.length ? <div className="dashboard-recent">{summary.recent_galleries.map((gallery) => <div key={gallery.id}><div><strong>{gallery.name}</strong><small>{gallery.selection_expires_at ? "Prazo configurado" : "Sem prazo definido"}</small></div><StatusBadge tone={gallery.access_enabled ? "success" : "danger"}>{gallery.access_enabled ? "Ativa" : "Bloqueada"}</StatusBadge></div>)}</div> : <SystemState title="Ainda não há galerias privadas" detail="Comece criando uma galeria-mãe e vinculando uma cliente." />}
        </SurfaceCard>
      </section>
    </div>
  );
}
