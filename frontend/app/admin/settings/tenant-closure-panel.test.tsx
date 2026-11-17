import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { PhotographerClosurePanel } from "./tenant-closure-panel";

type TestStatus = {
  lifecycle: "open" | "closing";
  credits_remaining: number;
  terms: { available: boolean; accepted: boolean; version: string | null; sha256: string | null };
  request: { requested_at: string; balance_snapshot: number } | null;
  blockers: { code: string; message: string }[];
};

const readyStatus: TestStatus = {
  lifecycle: "open",
  credits_remaining: 7,
  terms: { available: true, accepted: true, version: "v-test", sha256: "a".repeat(64) },
  request: null,
  blockers: [],
};

const closingStatus: TestStatus = {
  ...readyStatus,
  lifecycle: "closing",
  request: { requested_at: "2026-11-10T12:00:00Z", balance_snapshot: 7 },
  blockers: [{ code: "open_order", message: "Há pedidos em andamento que precisam ser concluídos." }],
};

afterEach(() => vi.restoreAllMocks());

function stubRequestStatus(status: TestStatus = readyStatus) {
  const fetchMock = vi.fn(async (path: string, init?: RequestInit) => {
    void init;
    return new Response(JSON.stringify(path === "/api/admin/closure" ? status : {}), { status: 200 });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function prepareId() {
  Object.defineProperty(window.crypto, "randomUUID", { configurable: true, value: vi.fn(() => "request-synthetic") });
}

describe("painel de encerramento do fotógrafo", () => {
  it("explica as consequências, saldo, termos e registra solicitação idempotente", async () => {
    prepareId();
    let didPost = false;
    const fetchMock = vi.fn(async (path: string, init?: RequestInit) => {
      if (path !== "/api/admin/closure") return new Response("{}", { status: 200 });
      if (init?.method === "POST") {
        didPost = true;
        return new Response(JSON.stringify({ state: "closing" }), { status: 202 });
      }
      return new Response(JSON.stringify(didPost ? closingStatus : readyStatus), { status: 200 });
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<PhotographerClosurePanel />);

    expect(await screen.findByText(/Novas galerias e envios de fotos serão bloqueados/)).toBeTruthy();
    expect(screen.getByText("Saldo atual:")).toBeTruthy();
    expect(screen.queryByText(/Google Drive|caminho de armazenamento/i)).toBeNull();
    const confirm = screen.getByLabelText("Confirmo que quero encerrar minha conta.");
    const acknowledge = screen.getByLabelText(/Reconheço que os 7 créditos restantes/);
    const submit = screen.getByRole("button", { name: "Solicitar encerramento" });
    expect((submit as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(confirm);
    fireEvent.click(acknowledge);
    fireEvent.click(submit);

    await screen.findByText(/Sua solicitação foi recebida/);
    const post = fetchMock.mock.calls.find(([path, init]) => path === "/api/admin/closure" && init?.method === "POST");
    expect(post).toBeTruthy();
    expect(JSON.parse(String(post?.[1]?.body))).toEqual({
      request_id: "request-synthetic",
      confirm_closure: true,
      acknowledge_remaining_balance: true,
      expected_balance: 7,
      terms_version: "v-test",
      terms_sha256: "a".repeat(64),
    });
  });

  it("preserva o mesmo identificador ao repetir uma solicitação que falhou", async () => {
    prepareId();
    let posts = 0;
    const fetchMock = vi.fn(async (path: string, init?: RequestInit) => {
      if (path !== "/api/admin/closure") return new Response("{}", { status: 200 });
      if (init?.method === "POST") {
        posts += 1;
        return new Response("{}", { status: posts === 1 ? 503 : 202 });
      }
      return new Response(JSON.stringify(posts > 1 ? closingStatus : readyStatus), { status: 200 });
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<PhotographerClosurePanel />);
    fireEvent.click(await screen.findByLabelText("Confirmo que quero encerrar minha conta."));
    fireEvent.click(screen.getByLabelText(/Reconheço que os 7 créditos restantes/));
    fireEvent.click(screen.getByRole("button", { name: "Solicitar encerramento" }));
    expect(await screen.findByText(/Você pode tentar novamente/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Solicitar encerramento" }));
    await screen.findByText(/Sua solicitação foi recebida/);
    const bodies = fetchMock.mock.calls
      .filter(([path, init]) => path === "/api/admin/closure" && init?.method === "POST")
      .map(([, init]) => JSON.parse(String(init?.body)));
    expect(bodies).toHaveLength(2);
    expect(bodies[0].request_id).toBe(bodies[1].request_id);
  });

  it("atualiza o estado após conflito e pede nova confirmação quando o saldo muda", async () => {
    const randomUUID = vi.fn().mockReturnValueOnce("request-before-conflict")
      .mockReturnValueOnce("request-after-conflict");
    Object.defineProperty(window.crypto, "randomUUID", { configurable: true, value: randomUUID });
    const updatedStatus = { ...readyStatus, credits_remaining: 5 };
    const updatedClosingStatus: TestStatus = {
      ...updatedStatus,
      lifecycle: "closing",
      request: { requested_at: "2026-11-10T12:00:00Z", balance_snapshot: 5 },
      blockers: closingStatus.blockers,
    };
    let reads = 0;
    let posts = 0;
    const fetchMock = vi.fn(async (path: string, init?: RequestInit) => {
      if (path !== "/api/admin/closure") throw new Error("unexpected route");
      if (init?.method === "POST") {
        posts += 1;
        return new Response("{}", { status: posts === 1 ? 409 : 202 });
      }
      reads += 1;
      if (reads === 2) return new Response("{}", { status: 503 });
      const loaded = reads === 1 ? readyStatus : reads === 3 ? updatedStatus : updatedClosingStatus;
      return new Response(JSON.stringify(loaded), { status: 200 });
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<PhotographerClosurePanel />);

    fireEvent.click(await screen.findByLabelText("Confirmo que quero encerrar minha conta."));
    fireEvent.click(screen.getByLabelText(/Reconheço que os 7 créditos restantes/));
    fireEvent.click(screen.getByRole("button", { name: "Solicitar encerramento" }));

    expect(await screen.findByText(/não foi possível atualizá-la/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Atualizar situação" }));
    const updatedAcknowledgement = await screen.findByLabelText(/Reconheço que os 5 créditos restantes/);
    expect((updatedAcknowledgement as HTMLInputElement).checked).toBe(false);
    expect((screen.getByRole("button", { name: "Solicitar encerramento" }) as HTMLButtonElement).disabled).toBe(true);

    fireEvent.click(updatedAcknowledgement);
    fireEvent.click(screen.getByRole("button", { name: "Solicitar encerramento" }));
    expect(await screen.findByText(/Sua solicitação foi recebida/)).toBeTruthy();
    const bodies = fetchMock.mock.calls
      .filter(([, init]) => init?.method === "POST")
      .map(([, init]) => JSON.parse(String(init?.body)));
    expect(bodies.map((body) => body.request_id)).toEqual([
      "request-before-conflict", "request-after-conflict",
    ]);
    expect(bodies.map((body) => body.expected_balance)).toEqual([7, 5]);
  });

  it("mostra pendências ao fotógrafo sem expor códigos internos", async () => {
    stubRequestStatus(closingStatus);
    render(<PhotographerClosurePanel />);
    expect(await screen.findByText("Pendências para concluir")).toBeTruthy();
    expect(screen.getByText("Há pedidos em andamento que precisam ser concluídos.")).toBeTruthy();
    expect(screen.queryByText("open_order")).toBeNull();
  });

  it("bloqueia a solicitação se os Termos vigentes não foram aceitos", async () => {
    stubRequestStatus({ ...readyStatus, terms: { ...readyStatus.terms, accepted: false, sha256: null } });
    render(<PhotographerClosurePanel />);
    expect(await screen.findByRole("link", { name: "Primeiros passos" })).toBeTruthy();
    expect((screen.getByRole("button", { name: "Solicitar encerramento" }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("permite recuperar uma falha na consulta do estado", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response("{}", { status: 503 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(readyStatus), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<PhotographerClosurePanel />);
    fireEvent.click(await screen.findByRole("button", { name: "Tentar novamente" }));
    await waitFor(() => expect(screen.getByText("Saldo atual:")).toBeTruthy());
  });
});
