import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { MediaArchiveRecoveryPanel } from "./media-archive-recovery-panel";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

const cycleId = "11111111-1111-4111-8111-111111111111";
const candidate = {
  cycle_id: cycleId,
  folder_id: "22222222-2222-4222-8222-222222222222",
  folder_name: "Ensaio arquivado",
  cycle_number: 1,
  archived_at: "2026-11-08T12:00:00Z",
};
const recovery = {
  operation_id: "33333333-3333-4333-8333-333333333333",
  cycle_id: cycleId,
  folder_id: candidate.folder_id,
  folder_name: candidate.folder_name,
  status: "queued",
  duration_days: 30,
  fee_credits: 2,
  owner_exempt: false,
  created_at: "2026-11-09T12:00:00Z",
  completed_at: null,
  progress: { stage: "queued", verified_objects: 0, total_objects: 4 },
};

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

function fixtureFetch({
  pricing = {
    recovery_fee_credits: 2, configured: true, owner_exempt: false,
    available_credits: 4, duration_days: [30], can_manage: false,
  },
  candidates = [candidate],
  initialRecoveries = [] as typeof recovery[],
}: {
  pricing?: Record<string, unknown>;
  candidates?: typeof candidate[];
  initialRecoveries?: typeof recovery[];
} = {}) {
  let recoveries = initialRecoveries;
  const fetcher = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path.endsWith("/recovery-pricing") && init?.method === "PUT") {
      const payload = JSON.parse(String(init.body));
      return json({ ...pricing, recovery_fee_credits: payload.recovery_fee_credits,
        configured: payload.recovery_fee_credits !== null });
    }
    if (path === "/api/admin/media-archive/recovery-pricing") return json(pricing);
    if (path === "/api/admin/media-archive/recovery-candidates") return json({ items: candidates });
    if (path.startsWith("/api/admin/media-archive/recoveries?")) return json({ items: recoveries });
    if (path.endsWith("/cycles/" + cycleId + "/recovery")) {
      recoveries = [recovery, ...recoveries];
      return json(recovery, 202);
    }
    throw new Error("Rota inesperada: " + path);
  });
  return fetcher;
}

