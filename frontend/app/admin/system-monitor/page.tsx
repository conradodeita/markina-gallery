"use client";

import { useEffect, useRef, useState } from "react";
import { PUSH_LOGOUT_EVENT } from "../../push-device";
import { InstallationDiagnostics } from "../installation-diagnostics";
import { useMonitorPermissions, type Permissions } from "./use-permissions";
import { UserTree } from "./user-tree";
import { bytes, date, incidentLabel, numeric, operations, states, type Incidents, type Report } from "./types";
import styles from "./monitor.module.css";

const jobStates: Record<string, string> = { queued: "Na fila", processing: "Em processamento", failed: "Falhou", completed: "Concluído", ready: "Pronto", cancelled: "Cancelado", open: "Aberto", closed: "Fechado" };

export function Trend({ label, points, unit = "" }: { label: string; points: { at: string; value: number | null }[]; unit?: string }) {
  const available = points.filter((point) => point.value !== null);
  if (!available.length) return <div className={styles.chart}><h3>{label}</h3><p>Não coletado neste período.</p></div>;
  const maximum = Math.max(...available.map((point) => point.value!));
  const scale = Math.max(1, maximum);
  const segments: string[] = []; let path = "";
  points.forEach((point, index) => {
    if (point.value === null) { if (path) segments.push(path); path = ""; return; }
    path += `${path ? " L" : "M"}${10 + index / Math.max(1, points.length - 1) * 580},${110 - point.value / scale * 95}`;
  });
  if (path) segments.push(path);
  return <div className={styles.chart}><h3>{label}</h3><svg viewBox="0 0 600 120" role="img" aria-label={`${label}: ${available.length} amostras; máximo ${numeric(maximum, unit)}`}>
    <line x1="10" y1="110" x2="590" y2="110" stroke="currentColor" opacity="0.2" />
    {segments.map((segment, index) => <path key={index} d={segment} fill="none" stroke="currentColor" strokeWidth="2" />)}
  </svg><small>{date(points[0]?.at)} → {date(points.at(-1)?.at)} · máximo {numeric(maximum, unit)}</small>
  <details><summary>Ver valores</summary><div className={styles.table}><table><thead><tr><th>Horário</th><th>{label}</th></tr></thead><tbody>{points.map((point, index) => <tr key={index}><td>{date(point.at)}</td><td>{numeric(point.value, unit)}</td></tr>)}</tbody></table></div></details></div>;
}

function Metric({ title, value, detail }: { title: string; value: string; detail?: string }) {
  return <div className={styles.metric}><span>{title}</span><strong>{value}</strong>{detail && <small>{detail}</small>}</div>;
}

export default function SystemMonitorPage() {
  const { permissions, loading, revoke, revision } = useMonitorPermissions();
  if (!permissions || !Object.values(permissions).some(Boolean)) return <div className={styles.monitor}><h1>Monitor do sistema</h1><p role="status">{loading ? "Verificando permissões…" : "Sem permissão para o monitor, ou autorização temporariamente indisponível."}</p></div>;
  return <MonitorContent key={revision} permissions={permissions} revoke={revoke} revision={revision} />;
}

