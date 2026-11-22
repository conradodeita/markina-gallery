import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import PaymentProvidersPanel from "./payment-providers-panel";

afterEach(() => {
  vi.unstubAllGlobals();
  Reflect.deleteProperty(navigator, "clipboard");
});

const settings = { version: 2, pix_enabled: true, mercadopago_enabled: true,
  mercadopago_available: false, account: { seller_id: "123456", status: "active",
    test_account: true, webhook_path: "/api/mercadopago/webhooks/own-account" } };

it("explica a conexão própria e associa hints aos campos sem exibir segredos salvos", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => Response.json(settings)));
  render(<PaymentProvidersPanel />);
  await screen.findByText("Mercado Pago em teste");
  expect(screen.getByText(/somente para a sua conta de fotógrafo/)).toBeTruthy();
  fireEvent.click(screen.getByText("Substituir credenciais Mercado Pago"));
  for (const label of ["Access Token", "Public Key", "Assinatura secreta dos webhooks"]) {
    const input = screen.getByLabelText(label) as HTMLInputElement;
    expect(input.value).toBe("");
    const hint = document.getElementById(input.getAttribute("aria-describedby")!);
    expect(hint?.textContent?.length).toBeGreaterThan(30);
  }
  expect((screen.getByLabelText("Access Token") as HTMLInputElement).type).toBe("password");
  expect((screen.getByLabelText("Assinatura secreta dos webhooks") as HTMLInputElement).type).toBe("password");
  expect(screen.getByRole("checkbox", { name: "PIX do sistema" })).toBeTruthy();
  expect(screen.getByRole("checkbox", { name: "Mercado Pago · Checkout Transparente" })).toBeTruthy();
  expect(screen.getByRole("link", { name: /Abrir minhas integrações/ }).getAttribute("rel"))
    .toBe("noopener noreferrer");
});

it("copia apenas a URL da própria configuração na origem atual", async () => {
  const copy = vi.fn(async () => undefined);
  Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText: copy } });
  vi.stubGlobal("fetch", vi.fn(async () => Response.json(settings)));
  render(<PaymentProvidersPanel />);
  const input = await screen.findByLabelText("Endereço do webhook da aplicação") as HTMLInputElement;
  expect(input.value).toBe(`${window.location.origin}${settings.account.webhook_path}`);
  fireEvent.click(screen.getByRole("button", { name: "Copiar URL" }));
  await screen.findByText("Endereço do webhook copiado.");
  expect(copy).toHaveBeenCalledExactlyOnceWith(input.value);
});

it("preserva o endereço e orienta cópia manual quando clipboard falha", async () => {
  Object.defineProperty(navigator, "clipboard", { configurable: true,
    value: { writeText: vi.fn(async () => { throw new Error("denied"); }) } });
  vi.stubGlobal("fetch", vi.fn(async () => Response.json(settings)));
  render(<PaymentProvidersPanel />);
  await screen.findByRole("button", { name: "Copiar URL" });
  fireEvent.click(screen.getByRole("button", { name: "Copiar URL" }));
  await waitFor(() => expect(screen.getByRole("alert").textContent).toMatch(/copie manualmente/));
  expect((screen.getByLabelText("Endereço do webhook da aplicação") as HTMLInputElement).value)
    .toContain(settings.account.webhook_path);
});
