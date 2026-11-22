import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import PhotographerSignupPage from "./page";

vi.mock("next/script", () => ({
  default: ({ onReady }: { onReady?: () => void }) => <span data-testid="turnstile-script" onClick={onReady} />,
}));

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
const json = (data: unknown, status = 200) => Promise.resolve(new Response(JSON.stringify(data), { status }));

describe("prova simples de cadastro do fotógrafo", () => {
  it("percorre nome/e-mail/senha sem TOTP nem aprovação do proprietário", async () => {
    const fetcher = vi.fn((input: RequestInfo | URL, _init?: RequestInit) => {
      void _init;
      const path = String(input);
      if (path.endsWith("/config")) return json({ turnstile_enabled: false, turnstile_site_key: null });
      if (path.endsWith("/verify-email")) return json({ state: "credentials_pending" });
      if (path.endsWith("/setup")) return json({ photographer_name: "Fotógrafa local", email: "local@example.test" });
      if (path.endsWith("/complete")) return json({ state: "active", redirect_to: "/admin" });
      return json({ request_id: "synthetic-request", message: "Se puder prosseguir, enviaremos código." });
    });
    vi.stubGlobal("fetch", fetcher);
    render(<PhotographerSignupPage />);
    await waitFor(() => expect(screen.getByRole("button", { name: "Receber código" })).not.toHaveProperty("disabled", true));
    fireEvent.change(screen.getByLabelText("Nome do fotógrafo"), { target: { value: "Fotógrafa local" } });
    fireEvent.change(screen.getByLabelText("E-mail"), { target: { value: "local@example.test" } });
    fireEvent.click(screen.getByLabelText(/Declaro que sou maior de 18 anos/));
    fireEvent.click(screen.getByRole("button", { name: "Receber código" }));
    fireEvent.change(await screen.findByLabelText("Código recebido por e-mail"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Verificar e-mail" }));
    expect(await screen.findByText(/autenticador é opcional/)).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Senha"), { target: { value: "IsolatedFlow!47Alpha" } });
    fireEvent.click(screen.getByRole("button", { name: "Criar minha conta" }));
    expect(await screen.findByText("Conta criada")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Entrar no painel" }).getAttribute("href")).toBe("/admin");
    expect(fetcher).toHaveBeenCalledTimes(5);
  });

  it("apresenta cadastro indisponível e não simula criação quando o backend está fechado", async () => {
    vi.stubGlobal("fetch", vi.fn(() => json({ detail: "Recurso indisponível." }, 404)));
    render(<PhotographerSignupPage />);
    await waitFor(() => expect(screen.getByRole("button", { name: "Receber código" })).not.toHaveProperty("disabled", true));
    fireEvent.change(screen.getByLabelText("Nome do fotógrafo"), { target: { value: "Local" } });
    fireEvent.change(screen.getByLabelText("E-mail"), { target: { value: "local@example.test" } });
    fireEvent.click(screen.getByLabelText(/Declaro que sou maior de 18 anos/));
    fireEvent.click(screen.getByRole("button", { name: "Receber código" }));
    expect(await screen.findByRole("alert")).toHaveProperty("textContent", "Cadastro em preparação. Tente novamente mais tarde.");
    expect(screen.queryByText("Conta criada")).toBeNull();
  });

  it("carrega o widget configurado e envia somente o token público no cadastro", async () => {
    let options: { callback: (token: string) => void } | null = null;
    const remove = vi.fn();
    const reset = vi.fn();
    Object.assign(window, {
      turnstile: {
        render: vi.fn((_container: HTMLElement, value: typeof options) => {
          options = value;
          return "widget-synthetic";
        }),
        remove,
        reset,
      },
    });
    const fetcher = vi.fn((input: RequestInfo | URL, _init?: RequestInit) => {
      void _init;
      const path = String(input);
      if (path.endsWith("/config")) return json({ turnstile_enabled: true, turnstile_site_key: "public-site-key" });
      return json({ request_id: "synthetic-request", message: "Se puder prosseguir, enviaremos código." });
    });
    vi.stubGlobal("fetch", fetcher);
    render(<PhotographerSignupPage />);
    fireEvent.change(screen.getByLabelText("Nome do fotógrafo"), { target: { value: "Fotógrafa local" } });
    fireEvent.change(screen.getByLabelText("E-mail"), { target: { value: "local@example.test" } });
    fireEvent.click(screen.getByLabelText(/Declaro que sou maior de 18 anos/));
    fireEvent.click(await screen.findByTestId("turnstile-script"));
    await waitFor(() => expect(options).not.toBeNull());
    await act(async () => { options?.callback("synthetic-turnstile-token"); });
    fireEvent.click(screen.getByRole("button", { name: "Receber código" }));
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2));
    const start = fetcher.mock.calls.find(([path]) => String(path).endsWith("/photographer-signup"));
    expect(JSON.parse(String(start?.[1]?.body))).toEqual({
      photographer_name: "Fotógrafa local",
      email: "local@example.test",
      adult_attested: true,
      anti_bot_proof: "synthetic-turnstile-token",
    });
    await waitFor(() => expect(remove).toHaveBeenCalledWith("widget-synthetic"));
  });
});