function MonitorContent({ permissions, revoke, revision }: { permissions: Permissions; revoke: () => void; revision: number }) {
  const loading = false;
  const [minutes, setMinutes] = useState(60);
  const [refresh, setRefresh] = useState(0);
  const [report, setReport] = useState<Report | null>(null);
  const [receivedAt, setReceivedAt] = useState(0);
  const [incidents, setIncidents] = useState<Incidents | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [clock, setClock] = useState(() => Date.now());
  const downloadController = useRef<AbortController | null>(null);

  useEffect(() => {
    const cancel = () => downloadController.current?.abort();
    window.addEventListener(PUSH_LOGOUT_EVENT, cancel);
    return () => { cancel(); window.removeEventListener(PUSH_LOGOUT_EVENT, cancel); };
  }, []);

  useEffect(() => {
    let current = true;
    let pending = false;
    const controller = new AbortController();
    async function load() {
      if (pending || document.visibilityState !== "visible") return;
      pending = true; setBusy(true); setError(null);
      async function get(path: string) {
        const response = await fetch(`${path}?minutes=${minutes}`, { credentials: "same-origin", cache: "no-store", signal: controller.signal });
        if ([401, 403].includes(response.status)) { if (current) { current = false; setReport(null); setIncidents(null); revoke(); controller.abort(); } throw new Error("access"); }
        if (!response.ok) throw new Error("unavailable");
        return response.json();
      }
      const outcomes = await Promise.allSettled([
        permissions?.metrics ? get("/api/admin/system-monitor").then((value) => { if (current) { setReport(value); const instant = Date.now(); setReceivedAt(instant); setClock(instant); } }) : Promise.resolve(),
        permissions?.incidents ? get("/api/admin/system-monitor/incidents").then((value) => { if (current) setIncidents(value); }) : Promise.resolve(),
      ]);
      if (current) { if (outcomes.some((item) => item.status === "rejected")) setError("Uma fonte não respondeu. Os dados anteriores podem estar desatualizados."); setBusy(false); }
      pending = false;
    }
    void load();
    const timer = window.setInterval(() => { void load(); }, 60_000);
    const tick = window.setInterval(() => setClock(Date.now()), 15_000);
    const visible = () => { if (document.visibilityState === "visible") { setClock(Date.now()); void load(); } };
    document.addEventListener("visibilitychange", visible);
    return () => { current = false; controller.abort(); window.clearInterval(timer); window.clearInterval(tick); document.removeEventListener("visibilitychange", visible); };
  }, [permissions, minutes, refresh, revoke]);

  async function download(format: "json" | "text") {
    if (exporting) return;
    const controller = new AbortController();
    downloadController.current = controller;
    setExporting(true);
    try {
      const response = await fetch(`/api/admin/system-monitor/report?minutes=${minutes}&format=${format}`, { credentials: "same-origin", cache: "no-store", signal: controller.signal });
      if ([401, 403].includes(response.status)) { setReport(null); setIncidents(null); revoke(); return; }
      if (!response.ok) throw new Error("unavailable");
      const blob = await response.blob();
      if (controller.signal.aborted) return;
      if (blob.size > 1048576) throw new Error("size");
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a"); link.href = url; link.download = `pick-your-pic-diagnostic.${format === "json" ? "json" : "txt"}`; link.click(); URL.revokeObjectURL(url);
    } catch { if (!controller.signal.aborted) setError("Não foi possível gerar o relatório. Tente um período menor ou atualize a autorização."); }
    finally { setExporting(false); }
  }

  const latest = report?.latest;
  const host = latest?.host.data;
  const capacity = latest?.capacity;
  const age = report?.age_seconds != null ? Math.max(0, report.age_seconds + (clock - receivedAt) / 1000) : null;
  const state = age !== null && age > (report?.stale_seconds ?? 180) ? "stale" : report?.state ?? "unknown";
  const allowed = permissions && Object.values(permissions).some(Boolean);

  return <div className={styles.monitor}>
    <header><p className="eyebrow">Administração da plataforma</p><h1>Monitor do sistema</h1><p>Atividade, desempenho e evidências operacionais. A capacidade máxima depende de testes autorizados.</p></header>
    {loading && <p role="status">Verificando permissões…</p>}
    {!loading && !allowed && <p role="status">Sem permissão para o monitor, ou autorização temporariamente indisponível.</p>}
    {allowed && <>
      <div className={styles.controls}><label>Período<select value={minutes} onChange={(event) => setMinutes(Number(event.target.value))}><option value={15}>15 minutos</option><option value={60}>1 hora</option><option value={360}>6 horas</option><option value={1440}>24 horas</option></select></label>
        <button disabled={busy} onClick={() => setRefresh(refresh + 1)}>Atualizar métricas</button>
        {permissions.metrics && permissions.export && <><button disabled={exporting} onClick={() => void download("json")}>Gerar relatório JSON</button><button disabled={exporting} onClick={() => void download("text")}>Relatório legível</button></>}
      </div>
      {error && <p role="alert">{error}</p>}
      {permissions.metrics && <>
        <section className={styles.section} aria-label="Resumo geral"><h2>Estado geral <span className={styles.badge} data-state={state}>{states[state]}</span></h2>
          <p>Última coleta: {date(report?.last_collected_at)} · Idade: {numeric(age, " s")}.</p>
          {!report?.collection_enabled && <p>A coleta contínua ainda não está habilitada. A ausência de dados não comprova indisponibilidade da aplicação.</p>}
          <div className={styles.grid}>
            <Metric title="CPU" value={numeric(host?.cpu_percent, "%")} detail={latest?.host.status === "observed" ? `Fonte: ${host?.source} · ${host?.scope === "host" ? "servidor" : "container"}` : states[latest?.host.status ?? "not_collected"]} />
            <Metric title="Memória disponível" value={bytes(host?.memory_available_bytes)} detail={`Total: ${bytes(host?.memory_total_bytes)}`} />
            <Metric title="Disco livre" value={bytes(host?.disk_free_bytes)} detail={`Filesystem verificado: ${bytes(host?.disk_total_bytes)}`} />
            <Metric title="Conexões em uso na API" value={numeric(capacity?.pool.checked_out.value)} detail="Somente o processo respondente" />
            <Metric title="Timeouts de conexão" value={numeric(report?.operations.find((row) => row.operation === "pool.acquire")?.timeouts)} detail="No período selecionado; distinto das demais falhas de aquisição" />
            <Metric title="Conexões ativas PostgreSQL" value={numeric(capacity?.database.database_client_connections.active.value)} detail={`Esperando lock: ${numeric(latest?.database_waits?.lock_waiters)}`} />
            <Metric title="Alertas ativos" value={numeric(report?.active_alerts)} detail="Alertas preventivos baseados em evidências" />
          </div>
        </section>
        <section className={styles.section}><h2>Aplicação e experiência</h2><p>Duração no backend até terminar a resposta. Tempo de renderização no dispositivo não coletado.</p>
          <div className={styles.grid}><Trend label="Requisições por 5 minutos" points={(report?.http_history ?? []).map((p) => ({ at: p.at, value: p.count }))} /><Trend label="Latência média" unit=" ms" points={(report?.http_history ?? []).map((p) => ({ at: p.at, value: p.mean_ms }))} /></div>
          {!report?.operations.length ? <p>Sem amostras no período.</p> : <div className={styles.table}><table><thead><tr><th>Operação</th><th>Amostras</th><th>Por segundo</th><th>Falhas 5xx</th><th>Recusas 4xx</th><th>p50</th><th>p95</th><th>p99</th></tr></thead><tbody>{report.operations.map((row) => <tr key={row.operation}><th>{operations[row.operation] ?? row.operation}</th><td>{row.count}</td><td>{numeric(row.rate_per_second)}</td><td>{row.errors}</td><td>{row.rejected}</td><td>{numeric(row.latency.p50, " ms")}</td><td>{numeric(row.latency.p95, " ms")}</td><td>{numeric(row.latency.p99, " ms")}</td></tr>)}</tbody></table></div>}
          <small>Percentis são limites superiores dos histogramas: p95 exige 20 amostras; p99, 100. Aquisição de conexão inclui abertura de conexão. Ciclos de trabalho não devem ser somados às requisições.</small>
        </section>
        <section className={styles.section}><h2>Filas, uploads e processamento</h2>
          <div className={styles.grid}>{capacity?.queues.map((queue) => <Metric key={queue.queue_class} title={operations[queue.queue_class]} value={`${numeric(queue.queued_total.value)} na fila`} detail={`${numeric(queue.processing_total.value)} em processamento · Idade: ${numeric(queue.oldest_record_age_seconds.value, " s")}`} />)}</div>
          {!capacity && <p>Filas não coletadas.</p>}
          <h3>Estado dos registros atualizados nos últimos 5 minutos</h3><p>Os estados incluem retentativas; não representam taxa de conclusões.</p>
          {!latest?.jobs.counts && <p>Processamento não coletado.</p>}
          {latest?.jobs.counts?.length === 0 && <p>Nenhum registro de processamento atualizado nesta janela.</p>}
          <ul>{latest?.jobs.counts?.map((row, index) => <li key={index}>{operations[row.kind ?? ""] ?? row.kind}: {jobStates[row.state] ?? row.state} — {row.count}</li>)}</ul>
          <h3>Workers</h3>{!latest?.workers.length && <p>Sinais de ciclo não coletados.</p>}
          <ul>{latest?.workers.map((worker) => <li key={worker.kind}>{operations[worker.kind]} — {states[worker.status]} · {worker.recent_instances}/{worker.observed_instances} instâncias com ciclo recente · Último progresso: {date(worker.last_progress_at)}</li>)}</ul>
          <p>Ciclo antigo significa ausência de confirmação recente. Um trabalho longo pode continuar em execução.</p>
          <h3>Uploads e integrações</h3>{!latest?.uploads && <p>Uploads não coletados.</p>}{!latest?.integrations && <p>Integrações não coletadas.</p>}<ul>{latest?.uploads?.map((row, i) => <li key={`u${i}`}>Lotes de upload: {jobStates[row.state]} — {row.count}</li>)}{latest?.integrations?.map((row, i) => <li key={`i${i}`}>{operations[row.kind ?? ""]}: {jobStates[row.state]} — {row.count}</li>)}</ul>
        </section>
        <section className={styles.section}><h2>Servidor e armazenamento</h2><p>Fonte do host: {states[latest?.host.status ?? "not_collected"]} · {date(host?.collected_at)}. Quotas e provisionamento OCI ainda não verificados.</p>
          <div className={styles.grid}><Trend label="Uso de CPU" unit="%" points={(report?.history ?? []).map((p) => ({ at: p.at, value: p.host.data?.cpu_percent ?? null }))} />
            <Metric title="Entrada de rede" value={numeric(host?.network_in_bytes_per_second, " B/s")} /><Metric title="Saída de rede" value={numeric(host?.network_out_bytes_per_second, " B/s")} />
            <Metric title="Leitura em disco" value={numeric(host?.io_read_bytes_per_second, " B/s")} /><Metric title="Escrita em disco" value={numeric(host?.io_write_bytes_per_second, " B/s")} />
            <Metric title="Fotos cadastradas" value={numeric(latest?.storage.registered_photos)} /><Metric title="Arquivos cadastrados" value={bytes(latest?.storage.registered_file_bytes)} detail={`Originais e prévias registrados · Inventário: ${date(latest?.storage.inventory_at)}`} />
            {!latest?.storage.inventory_complete && <Metric title="Inventário parcial de arquivos" value={bytes(latest?.storage.verified_file_bytes_lower_bound)} detail="Limite inferior verificado; não representa o total. Histórico, temporários e biometria ficam fora deste inventário." />}
            <Metric title="Armazenamento provisionado OCI" value={bytes(latest?.storage.provisioned_bytes)} /><Metric title="Quota verificada" value={bytes(latest?.storage.verified_quota_bytes)} />
          </div>
        </section>
      </>}
      {permissions.tree && <section className={styles.section}><h2>Fotógrafos e clientes</h2><p>Atividade indica interação autenticada observada. Sessão válida não comprova presença. Cada conta permanece independente.</p><UserTree key={revision} denied={revoke} /></section>}
      {permissions.incidents && <section className={styles.section}><h2>Incidentes e alertas</h2>{!incidents ? <p>Indisponível.</p> : <>
        {!incidents.active.length && <p>Sem alertas ativos registrados. Confira também a atualidade da coleta.</p>}
        <ul>{incidents.active.map((item) => <li key={item.code}><strong>{incidentLabel(item.code)}</strong> · desde {date(item.started_at)} · observado {numeric(item.evidence.observed)}, limiar {numeric(item.evidence.threshold)}<p>Compare a operação, as filas e os recursos no mesmo período antes de atribuir causa ou expandir infraestrutura.</p></li>)}</ul>
        <details><summary>Mudanças de estado</summary><ul>{incidents.history.map((item, index) => <li key={index}>{date(item.at)} · {incidentLabel(item.code)} · {item.state === "active" ? "Alerta ativado" : states[item.state] ?? item.state}</li>)}</ul>{incidents.history_truncated && <p>Histórico limitado às 200 transições mais recentes. Reduza o período.</p>}</details>
      </>}</section>}
      {permissions.metrics && <><InstallationDiagnostics /><section className={styles.section}><h2>Qualidade da coleta</h2><p>Versão: {report?.version ?? "Não informada"} · Ambiente: {report?.environment ?? "Não informado"}.</p><p>Observações perdidas no processo coletor: {numeric(latest?.quality.lost_observations)} · Falhas de coleta: {numeric(latest?.quality.collection_failures)}.</p><p>A coleta usa buffers limitados, sujeitos a perda em reinício. Fontes sem dados continuam desconhecidas; nenhum valor deste painel é garantia de capacidade máxima.</p></section></>}
    </>}
  </div>;
}
