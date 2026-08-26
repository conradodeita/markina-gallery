"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { EmptyState, StateCard, ValidationHeader } from "../validation-ui";

type Summary = { environment: string; version: string; counts: { clients: number; parent_galleries: number; derived_galleries: number; imports: Record<string, number> }; recent_galleries: Array<{ id: string; name: string; access_enabled: boolean }> };
export default function AdminPage() {
  const [summary, setSummary] = useState<Summary | null>(null); const [failed, setFailed] = useState(false);
  useEffect(() => { fetch("/api/admin/validation-summary", { credentials: "same-origin" }).then(async (response) => { if (!response.ok) throw new Error(); setSummary(await response.json()); }).catch(() => { setFailed(true); setSummary({ environment: "homologação", version: "indisponível", counts: { clients: 0, parent_galleries: 0, derived_galleries: 0, imports: {} }, recent_galleries: [] }); }); }, []);
  if (!summary) return <main className="admin-shell">Carregando painel de validação…</main>;
  if (failed) return <main className="admin-shell"><h1>Acesso restrito</h1><Link href="/">Voltar para entrada</Link></main>;
  const processing = (summary.counts.imports.queued ?? 0) + (summary.counts.imports.processing ?? 0);
  return <main className="admin-shell"><ValidationHeader role="Painel do fotógrafo" version={`${summary.environment} · ${summary.version}`} /><h1>Valide seu fluxo de trabalho</h1><p className="intro">Relate nesta conversa a tela e a versão exibida quando encontrar algo inesperado.</p><section className="state-grid"><StateCard title="Clientes" value={summary.counts.clients} detail="cadastros autorizados" href="/admin/operations" /><StateCard title="Acervos" value={summary.counts.parent_galleries} detail="somente administrativos" href="/admin/operations" /><StateCard title="Galerias privadas" value={summary.counts.derived_galleries} detail="acessos derivados" href="/admin/operations" /><StateCard title="Importações" value={processing} detail="em processamento" href="/admin/operations" /></section><section className="admin-card"><h2>Próximas validações</h2><div className="action-grid"><Link className="primary" href="/admin/operations">Criar cliente e galeria</Link><Link className="secondary" href="/admin/statistics">Estatísticas</Link><Link className="secondary" href="/admin/purchases">Compras</Link><Link className="secondary" href="/admin/previews">Prévias</Link></div></section><section className="admin-card"><h2>Galerias recentes</h2>{summary.recent_galleries.length ? <div className="recent-list">{summary.recent_galleries.map((gallery) => <article key={gallery.id}><strong>{gallery.name}</strong><span>{gallery.access_enabled ? "Acesso ativo" : "Acesso bloqueado"}</span></article>)}</div> : <EmptyState title="Nenhuma galeria privada ainda" detail="Comece criando cliente, acervo e JPEG na operação." />}</section></main>;
}
