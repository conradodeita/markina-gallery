import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import AdminPaymentsPage from "./page";
import type { CartRecoveryStatus } from "./cart-recovery";

beforeEach(() => {
  HTMLDialogElement.prototype.showModal = vi.fn(function (this: HTMLDialogElement) { this.open = true; });
  HTMLDialogElement.prototype.close = vi.fn(function (this: HTMLDialogElement) { this.open = false; });
});
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); document.body.style.overflow = ""; });
const response = (data: object) => Promise.resolve(new Response(JSON.stringify(data)));
const card = (id: string) => ({ id, gallery: { id: "gallery", name: "Galeria", removed: false },
  parent_gallery: { id: "parent", name: "Galeria pública", removed: false }, total_cents: 700,
  financial_status: "verifying", created_at: "2026-10-21T10:00:00Z", communication: null,
  payment_method: "credit_card", provider_payment_state: "verification_required", provider_payment_id: "purchase-123",
  provider_cart_recovery: { can_reopen: true, revision: 2, reopened_at: null } as CartRecoveryStatus,
  folders: [{ id: "folder", name: "Pasta", items: [{ id: `item-${id}`, photo_id: `photo-${id}`, name: `${id}.jpg`,
    unit_price_cents: 700, thumbnail_url: `/admin/orders/${id}/items/item/preview?size=thumbnail`,
    preview_url: `/admin/orders/${id}/items/item/preview?size=preview` }] }],
});
const client = (id: string, orders = [card(`order-${id}`)]) => ({
  client: { id, name: `Cliente ${id}` }, financial_status: "verifying",
  totals: { orders: orders.length, reported_orders: 0, reported_cents: 0, confirmed_cents: 0 }, orders,
});
const dashboard = (groups: ReturnType<typeof client>[], cursor: string | null = null) => ({
  summary: { clients: 2, orders: 2, selected_carts: 0, selected_cents: 0, selected_pricing_unavailable: 0,
    reported_orders: 0, reported_cents: 0, confirmed_orders: 0, confirmed_cents: 0 },
  facets: { parent_galleries: [] }, templates: { confirmed: "", refused: "" }, groups,
  page: { next_cursor: cursor, limit: 12 },
});

it("PIX InfinitePay confirmado usa confirmação do provedor sem decisão de PIX manual", async () => {
  const order = { ...card("pix-external"), payment_method: "pix", financial_status: "confirmed",
    provider_payment_state: "confirmed", provider_cart_recovery: { can_reopen: false, revision: 3, reopened_at: null } };
  vi.stubGlobal("fetch", vi.fn((path: string) => response(path.endsWith("gallery-reopening-requests")
    ? { requests: [] } : dashboard([client("a", [order])]))));
  render(<AdminPaymentsPage />);
  fireEvent.click(await screen.findByText("Ver pedido e entrega"));
  expect(screen.getByText(/Estado do checkout InfinitePay: confirmed/)).toBeTruthy();
  expect(screen.getByText(/PIX InfinitePay/)).toBeTruthy();
  expect(screen.queryByRole("button", { name: "Confirmar pagamento" })).toBeNull();
  expect(screen.queryByRole("button", { name: "Pagamento não localizado" })).toBeNull();
});

it("oferece uma reabertura por compra agrupada e não permite reabrir cartão ou PIX confirmado", async () => {
  const orders = [card("order-a"), card("order-b"),
    { ...card("confirmed-card"), financial_status: "confirmed", provider_payment_state: "confirmed", provider_payment_id: "confirmed-card" },
    { ...card("confirmed-pix"), financial_status: "confirmed", payment_method: "pix", provider_payment_id: "" }];
  vi.stubGlobal("fetch", vi.fn((path: string) => response(path.endsWith("gallery-reopening-requests")
    ? { requests: [] } : dashboard([client("a", orders)]))));
  render(<AdminPaymentsPage />);
  const summaries = await screen.findAllByText("Ver pedido e entrega");
  summaries.forEach((summary) => fireEvent.click(summary));
  expect(screen.getAllByRole("button", { name: "Reabrir carrinho" })).toHaveLength(1);
  expect(screen.queryByRole("button", { name: "Confirmar pagamento" })).toBeNull();
});

