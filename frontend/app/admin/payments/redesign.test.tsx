import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import AdminPaymentsPage from "./page";

afterEach(() => vi.restoreAllMocks());

const payload = {
  summary: { clients: 1, orders: 0, selected_carts: 0, selected_cents: 0, selected_pricing_unavailable: 0, reported_orders: 0, reported_cents: 0, confirmed_orders: 0, confirmed_cents: 0 },
  facets: { parent_galleries: [{ id: "event-1", name: "Festa", count: 1 }] },
  templates: { confirmed: "Confirmado", refused: "Não localizado" },
  groups: [], page: { next_cursor: null, limit: 12 },
};
function mockFetch() {
  const mock = vi.fn((path: string) => {
    if (path.includes("/clients?")) return Promise.resolve(new Response(JSON.stringify({ clients: [{ id: "client-1", name: "Maria" }] })));
    return Promise.resolve(new Response(JSON.stringify(path.endsWith("gallery-reopening-requests") ? { requests: [] } : payload)));
  });
  vi.stubGlobal("fetch", mock);
  return mock;
}
const queries = (mock: ReturnType<typeof mockFetch>) => mock.mock.calls.map(([path]) => path).filter((path) => path.includes("payment-communications?"));

it("inicia com pendências, diferencia Todos e restaura priority ao limpar", async () => {
  const mock = mockFetch(); render(<AdminPaymentsPage />);
  await screen.findByText("Nenhuma pendência prioritária");
  expect(new URL(queries(mock)[0], "http://localhost").searchParams.get("financial_status")).toBe("priority");
  fireEvent.click(screen.getByText("Mais filtros"));
  fireEvent.change(screen.getByLabelText("Situação financeira"), { target: { value: "" } });
  fireEvent.change(screen.getByLabelText("Galeria pública"), { target: { value: "event-1" } });
  fireEvent.change(screen.getByLabelText("De"), { target: { value: "2026-10-01" } });
  fireEvent.click(screen.getByRole("button", { name: "Aplicar filtros" }));
  await waitFor(() => expect(queries(mock).length).toBe(2));
  const all = new URL(queries(mock)[1], "http://localhost").searchParams;
  expect(all.has("financial_status")).toBe(false);
  expect(all.get("parent_gallery_id")).toBe("event-1");
  fireEvent.click(screen.getAllByRole("button", { name: "Limpar filtros" })[0]);
  await waitFor(() => expect(queries(mock).length).toBe(3));
  expect(new URL(queries(mock)[2], "http://localhost").searchParams.toString()).toBe("financial_status=priority&limit=12");
  expect((screen.getByLabelText("Situação financeira") as HTMLSelectElement).value).toBe("priority");
});

it.each(["mouse", "Enter"])("aplica sugestão por %s uma vez com filtros já aplicados", async (method) => {
  const mock = mockFetch(); render(<AdminPaymentsPage />);
  const input = await screen.findByLabelText("Cliente / telefone");
  fireEvent.click(screen.getByText("Mais filtros"));
  fireEvent.change(screen.getByLabelText("Situação financeira"), { target: { value: "confirmed_undelivered" } });
  fireEvent.change(screen.getByLabelText("Galeria pública"), { target: { value: "event-1" } });
  fireEvent.click(screen.getByRole("button", { name: "Aplicar filtros" }));
  await waitFor(() => expect(queries(mock).length).toBe(2));
  fireEvent.change(input, { target: { value: "Ma" } });
  const option = await screen.findByRole("option", { name: "Maria" });
  if (method === "mouse") fireEvent.click(option);
  else { fireEvent.keyDown(input, { key: "ArrowDown" }); fireEvent.keyDown(input, { key: "Enter" }); }
  await waitFor(() => expect(queries(mock).length).toBe(3));
  const params = new URL(queries(mock)[2], "http://localhost").searchParams;
  expect(params.get("client_id")).toBe("client-1");
  expect(params.get("financial_status")).toBe("confirmed_undelivered");
  expect(params.get("parent_gallery_id")).toBe("event-1");
});

