import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import RawDevelopmentPanel from "./raw-development-panel";

const settings = {
  enabled: false,
  selected_engine: "lightcraft",
  engines: [
    { id: "lightcraft", installed_version: "0.5.0", available: true, supported_formats: [".arw", ".nef", ".dng"] },
    { id: "rawtherapee", installed_version: null, available: false, supported_formats: [] },
  ],
  installed_version: "0.5.0",
  lightcraft_installed_version: "0.5.0",
  lightcraft_latest_stable_version: "0.6.0",
  lightcraft_update_available: true,
  lightcraft_latest_stable_url: "https://github.com/storytold/lightcraft/releases/tag/v0.6.0",
  lightcraft_latest_stable_published_at: "2026-10-11T00:54:00Z",
  last_release_check_at: "2026-10-12T12:00:00Z",
  release_check_status: "ok",
  supported_formats: [".arw", ".nef", ".dng"],
  compatibility_policy: "Formatos são definidos pelo motor selecionado, sem restrição de fabricante.",
};

afterEach(() => vi.restoreAllMocks());

describe("configuração do desenvolvimento RAW", () => {
  it("mostra versão instalada e release novo, sem disparar atualização automática", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(settings), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<RawDevelopmentPanel />);

    expect(await screen.findByText("0.5.0")).toBeTruthy();
    expect(screen.getByText("0.6.0")).toBeTruthy();
    expect(screen.getByText(/Há uma versão mais recente/)).toBeTruthy();
    expect(screen.getByText(/\.ARW, \.NEF, \.DNG/)).toBeTruthy();
    expect(screen.getByRole("link", { name: "Notas do lançamento" }).getAttribute("href"))
      .toBe(settings.lightcraft_latest_stable_url);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect((screen.getByLabelText("Aceitar arquivos RAW compatíveis") as HTMLInputElement).disabled)
      .toBe(false);
  });

  it("salva a opção de engine escolhida pelo administrador", async () => {
    const approvedSettings = settings;
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify(approvedSettings), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ ...approvedSettings, enabled: true }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<RawDevelopmentPanel />);

    const toggle = await screen.findByLabelText("Aceitar arquivos RAW compatíveis");
    expect((toggle as HTMLInputElement).disabled).toBe(false);
    fireEvent.click(toggle);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/admin/settings/raw-development",
      expect.objectContaining({ method: "PATCH", body: JSON.stringify({ enabled: true, selected_engine: "lightcraft" }) }),
    ));
  });
});