describe("painel de recuperação de arquivos frios", () => {
  it("acompanha a conclusão sem repetir o pedido e avisa a carteira", async () => {
    const baseFetch = fixtureFetch();
    let reads = 0;
    const fetcher = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input).startsWith("/api/admin/media-archive/recoveries?") && ++reads >= 3) {
        return json({ items: [{ ...recovery, status: "completed", completed_at: "2026-11-09T12:00:05Z" }] });
      }
      return baseFetch(input, init);
    });
    vi.stubGlobal("fetch", fetcher);
    const onWalletChange = vi.fn();
    render(<MediaArchiveRecoveryPanel onWalletChange={onWalletChange} />);
    fireEvent.click(await screen.findByRole("button", { name: "Solicitar recuperação" }));
    expect(await screen.findByText("Na fila")).toBeTruthy();
    expect(await screen.findByText("Concluída", {}, { timeout: 4500 })).toBeTruthy();
    expect(onWalletChange).toHaveBeenCalledTimes(2);
    expect(fetcher.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(1);
  });
  it("mostra 30 dias fixos e envia uma chave idempotente ao pedir uma pasta", async () => {
    const fetcher = fixtureFetch();
    vi.stubGlobal("fetch", fetcher);
    vi.stubGlobal("crypto", { randomUUID: () => "synthetic-request-key" });
    render(<MediaArchiveRecoveryPanel />);

    expect(await screen.findByText("Ensaio arquivado")).toBeTruthy();
    expect(screen.getByText(/2 créditos por pasta e ciclo/)).toBeTruthy();
    expect(screen.getByText(/30 dias a partir da conclusão/)).toBeTruthy();
    expect(screen.queryByRole("combobox", { name: "Prazo de acesso" })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Solicitar recuperação" }));

    expect(await screen.findByRole("status")).toBeTruthy();
    const request = fetcher.mock.calls.find(([path, init]) => String(path).includes("/cycles/" + cycleId + "/recovery") && init?.method === "POST");
    expect(JSON.parse(String(request?.[1]?.body))).toEqual({ duration_days: 30, idempotency_key: "synthetic-request-key" });
    expect(await screen.findByText("Na fila")).toBeTruthy();
  });

  it("não permite pedir sem saldo suficiente e orienta a adquirir créditos", async () => {
    vi.stubGlobal("fetch", fixtureFetch({
      pricing: {
        recovery_fee_credits: 3, configured: true, owner_exempt: false,
        available_credits: 2, duration_days: [7, 14, 30], can_manage: false,
      },
    }));
    render(<MediaArchiveRecoveryPanel />);
    expect(await screen.findByText(/Saldo insuficiente/)).toBeTruthy();
    expect(screen.getByRole("link", { name: "Adquira um pacote de créditos" }).getAttribute("href")).toBe("#credit-packages");
    expect(screen.getByRole("button", { name: "Solicitar recuperação" })).toHaveProperty("disabled", true);
  });

  it("protege a mudança da taxa com senha atual e TOTP e pode desconfigurar novos pedidos", async () => {
    const fetcher = fixtureFetch({
      pricing: {
        recovery_fee_credits: 2, configured: true, owner_exempt: true,
        available_credits: null, duration_days: [7, 14, 30], can_manage: true,
      },
      candidates: [],
    });
    vi.stubGlobal("fetch", fetcher);
    vi.stubGlobal("crypto", { randomUUID: () => "synthetic-pricing-request" });
    render(<MediaArchiveRecoveryPanel />);

    fireEvent.change(await screen.findByLabelText("Nova taxa em créditos"), { target: { value: "" } });
    fireEvent.change(screen.getByLabelText("Senha atual do proprietário"), { target: { value: "synthetic-password" } });
    fireEvent.change(screen.getByLabelText("Código do autenticador"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Salvar taxa" }));

    expect(await screen.findByText("Novos pedidos pagos foram suspensos até definir uma taxa.")).toBeTruthy();
    const update = fetcher.mock.calls.find(([path, init]) => String(path).endsWith("/recovery-pricing") && init?.method === "PUT");
    expect(JSON.parse(String(update?.[1]?.body))).toMatchObject({
      request_id: "synthetic-pricing-request", recovery_fee_credits: null,
      current_password: "synthetic-password", totp_code: "123456",
    });
    await waitFor(() => expect(screen.queryByDisplayValue("synthetic-password")).toBeNull());
  });

  it("envia uma vez por clique e reutiliza o mesmo pedido após erro de comunicação", async () => {
    const requestBodies: Array<{ duration_days: number; idempotency_key: string }> = [];
    let recoveries: typeof recovery[] = [];
    let finishFirstRequest: ((response: Response) => void) | null = null;
    let generatedKey = 0;
    vi.stubGlobal("crypto", { randomUUID: () => `synthetic-recovery-${++generatedKey}` });
    const fetcher = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path === "/api/admin/media-archive/recovery-pricing") return Promise.resolve(json({
        recovery_fee_credits: 2, configured: true, owner_exempt: false,
        available_credits: 4, duration_days: [7, 14, 30], can_manage: false,
      }));
      if (path === "/api/admin/media-archive/recovery-candidates") return Promise.resolve(json({ items: [candidate] }));
      if (path.startsWith("/api/admin/media-archive/recoveries?")) return Promise.resolve(json({ items: recoveries }));
      if (path.endsWith(`/cycles/${cycleId}/recovery`) && init?.method === "POST") {
        const body = JSON.parse(String(init.body)) as { duration_days: number; idempotency_key: string };
        requestBodies.push(body);
        if (requestBodies.length === 1) {
          return new Promise<Response>((resolve) => { finishFirstRequest = resolve; });
        }
        recoveries = [{ ...recovery, duration_days: body.duration_days }];
        return Promise.resolve(json(recoveries[0], 202));
      }
      throw new Error(`Rota inesperada: ${path}`);
    });
    vi.stubGlobal("fetch", fetcher);
    render(<MediaArchiveRecoveryPanel />);

    const button = await screen.findByRole("button", { name: "Solicitar recuperação" });
    fireEvent.click(button);
    expect(button).toHaveProperty("disabled", true);
    fireEvent.click(button);
    expect(requestBodies).toHaveLength(1);
    await act(async () => {
      if (!finishFirstRequest) throw new Error("A solicitação não iniciou o POST pendente.");
      finishFirstRequest(json({ detail: "Resposta temporariamente indisponível." }, 503));
    });
    expect(await screen.findByRole("alert")).toHaveProperty("textContent", expect.stringContaining("temporariamente"));
    expect(button).toHaveProperty("disabled", false);
    fireEvent.click(button);
    expect(await screen.findByText("Na fila")).toBeTruthy();
    expect(requestBodies).toHaveLength(2);
    expect(requestBodies[0].duration_days).toBe(30);
    expect(requestBodies[1]).toEqual(requestBodies[0]);
  });

  it("exibe a contagem verificada e mantém finalização sem declarar sucesso", async () => {
    const fetcher = fixtureFetch({ initialRecoveries: [
      { ...recovery, status: "processing", progress: { stage: "downloading", verified_objects: 2, total_objects: 4 } },
      { ...recovery, operation_id: "another-recovery", status: "processing",
        progress: { stage: "finishing", verified_objects: 4, total_objects: 4 } },
    ] });
    vi.stubGlobal("fetch", fetcher);
    render(<MediaArchiveRecoveryPanel />);

    const download = await screen.findByRole("progressbar", { name: /2 de 4 arquivos verificados/ });
    expect(download.getAttribute("value")).toBe("2");
    expect(download.getAttribute("max")).toBe("4");
    const finish = screen.getByRole("progressbar", { name: /Finalizando a liberação/ });
    expect(finish.hasAttribute("value")).toBe(false);
    expect(screen.queryByText("Concluída")).toBeNull();
  });

  it("bloqueia taxa, senha e TOTP enquanto a atualização aguarda resposta", async () => {
    let pricing = {
      recovery_fee_credits: 2, configured: true, owner_exempt: true,
      available_credits: null, duration_days: [7, 14, 30], can_manage: true,
    };
    let finishPricing: ((response: Response) => void) | null = null;
    const fetcher = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path === "/api/admin/media-archive/recovery-pricing") return Promise.resolve(json(pricing));
      if (path === "/api/admin/media-archive/recovery-candidates") return Promise.resolve(json({ items: [] }));
      if (path.startsWith("/api/admin/media-archive/recoveries?")) return Promise.resolve(json({ items: [] }));
      if (path.endsWith("/recovery-pricing") && init?.method === "PUT") {
        const payload = JSON.parse(String(init.body));
        pricing = { ...pricing, recovery_fee_credits: payload.recovery_fee_credits, configured: true };
        return new Promise<Response>((resolve) => { finishPricing = resolve; });
      }
      throw new Error(`Rota inesperada: ${path}`);
    });
    vi.stubGlobal("fetch", fetcher);
    render(<MediaArchiveRecoveryPanel />);

    const fee = await screen.findByLabelText("Nova taxa em créditos");
    const password = screen.getByLabelText("Senha atual do proprietário");
    const totp = screen.getByLabelText("Código do autenticador");
    fireEvent.change(fee, { target: { value: "5" } });
    fireEvent.change(password, { target: { value: "synthetic-password" } });
    fireEvent.change(totp, { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Salvar taxa" }));

    await waitFor(() => {
      expect(fee).toHaveProperty("disabled", true);
      expect(password).toHaveProperty("disabled", true);
      expect(totp).toHaveProperty("disabled", true);
    });
    await act(async () => {
      if (!finishPricing) throw new Error("A atualização não iniciou o PUT pendente.");
      finishPricing(json(pricing));
    });
    expect(await screen.findByText("Taxa global de recuperação atualizada.")).toBeTruthy();
  });
});
