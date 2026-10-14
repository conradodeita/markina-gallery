export type Evidence = "observed" | "calculated" | "estimated" | "unavailable";
export type Scope = "responding_api_process" | "application_database" | "postgresql_server";
export type Unit = "connections" | "jobs" | "seconds";
export type Source = "sqlalchemy_pool" | "pg_stat_activity" | "pg_settings" | "media_job" | "preview_adjustment" | "facial_job" | "none";
export type UnavailableReason =
  | "empty_queue"
  | "unsupported_backend"
  | "unsupported_pool"
  | "permission_denied"
  | "source_unavailable"
  | "query_timeout"
  | "collection_busy"
  | "inconsistent_timestamp"
  | "process_inventory_missing"
  | "external_consumers_unknown"
  | "operational_reserve_unapproved"
  | "field_unavailable";

export type Metric = {
  value: number | null;
  unit: Unit;
  evidence: Evidence;
  scope: Scope;
  source: Source;
  collected_at: string;
  reason: UnavailableReason | null;
};

export type QueueClass = "media" | "preview_adjustment" | "search" | "index" | "maintenance";

export type Queue = {
  queue_class: QueueClass;
  queued_total: Metric;
  scheduled_total: Metric;
  claim_candidates_total: Metric;
  processing_total: Metric;
  blocked_dependency_total: Metric;
  reclaimable_total: Metric;
  oldest_record_age_seconds: Metric;
  oldest_due_age_seconds: Metric;
  oldest_updated_age_seconds: Metric;
  wait_semantics: "created_age_estimate" | "updated_age_estimate" | "available_at_age_estimate" | "exact_wait_unavailable";
};

export type ConnectionStates = {
  active: Metric;
  idle: Metric;
  idle_in_transaction: Metric;
  other: Metric;
  unknown: Metric;
};

export type Snapshot = {
  schema_version: 1;
  collection_started_at: string;
  collection_finished_at: string;
  cached: boolean;
  database: {
    database_client_connections: ConnectionStates;
    server_client_connections: ConnectionStates;
    max_connections: Metric;
    superuser_reserved_connections: Metric;
    reserved_connections: Metric;
  };
  pool: {
    pool_class: "queue_pool" | "null_pool" | "other";
    finite_limit: boolean;
    unbounded_overflow: boolean;
    base_size: Metric;
    max_overflow: Metric;
    checked_in: Metric;
    checked_out: Metric;
    open_connections_estimate: Metric;
    potential_max: Metric;
    acquisition_timeout_seconds: Metric;
    wait_seconds: Metric;
    timeout_count: Metric;
  };
  queues: Queue[];
  connection_budget: {
    status: "unavailable";
    potential_connections: Metric;
    budget_headroom: Metric;
    limitations: UnavailableReason[];
  };
  coverage: QueueClass[];
  limitations: UnavailableReason[];
};

const QUEUE_ORDER: QueueClass[] = ["media", "preview_adjustment", "search", "index", "maintenance"];
const CONNECTION_STATE_ORDER: (keyof ConnectionStates)[] = ["active", "idle", "idle_in_transaction", "other", "unknown"];

function metricLine(name: string, metric: Metric): string {
  return `- ${name}: value=${metric.value === null ? "null" : String(metric.value)} | unit=${metric.unit} | evidence=${metric.evidence} | scope=${metric.scope} | source=${metric.source} | collected_at=${metric.collected_at} | reason=${metric.reason ?? "null"}`;
}

function appendConnectionStates(lines: string[], title: string, states: ConnectionStates): void {
  lines.push(`### ${title}`);
  for (const state of CONNECTION_STATE_ORDER) lines.push(metricLine(state, states[state]));
  lines.push("");
}

function orderedReasons(reasons: UnavailableReason[]): string {
  return [...reasons].sort().join(", ") || "none";
}

export function formatCapacityReport(snapshot: Snapshot): string {
  const lines = [
    "# Relatório de capacidade e filas",
    "",
    "- report_format: capacity-report/v1",
    `- schema_version: ${snapshot.schema_version}`,
    "",
    "## Coleta",
    `- collection_started_at: ${snapshot.collection_started_at}`,
    `- collection_finished_at: ${snapshot.collection_finished_at}`,
    `- cached: ${String(snapshot.cached)}`,
    "",
    "## Pool da API",
    `- pool_class: ${snapshot.pool.pool_class}`,
    `- finite_limit: ${String(snapshot.pool.finite_limit)}`,
    `- unbounded_overflow: ${String(snapshot.pool.unbounded_overflow)}`,
    metricLine("base_size", snapshot.pool.base_size),
    metricLine("max_overflow", snapshot.pool.max_overflow),
    metricLine("checked_in", snapshot.pool.checked_in),
    metricLine("checked_out", snapshot.pool.checked_out),
    metricLine("open_connections_estimate", snapshot.pool.open_connections_estimate),
    metricLine("potential_max", snapshot.pool.potential_max),
    metricLine("acquisition_timeout_seconds", snapshot.pool.acquisition_timeout_seconds),
    metricLine("wait_seconds", snapshot.pool.wait_seconds),
    metricLine("timeout_count", snapshot.pool.timeout_count),
    "",
    "## PostgreSQL",
    metricLine("max_connections", snapshot.database.max_connections),
    metricLine("superuser_reserved_connections", snapshot.database.superuser_reserved_connections),
    metricLine("reserved_connections", snapshot.database.reserved_connections),
    "",
  ];

  appendConnectionStates(lines, "Conexões no banco atual", snapshot.database.database_client_connections);
  appendConnectionStates(lines, "Conexões visíveis no servidor", snapshot.database.server_client_connections);

  lines.push("## Filas", "");
  for (const queueClass of QUEUE_ORDER) {
    const queue = snapshot.queues.find((candidate) => candidate.queue_class === queueClass);
    if (!queue) continue;
    lines.push(
      `### ${queueClass}`,
      `- queue_class: ${queue.queue_class}`,
      `- wait_semantics: ${queue.wait_semantics}`,
      metricLine("queued_total", queue.queued_total),
      metricLine("scheduled_total", queue.scheduled_total),
      metricLine("claim_candidates_total", queue.claim_candidates_total),
      metricLine("processing_total", queue.processing_total),
      metricLine("blocked_dependency_total", queue.blocked_dependency_total),
      metricLine("reclaimable_total", queue.reclaimable_total),
      metricLine("oldest_record_age_seconds", queue.oldest_record_age_seconds),
      metricLine("oldest_due_age_seconds", queue.oldest_due_age_seconds),
      metricLine("oldest_updated_age_seconds", queue.oldest_updated_age_seconds),
      "",
    );
  }

  lines.push(
    "## Orçamento global",
    `- status: ${snapshot.connection_budget.status}`,
    metricLine("potential_connections", snapshot.connection_budget.potential_connections),
    metricLine("budget_headroom", snapshot.connection_budget.budget_headroom),
    `- limitations: ${orderedReasons(snapshot.connection_budget.limitations)}`,
    "",
    "## Cobertura",
    `- queues: ${QUEUE_ORDER.filter((queueClass) => snapshot.coverage.includes(queueClass)).join(", ") || "none"}`,
    "",
    "## Limitações",
    `- limitations: ${orderedReasons(snapshot.limitations)}`,
  );

  return lines.join("\n");
}
