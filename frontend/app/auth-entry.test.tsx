import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AuthEntry } from "./auth-entry";

afterEach(() => {
  vi.restoreAllMocks();
  document.head.querySelectorAll('link[data-branding-test]').forEach((element) => element.remove());
});

describe("entrada com identidade configurável", () => {
  it("mantém os textos de fallback quando a marca não pode ser carregada", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 500 })));
    render(<AuthEntry />);
    expect(screen.getByRole("heading", { name: "Sua galeria, do seu jeito." })).toBeTruthy();
    expect(screen.getByText("Escolha seu tipo de acesso para continuar.")).toBeTruthy();
  });

  it("aplica favicon e ícone do aplicativo retornados pelo servidor", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ login_title: "Entrada", login_intro: "Intro", login_helper: "Ajuda", logo_url: null, favicon_url: "/branding/favicon", app_icon_url: "/branding/app-icon" }), { status: 200 })));
    render(<AuthEntry />);
    await waitFor(() => expect(document.querySelector<HTMLLinkElement>('link[rel="icon"]')?.href).toContain("/api/branding/favicon"));
    expect(document.querySelector<HTMLLinkElement>('link[rel="apple-touch-icon"]')?.href).toContain("/api/branding/app-icon");
  });
});