it("exporta filtros aplicados sem cursor, mostra busy e informa vazio/erro", async () => {
  const mock = mockFetch(); render(<AdminPaymentsPage />);
  await screen.findByLabelText("Cliente / telefone");
  let resolveExport: (response: Response) => void = () => {};
  mock.mockImplementation((path) => path.includes("export.csv") ? new Promise<Response>((resolve) => { resolveExport = resolve; }) : Promise.resolve(new Response(JSON.stringify(payload))));
  fireEvent.change(screen.getByLabelText("Situação financeira"), { target: { value: "reported" } });
  fireEvent.click(screen.getByRole("button", { name: "Exportar CSV" }));
  expect(screen.getByRole("button", { name: "Exportando…" })).toHaveProperty("disabled", true);
  const exportPath = mock.mock.calls.at(-1)![0];
  const params = new URL(exportPath, "http://localhost").searchParams;
  expect(params.get("financial_status")).toBe("priority");
  expect(params.has("cursor") || params.has("limit")).toBe(false);
  resolveExport(new Response(null, { status: 204 }));
  await screen.findByText("Nenhum pedido nos filtros aplicados para exportar.");
  fireEvent.click(screen.getByRole("button", { name: "Exportar CSV" }));
  resolveExport(new Response("", { status: 503 }));
  await screen.findByText("Não foi possível exportar o CSV. Tente novamente.");
});

it("não monta miniaturas antes de expandir o pedido e as desmonta ao recolher", async () => {
  const data = { ...payload, groups: [{
    client: { id: "client", name: "Cliente Sintética" }, financial_status: "reported",
    totals: { orders: 1, reported_orders: 1, reported_cents: 700, confirmed_cents: 0 },
    orders: [{ id: "order", gallery: { id: "private", name: "Privada", removed: false },
      parent_gallery: { id: "public", name: "Festa", removed: false }, total_cents: 700,
      financial_status: "reported", created_at: "2026-10-17T12:00:00Z", communication: null,
      folders: [{ id: "folder", name: "Pasta", items: [{ id: "item", photo_id: "photo", name: "foto.jpg", unit_price_cents: 700,
        thumbnail_url: "/admin/orders/order/items/item/preview?size=thumbnail", preview_url: "/admin/orders/order/items/item/preview?size=preview" }] }],
    }],
  }] };
  vi.stubGlobal("fetch", vi.fn((path: string) => Promise.resolve(new Response(JSON.stringify(path.endsWith("gallery-reopening-requests") ? { requests: [] } : data)))));
  render(<AdminPaymentsPage />);
  const summary = await screen.findByText("Ver pedido e entrega");
  expect(document.querySelectorAll("img")).toHaveLength(0);
  fireEvent.click(summary);
  await screen.findByRole("button", { name: "Ampliar foto.jpg" });
  expect(document.querySelector("img")?.getAttribute("loading")).toBe("lazy");
  fireEvent.click(summary);
  await waitFor(() => expect(screen.queryByRole("button", { name: "Ampliar foto.jpg" })).toBeNull());
});

it("descarta uma resposta antiga quando a consulta livre muda", async () => {
  const mock = mockFetch(); render(<AdminPaymentsPage />);
  await screen.findByLabelText("Cliente / telefone");
  let finishOld: (response: Response) => void = () => {};
  mock.mockImplementation((path) => path.includes("query=antiga") ? new Promise<Response>((resolve) => { finishOld = resolve; }) : Promise.resolve(new Response(JSON.stringify({ ...payload, summary: { ...payload.summary, clients: 2 } }))));
  fireEvent.change(screen.getByLabelText("Cliente / telefone"), { target: { value: "antiga" } });
  fireEvent.click(screen.getByRole("button", { name: "Aplicar" }));
  fireEvent.change(screen.getByLabelText("Cliente / telefone"), { target: { value: "nova" } });
  fireEvent.click(screen.getByRole("button", { name: "Aplicar" }));
  await screen.findByText("2");
  finishOld(new Response(JSON.stringify({ ...payload, summary: { ...payload.summary, clients: 99 } })));
  await waitFor(() => expect(screen.queryByText("99")).toBeNull());
});

it("baixa CSV recebido do servidor e libera o objeto temporário", async () => {
  const mock = mockFetch(); render(<AdminPaymentsPage />);
  await screen.findByLabelText("Cliente / telefone");
  const create = vi.fn(() => "blob:synthetic"); const revoke = vi.fn();
  Object.defineProperty(URL, "createObjectURL", { configurable: true, value: create });
  Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: revoke });
  const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
  mock.mockImplementation(() => Promise.resolve(new Response("\ufeffNome do cliente;Item/descrição;Total dos itens/pedido;Data e hora\r\n")));
  fireEvent.click(screen.getByRole("button", { name: "Exportar CSV" }));
  await screen.findByText("CSV exportado com todos os pedidos dos filtros aplicados.");
  expect(click).toHaveBeenCalledOnce();
  expect(create).toHaveBeenCalledOnce();
  expect(revoke).toHaveBeenCalledWith("blob:synthetic");
});