it("reabre, retira a tentativa da lista ativa e permite consultar seu histórico", async () => {
  let reopened = false;
  const requests: string[] = [];
  const fetcher = vi.fn((path: string) => {
    if (path.endsWith("gallery-reopening-requests")) return response({ requests: [] });
    if (path.endsWith("/preview")) return response({ payment_id: "purchase-123", revision: 2,
      fingerprint: "f".repeat(64), restored_quantity: 1, quantity: 1, total_cents: 700, card_available: true, pix_available: true });
    if (path.endsWith("/cart-recovery")) { reopened = true; return response({ already_reopened: false }); }
    requests.push(path);
    const params = new URL(path, "http://localhost").searchParams;
    const group = client(params.has("cursor") ? "b" : "a");
    if (group.client.id === "a" && reopened) Object.assign(group.orders[0], {
      provider_payment_state: "exception", provider_cart_recovery: {
        can_reopen: false, revision: 3, reopened_at: "2026-10-21T14:00:00Z" },
    });
    const historical = params.get("financial_status") === "reopened";
    return response(dashboard(group.client.id === "a" && reopened && !historical ? [] : [group], params.has("cursor") ? null : "page-two"));
  });
  vi.stubGlobal("fetch", fetcher);
  render(<AdminPaymentsPage />);
  await screen.findByRole("heading", { name: "Cliente a" });
  fireEvent.click(screen.getByText("Mais filtros"));
  fireEvent.change(screen.getByLabelText("Situação financeira"), { target: { value: "verifying" } });
  fireEvent.click(screen.getByRole("button", { name: "Aplicar filtros" }));
  await waitFor(() => expect(requests).toHaveLength(2));
  fireEvent.click(screen.getByRole("button", { name: "Carregar mais clientes" }));
  await screen.findByRole("heading", { name: "Cliente b" });
  fireEvent.click(screen.getAllByText("Ver pedido e entrega")[0]);
  await screen.findByRole("button", { name: "Ampliar order-a.jpg" });
  const firstClient = screen.getByRole("heading", { name: "Cliente a" }).closest("section")!;
  fireEvent.click(within(firstClient).getByRole("button", { name: "Reabrir carrinho" }));
  await screen.findByText(/1 foto\(s\) da compra voltarão selecionadas/);
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.click(screen.getByRole("button", { name: "Confirmar e reabrir carrinho" }));
  await waitFor(() => expect(requests).toHaveLength(5));
  expect(screen.getByRole("heading", { name: "Cliente b" })).toBeTruthy();
  expect(screen.queryByRole("heading", { name: "Cliente a" })).toBeNull();
  expect(screen.queryByRole("button", { name: "Ampliar order-a.jpg" })).toBeNull();
  expect(screen.getByLabelText("Situação financeira")).toHaveProperty("value", "verifying");
  expect(requests.slice(-2).every((path) => new URL(path, "http://localhost").searchParams.get("financial_status") === "verifying")).toBe(true);
  expect(new URL(requests.at(-1)!, "http://localhost").searchParams.get("cursor")).toBe("page-two");
  fireEvent.change(screen.getByLabelText("Situação financeira"), { target: { value: "reopened" } });
  fireEvent.click(screen.getByRole("button", { name: "Aplicar filtros" }));
  await screen.findByRole("heading", { name: "Cliente a" });
  expect(screen.getAllByText("Tentativa encerrada por reabertura").length).toBeGreaterThan(0);
  fireEvent.click(screen.getByText("Ver pedido e entrega"));
  expect(await screen.findByRole("button", { name: "Ampliar order-a.jpg" })).toBeTruthy();
  expect(screen.queryByRole("button", { name: "Reabrir carrinho" })).toBeNull();
  expect(screen.queryByRole("button", { name: /Salvar|Enviar álbum|Confirmar pagamento/ })).toBeNull();
});

it("destaca evidência tardia sem substituir por aviso de carrinho reaberto", async () => {
  const order = { ...card("late"), provider_payment_state: "exception", financial_status: "exception",
    provider_cart_recovery: { can_reopen: false, revision: 3, reopened_at: "2026-10-21T14:00:00Z", requires_reconciliation: true } };
  vi.stubGlobal("fetch", vi.fn((path: string) => response(path.endsWith("gallery-reopening-requests")
    ? { requests: [] } : dashboard([client("a", [order])]))));
  render(<AdminPaymentsPage />);
  await screen.findByRole("heading", { name: "Cliente a" });
  expect(screen.getAllByText("Conferência após reabertura").length).toBeGreaterThan(0);
  fireEvent.click(screen.getByText("Ver pedido e entrega"));
  expect(screen.getByText(/retorno da tentativa anterior/)).toBeTruthy();
  expect(screen.queryByRole("button", { name: "Reabrir carrinho" })).toBeNull();
});
