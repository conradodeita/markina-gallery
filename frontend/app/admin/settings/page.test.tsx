import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import AdminSettingsPage from "./page";

const branding = {
  login_title: "Sua galeria, do seu jeito.",
  login_intro: "Entre para acessar fotos.",
  login_helper: "Escolha seu acesso.",
  logo_url: null,
  app_icon_url: null,
  favicon_url: null,
};

afterEach(() => vi.restoreAllMocks());

describe("configurações administrativas de marca", () => {
  it("apresenta fallback e envia cada ativo ao endpoint autorizado", async () => {
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (init?.method === "PUT") {
        const asset = path.split("/").at(-1);
        return Promise.resolve(new Response(JSON.stringify({ ...branding, [`${asset?.replace("-", "_")}_url`]: `/branding/${asset}` }), { status: 200 }));
      }
      return Promise.resolve(new Response(JSON.stringify(branding), { status: 200 }));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<AdminSettingsPage />);

    expect((await screen.findAllByText("Usando fallback Markina")).length).toBe(3);
    const logo = new File(["logo"], "logo.png", { type: "image/png" });
    fireEvent.change(screen.getByLabelText("Enviar Logo principal"), { target: { files: [logo] } });

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/admin/branding/logo", expect.objectContaining({ method: "PUT", body: logo })));
    expect(await screen.findByText("Logo principal atualizado.")).toBeTruthy();
  });

  it("informa indisponibilidade quando a configuração não carrega", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 403 })));
    render(<AdminSettingsPage />);
    expect(await screen.findByText("Configurações indisponíveis")).toBeTruthy();
  });
});
