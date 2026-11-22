import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { OnboardingPanel } from "./onboarding-panel";

afterEach(() => {
  vi.unstubAllGlobals();
  window.history.replaceState({}, "", "/");
});

describe("progresso de onboarding do fotógrafo", () => {
  it("organiza cada etapa recolhível e salva CPF/endereço sem repetir a identidade do ingresso", async () => {
    let profileComplete = false;
    let termsAccepted = false;
    const fetchMock = vi.fn((input: string | URL | Request, init?: RequestInit) => {
      void init;
      const path = String(input);
      if (path === "/api/admin/onboarding/terms") {
        return Promise.resolve(new Response(JSON.stringify({ version: "teste-local-v1", text: "Termos sintéticos", test_only: true })));
      }
      if (path === "/api/admin/onboarding/profile") {
        profileComplete = true;
        return Promise.resolve(new Response(JSON.stringify({ ok: true })));
      }
      if (path.endsWith("/test-acceptance")) {
        termsAccepted = true;
        return Promise.resolve(new Response(JSON.stringify({ ok: true })));
      }
      return Promise.resolve(new Response(JSON.stringify({
        profile_complete: profileComplete,
        terms_accepted: termsAccepted,
        terms_available: true,
        pix_configured: false,
        whatsapp_configured: false,
        credits_available: false,
        mercado_pago_optional: true,
        steps: [{ id: "totp", complete: false }],
      })));
    });
    vi.stubGlobal("fetch", fetchMock);
    window.history.replaceState({}, "", "/admin/settings?return_to=%2Fadmin%2Fcredits#onboarding");
    render(<OnboardingPanel />);

    expect(await screen.findByRole("group", { name: "Etapas para operar" })).toBeTruthy();
    expect(screen.getByText("0 de 5")).toBeTruthy();
    expect(screen.getByText("Dados do titular").closest("summary")?.textContent).toContain("Pendente");
    expect(screen.getByText("Dados do titular").closest("details")?.getAttribute("open")).not.toBeNull();
    expect(screen.getByText("PIX de recebimento").closest("summary")?.textContent).toContain("Pendente");
    expect(screen.getByText("WhatsApp").closest("summary")?.textContent).toContain("Pendente");
    expect(screen.getByRole("link", { name: "volte à ação que iniciou o cadastro" }).getAttribute("href"))
      .toBe("/admin/credits");
    expect(screen.queryByText("Evolution API")).toBeNull();
    expect(screen.getByText("Mercado Pago próprio").closest("summary")?.textContent).toContain("Opcional");
    expect(screen.queryByLabelText("Nome completo")).toBeNull();

    fireEvent.change(screen.getByLabelText("CPF"), { target: { value: "52998224725" } });
    fireEvent.change(screen.getByLabelText("CEP"), { target: { value: "01311-000" } });
    fireEvent.change(screen.getByLabelText("Logradouro"), { target: { value: "Avenida Paulista" } });
    fireEvent.change(screen.getByLabelText("Número"), { target: { value: "1000" } });
    fireEvent.change(screen.getByLabelText("Bairro"), { target: { value: "Bela Vista" } });
    fireEvent.change(screen.getByLabelText("Cidade"), { target: { value: "São Paulo" } });
    fireEvent.change(screen.getByLabelText("Estado"), { target: { value: "SP" } });
    fireEvent.click(screen.getByRole("button", { name: "Salvar CPF e endereço" }));
    await screen.findByText("Perfil salvo. Nome e e-mail vieram do cadastro verificado.");
    const profileRequest = fetchMock.mock.calls.find(([path, init]) =>
      String(path) === "/api/admin/onboarding/profile" && init?.method === "PUT");
    expect(JSON.parse(String(profileRequest?.[1]?.body))).toEqual({
      cpf: "52998224725",
      address: {
        zip_code: "01311-000", street_name: "Avenida Paulista", street_number: "1000",
        neighborhood: "Bela Vista", city: "São Paulo", state: "SP", complement: "",
      },
    });
    expect(screen.queryByLabelText("CPF")).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Ler termos" }));
    expect(await screen.findByText("Termos sintéticos")).toBeTruthy();
    fireEvent.click(screen.getByLabelText("Li e aceito os termos sintéticos para teste local"));
    fireEvent.click(screen.getByRole("button", { name: "Aceitar termos de teste" }));
    expect(await screen.findByText("Aceite de teste registrado para esta demonstração local.")).toBeTruthy();
    await waitFor(() => expect(fetchMock.mock.calls.some(([path, init]) =>
      String(path).endsWith("/test-acceptance") && init?.method === "POST")).toBe(true));
  });

  it("aceita a versão publicada e envia seu identificador sem usar a rota sintética", async () => {
    let accepted = false;
    const fetchMock = vi.fn((input: string | URL | Request, init?: RequestInit) => {
      void init;
      const path = String(input);
      if (path === "/api/admin/onboarding/terms") {
        return Promise.resolve(new Response(JSON.stringify({ version: "v3", text: "Termos publicados", test_only: false })));
      }
      if (path === "/api/admin/onboarding/terms/accept") {
        accepted = true;
        return Promise.resolve(new Response(JSON.stringify({ terms_accepted: true, version: "v3" })));
      }
      if (path === "/api/admin/onboarding/terms/acceptances") {
        return Promise.resolve(new Response(JSON.stringify({ items: [{ id: "acceptance-1", version: "v3", accepted_at: "2026-11-07T12:00:00Z" }] })));
      }
      return Promise.resolve(new Response(JSON.stringify({
        profile_complete: true, terms_accepted: accepted, terms_available: true,
        pix_configured: false, whatsapp_configured: false, credits_available: false,
        mercado_pago_optional: true,
      })));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<OnboardingPanel />);
    fireEvent.click(await screen.findByRole("button", { name: "Ler termos" }));
    expect(await screen.findByText("Termos publicados")).toBeTruthy();
    fireEvent.click(screen.getByLabelText("Li e aceito os Termos do Fotógrafo Tenant, versão v3"));
    fireEvent.click(screen.getByRole("button", { name: "Aceitar termos" }));
    expect((await screen.findByRole("status")).textContent).toContain("Aceite registrado para a versão vigente.");
    expect((await screen.findByRole("link", { name: "Baixar cópia do aceite v3" })).getAttribute("href"))
      .toBe("/api/admin/onboarding/terms/acceptances/acceptance-1/copy");
    const request = fetchMock.mock.calls.find(([path]) => String(path) === "/api/admin/onboarding/terms/accept");
    expect(JSON.parse(String(request?.[1]?.body))).toEqual({ version: "v3", accepted: true });
    expect(fetchMock.mock.calls.some(([path]) => String(path).endsWith("/test-acceptance"))).toBe(false);
  });
});
