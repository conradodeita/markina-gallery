"use client";

import { useEffect, useRef, useState } from "react";

import { MarkinaButton, SurfaceCard, SystemState } from "../ui-kit";
import { formatCapacityReport, type Metric, type Snapshot } from "./capacity-report";

const labels: Record<string, string> = {
  media: "Mídia", preview_adjustment: "Ajuste de prévias", search: "Busca facial",
  index: "Índice facial", maintenance: "Manutenção facial",
};
const connectionStateLabels: Record<string, string> = {
  active: "Ativas", idle: "Ociosas", idle_in_transaction: "Ociosas em transação",
  other: "Outros estados", unknown: "Estado não informado",
};
const waitLabels: Record<string, string> = {
  created_age_estimate: "estimada pela criação do registro",
  updated_age_estimate: "estimada pela última atualização",
  available_at_age_estimate: "estimada pelo agendamento vencido",
  exact_wait_unavailable: "espera exata indisponível",
};
const evidenceLabels: Record<string, string> = {
  observed: "observado", calculated: "calculado", estimated: "estimado", unavailable: "indisponível",
};
const reasonLabels: Record<string, string> = {
  empty_queue: "fila vazia", unsupported_backend: "origem não compatível",
  unsupported_pool: "pool não compatível", permission_denied: "permissão insuficiente",
  source_unavailable: "fonte indisponível", query_timeout: "tempo de consulta excedido",
  collection_busy: "outra coleta está em andamento", inconsistent_timestamp: "horário inconsistente",
  process_inventory_missing: "inventário de processos incompleto",
  external_consumers_unknown: "consumidores externos desconhecidos",
  operational_reserve_unapproved: "reserva operacional não aprovada", field_unavailable: "campo indisponível",
};

function metricText(metric: Metric) {
  if (metric.value === null) return `Indisponível (${reasonLabels[metric.reason ?? ""] ?? "sem motivo informado"})`;
  const value = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 }).format(metric.value);
  const unit = metric.unit === "seconds" ? "s" : metric.unit === "connections" ? (metric.value === 1 ? "conexão" : "conexões") : (metric.value === 1 ? "tarefa" : "tarefas");
  return `${value} ${unit} · ${evidenceLabels[metric.evidence] ?? metric.evidence}`;
}

