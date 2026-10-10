import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import SystemMonitorPage, { Trend } from "./page";
import { UserTree } from "./user-tree";
import { MonitorActivity } from "../../monitor-activity";
import { PUSH_LOGOUT_EVENT } from "../../push-device";

vi.mock("next/navigation", () => ({ usePathname: () => "/library" }));
const json = (body: unknown, status = 200) => Promise.resolve(new Response(JSON.stringify(body), { status }));
const grants = { metrics: true, tree: false, incidents: false, export: true };
const summary = { collection_enabled: false, state: "unknown", last_collected_at: null,
  operations: [], history: [], http_history: [], latest: null, active_alerts: 0 };

afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe("Monitor do sistema sem servidor", () => {
  it("carrega resumo, incidentes e árvore sem disputar as duas leituras disponíveis", async () => {
    let active = 0;
    let peak = 0;
    const fetcher = vi.fn(async (url: string) => {
      if (url.includes("/capabilities")) return json({ ...grants, tree: true, incidents: true });
      if (url.includes("installation-capabilities")) return json({});
      active++;
      peak = Math.max(peak, active);
      const refused = active > 2;
      await new Promise((resolve) => setTimeout(resolve, 20));
      active--;
      if (refused) return json({}, 429);
      if (url.includes("/tree")) return json({ items: [{ id: "t1", label: "Fotógrafo photographer@example.invalid", sessions: 0, state: "inactive", last_activity: null }], next_cursor: null, collected_at: "2026-10-09T12:00:00Z" });
      return json(url.includes("/incidents") ? { active: [], history: [] } : summary);
    });
    vi.stubGlobal("fetch", fetcher);
    render(<SystemMonitorPage />);
    await screen.findByRole("button", { name: /Fotógrafo photographer@example.invalid/ });
    await screen.findByText(/Sem alertas ativos registrados/);
    expect(peak).toBeLessThanOrEqual(2);
    expect(screen.queryByText(/Uma fonte não respondeu/)).toBeNull();
    expect(screen.queryByText(/Não foi possível consultar a árvore/)).toBeNull();
  });

  it("mantém máximo zero quando todas as amostras observadas são zero", () => {
    render(<Trend label="Erros" points={[{ at: "2026-10-09T12:00:00Z", value: 0 }]} />);
    expect(screen.getByRole("img", { name: "Erros: 1 amostras; máximo 0" })).toBeTruthy();
  });

  it("não busca dados sensíveis quando nenhuma capability foi concedida", async () => {
    const fetcher = vi.fn(() => json({})); vi.stubGlobal("fetch", fetcher);
    render(<SystemMonitorPage />);
    await screen.findByText(/Sem permissão para o monitor/);
    expect(fetcher.mock.calls).toHaveLength(1);
    expect(screen.queryByText("Gerar relatório JSON")).toBeNull();
  });

  it("mostra lacunas sem zeros inventados e preserva o gate separado do card", async () => {
    const fetcher = vi.fn((url: string) => json(url.includes("system-monitor/capabilities") ? grants : url.includes("installation-capabilities") ? { capacity_diagnostics: false } : summary));
    vi.stubGlobal("fetch", fetcher);
    render(<SystemMonitorPage />);
    await screen.findByText("CPU");
    await waitFor(() => expect(fetcher.mock.calls.some(([url]) => url.includes("installation-capabilities"))).toBe(true));
    expect(screen.getAllByText("Não coletado").length).toBeGreaterThan(4);
    expect(screen.getByText("Desconhecido")).toBeTruthy();
    expect(fetcher.mock.calls.some(([url]) => url.includes("/tree") || url.includes("/incidents") || url.includes("capacity-observability"))).toBe(false);
  });

  it("sinaliza dados antigos e limpa a interface quando a sessão termina", async () => {
    vi.stubGlobal("fetch", vi.fn((url: string) => json(url.includes("system-monitor/capabilities") ? grants : url.includes("installation-capabilities") ? {} : { ...summary, state: "healthy", collection_enabled: true, last_collected_at: "2020-01-01T00:00:00Z", age_seconds: 3600, stale_seconds: 180 })));
    render(<SystemMonitorPage />);
    await screen.findByText("Dados desatualizados");
    act(() => { window.dispatchEvent(new Event(PUSH_LOGOUT_EVENT)); });
    await screen.findByText(/Sem permissão para o monitor/);
    expect(screen.queryByText("CPU")).toBeNull();
  });

  it("exporta apenas sob ação explícita e recusa download após logout", async () => {
    let resolveReport!: (response: Response) => void;
    let signal: AbortSignal | undefined;
    const fetcher = vi.fn((url: string, options?: RequestInit) => {
      if (url.includes("/report?")) { signal = options?.signal as AbortSignal; return new Promise<Response>((resolve) => { resolveReport = resolve; }); }
      return json(url.includes("system-monitor/capabilities") ? grants : url.includes("installation-capabilities") ? {} : summary);
    });
    vi.stubGlobal("fetch", fetcher);
    const createObjectURL = vi.fn();
    vi.stubGlobal("URL", Object.assign(URL, { createObjectURL, revokeObjectURL: vi.fn() }));
    render(<SystemMonitorPage />);
    fireEvent.click(await screen.findByText("Gerar relatório JSON"));
    await waitFor(() => expect(fetcher.mock.calls.filter(([url]) => url.includes("/report?"))).toHaveLength(1));
    act(() => { window.dispatchEvent(new Event(PUSH_LOGOUT_EVENT)); });
    expect(signal?.aborted).toBe(true);
    await act(async () => { resolveReport(new Response("{}")); });
    expect(createObjectURL).not.toHaveBeenCalled();
  });

  it("carrega clientes somente ao expandir e pagina sem reiniciar toda a árvore", async () => {
    const fetcher = vi.fn((url: string) => json({ items: url.includes("tenant_id=") ? [{ id: "c1", label: "Cliente sintético", sessions: 1, state: "valid_session", last_activity: null }] : [{ id: url.includes("cursor=") ? "t2" : "t1", label: url.includes("cursor=") ? "Fotógrafo B" : "Fotógrafo A", clients: 1, sessions: 0, state: "inactive", last_activity: null }], next_cursor: url.includes("cursor=") || url.includes("tenant_id=") ? null : "t1", collected_at: "2026-10-09T12:00:00Z" }));
    vi.stubGlobal("fetch", fetcher);
    render(<UserTree denied={vi.fn()} />);
    const account = await screen.findByRole("button", { name: /Fotógrafo A/ });
    expect(fetcher).toHaveBeenCalledTimes(1);
    fireEvent.click(account);
    await screen.findByText("Cliente sintético");
    expect(screen.getByText("Sessão válida", { selector: "span" })).toBeTruthy();
    expect(screen.queryByText("Ativo agora", { selector: "span" })).toBeNull();
    fireEvent.click(screen.getByText("Carregar mais"));
    await screen.findByRole("button", { name: /Fotógrafo B/ });
    expect(fetcher).toHaveBeenCalledTimes(3);
    expect(fetcher.mock.calls[1][0]).toContain("tenant_id=t1");
    expect(fetcher.mock.calls[2][0]).toContain("cursor=t1");
  });

  it("descarta a árvore quando o backend revoga a permissão", async () => {
    const denied = vi.fn();
    vi.stubGlobal("fetch", vi.fn(() => json({}, 403)));
    render(<UserTree denied={denied} />);
    await waitFor(() => expect(denied).toHaveBeenCalledOnce());
    expect(screen.queryByText("Cliente sintético")).toBeNull();
  });

  it("sinaliza somente interação visível, limita frequência e respeita logout", async () => {
    let instant = 100000;
    vi.spyOn(Date, "now").mockImplementation(() => instant);
    const visibility = vi.spyOn(document, "visibilityState", "get").mockReturnValue("visible");
    const fetcher = vi.fn(() => json({ enabled: true })); vi.stubGlobal("fetch", fetcher);
    render(<MonitorActivity />);
    await act(async () => { await Promise.resolve(); });
    expect(fetcher).toHaveBeenCalledTimes(1);
    await act(async () => { fireEvent.pointerDown(window); });
    expect(fetcher).toHaveBeenCalledTimes(2);
    fireEvent.keyDown(window); expect(fetcher).toHaveBeenCalledTimes(2);
    instant += 61000; visibility.mockReturnValue("hidden");
    fireEvent.pointerDown(window); expect(fetcher).toHaveBeenCalledTimes(2);
    visibility.mockReturnValue("visible");
    await act(async () => { fireEvent.pointerDown(window); });
    expect(fetcher).toHaveBeenCalledTimes(3);
    instant += 61000;
    act(() => { window.dispatchEvent(new Event(PUSH_LOGOUT_EVENT)); });
    fireEvent.pointerDown(window); expect(fetcher).toHaveBeenCalledTimes(3);
  });
});


it("mantém o card autorizado exclusivamente no Monitor e sem coleta automática", async () => {
  const fetcher = vi.fn((url: string) => json(
    url.includes("system-monitor/capabilities") ? grants :
    url.includes("installation-capabilities") ? { capacity_diagnostics: true } : summary,
  ));
  vi.stubGlobal("fetch", fetcher);
  render(<SystemMonitorPage />);
  expect(await screen.findByRole("heading", { name: "Capacidade e filas" })).toBeTruthy();
  expect(screen.getByText("Diagnóstico sob demanda")).toBeTruthy();
  expect(screen.getByRole("button", { name: "Consultar diagnóstico" }).getAttribute("aria-expanded")).toBe("false");
  expect(fetcher.mock.calls.some(([url]) => url.includes("capacity-observability"))).toBe(false);
});
