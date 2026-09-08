"use client";


import { useEffect, useState } from "react";

import { MarkinaLink, MetricCard, PageHeading, StatusBadge, SurfaceCard, SystemState } from "../ui-kit";

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
  const preparing = summary.counts.folders_preparing ?? 0;
  return (
    <div className="admin-dashboard">
      <PageHeading eyebrow="Central de operações" title="Seu próximo passo está à vista." detail="Acompanhe as galerias, conclua as pastas que estão em preparação e mantenha cada entrega no ritmo certo." actions={<><MarkinaLink href="/admin/galleries/new">Nova galeria</MarkinaLink><MarkinaLink href="/admin/galleries" variant="secondary">Ver galerias</MarkinaLink></>} />
      <section className="dashboard-context" aria-label="Contexto do ambiente"><div><span>Ambiente de trabalho</span><strong>{summary.environment}</strong><small>versão {summary.version}</small></div><p>{processing ? `${processing} importação(ões) em processamento. Confira as pastas antes de liberar.` : "Nenhuma importação em andamento. Você pode revisar e liberar as pastas prontas."}</p></section>
      <section className="dashboard-metrics">
        <MetricCard label="Galerias-fonte" value={summary.counts.parent_galleries} detail="eventos sob seu controle" />
        <MetricCard label="Galerias privadas" value={summary.counts.derived_galleries} detail="históricos individuais ativos" tone="success" />
        <MetricCard label="Pastas em preparação" value={preparing} detail={`${processing} importação(ões) em andamento`} tone={preparing ? "warning" : "success"} />
        <MetricCard label="Pastas liberadas" value={summary.counts.folders_released ?? 0} detail="visíveis a clientes autorizadas" tone="success" />
      </section>
      <section className="dashboard-columns">
        <SurfaceCard>
          <div className="section-heading"><div><p className="eyebrow">Atenção agora</p><h2>Ritual de publicação</h2><p className="dashboard-section-detail">Uma ordem simples para evitar liberar fotos incompletas.</p></div></div>
          <ol className="task-steps">
            <li><b>1</b><div><strong>Contextualize a galeria</strong><small>Confira identidade, prazo e mensagem antes de adicionar fotos.</small></div></li>
            <li><b>2</b><div><strong>Prepare uma pasta completa</strong><small>Envie JPEGs e revise as prévias antes de disponibilizar.</small></div></li>
            <li><b>3</b><div><strong>Libere para as clientes certas</strong><small>Vincule responsáveis e publique somente a rodada concluída.</small></div></li>
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