export function CapacityDiagnostics({ onAccessDenied }: { onAccessDenied?: () => void }) {
  const [denied, setDenied] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copyState, setCopyState] = useState<"idle" | "copying" | "success" | "error">("idle");
  const request = useRef<AbortController | null>(null);
  const copyInProgress = useRef(false);
  const copyOperation = useRef(0);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      request.current?.abort();
      request.current = null;
      copyOperation.current += 1;
      copyInProgress.current = false;
    };
  }, []);

  async function load() {
    if (loading || request.current) return;
    const controller = new AbortController();
    request.current = controller;
    setLoading(true);
    setError(null);
    setSnapshot(null);
    copyOperation.current += 1;
    copyInProgress.current = false;
    setCopyState("idle");
    try {
      const response = await fetch("/api/admin/capacity-observability", {
        credentials: "same-origin", cache: "no-store", signal: controller.signal,
      });
      if (!response.ok) {
        if (response.status === 401 || response.status === 403) {
          setDenied(true);
          onAccessDenied?.();
          return;
        }
        setError("Não foi possível consultar o diagnóstico agora.");
        return;
      }
      setSnapshot(await response.json() as Snapshot);
    } catch (cause) {
      if (cause instanceof DOMException && cause.name === "AbortError") return;
      setError("Não foi possível consultar o diagnóstico agora.");
      setSnapshot(null);
    } finally {
      if (request.current === controller) {
        request.current = null;
        setLoading(false);
      }
    }
  }

  async function copyReport() {
    if (!snapshot || copyInProgress.current) return;
    const operation = copyOperation.current + 1;
    copyOperation.current = operation;
    copyInProgress.current = true;
    setCopyState("copying");
    try {
      if (!navigator.clipboard?.writeText) throw new Error("clipboard_unavailable");
      await navigator.clipboard.writeText(formatCapacityReport(snapshot));
      if (mounted.current && copyOperation.current === operation) setCopyState("success");
    } catch {
      if (mounted.current && copyOperation.current === operation) setCopyState("error");
    } finally {
      if (copyOperation.current === operation) copyInProgress.current = false;
    }
  }

  if (denied) return null;
  return (
    <SurfaceCard>
      <div className="section-heading">
        <div>
          <p className="eyebrow">Diagnóstico sob demanda</p>
          <h2>Capacidade e filas</h2>
          <p className="dashboard-section-detail">Leitura agregada do processo que respondeu, banco e filas cobertas.</p>
        </div>
        <MarkinaButton type="button" variant="secondary" aria-expanded={expanded} aria-controls="capacity-diagnostics-panel" onClick={() => { const next = !expanded; setExpanded(next); if (next && !snapshot && !loading) void load(); }}>
          {expanded ? "Recolher" : "Consultar diagnóstico"}
        </MarkinaButton>
      </div>
      <div id="capacity-diagnostics-panel" hidden={!expanded} aria-live="polite">
        {expanded && loading && <SystemState tone="loading" title="Consultando diagnóstico" detail="A leitura é agregada e pode levar alguns instantes." />}
        {expanded && error && <div><SystemState tone="error" title="Diagnóstico indisponível" detail={error} /><MarkinaButton type="button" variant="secondary" onClick={() => void load()} disabled={loading}>Tentar novamente</MarkinaButton></div>}
        {expanded && snapshot && <div className="capacity-diagnostics">
          <p>{snapshot.cached ? "Snapshot em cache do processo" : "Coletado agora"} · início {new Date(snapshot.collection_started_at).toLocaleString("pt-BR", { timeZone: "UTC" })} UTC · fim {new Date(snapshot.collection_finished_at).toLocaleString("pt-BR", { timeZone: "UTC" })} UTC</p>
          <p>Escopos: processo da API respondente, banco atual e servidor PostgreSQL. Cobertura: {snapshot.coverage.map((name) => labels[name] ?? name).join(", ")}.</p>
          <h3>Pool da API</h3>
          <dl><dt>Tipo</dt><dd>{snapshot.pool.pool_class}</dd><dt>Teto finito</dt><dd>{snapshot.pool.finite_limit ? "Sim" : "Não"}</dd><dt>Overflow sem limite</dt><dd>{snapshot.pool.unbounded_overflow ? "Sim" : "Não"}</dd><dt>Conexões abertas estimadas</dt><dd>{metricText(snapshot.pool.open_connections_estimate)}</dd><dt>Em uso</dt><dd>{metricText(snapshot.pool.checked_out)}</dd><dt>Disponíveis no pool</dt><dd>{metricText(snapshot.pool.checked_in)}</dd><dt>Overflow máximo</dt><dd>{metricText(snapshot.pool.max_overflow)}</dd><dt>Teto potencial deste processo</dt><dd>{metricText(snapshot.pool.potential_max)}</dd><dt>Timeout de aquisição configurado</dt><dd>{metricText(snapshot.pool.acquisition_timeout_seconds)}</dd><dt>Espera medida</dt><dd>{metricText(snapshot.pool.wait_seconds)}</dd><dt>Timeouts contados</dt><dd>{metricText(snapshot.pool.timeout_count)}</dd></dl>
          <h3>Conexões PostgreSQL</h3>
          <p>Banco atual e servidor são escopos distintos. Máximo: {metricText(snapshot.database.max_connections)}; reservas superusuário: {metricText(snapshot.database.superuser_reserved_connections)}; reservas adicionais: {metricText(snapshot.database.reserved_connections)}.</p>
          <div className="capacity-queue-grid">
            {([["Conexões no banco atual", snapshot.database.database_client_connections], ["Conexões visíveis no servidor", snapshot.database.server_client_connections]] as const).map(([title, states]) => <section key={title}><h4>{title}</h4><dl>{Object.entries(states).map(([state, metric]) => <div key={state} className="capacity-state-row"><dt>{connectionStateLabels[state] ?? state}</dt><dd>{metricText(metric)}</dd></div>)}</dl></section>)}
          </div>
          <h3>Filas cobertas</h3>
          <div className="capacity-queue-grid">{snapshot.queues.map((queue) => <section key={queue.queue_class} aria-label={labels[queue.queue_class] ?? queue.queue_class}><h4>{labels[queue.queue_class] ?? queue.queue_class}</h4><dl><dt>Queued</dt><dd>{metricText(queue.queued_total)}</dd><dt>Programados</dt><dd>{metricText(queue.scheduled_total)}</dd><dt>Candidatos</dt><dd>{metricText(queue.claim_candidates_total)}</dd><dt>Processing</dt><dd>{metricText(queue.processing_total)}</dd><dt>Bloqueados por dependência</dt><dd>{metricText(queue.blocked_dependency_total)}</dd><dt>Recuperáveis</dt><dd>{metricText(queue.reclaimable_total)}</dd><dt>Idade desde a criação</dt><dd>{metricText(queue.oldest_record_age_seconds)}</dd><dt>Idade desde o agendamento vencido</dt><dd>{metricText(queue.oldest_due_age_seconds)}</dd><dt>Idade desde atualização</dt><dd>{metricText(queue.oldest_updated_age_seconds)}</dd></dl><p>Espera: {waitLabels[queue.wait_semantics] ?? "indisponível"}.</p></section>)}</div>
          <h3>Orçamento global</h3><p>Indisponível. O pool deste processo não representa todos os processos e consumidores; não há orçamento nem margem calculados. Lacunas: {snapshot.connection_budget.limitations.map((reason) => reasonLabels[reason] ?? reason).join(", ")}.</p>
          {snapshot.limitations.length > 0 && <p>Limitações: {snapshot.limitations.join(", ")}.</p>}
          <div className="capacity-diagnostics-actions">
            <MarkinaButton type="button" variant="secondary" onClick={() => void load()} disabled={loading}>Atualizar agora</MarkinaButton>
            <MarkinaButton type="button" variant="secondary" onClick={() => void copyReport()} disabled={copyState === "copying"}>{copyState === "copying" ? "Copiando…" : "Copiar relatório"}</MarkinaButton>
          </div>
          {copyState === "success" && <p role="status" aria-live="polite">Relatório copiado para a área de transferência.</p>}
          {copyState === "error" && <p role="alert">Não foi possível copiar o relatório. Tente novamente.</p>}
        </div>}
      </div>
    </SurfaceCard>
  );
}
