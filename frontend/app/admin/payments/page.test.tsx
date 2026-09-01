import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import AdminPaymentsPage from "./page";

afterEach(() => vi.restoreAllMocks());

const communication = {
  id: "communication-1",
  status: "pending_review",
  order_id: "12345678-order",
  client_name: "Ana",
  gallery_name: "Formatura privada",
  gallery_removed: false,
  total_cents: 1200,
  created_at: "2026-08-29T10:00:00Z",
  decided_at: null,
  can_decide: true,
  photographer_notification: { id: "notice-1", status: "failed", attempts: 1, last_error: "Falha temporária de entrega.", can_retry: true },
  client_notification: null,
};

function dashboard(name = "Ana", nextCursor: string | null = null) {
  return {
    summary: { clients: 1, orders: 1, total_cents: 1200, financial_statuses: { reported: 1 }, failed_messages: 1 },
    facets: {
      parent_galleries: [{ id: "gallery-public-1", name: "Formatura", count: 1 }],
      financial_statuses: { reported: 1 },
      delivery_statuses: { failed: 1 },
    },
    groups: [{
      client: { id: `client-${name}`, name },
      totals: { orders: 1, total_cents: 1200 },
      orders: [{
        id: `${name.toLowerCase()}-order-12345678`,
        parent_gallery: { id: "gallery-public-1", name: "Formatura", removed: false },
        gallery: { id: "gallery-private-1", name: "Formatura privada", removed: false },
        total_cents: 1200,
        financial_status: "reported",
        created_at: "2026-08-29T10:00:00Z",
        selection_expires_at: null,
        communications: [communication],
        communication,
        delivery_statuses: ["failed"],
      }],
    }],
    page: { next_cursor: nextCursor, limit: 12 },
  };
}

const emptyDashboard = {
  summary: { clients: 0, orders: 0, total_cents: 0, financial_statuses: {}, failed_messages: 0 },
  facets: { parent_galleries: [], financial_statuses: {}, delivery_statuses: {} },
  groups: [],
  page: { next_cursor: null, limit: 12 },
};

describe("controle operacional de pagamentos", () => {
  it("agrupa por cliente, mostra resumo e preserva decisão e retry autorizados", async () => {
    const fetchMock = vi.fn((_path: string, options?: RequestInit) => {
      if (options?.method === "POST") return Promise.resolve(new Response(JSON.stringify({ status: "confirmed" }), { status: 200 }));
      return Promise.resolve(new Response(JSON.stringify(dashboard()), { status: 200 }));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<AdminPaymentsPage />);

    expect(await screen.findByRole("heading", { name: "Ana" })).toBeTruthy();
    expect(screen.getAllByText(/12,00/).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Pagamento comunicado").length).toBeGreaterThan(0);
    expect(screen.getByText(/Aviso ao fotógrafo: falha de mensagem/i)).toBeTruthy();
    expect(screen.queryByText(/copia e cola|telefone|api key/i)).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Confirmar pagamento" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/admin/payment-communications/communication-1/decision",
      expect.objectContaining({ method: "POST" }),
    ));
    expect(await screen.findByText(/Decisão registrada/i)).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Tentar enviar novamente" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/admin/payment-notifications/notice-1/retry",
      expect.objectContaining({ method: "POST" }),
    ));
  });

  it("combina filtros, apresenta vazio específico e permite limpar", async () => {
    const fetchMock = vi.fn((path: string) => Promise.resolve(new Response(
      JSON.stringify(path.includes("query=Inexistente") ? emptyDashboard : dashboard()),
      { status: 200 },
    )));
    vi.stubGlobal("fetch", fetchMock);
    render(<AdminPaymentsPage />);
    await screen.findByRole("heading", { name: "Ana" });

    fireEvent.change(screen.getByLabelText("Cliente"), { target: { value: "Inexistente" } });
    fireEvent.change(screen.getByLabelText("Situação financeira"), { target: { value: "reported" } });
    fireEvent.change(screen.getByLabelText("Entrega de mensagem"), { target: { value: "failed" } });
    fireEvent.click(screen.getByRole("button", { name: "Aplicar filtros" }));

    expect(await screen.findByText("Nenhum pagamento neste filtro")).toBeTruthy();
    expect(fetchMock.mock.calls.some(([path]) => String(path).includes("query=Inexistente") && String(path).includes("financial_status=reported") && String(path).includes("delivery_status=failed"))).toBe(true);
    fireEvent.click(screen.getAllByRole("button", { name: "Limpar filtros" })[1]);
    expect(await screen.findByRole("heading", { name: "Ana" })).toBeTruthy();
  });

  it("carrega a próxima página sem substituir os grupos anteriores", async () => {
    const fetchMock = vi.fn((path: string) => Promise.resolve(new Response(
      JSON.stringify(path.includes("cursor=next-page") ? dashboard("Bia") : dashboard("Ana", "next-page")),
      { status: 200 },
    )));
    vi.stubGlobal("fetch", fetchMock);
    render(<AdminPaymentsPage />);
    await screen.findByRole("heading", { name: "Ana" });

    fireEvent.click(screen.getByRole("button", { name: "Carregar mais clientes" }));
    expect(await screen.findByRole("heading", { name: "Bia" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Ana" })).toBeTruthy();
  });
});
