import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CapacityDiagnostics } from "./capacity-diagnostics";

afterEach(() => vi.unstubAllGlobals());

const metric = (value: number | null, unit = "jobs", reason: string | null = null) => ({
  value, unit, evidence: value === null ? "unavailable" : "observed",
  scope: "application_database", source: "media_job", collected_at: "2026-09-30T10:00:00Z", reason,
});

function snapshot() {
  const states = { active: metric(1, "connections"), idle: metric(0, "connections"), idle_in_transaction: metric(null, "connections", "field_unavailable"), other: metric(0, "connections"), unknown: metric(0, "connections") };
  const queue = (queue_class: string) => ({
    queue_class, queued_total: metric(0), scheduled_total: metric(0),
    claim_candidates_total: metric(null, "jobs", "field_unavailable"), processing_total: metric(0),
    blocked_dependency_total: metric(null, "jobs", "field_unavailable"), reclaimable_total: metric(0),
    oldest_record_age_seconds: { ...metric(4.5, "seconds"), evidence: "estimated" },
    oldest_due_age_seconds: metric(null, "seconds", "empty_queue"),
    oldest_updated_age_seconds: metric(null, "seconds", "empty_queue"), wait_semantics: "created_age_estimate",
  });
  return {
    collection_started_at: "2026-09-30T10:00:00Z", collection_finished_at: "2026-09-30T10:00:01Z", cached: false,
    database: { database_client_connections: states, server_client_connections: states, max_connections: metric(null, "connections", "field_unavailable"), superuser_reserved_connections: metric(null, "connections", "field_unavailable"), reserved_connections: metric(null, "connections", "field_unavailable") },
    pool: { pool_class: "queue_pool", finite_limit: true, unbounded_overflow: false, max_overflow: metric(3, "connections"), checked_in: metric(0, "connections"), checked_out: metric(1, "connections"), open_connections_estimate: metric(1, "connections"), potential_max: metric(5, "connections"), acquisition_timeout_seconds: metric(30, "seconds"), wait_seconds: metric(null, "seconds", "field_unavailable"), timeout_count: metric(null, "connections", "field_unavailable") },
    queues: ["media", "preview_adjustment", "search", "index", "maintenance"].map(queue),
    connection_budget: { status: "unavailable", potential_connections: metric(null, "connections", "process_inventory_missing"), budget_headroom: metric(null, "connections", "process_inventory_missing"), limitations: ["process_inventory_missing"] },
    coverage: ["media", "preview_adjustment", "search", "index", "maintenance"], limitations: [],
  };
}

describe("diagnóstico local de capacidade", () => {
  it("fica recolhido sem requisitar e mostra zero observado e indisponibilidade após consulta", async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify(snapshot()), { status: 200 }));
    vi.stubGlobal("fetch", fetcher);
    render(<CapacityDiagnostics />);
    expect(fetcher).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Consultar diagnóstico" }));
    expect(await screen.findByText(/Snapshot em cache|Coletado agora/)).toBeTruthy();
    expect(fetcher).toHaveBeenCalledTimes(1);
    expect(screen.getAllByText(/0 tarefas · observado/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Indisponível/).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Ativas").length).toBe(2);
    expect(screen.getByText(/Orçamento global/)).toBeTruthy();
    expect(screen.getAllByText(/UTC/).length).toBeGreaterThan(0);
    expect(screen.getByText(/Escopos: processo da API respondente/)).toBeTruthy();
    expect(screen.getByText(/Cobertura: Mídia, Ajuste de prévias/)).toBeTruthy();
    expect(screen.queryByRole("spinbutton")).toBeNull();
  });

  it("remove o snapshot quando atualização perde autorização e permite nova tentativa", async () => {
    const fetcher = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify(snapshot()), { status: 200 }))
      .mockResolvedValueOnce(new Response(null, { status: 403 }));
    vi.stubGlobal("fetch", fetcher);
    render(<CapacityDiagnostics />);
    fireEvent.click(screen.getByRole("button", { name: "Consultar diagnóstico" }));
    await screen.findByText(/Snapshot em cache|Coletado agora/);
    fireEvent.click(screen.getByRole("button", { name: "Atualizar agora" }));
    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(screen.queryByText(/Coletado agora/)).toBeNull();
    expect(screen.getByText(/sessão administrativa não está mais autorizada/i)).toBeTruthy();
  });

  it("cancela a consulta em andamento ao desmontar", async () => {
    let signal: AbortSignal | undefined;
    const fetcher = vi.fn((_input: RequestInfo | URL, init?: RequestInit) => {
      signal = init?.signal as AbortSignal;
      return new Promise<Response>(() => {});
    });
    vi.stubGlobal("fetch", fetcher);
    const view = render(<CapacityDiagnostics />);
    fireEvent.click(screen.getByRole("button", { name: "Consultar diagnóstico" }));
    fireEvent.click(screen.getByRole("button", { name: "Recolher" }));
    fireEvent.click(screen.getByRole("button", { name: "Consultar diagnóstico" }));
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(1));
    view.unmount();
    expect(signal?.aborted).toBe(true);
  });

  it("explica cache e mantém idade estimada distinta de observação", async () => {
    const cached = snapshot();
    cached.cached = true;
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(cached), { status: 200 })));
    render(<CapacityDiagnostics />);
    fireEvent.click(screen.getByRole("button", { name: "Consultar diagnóstico" }));
    expect(await screen.findByText(/Snapshot em cache do processo/)).toBeTruthy();
    expect(screen.getAllByText("4,5 s · estimado").length).toBeGreaterThan(0);
  });

  it("expõe a seção recolhida como disclosure acessível por teclado", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(snapshot()), { status: 200 })));
    render(<CapacityDiagnostics />);
    const user = userEvent.setup();
    const button = screen.getByRole("button", { name: "Consultar diagnóstico" });
    await user.tab();
    expect(document.activeElement).toBe(button);
    expect(button.getAttribute("aria-expanded")).toBe("false");
    expect(button.getAttribute("aria-controls")).toBe("capacity-diagnostics-panel");
    expect(document.getElementById("capacity-diagnostics-panel")?.hasAttribute("hidden")).toBe(true);
    await user.keyboard("{Enter}");
    expect(await screen.findByText(/Coletado agora/)).toBeTruthy();
    expect(button.getAttribute("aria-expanded")).toBe("true");
  });

  it("isola erro de rede e permite tentar novamente", async () => {
    const fetcher = vi.fn()
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValueOnce(new Response(JSON.stringify(snapshot()), { status: 200 }));
    vi.stubGlobal("fetch", fetcher);
    render(<CapacityDiagnostics />);
    fireEvent.click(screen.getByRole("button", { name: "Consultar diagnóstico" }));
    expect(await screen.findByText("Não foi possível consultar o diagnóstico agora.")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
    expect(await screen.findByText(/Coletado agora/)).toBeTruthy();
    expect(fetcher).toHaveBeenCalledTimes(2);
  });
});
