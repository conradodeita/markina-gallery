import type { Snapshot } from "../capacity-report";

export type Host = { status: string; reason?: string | null; data: {
  source: string; scope: string; collected_at: string; cpu_percent: number | null;
  memory_total_bytes: number | null; memory_available_bytes: number | null;
  disk_total_bytes: number | null; disk_free_bytes: number | null;
  network_in_bytes_per_second: number | null; network_out_bytes_per_second: number | null;
  io_read_bytes_per_second: number | null; io_write_bytes_per_second: number | null;
} | null };
export type Count = { kind?: string; state: string; count: number };
export type Report = {
  generated_at: string; state: string; last_collected_at: string | null; age_seconds: number | null;
  collection_enabled: boolean; stale_seconds: number; active_alerts: number; version: string | null; environment: string | null;
  operations: { operation: string; count: number; errors: number; rejected: number; timeouts: number; error_percent: number;
    rate_per_second: number; mean_ms: number; latency: { samples: number; p50: number | null; p95: number | null; p99: number | null } }[];
  http_history: { at: string; count: number; errors: number; mean_ms: number }[];
  history: { at: string; host: Host; queues: { kind: string; queued: number | null; processing: number | null }[] }[];
  latest: { host: Host; capacity: Snapshot | null; jobs: { counts: Count[] | null };
    integrations: Count[] | null; uploads: Count[] | null;
    storage: { registered_photos: number | null; registered_file_bytes: number | null; provisioned_bytes: number | null; verified_quota_bytes: number | null; inventory_at?: string | null; inventory_complete?: boolean; verified_file_bytes_lower_bound?: number | null };
    workers: { kind: string; recent_instances: number; observed_instances: number; last_cycle_at: string; last_progress_at: string | null; status: string }[];
    database_waits: { lock_waiters?: number | null; idle_transactions?: number | null; unknown_states?: number | null };
    quality: { lost_observations: number | null; collection_failures: number | null };
  } | null;
};
export type Incidents = { active: { code: string; started_at: string; updated_at: string; evidence: { observed: number; threshold: number } }[];
  history: { code: string; state: string; at: string }[]; history_truncated: boolean };

export const states: Record<string, string> = { healthy: "Saudável", attention: "Atenção", critical: "Crítico", stale: "Dados desatualizados", unknown: "Desconhecido", partial: "Cobertura parcial", observed: "Coletado", not_collected: "Não coletado", unavailable: "Indisponível", permission_denied: "Sem permissão", active: "Ativo agora", recent: "Atividade recente", valid_session: "Sessão válida", inactive: "Sem atividade recente", resolved: "Recuperado", pending: "Em observação" };
export const operations: Record<string, string> = { "http.auth": "Autenticação", "http.upload": "Uploads", "http.preview": "Prévias e capas", "http.gallery": "Galerias", "http.checkout": "Carrinho e checkout", "http.other": "Outras requisições", "pool.acquire": "Aquisição de conexão", "work.media": "Geração de prévias", "work.preview_adjustment": "Ajuste de prévias", "work.search": "Busca facial", "work.index": "Indexação facial", "work.maintenance": "Manutenção facial", "work.general": "Ciclo geral de tarefas", media: "Mídia", preview_adjustment: "Ajuste de prévias", search: "Busca facial", index: "Indexação facial", maintenance: "Manutenção facial", general: "Worker geral", whatsapp: "WhatsApp", email: "E-mail" };
export function numeric(value: number | null | undefined, unit = "") { return value == null ? "Não coletado" : `${value.toLocaleString("pt-BR", { maximumFractionDigits: 2 })}${unit}`; }
export function bytes(value: number | null | undefined) { return value == null ? "Não coletado" : numeric(value / 1024 ** 3, " GiB"); }
export function date(value: string | null | undefined) { return value ? new Date(value).toLocaleString("pt-BR") : "Não coletado"; }

export function incidentLabel(code: string) {
  const [prefix, ...rest] = code.split(".");
  if (prefix === "cpu") return "CPU com uso elevado";
  if (prefix === "memory") return "Pouca memória disponível";
  const labels: Record<string, string> = { errors: "Erros confirmados", latency: "Latência elevada", rejected: "Requisições recusadas", queue: "Fila antiga", worker: "Sinal de worker desatualizado", progress: "Progresso sem confirmação recente", failed: "Falhas registradas", pool: "Ocupação do pool", disk: "Pouco espaço em disco", host: "Coleta do host desatualizada" };
  return `${labels[prefix] ?? "Alerta operacional"}${operations[rest.join(".")] ? ` · ${operations[rest.join(".")]}` : ""}`;
}
