import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import AdminPaymentsPage from "./page";

afterEach(() => vi.restoreAllMocks());

describe("revisão manual de pagamentos", () => {
  it("mostra decisão e falha de entrega sem expor dados financeiros", async () => {
    const communication = {
      id: "communication-1",
      status: "pending_review",
      order_id: "12345678-order",
      client_name: "Ana",
      gallery_name: "Formatura",
      total_cents: 1200,
      created_at: "2026-08-29T10:00:00Z",
      decided_at: null,
      photographer_notification: { id: "notice-1", status: "failed", attempts: 1, last_error: "Configuração do provedor indisponível.", can_retry: true },
      client_notification: null,
    };
    const fetchMock = vi.fn((path: string, options?: RequestInit) => {
      if (options?.method === "POST") return Promise.resolve(new Response(JSON.stringify({ status: "confirmed" }), { status: 200 }));
      return Promise.resolve(new Response(JSON.stringify({ communications: [communication] }), { status: 200 }));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<AdminPaymentsPage />);

    expect(await screen.findByRole("heading", { name: "Ana · R$ 12,00" })).toBeTruthy();
    expect(screen.getByText(/Aviso ao fotógrafo: falhou/i)).toBeTruthy();
    expect(screen.queryByText(/copia e cola|telefone|api key/i)).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Confirmar pagamento" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/admin/payment-communications/communication-1/decision",
      expect.objectContaining({ method: "POST" }),
    ));
    expect(await screen.findByText(/Decisão registrada/i)).toBeTruthy();
  });
});
