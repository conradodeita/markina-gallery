import { describe, expect, it } from "vitest";

import { formatCapacityReport, type Metric, type Queue, type Snapshot } from "./capacity-report";

const at = "2026-09-30T10:00:00Z";

function metric(
  value: number | null,
  unit: Metric["unit"] = "jobs",
  evidence: Metric["evidence"] = value === null ? "unavailable" : "observed",
  source: Metric["source"] = "media_job",
  scope: Metric["scope"] = "application_database",
  reason: Metric["reason"] = value === null ? "field_unavailable" : null,
): Metric {
  return { value, unit, evidence, scope, source, collected_at: at, reason };
}

function queue(queue_class: Queue["queue_class"]): Queue {
  const source = queue_class === "media" ? "media_job" : queue_class === "preview_adjustment" ? "preview_adjustment" : "facial_job";
  return {
    queue_class,
    queued_total: metric(0, "jobs", "observed", source),
    scheduled_total: metric(1, "jobs", "observed", source),
    claim_candidates_total: metric(2, "jobs", "calculated", source),
    processing_total: metric(3, "jobs", "observed", source),
    blocked_dependency_total: metric(null, "jobs", "unavailable", "none", "application_database", "field_unavailable"),
    reclaimable_total: metric(0, "jobs", "observed", source),
    oldest_record_age_seconds: metric(4.5, "seconds", "estimated", source),
    oldest_due_age_seconds: metric(null, "seconds", "unavailable", "none", "application_database", "empty_queue"),
    oldest_updated_age_seconds: metric(null, "seconds", "unavailable", "none", "application_database", "empty_queue"),
    wait_semantics: queue_class === "preview_adjustment" ? "updated_age_estimate" : "created_age_estimate",
  };
}

function snapshot(): Snapshot {
  const states = {
    active: metric(1, "connections", "observed", "pg_stat_activity", "application_database"),
    idle: metric(0, "connections", "observed", "pg_stat_activity", "application_database"),
    idle_in_transaction: metric(null, "connections", "unavailable", "none", "application_database", "field_unavailable"),
    other: metric(0, "connections", "observed", "pg_stat_activity", "application_database"),
    unknown: metric(0, "connections", "observed", "pg_stat_activity", "application_database"),
  };
  return {
    schema_version: 1,
    collection_started_at: at,
    collection_finished_at: "2026-09-30T10:00:01Z",
    cached: false,
    database: {
      database_client_connections: states,
      server_client_connections: { ...states, active: { ...states.active, scope: "postgresql_server" } },
      max_connections: metric(100, "connections", "observed", "pg_settings", "postgresql_server"),
      superuser_reserved_connections: metric(3, "connections", "observed", "pg_settings", "postgresql_server"),
      reserved_connections: metric(null, "connections", "unavailable", "none", "postgresql_server", "field_unavailable"),
    },
    pool: {
      pool_class: "queue_pool",
      finite_limit: true,
      unbounded_overflow: false,
      base_size: metric(2, "connections", "observed", "sqlalchemy_pool", "responding_api_process"),
      max_overflow: metric(3, "connections", "observed", "sqlalchemy_pool", "responding_api_process"),
      checked_in: metric(0, "connections", "observed", "sqlalchemy_pool", "responding_api_process"),
      checked_out: metric(1, "connections", "observed", "sqlalchemy_pool", "responding_api_process"),
      open_connections_estimate: metric(1, "connections", "calculated", "sqlalchemy_pool", "responding_api_process"),
      potential_max: metric(5, "connections", "calculated", "sqlalchemy_pool", "responding_api_process"),
      acquisition_timeout_seconds: metric(30, "seconds", "observed", "sqlalchemy_pool", "responding_api_process"),
      wait_seconds: metric(null, "seconds", "unavailable", "none", "responding_api_process", "field_unavailable"),
      timeout_count: metric(null, "connections", "unavailable", "none", "responding_api_process", "field_unavailable"),
    },
    queues: [queue("maintenance"), queue("index"), queue("search"), queue("preview_adjustment"), queue("media")],
    connection_budget: {
      status: "unavailable",
      potential_connections: metric(null, "connections", "unavailable", "none", "postgresql_server", "process_inventory_missing"),
      budget_headroom: metric(null, "connections", "unavailable", "none", "postgresql_server", "external_consumers_unknown"),
      limitations: ["process_inventory_missing", "external_consumers_unknown"],
    },
    coverage: ["maintenance", "media", "index", "search", "preview_adjustment"],
    limitations: ["operational_reserve_unapproved", "external_consumers_unknown"],
  };
}

describe("formatCapacityReport", () => {
  it("gera relatório completo e canônico sem depender do navegador", () => {
    const report = formatCapacityReport(snapshot());

    expect(report.startsWith([
      "# Relatório de capacidade e filas",
      "",
      "- report_format: capacity-report/v1",
      "- schema_version: 1",
      "",
      "## Coleta",
      `- collection_started_at: ${at}`,
      "- collection_finished_at: 2026-09-30T10:00:01Z",
      "- cached: false",
    ].join("\n"))).toBe(true);
    expect(report).toContain("- open_connections_estimate: value=1 | unit=connections | evidence=calculated | scope=responding_api_process | source=sqlalchemy_pool | collected_at=2026-09-30T10:00:00Z | reason=null");
    expect(report).toContain("- oldest_record_age_seconds: value=4.5 | unit=seconds | evidence=estimated | scope=application_database | source=media_job | collected_at=2026-09-30T10:00:00Z | reason=null");
    expect(report).toContain("- oldest_due_age_seconds: value=null | unit=seconds | evidence=unavailable | scope=application_database | source=none | collected_at=2026-09-30T10:00:00Z | reason=empty_queue");
    expect(report).toContain("- idle: value=0 | unit=connections | evidence=observed");
    expect(report.indexOf("### media")).toBeLessThan(report.indexOf("### preview_adjustment"));
    expect(report.indexOf("### preview_adjustment")).toBeLessThan(report.indexOf("### search"));
    expect(report.indexOf("### search")).toBeLessThan(report.indexOf("### index"));
    expect(report.indexOf("### index")).toBeLessThan(report.indexOf("### maintenance"));
    expect(report.match(/: value=/g)).toHaveLength(69);
    expect(report).toContain("- queues: media, preview_adjustment, search, index, maintenance");
    expect(report.endsWith("- limitations: external_consumers_unknown, operational_reserve_unapproved")).toBe(true);
    expect(report).not.toContain("\r");
  });

  it("ignora propriedades extras, preserva lacunas e mantém saída determinística", () => {
    const first = snapshot() as Snapshot & { token?: string; database: Snapshot["database"] & { host?: string } };
    first.token = "SENTINELA_TOKEN_SECRETO";
    first.database.host = "SENTINELA_HOST_SECRETO";
    (first.queues[0] as Queue & { payload?: string }).payload = "SENTINELA_PAYLOAD_SECRETO";
    const second = snapshot();
    second.queues.reverse();
    second.connection_budget.limitations.reverse();
    second.limitations.reverse();

    const report = formatCapacityReport(first);

    expect(report).not.toContain("SENTINELA_");
    expect(report).toContain("value=null");
    expect(report).toContain("reason=process_inventory_missing");
    expect(report).toBe(formatCapacityReport(second));
  });
});
