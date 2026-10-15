import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { PUSH_LOGOUT_EVENT } from "../push-device";
import { InstallationDiagnostics } from "./installation-diagnostics";

afterEach(() => vi.unstubAllGlobals());

describe("permissão técnica da instalação", () => {
  it.each([false, undefined, "true", 1])("omite o monitor sem capability positiva: %s", async (permission) => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ capacity_diagnostics: permission })));
    vi.stubGlobal("fetch", fetcher);
    render(<InstallationDiagnostics />);
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(1));
    await act(async () => {});
    expect(screen.queryByText("Capacidade e filas")).toBeNull();
    expect(screen.queryByRole("button", { name: "Copiar relatório" })).toBeNull();
    expect(fetcher).toHaveBeenCalledWith("/api/admin/installation-capabilities", expect.objectContaining({ cache: "no-store", credentials: "same-origin" }));
  });

  it.each([401, 403, 503])("omite com falha HTTP %s sem consultar métricas", async (status) => {
    const fetcher = vi.fn().mockResolvedValue(new Response(null, { status }));
    vi.stubGlobal("fetch", fetcher);
    render(<InstallationDiagnostics />);
    await act(async () => {});
    expect(fetcher).toHaveBeenCalledTimes(1);
    expect(screen.queryByText("Capacidade e filas")).toBeNull();
  });

  it("mostra somente ao dono autorizado e retira após revogação detectada no foco", async () => {
    const fetcher = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ capacity_diagnostics: true })))
      .mockResolvedValueOnce(new Response(JSON.stringify({ capacity_diagnostics: false })));
    vi.stubGlobal("fetch", fetcher);
    render(<InstallationDiagnostics />);
    expect(await screen.findByText("Capacidade e filas")).toBeTruthy();
    expect(fetcher).toHaveBeenCalledTimes(1); // Não há coleta automática de métricas.
    fireEvent(window, new Event("focus"));
    await waitFor(() => expect(screen.queryByText("Capacidade e filas")).toBeNull());
    expect(fetcher).toHaveBeenCalledTimes(2);
  });

  it("retira toda a seção quando o endpoint de métricas nega acesso", async () => {
    const fetcher = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ capacity_diagnostics: true })))
      .mockResolvedValueOnce(new Response(null, { status: 403 }));
    vi.stubGlobal("fetch", fetcher);
    const view = render(<InstallationDiagnostics />);
    fireEvent.click(await screen.findByRole("button", { name: "Consultar diagnóstico" }));
    await waitFor(() => expect(view.container.querySelector("section")).toBeNull());
    expect(screen.queryByRole("button", { name: "Copiar relatório" })).toBeNull();
  });

  it("invalida resposta antiga, cancela consulta e não reabre após logout", async () => {
    let resolve: (response: Response) => void = () => {};
    let signal: AbortSignal | undefined;
    const fetcher = vi.fn((_url, init) => {
      signal = init.signal;
      return new Promise<Response>((done) => { resolve = done; });
    });
    vi.stubGlobal("fetch", fetcher);
    render(<InstallationDiagnostics />);
    fireEvent(window, new Event(PUSH_LOGOUT_EVENT));
    expect(signal?.aborted).toBe(true);
    await act(async () => resolve(new Response(JSON.stringify({ capacity_diagnostics: true }))));
    expect(screen.queryByText("Capacidade e filas")).toBeNull();
  });

  it("falha fechada em rede indisponível e cancela ao desmontar", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
    const view = render(<InstallationDiagnostics />);
    await act(async () => {});
    expect(screen.queryByText("Capacidade e filas")).toBeNull();
    view.unmount();
    let signal: AbortSignal | undefined;
    vi.stubGlobal("fetch", vi.fn((_url, init) => {
      signal = init.signal;
      return new Promise<Response>(() => {});
    }));
    const pending = render(<InstallationDiagnostics />);
    pending.unmount();
    expect(signal?.aborted).toBe(true);
  });
});
