import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SessionBoundary } from "./session-boundary";
import { protectedContext, recoveryLocation, safeAdminReturn } from "./session-recovery";

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

  it.each([408, 502, "network"])("falha temporária %s preserva sessão sem replay de upload", async (failure) => {
    const navigate = vi.fn();
    const fetchMock = vi.fn((input: string | URL | Request) => {
      if (String(input) === "/api/auth/destination") return Promise.resolve(authorized());
      return failure === "network" ? Promise.reject(new TypeError("network")) : Promise.resolve(new Response(null, { status: failure as number }));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<SessionBoundary navigate={navigate}><p>Conteúdo privado</p></SessionBoundary>);
    await screen.findByText("Conteúdo privado");
    await act(async () => { await window.fetch("/api/admin/upload", { method: "POST" }).catch(() => undefined); });
    expect((await screen.findByRole("alert")).textContent).toContain("temporariamente indisponível");
    expect(screen.getByText("Conteúdo privado")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Verificar conexão novamente" }));
    await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("Conexão confirmada"));
    expect(fetchMock.mock.calls.filter(([input]) => String(input) === "/api/admin/upload")).toHaveLength(1);
    expect(navigate).not.toHaveBeenCalled();
  });

  it("falha inicial permite retry da leitura sem montar conteúdo antes da validação", async () => {
    const fetchMock = vi.fn().mockRejectedValueOnce(new TypeError("network")).mockResolvedValueOnce(authorized());
    vi.stubGlobal("fetch", fetchMock);
    const navigate = vi.fn();
    render(<SessionBoundary navigate={navigate}><p>Conteúdo privado</p></SessionBoundary>);
    await screen.findByRole("alert");
    expect(screen.queryByText("Conteúdo privado")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Verificar conexão novamente" }));
    await screen.findByText("Conteúdo privado");
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(navigate).not.toHaveBeenCalled();
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

  it("revalida no foco, no retorno do histórico, na periodicidade e na navegação protegida", async () => {
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
    expect(protectedContext("/administrator")).toBeNull();
  });
});
