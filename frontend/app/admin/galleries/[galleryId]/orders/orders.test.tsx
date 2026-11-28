import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import GalleryOrdersPage from "./page";

vi.mock("next/navigation", () => ({ useParams: () => ({ galleryId: "gallery" }) }));
vi.mock("next/link", () => ({ default: ({ children, href }: { children: React.ReactNode; href: string }) => <a href={href}>{children}</a> }));
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });
const order = { id: "original-order", payment_status: "cancelled", total_cents: 15400, client_name: "Cliente",
  cart_reopened_at: "2026-10-21T14:00:00Z", created_at: "2026-10-16T10:00:00Z", price_rule: null,
  sales_message: null, pix: { copy_paste: null, qr_code_payload: null, instructions: null },
  items: [{ photo_id: "original-photo", name: "Foto já escolhida", unit_price_cents: 15400 }] };

it("identifica o original como carrinho reaberto sem outro pedido do rascunho", async () => {
  vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(new Response(JSON.stringify({ orders: [order] })))));
  render(<GalleryOrdersPage />);
  expect(await screen.findByText("Carrinho reaberto")).toBeTruthy();
  expect(screen.getAllByRole("heading", { level: 2 })).toHaveLength(1);
  expect(screen.getByRole("list", { name: "Fotos do pedido original-order" })).toBeTruthy();
  expect(screen.queryByText("Pendente de confirmação")).toBeNull();
});

it.each(["pending", "confirmed"])("preserva a consulta de um pedido %s efetivo", async (payment_status) => {
  vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(new Response(JSON.stringify({ orders: [{ ...order,
    payment_status, cart_reopened_at: null, payment_group: { id: "reported-pix", total_cents: 15400 } }] })))));
  render(<GalleryOrdersPage />);
  expect(await screen.findByText(payment_status === "pending" ? "Pendente de confirmação" : "Confirmado")).toBeTruthy();
  expect(screen.getByText(/Integra o PIX único/)).toBeTruthy();
  expect(screen.queryByText("Carrinho reaberto")).toBeNull();
});

it("busca por nome ou ID e filtra a situação sem nova consulta ou alteração do total confirmado", async () => {
  const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ orders: [
    { ...order, id: "pedido-confirmado", client_name: "Ágata", payment_status: "confirmed", total_cents: 1200 },
    { ...order, id: "pedido-pendente", client_name: "Beatriz", payment_status: "pending", total_cents: 500 },
  ] })));
  vi.stubGlobal("fetch", fetch);
  render(<GalleryOrdersPage />);
  await screen.findByRole("heading", { name: "Ágata · R$ 12,00" });
  const search = screen.getByRole("searchbox", { name: "Buscar pedido por cliente ou ID" });
  fireEvent.change(search, { target: { value: "agata" } });
  expect(screen.queryByRole("heading", { name: "Beatriz · R$ 5,00" })).toBeNull();
  fireEvent.change(search, { target: { value: "pedido-pend" } });
  expect(screen.getByRole("heading", { name: "Beatriz · R$ 5,00" })).toBeTruthy();
  fireEvent.change(screen.getByLabelText("Situação"), { target: { value: "confirmed" } });
  expect(screen.getByText("Nenhum pedido neste filtro")).toBeTruthy();
  expect(within(screen.getByRole("region", { name: "Resumo dos pedidos" })).getByText("R$ 12,00")).toBeTruthy();
  expect(fetch).toHaveBeenCalledOnce();
});
