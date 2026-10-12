import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SessionBoundary } from "./session-boundary";
import { protectedContext, recoveryLocation, safeAdminReturn, safeClientGalleryReturn } from "./session-recovery";

const navigation = vi.hoisted(() => ({ pathname: "/admin" }));
vi.mock("next/navigation", () => ({ usePathname: () => navigation.pathname }));

function authorized(destination = "/admin") {
  return new Response(JSON.stringify({ destination }), { status: 200 });
}

beforeEach(() => {
  navigation.pathname = "/admin";
  window.sessionStorage.clear();
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("recuperação uniforme de sessão", () => {
  it.each(["/admin/settings", "/library/cart", "/gallery/abc", "/public-galleries/abc"])("retira conteúdo privado e retorna à entrada em %s", async (pathname) => {
    navigation.pathname = pathname;
    window.sessionStorage.setItem("markina:facial-search:v2:context:gallery", "request");
    window.sessionStorage.setItem("unrelated", "preserve");
    const navigate = vi.fn();
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 401 })));
    render(<SessionBoundary navigate={navigate}><p>Conteúdo privado</p></SessionBoundary>);
    expect(screen.queryByText("Conteúdo privado")).toBeNull();
    await waitFor(() => expect(navigate).toHaveBeenCalledWith(recoveryLocation(pathname)));
    expect(screen.queryByText("Conteúdo privado")).toBeNull();
    expect(window.sessionStorage.getItem("markina:facial-search:v2:context:gallery")).toBeNull();
    expect(window.sessionStorage.getItem("unrelated")).toBe("preserve");
    expect(navigate).toHaveBeenCalledTimes(1);
  });

  it.each(["/", "/admin/reset-password", "/admin/verify-email"])("não interfere no fluxo público %s", (pathname) => {
    navigation.pathname = pathname;
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    render(<SessionBoundary><p>Entrada pública</p></SessionBoundary>);
    expect(screen.getByText("Entrada pública")).toBeTruthy();
    expect(fetchMock).not.toHaveBeenCalled();
    expect(window.fetch).toBe(fetchMock);
  });

  it("valida antes de montar conteúdo e restaura fetch ao sair", async () => {
    let resolve: (response: Response) => void = () => undefined;
    const fetchMock = vi.fn(() => new Promise<Response>((complete) => { resolve = complete; }));
    vi.stubGlobal("fetch", fetchMock);
    const view = render(<SessionBoundary><p>Conteúdo privado</p></SessionBoundary>);
    expect(screen.queryByText("Conteúdo privado")).toBeNull();
    await act(async () => resolve(authorized()));
    expect(await screen.findByText("Conteúdo privado")).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledWith("/api/auth/destination", expect.objectContaining({ cache: "no-store", credentials: "same-origin" }));
    view.unmount();
    expect(window.fetch).toBe(fetchMock);
  });

  it("confirma sessão expirada depois de recusa 403 sem repetir a mutação", async () => {
    let expired = false;
    const fetchMock = vi.fn((input: string | URL | Request) => {
      if (String(input) === "/api/auth/destination") return Promise.resolve(expired ? new Response(null, { status: 401 }) : authorized());
      expired = true;
      return Promise.resolve(new Response(null, { status: 403 }));
    });
    vi.stubGlobal("fetch", fetchMock);
    const navigate = vi.fn();
    render(<SessionBoundary navigate={navigate}><p>Conteúdo privado</p></SessionBoundary>);
    await screen.findByText("Conteúdo privado");
    await act(async () => { await window.fetch("/api/admin/upload", { method: "POST", body: "synthetic" }); });
    await waitFor(() => expect(navigate).toHaveBeenCalledTimes(1));
    expect(fetchMock.mock.calls.filter(([input]) => String(input) === "/api/admin/upload")).toHaveLength(1);
    expect(screen.queryByText("Conteúdo privado")).toBeNull();
    await expect(window.fetch("/api/admin/upload", { method: "POST" })).rejects.toMatchObject({ name: "AbortError" });
  });

  it("403 específico com sessão válida não é expiração", async () => {
    const navigate = vi.fn();
    vi.stubGlobal("fetch", vi.fn((input: string | URL | Request) => Promise.resolve(String(input) === "/api/auth/destination" ? authorized() : new Response(null, { status: 403 }))));
    render(<SessionBoundary navigate={navigate}><p>Conteúdo privado</p></SessionBoundary>);
    await screen.findByText("Conteúdo privado");
    await act(async () => { await window.fetch("/api/admin/restricted"); });
    expect((await screen.findByRole("alert")).textContent).toContain("Acesso negado");
    await act(async () => { window.dispatchEvent(new Event("focus")); });
    expect(screen.getByRole("alert").textContent).toContain("Acesso negado");
    expect(screen.getByText("Conteúdo privado")).toBeTruthy();
    expect(navigate).not.toHaveBeenCalled();
  });

  it("recusa durante verificação anterior agenda nova leitura deduplicada", async () => {
    let checks = 0;
    let complete: (response: Response) => void = () => undefined;
    const fetchMock = vi.fn((input: string | URL | Request) => {
      if (String(input) !== "/api/auth/destination") return Promise.resolve(new Response(null, { status: 403 }));
      checks += 1;
      if (checks === 2) return new Promise<Response>((resolve) => { complete = resolve; });
      return Promise.resolve(checks === 1 ? authorized() : new Response(null, { status: 401 }));
    });
    const navigate = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    render(<SessionBoundary navigate={navigate}><p>Conteúdo privado</p></SessionBoundary>);
    await screen.findByText("Conteúdo privado");
    await act(async () => { window.dispatchEvent(new Event("focus")); });
    await act(async () => { await Promise.all([window.fetch("/api/admin/first"), window.fetch("/api/admin/second")]); });
    expect(checks).toBe(2);
    await act(async () => complete(authorized()));
    await waitFor(() => expect(navigate).toHaveBeenCalledTimes(1));
    expect(checks).toBe(3);
    expect(screen.queryByText("Conteúdo privado")).toBeNull();
  });

  it.each([403, 200])("contexto recusado ou papel errado não entra em loop (%s)", async (status) => {
    const navigate = vi.fn();
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(status === 403 ? new Response(null, { status: 403 }) : authorized("/library")));
    render(<SessionBoundary navigate={navigate}><p>Conteúdo privado</p></SessionBoundary>);
    expect((await screen.findByRole("alert")).textContent).toContain("Acesso negado");
    expect(screen.queryByText("Conteúdo privado")).toBeNull();
    expect(screen.getByRole("link", { name: "Voltar à entrada" })).toBeTruthy();
    expect(navigate).not.toHaveBeenCalled();
  });

  it.each([408, 502, "network"])("falha temporária %s revalida a sessão automaticamente sem replay de upload", async (failure) => {
    const navigate = vi.fn();
    let checks = 0;
    const fetchMock = vi.fn((input: string | URL | Request) => {
      if (String(input) === "/api/auth/destination") {
        checks += 1;
        return Promise.resolve(authorized());
      }
      return failure === "network" ? Promise.reject(new TypeError("network")) : Promise.resolve(new Response(null, { status: failure as number }));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<SessionBoundary navigate={navigate}><p>Conteúdo privado</p></SessionBoundary>);
    await screen.findByText("Conteúdo privado");
    await act(async () => { await window.fetch("/api/admin/upload", { method: "POST" }).catch(() => undefined); });
    await waitFor(() => expect(checks).toBe(2));
    expect(screen.queryByRole("alert")).toBeNull();
    expect(screen.queryByRole("button", { name: /verificar conexão|reconectar/i })).toBeNull();
    expect(screen.getByText("Conteúdo privado")).toBeTruthy();
    expect(fetchMock.mock.calls.filter(([input]) => String(input) === "/api/admin/upload")).toHaveLength(1);
    expect(navigate).not.toHaveBeenCalled();
  });

  it("mantém o aviso enquanto a sessão falha e o limpa quando a reconexão automática funciona", async () => {
    vi.useFakeTimers();
    let checks = 0;
    const fetchMock = vi.fn((input: string | URL | Request) => {
      if (String(input) !== "/api/auth/destination") return Promise.resolve(new Response(null, { status: 503 }));
      checks += 1;
      return Promise.resolve(checks === 2 ? new Response(null, { status: 503 }) : authorized());
    });
    vi.stubGlobal("fetch", fetchMock);
    const navigate = vi.fn();
    render(<SessionBoundary navigate={navigate}><p>Conteúdo privado</p></SessionBoundary>);
    await act(async () => undefined);
    await act(async () => { await window.fetch("/api/admin/orders"); });
    await act(async () => undefined);
    expect(screen.getByRole("alert").textContent).toContain("temporariamente indisponível");
    expect(screen.queryByRole("button", { name: /verificar conexão|reconectar/i })).toBeNull();
    await act(async () => { await vi.advanceTimersByTimeAsync(1_000); });
    expect(checks).toBe(3);
    expect(screen.queryByRole("alert")).toBeNull();
    expect(screen.getByText("Conteúdo privado")).toBeTruthy();
    expect(navigate).not.toHaveBeenCalled();
  });

  it("não executa probes enquanto oculta e revalida ao voltar a ficar visível", async () => {
    vi.useFakeTimers();
    let checks = 0;
    const fetchMock = vi.fn((input: string | URL | Request) => {
      if (String(input) === "/api/auth/destination") {
        checks += 1;
        return Promise.resolve(authorized());
      }
      return Promise.resolve(new Response(null, { status: 503 }));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<SessionBoundary><p>Conteúdo privado</p></SessionBoundary>);
    await act(async () => undefined);
    Object.defineProperty(document, "visibilityState", { configurable: true, value: "hidden" });
    await act(async () => { await window.fetch("/api/admin/orders"); });
    await act(async () => { await vi.advanceTimersByTimeAsync(30_000); });
    expect(checks).toBe(1);
    Object.defineProperty(document, "visibilityState", { configurable: true, value: "visible" });
    await act(async () => { document.dispatchEvent(new Event("visibilitychange")); });
    expect(checks).toBe(2);
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("deduplica verificações simultâneas e aumenta o intervalo entre retries", async () => {
    vi.useFakeTimers();
    let checks = 0;
    let finishSecondCheck: (response: Response) => void = () => undefined;
    const fetchMock = vi.fn((input: string | URL | Request) => {
      if (String(input) !== "/api/auth/destination") return Promise.resolve(new Response(null, { status: 503 }));
      checks += 1;
      if (checks === 2) return new Promise<Response>((resolve) => { finishSecondCheck = resolve; });
      return Promise.resolve(checks === 1 || checks >= 4 ? authorized() : new Response(null, { status: 503 }));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<SessionBoundary><p>Conteúdo privado</p></SessionBoundary>);
    await act(async () => undefined);
    await act(async () => { await window.fetch("/api/admin/orders"); });
    expect(checks).toBe(2);
    await act(async () => { window.dispatchEvent(new Event("focus")); });
    await act(async () => { window.dispatchEvent(new Event("pageshow")); });
    expect(checks).toBe(2);
    await act(async () => { finishSecondCheck(new Response(null, { status: 503 })); });
    await act(async () => { await vi.advanceTimersByTimeAsync(1_000); });
    expect(checks).toBe(3);
    await act(async () => { await vi.advanceTimersByTimeAsync(1_999); });
    expect(checks).toBe(3);
    await act(async () => { await vi.advanceTimersByTimeAsync(1); });
    expect(checks).toBe(4);
  });

  it("limita o backoff automático a 30 segundos", async () => {
    vi.useFakeTimers();
    let checks = 0;
    const fetchMock = vi.fn((input: string | URL | Request) => {
      if (String(input) !== "/api/auth/destination") return Promise.resolve(new Response(null, { status: 503 }));
      checks += 1;
      return Promise.resolve(checks === 1 ? authorized() : new Response(null, { status: 503 }));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<SessionBoundary><p>Conteúdo privado</p></SessionBoundary>);
    await act(async () => undefined);
    await act(async () => { await window.fetch("/api/admin/orders"); });
    await act(async () => undefined);
    await act(async () => {
      await Promise.all([
        window.fetch("/api/admin/orders"),
        window.fetch("/api/admin/notifications"),
        window.fetch("/api/admin/settings"),
      ]);
    });
    expect(checks).toBe(2);
    await act(async () => { await vi.advanceTimersByTimeAsync(1_000); });
    await act(async () => { await vi.advanceTimersByTimeAsync(2_000); });
    await act(async () => { await vi.advanceTimersByTimeAsync(4_000); });
    await act(async () => { await vi.advanceTimersByTimeAsync(8_000); });
    await act(async () => { await vi.advanceTimersByTimeAsync(16_000); });
    expect(checks).toBe(7);
    await act(async () => { await vi.advanceTimersByTimeAsync(29_999); });
    expect(checks).toBe(7);
    await act(async () => { await vi.advanceTimersByTimeAsync(1); });
    expect(checks).toBe(8);
    await act(async () => { await vi.advanceTimersByTimeAsync(30_000); });
    expect(checks).toBe(9);
  });

  it("recupera a falha inicial automaticamente e só então monta conteúdo privado", async () => {
    vi.useFakeTimers();
    const fetchMock = vi.fn()
      .mockRejectedValueOnce(new TypeError("network"))
      .mockImplementation(() => Promise.resolve(authorized()));
    vi.stubGlobal("fetch", fetchMock);
    const view = render(<SessionBoundary><p>Conteúdo privado</p></SessionBoundary>);
    await act(async () => undefined);
    expect(screen.queryByText("Conteúdo privado")).toBeNull();
    expect(screen.getByRole("alert").textContent).toContain("temporariamente indisponível");
    await act(async () => { await vi.advanceTimersByTimeAsync(1_000); });
    expect(screen.getByText("Conteúdo privado")).toBeTruthy();
    expect(screen.queryByRole("alert")).toBeNull();
    view.unmount();
    await act(async () => { await vi.advanceTimersByTimeAsync(60_000); });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("detecta revogação sem interação pela revalidação periódica", async () => {
    vi.useFakeTimers();
    const navigate = vi.fn();
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(authorized())
      .mockImplementation(() => Promise.resolve(new Response(null, { status: 401 })));
    vi.stubGlobal("fetch", fetchMock);
    render(<SessionBoundary navigate={navigate}><p>Conteúdo privado</p></SessionBoundary>);
    await act(async () => undefined);
    expect(screen.getByText("Conteúdo privado")).toBeTruthy();
    await act(async () => { await vi.advanceTimersByTimeAsync(60_000); });
    expect(screen.queryByText("Conteúdo privado")).toBeNull();
    expect(navigate).toHaveBeenCalledTimes(1);
  });

  it("timeout de verificação é temporário, não logout", async () => {
    vi.useFakeTimers();
    const navigate = vi.fn();
    vi.stubGlobal("fetch", vi.fn((_input, options) => new Promise<Response>((_resolve, reject) => {
      options.signal.addEventListener("abort", () => reject(new DOMException("aborted", "AbortError")));
    })));
    render(<SessionBoundary navigate={navigate}><p>Conteúdo privado</p></SessionBoundary>);
    await act(async () => { await vi.advanceTimersByTimeAsync(10_000); });
    expect(screen.getByRole("alert").textContent).toContain("temporariamente indisponível");
    expect(navigate).not.toHaveBeenCalled();
  });

  it("revalida no foco, no retorno do histórico, periodicamente e na navegação protegida", async () => {
    vi.useFakeTimers();
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(authorized()));
    vi.stubGlobal("fetch", fetchMock);
    const view = render(<SessionBoundary><p>Conteúdo privado</p></SessionBoundary>);
    await act(async () => undefined);
    await act(async () => { window.dispatchEvent(new Event("focus")); });
    await act(async () => { window.dispatchEvent(new Event("pageshow")); });
    await act(async () => { await vi.advanceTimersByTimeAsync(60_000); });
    expect(fetchMock).toHaveBeenCalledTimes(4);
    navigation.pathname = "/admin/settings";
    view.rerender(<SessionBoundary><p>Outra página privada</p></SessionBoundary>);
    await act(async () => undefined);
    expect(fetchMock).toHaveBeenCalledTimes(5);
  });

  it("não observa API externa nem cancelamento intencional", async () => {
    const navigate = vi.fn();
    const fetchMock = vi.fn((input: string | URL | Request, options?: RequestInit) => {
      if (options?.signal?.aborted) return Promise.reject(new DOMException("aborted", "AbortError"));
      return Promise.resolve(String(input) === "/api/auth/destination" ? authorized() : new Response(null, { status: 401 }));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<SessionBoundary navigate={navigate}><p>Conteúdo privado</p></SessionBoundary>);
    await screen.findByText("Conteúdo privado");
    await act(async () => { await window.fetch("https://other.example.test/api/data"); });
    const controller = new AbortController();
    controller.abort();
    await act(async () => { await window.fetch("/api/admin/data", { signal: controller.signal }).catch(() => undefined); });
    expect(screen.queryByRole("alert")).toBeNull();
    expect(navigate).not.toHaveBeenCalled();
  });

  it("remove query/token do retorno e rejeita caminhos externos ou manipulados", () => {
    for (const value of ["https://evil.test", "//evil.test", "/admin/../library", "/admin?access_token=secret", "/admin/%2e%2e/library", "/admin/reset-password"]) {
      expect(safeAdminReturn(value)).toBe("/admin");
    }
    expect(safeAdminReturn("/admin/galleries/sources/abc/edit/imagens")).toBe("/admin/galleries/sources/abc/edit/imagens");
    expect(recoveryLocation("/public-galleries/abc")).toBe("/?reauth=client");
    const galleryId = "0f581c42-08aa-4305-9bfb-55f803d1cfc6";
    expect(safeClientGalleryReturn(`/public-galleries/${galleryId}`)).toEqual({
      path: `/public-galleries/${galleryId}`,
      galleryId,
    });
    expect(recoveryLocation(`/public-galleries/${galleryId}`)).toBe(
      `/?reauth=client&return_to=%2Fpublic-galleries%2F${galleryId}`,
    );
    expect(safeClientGalleryReturn(`/public-galleries/${galleryId}?access_token=secret`)).toBeNull();
    expect(protectedContext("/administrator")).toBeNull();
  });
});


it("revalida nova rota no mesmo papel sem desmontar rascunho ou reabrir o gate inicial", async () => {
  let checks = 0;
  let complete: (response: Response) => void = () => undefined;
  const fetcher = vi.fn(() => {
    checks += 1;
    return checks === 2 ? new Promise<Response>((resolve) => { complete = resolve; }) : Promise.resolve(authorized());
  });
  vi.stubGlobal("fetch", fetcher);
  const child = <input aria-label="Rascunho privado" defaultValue="" />;
  const view = render(<SessionBoundary>{child}</SessionBoundary>);
  const input = await screen.findByLabelText("Rascunho privado");
  fireEvent.change(input, { target: { value: "não perder" } });
  navigation.pathname = "/admin/settings";
  view.rerender(<SessionBoundary>{child}</SessionBoundary>);
  expect(screen.getByLabelText("Rascunho privado")).toBe(input);
  expect((input as HTMLInputElement).value).toBe("não perder");
  expect(screen.queryByText("Verificando sua sessão…")).toBeNull();
  expect(checks).toBe(2);
  await act(async () => complete(authorized()));
  expect(screen.getByLabelText("Rascunho privado")).toBe(input);
});

it("novo papel exige gate inicial mesmo depois de validar administrador", async () => {
  let complete: (response: Response) => void = () => undefined;
  vi.stubGlobal("fetch", vi.fn().mockImplementationOnce(() => Promise.resolve(authorized())).mockImplementationOnce(() => new Promise<Response>((resolve) => { complete = resolve; })));
  const view = render(<SessionBoundary><p>Privado administrador</p></SessionBoundary>);
  await screen.findByText("Privado administrador");
  navigation.pathname = "/library";
  view.rerender(<SessionBoundary><p>Privado cliente</p></SessionBoundary>);
  expect(screen.queryByText("Privado cliente")).toBeNull();
  expect(screen.queryByText("Privado administrador")).toBeNull();
  expect(screen.getByText("Verificando sua sessão…")).toBeTruthy();
  await act(async () => complete(authorized("/library")));
  expect(screen.getByText("Privado cliente")).toBeTruthy();
});

it("falha de leitura não presume compra incerta e aviso some após confirmação no foco", async () => {
  let checks = 0;
  const fetcher = vi.fn((input: RequestInfo | URL) => {
    if (String(input) !== "/api/auth/destination") return Promise.resolve(new Response(null, { status: 503 }));
    checks += 1;
    return Promise.resolve(checks === 2 ? new Response(null, { status: 503 }) : authorized());
  });
  vi.stubGlobal("fetch", fetcher);
  render(<SessionBoundary><p>Conteúdo privado</p></SessionBoundary>);
  await screen.findByText("Conteúdo privado");
  await act(async () => { await window.fetch("/api/admin/read-only"); });
  expect(screen.getByRole("alert").textContent).not.toMatch(/envios|compras/);
  await act(async () => { window.dispatchEvent(new Event("focus")); });
  expect(screen.queryByRole("alert")).toBeNull();
  expect(fetcher.mock.calls.filter(([input]) => String(input) === "/api/admin/read-only")).toHaveLength(1);
});

it("confirmar a sessão após falha de mutação preserva orientação sem repetir a ação", async () => {
  let checks = 0;
  let complete: (response: Response) => void = () => undefined;
  const fetcher = vi.fn((input: RequestInfo | URL) => {
    if (String(input) !== "/api/auth/destination") return Promise.reject(new TypeError("network"));
    checks += 1;
    return checks === 2 ? new Promise<Response>((resolve) => { complete = resolve; }) : Promise.resolve(authorized());
  });
  vi.stubGlobal("fetch", fetcher);
  render(<SessionBoundary><p>Conteúdo privado</p></SessionBoundary>);
  await screen.findByText("Conteúdo privado");
  await act(async () => { await window.fetch(new Request(new URL("/api/admin/upload", window.location.origin), { method: "POST" })).catch(() => undefined); });
  expect(screen.getByRole("status").textContent).toContain("Confira antes de repetir envios ou compras");
  expect(screen.queryByRole("alert")).toBeNull();
  await act(async () => { window.dispatchEvent(new Event("focus")); complete(authorized()); });
  expect(screen.getByRole("status").textContent).toContain("Conexão confirmada");
  expect(screen.getByRole("status").textContent).toContain("Confira o resultado da ação anterior");
  fireEvent.click(screen.getByRole("button", { name: "Fechar aviso" }));
  expect(screen.queryByRole("status")).toBeNull();
  expect(fetcher.mock.calls.filter(([input]) => String(input) !== "/api/auth/destination")).toHaveLength(1);
});


it.each([401, 403])("revalidação da nova rota confirma %s e retira conteúdo do mesmo papel", async (status) => {
  let complete: (response: Response) => void = () => undefined;
  const fetcher = vi.fn().mockImplementationOnce(() => Promise.resolve(authorized())).mockImplementationOnce(() => new Promise<Response>((resolve) => { complete = resolve; }));
  const navigate = vi.fn();
  vi.stubGlobal("fetch", fetcher);
  const view = render(<SessionBoundary navigate={navigate}><p>Privado</p></SessionBoundary>);
  await screen.findByText("Privado");
  navigation.pathname = "/admin/settings";
  view.rerender(<SessionBoundary navigate={navigate}><p>Privado</p></SessionBoundary>);
  expect(screen.getByText("Privado")).toBeTruthy();
  await act(async () => complete(new Response(null, { status })));
  expect(screen.queryByText("Privado")).toBeNull();
  if (status === 401) expect(navigate).toHaveBeenCalledWith(recoveryLocation("/admin/settings"));
  else { expect(screen.getByRole("alert").textContent).toContain("Acesso negado"); expect(navigate).not.toHaveBeenCalled(); }
});

it("recusa de API durante navegação continua agendando revalidação após a leitura pendente", async () => {
  let checks = 0;
  let complete: (response: Response) => void = () => undefined;
  const fetcher = vi.fn((input: RequestInfo | URL) => {
    if (String(input) !== "/api/auth/destination") return Promise.resolve(new Response(null, { status: 403 }));
    checks += 1;
    if (checks === 2) return new Promise<Response>((resolve) => { complete = resolve; });
    return Promise.resolve(checks === 1 ? authorized() : new Response(null, { status: 401 }));
  });
  const navigate = vi.fn();
  vi.stubGlobal("fetch", fetcher);
  const view = render(<SessionBoundary navigate={navigate}><p>Privado</p></SessionBoundary>);
  await screen.findByText("Privado");
  navigation.pathname = "/admin/settings";
  view.rerender(<SessionBoundary navigate={navigate}><p>Privado</p></SessionBoundary>);
  await act(async () => { await window.fetch("/api/admin/restricted"); });
  expect(checks).toBe(2);
  await act(async () => complete(authorized()));
  await waitFor(() => expect(navigate).toHaveBeenCalledTimes(1));
  expect(checks).toBe(3);
  expect(screen.queryByText("Privado")).toBeNull();
});


it("falha de sinal técnico de atividade não presume envio ou compra incerta", async () => {
  let checks = 0;
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
    if (String(input) !== "/api/auth/destination") return Promise.reject(new TypeError("network"));
    checks += 1;
    return Promise.resolve(authorized());
  }));
  render(<SessionBoundary><p>Privado</p></SessionBoundary>);
  await screen.findByText("Privado");
  await act(async () => { await window.fetch("/api/auth/activity", { method: "POST" }).catch(() => undefined); });
  expect(checks).toBe(2);
  expect(screen.queryByRole("alert")).toBeNull();
  expect(screen.queryByText(/ação anterior/)).toBeNull();
});
