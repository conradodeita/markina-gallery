import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useEffect } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { CardData } from "./card-payment";
import CheckoutPage from "./page";
import { PaymentRequestError, type MercadoPagoPayment } from "../mercadopago";

vi.mock("next/link", () => ({ default: ({ children, href, ...props }: {
  children: React.ReactNode; href: string;
}) => <a href={href} {...props}>{children}</a> }));
vi.mock("next/script", () => ({ default: function ScriptMock({ onReady }: { onReady(): void }) {
  useEffect(() => { onReady(); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  return null;
} }));

const prepared: MercadoPagoPayment = {
  id: "11111111-1111-4111-8111-111111111111", provider: "mercadopago",
  method: "credit_card", state: "prepared", active: true, total_cents: 2100,
  cart_revision: "a".repeat(64), public_key: "APP_USR-public-fixture", can_cancel: true, items: [],
};
const cart = { mercadopago_available: true, cart_revision: "a".repeat(64), total_cents: 2100,
  groups: [{ name: "Evento", quantity: 3, items: [{ id: "1", name: "FOTO_01.jpg" },
    { id: "2", name: "FOTO_02.jpg" }, { id: "3", name: "FOTO_03.jpg" }] }] };
const cardData: CardData = { token: "single-use-token", payment_method_id: "visa",
  payer: { email: "buyer@testuser.test", identification: { type: "CPF", number: "12345678909" } } };
type Settings = {
  initialization: { amount: number };
  customization: { paymentMethods: { minInstallments: number; maxInstallments: number } };
  callbacks: { onReady(): void; onSubmit(data: CardData): Promise<void> };
};
let settings: Settings;
const unmount = vi.fn(async () => undefined);
beforeEach(() => {
  settings = undefined!;
  vi.clearAllMocks();
  window.history.replaceState({}, "", "/library/checkout");
  vi.stubGlobal("MercadoPago", function MercadoPagoMock() {
    return { bricks: () => ({ create: async (_type: string, _id: string, value: Settings) => {
      settings = value; value.callbacks.onReady(); return { unmount };
    } }) };
  });
});
afterEach(() => vi.unstubAllGlobals());
function mockFetch(submit?: (body: Record<string, unknown>) => Promise<MercadoPagoPayment>,
  active: MercadoPagoPayment | null = null,
  currentCart: typeof cart = cart) {
  const fetch = vi.fn(async (url: string, init?: RequestInit) => {
    let result: unknown;
    if (url === "/api/library/cart") result = currentCart;
    else if (url.endsWith("/active")) result = { payments: active ? [active] : [] };
    else if (url.endsWith("/prepare")) {
      const body = JSON.parse(String(init?.body));
      result = { ...prepared, method: body.method };
    } else if (url.endsWith("/submit")) result = await submit!(JSON.parse(String(init?.body)));
    else if (url.endsWith("/cancel")) result = { ...prepared, state: "abandoned", active: false };
    else result = active ?? prepared;
    return new Response(JSON.stringify(result), { status: 200 });
  });
  vi.stubGlobal("fetch", fetch);
  return fetch;
}

describe("Checkout Transparente Orders", () => {
  it("mostra seleção/total e usa componente oficial com uma parcela", async () => {
    mockFetch();
    render(<CheckoutPage />);
    expect(await screen.findByText("3 foto(s) · R$ 21,00")).toBeTruthy();
    await waitFor(() => expect(settings.initialization.amount).toBe(21));
    expect(settings.customization.paymentMethods).toMatchObject({ minInstallments: 1, maxInstallments: 1 });
    expect(screen.getByRole("link", { name: "Voltar ao carrinho" }).getAttribute("href")).toBe("/library/cart");
    expect(screen.queryByLabelText(/número do cartão/i)).toBeNull();
  });

  it("prepara a seleção atual sem retomar uma compra ativa de outra revisão", async () => {
    const older: MercadoPagoPayment = { ...prepared, id: "22222222-2222-4222-8222-222222222222",
      state: "processing", total_cents: 10500, cart_revision: "b".repeat(64) };
    const fetch = mockFetch(undefined, older);
    render(<CheckoutPage />);
    expect(await screen.findByText("3 foto(s) · R$ 21,00")).toBeTruthy();
    expect(fetch.mock.calls.some(([url]) => url.endsWith("/prepare"))).toBe(true);
    expect(screen.queryByText("Compra 22222222")).toBeNull();
  });

  it("não prepara Mercado Pago abaixo de R$ 1 e mantém a seleção", async () => {
    const fetch = mockFetch(undefined, null, { ...cart, total_cents: 99 });
    render(<CheckoutPage />);
    expect(await screen.findByText(/selecione fotos que somem pelo menos R\$ 1,00/i)).toBeTruthy();
    expect(fetch.mock.calls.some(([url]) => url.endsWith("/prepare"))).toBe(false);
    expect(screen.queryByLabelText(/pagamento seguro com cartão/i)).toBeNull();
  });

  it("mostra recusa de validação HTTP sem marcar pagamento como incerto", async () => {
    const fetch = mockFetch(async () => {
      throw new PaymentRequestError("Essa forma de pagamento aceita compras a partir de R$ 22,00.", 409);
    });
    render(<CheckoutPage />);
    await waitFor(() => expect(settings).toBeTruthy());
    await act(async () => { await settings.callbacks.onSubmit(cardData); });
    expect(await screen.findByText("Essa forma de pagamento aceita compras a partir de R$ 22,00.")).toBeTruthy();
    expect(screen.queryByText("Verificando pagamento")).toBeNull();
    expect(screen.getByRole("radio", { name: "Cartão de crédito" })).toBeTruthy();
    expect(fetch.mock.calls.filter(([url]) => url.endsWith("/submit"))).toHaveLength(1);
  });

  it("envia token uma vez, sem aceitar valor do formulário e desmonta o componente", async () => {
    let finish: (value: MercadoPagoPayment) => void = () => undefined;
    const pending = new Promise<MercadoPagoPayment>((resolve) => { finish = resolve; });
    const fetch = mockFetch(async () => pending);
    render(<CheckoutPage />);
    await screen.findByRole("radio", { name: "Cartão de crédito" });
    await waitFor(() => expect(settings).toBeTruthy());
    let first: Promise<void>;
    await act(async () => {
      first = settings.callbacks.onSubmit(cardData);
      await settings.callbacks.onSubmit(cardData);
    });
    const requests = fetch.mock.calls.filter(([url]) => url.endsWith("/submit"));
    expect(requests).toHaveLength(1);
    expect(JSON.parse(String(requests[0][1]?.body))).toEqual({
      token: "single-use-token", payment_method_id: "visa",
      email: "buyer@testuser.test", identification_number: "12345678909",
    });
    await act(async () => {
      finish({ ...prepared, state: "confirmed", active: false, can_cancel: false }); await first!;
    });
    expect(await screen.findByText("Pagamento confirmado")).toBeTruthy();
    await waitFor(() => expect(unmount).toHaveBeenCalled());
  });

  it("gera PIX sem coletar cartão e mostra pendência confirmada pelo servidor", async () => {
    const fetch = mockFetch(async () => ({
      ...prepared, method: "pix", state: "pending", pix_copy_paste: "PIX-FIXTURE",
    }));
    render(<CheckoutPage />);
    await userEvent.click(await screen.findByRole("radio", { name: "PIX Mercado Pago" }));
    await userEvent.type(await screen.findByLabelText("E-mail para o pagamento"), "buyer@testuser.test");
    await userEvent.type(screen.getByLabelText("CPF do pagador"), "12345678909");
    await userEvent.click(screen.getByRole("button", { name: "Gerar PIX" }));
    expect(await screen.findByText("Aguardando pagamento")).toBeTruthy();
    expect(screen.getByLabelText("PIX copia e cola")).toHaveProperty("value", "PIX-FIXTURE");
    const body = JSON.parse(String(fetch.mock.calls.find(([url]) => url.endsWith("/submit"))?.[1]?.body));
    expect(body.token).toBeUndefined(); expect(body.total_amount).toBeUndefined();
  });

  it("resposta perdida entra em verificação e impede novo envio de cartão", async () => {
    mockFetch(async () => { throw new Error("network"); });
    render(<CheckoutPage />);
    await waitFor(() => expect(settings).toBeTruthy());
    await act(async () => { await settings.callbacks.onSubmit(cardData); });
    expect(await screen.findByText("Verificando pagamento")).toBeTruthy();
    expect(screen.queryByRole("radio", { name: "Cartão de crédito" })).toBeNull();
    expect(screen.getByRole("button", { name: "Atualizar pagamento" })).toBeTruthy();
  });

  it("retoma tentativa pendente sem criar outra mesmo sem novo meio habilitado", async () => {
    const fetch = mockFetch(undefined, { ...prepared, state: "pending" });
    render(<CheckoutPage />);
    expect(await screen.findByText("Aguardando pagamento")).toBeTruthy();
    expect(fetch.mock.calls.some(([url]) => url.endsWith("/prepare"))).toBe(false);
    expect(screen.getByRole("button", { name: "Cancelar tentativa e editar seleção" })).toBeTruthy();
  });

  it("mantém edição bloqueada e explica enquanto a tentativa está em processamento", async () => {
    mockFetch(undefined, { ...prepared, state: "processing", can_cancel: false });
    render(<CheckoutPage />);
    expect(await screen.findByText("Pagamento em processamento")).toBeTruthy();
    expect(screen.getByRole("status").textContent).toContain(
      "Aguarde o resultado; a seleção vinculada não pode ser cancelada ou editada agora.");
    expect(screen.queryByRole("button", { name: "Cancelar tentativa e editar seleção" })).toBeNull();
  });

  it("atualiza o carrinho quando polling recupera a confirmação", async () => {
    const pending = { ...prepared, state: "verification_required" };
    const fetch = mockFetch(undefined, pending);
    const timer = vi.spyOn(window, "setInterval");
    const poll = () => {
      const interval = timer.mock.calls.find(([, delay]) => delay === 10_000);
      if (interval && typeof interval[0] === "function") interval[0](...interval.slice(2));
    };
    const changed = vi.fn();
    window.addEventListener("client-cart-changed", changed);
    try {
      render(<CheckoutPage />);
      await screen.findByText("Verificando pagamento");
      await waitFor(() => expect(timer.mock.calls.some(([, delay]) => delay === 10_000)).toBe(true));
      pending.state = "confirmed"; pending.active = false;
      await act(async () => {
        poll?.();
      });
      await waitFor(() => expect(fetch.mock.calls.some(([url]) =>
        String(url).endsWith(`/library/mercadopago/${pending.id}`))).toBe(true));
      await screen.findByText("Pagamento confirmado");
      expect(changed).toHaveBeenCalledOnce();
      expect(fetch.mock.calls.some(([url]) => url.endsWith("/submit") || url.endsWith("/prepare"))).toBe(false);
    } finally {
      timer.mockRestore();
      window.removeEventListener("client-cart-changed", changed);
    }
  });
});
