import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import PaymentProvidersPanel from "../admin/settings/payment-providers-panel";
import PurchasesPage from "./purchases/page";
import AdminPaymentsPage from "../admin/payments/page";

afterEach(() => vi.unstubAllGlobals());
const settings = { version: 0, pix_enabled: true, mercadopago_enabled: false,
  mercadopago_available: false, account: null };

it("configura flags independentes com senha e confirmação final vinculada", async () => {
  const fetch = vi.fn(async (_url: string, init?: RequestInit) => new Response(JSON.stringify(
    !init?.method ? settings : String(_url).endsWith("/challenge")
      ? { challenge_id: "challenge", expires_at: "2099-01-01T00:00:00Z" }
      : { ...settings, version: 1, pix_enabled: false, mercadopago_enabled: true, mercadopago_available: true },
  )));
  vi.stubGlobal("fetch", fetch);
  render(<PaymentProvidersPanel />);
  const pix = await screen.findByRole("checkbox", { name: "PIX do sistema" });
  await waitFor(() => expect((pix as HTMLInputElement).disabled).toBe(false));
  await userEvent.click(pix);
  await userEvent.click(screen.getByRole("checkbox", { name: "Mercado Pago · Checkout Transparente" }));
  fireEvent.change(screen.getByLabelText("Sua senha atual"), { target: { value: "local-password" } });
  await userEvent.click(screen.getByRole("button", { name: "Confirmar alteração por código" }));
  expect(JSON.parse(String(fetch.mock.calls[1][1]?.body))).toMatchObject({
    pix_enabled: false, mercadopago_enabled: true, expected_version: 0, current_password: "local-password",
  });
  fireEvent.change(await screen.findByLabelText("Código de confirmação"), { target: { value: "123456" } });
  await userEvent.click(screen.getByRole("button", { name: "Salvar meios de pagamento" }));
  await screen.findByText(/Meios de pagamento salvos/);
  expect(JSON.parse(String(fetch.mock.calls[2][1]?.body))).toEqual({
    challenge_id: "challenge", code: "123456",
  });
});

it("Compras agrupa Mercado Pago sem apresentar PIX manual ou InfinitePay", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({
    orders: [], payment_groups: [], provider_payment_groups: [],
    mercadopago_payment_groups: [{ id: "12345678-fixture", state: "pending", active: true,
      method: "pix", total_cents: 2100, test_account: true, orders: [] }],
  }))));
  render(<PurchasesPage />);
  expect(await screen.findByText("Aguardando pagamento")).toBeTruthy();
  expect(screen.getByText(/Mercado Pago · TESTE/)).toBeTruthy();
  expect(screen.getByRole("link", { name: "Acompanhar pagamento" }).getAttribute("href"))
    .toBe("/library/checkout?payment=12345678-fixture");
  expect(screen.queryByText(/InfinitePay/)).toBeNull();
  expect(screen.queryByText(/Nenhuma compra/)).toBeNull();
});

it("painel distingue situação, provedor e transação e envia os filtros", async () => {
  const mp = { id: "12345678-fixture", state: "partially_refunded", method: "pix", test_account: true,
    order_status: "processed", order_detail: "partially_refunded",
    transaction_status: "processed", transaction_detail: "partially_refunded",
    provider_order_id: "ORDFIXTURE", provider_payment_id: "PAYFIXTURE" };
  const fetch = vi.fn(async (url: string) => new Response(JSON.stringify(
    url.endsWith("gallery-reopening-requests") ? { requests: [] } : {
      summary: { clients: 1, selected_carts: 0, selected_cents: 0, selected_pricing_unavailable: 0,
        reported_orders: 0, reported_cents: 0, confirmed_orders: 0, confirmed_cents: 0 },
      facets: { parent_galleries: [] }, selections_without_order: [],
      templates: { confirmed: "Confirmado", refused: "Recusado" }, page: { next_cursor: null, limit: 12 },
      groups: [{ client: { id: "client", name: "Cliente teste" }, financial_status: "partially_refunded",
        totals: { orders: 1 }, orders: [{ id: "order", gallery: { id: "gallery", name: "Evento", removed: false },
          parent_gallery: { id: "parent", name: "Evento", removed: false }, total_cents: 2100,
          financial_status: "partially_refunded", payment_provider: "mercadopago", payment_method: "pix",
          mercadopago: mp, payment_status: "pending", created_at: "2026-10-24T12:00:00Z",
          communications: [], communication: null, delivery_statuses: [], folders: [] }] }],
    },
  )));
  vi.stubGlobal("fetch", fetch);
  render(<AdminPaymentsPage />);
  await screen.findByText("Cliente teste");
  fireEvent.click(screen.getByText("Mais filtros"));
  fireEvent.change(screen.getByLabelText("Provedor"), { target: { value: "mercadopago" } });
  fireEvent.change(screen.getByLabelText("Situação financeira"), { target: { value: "partially_refunded" } });
  fireEvent.click(screen.getByRole("button", { name: "Aplicar filtros" }));
  await waitFor(() => expect(fetch.mock.calls.some(([url]) => url.includes("payment_provider=mercadopago"))).toBe(true));
  fireEvent.click(screen.getByText("Ver pedido e entrega"));
  expect(screen.getByText("ORDFIXTURE")).toBeTruthy();
  expect(screen.getByText("PAYFIXTURE")).toBeTruthy();
  expect(screen.getByText(/TESTE · Compra simulada, excluída da receita/)).toBeTruthy();
  expect(screen.queryByRole("button", { name: /confirmar pagamento/i })).toBeNull();
  expect(screen.getByText(/A entrega desta compra aguarda revisão financeira/)).toBeTruthy();
});
