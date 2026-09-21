import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { FinancialOrderShortcuts, PaymentActions, type FinancialOrder } from "./payment-actions";

afterEach(() => vi.restoreAllMocks());
const order: FinancialOrder = { id: "communication-1", order_id: "order-1", gallery_name: "Evento A", total_cents: 700, quantity: 1, created_at: "2026-09-19T12:00:00Z", status: "pending_review", can_decide: true, can_correct: false };
describe("atalhos por pedido", () => {
  it("expõe total e galerias e exige decisão sobre todo o PIX", async () => {
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
    const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ status: "confirmed" })));
    vi.stubGlobal("fetch", fetch);
    const refresh = vi.fn();
    render(<PaymentActions order={{ ...order, payment_group: { id: "group-1", total_cents: 2100,
      galleries: [{ order_id: "order-1", name: "Galeria 1", total_cents: 700 },
        { order_id: "order-2", name: "Galeria 2", total_cents: 1400 }] } }} clientName="Ana" onRefresh={refresh} />);
    fireEvent.click(screen.getByRole("button", { name: "Confirmar pagamento" }));
    await waitFor(() => expect(refresh).toHaveBeenCalledOnce());
    expect(confirm.mock.calls[0][0]).toContain("21,00");
    expect(confirm.mock.calls[0][0]).toContain("Galeria 2");
    expect(confirm.mock.calls[0][0]).toContain("todos esses pedidos");
    expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({ decision: "confirmed", payment_group_id: "group-1" });
  });
  it("identifica pedidos e confirma apenas a compra escolhida", async () => {
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
    const fetch = vi.fn().mockResolvedValue(new Response("{}")); vi.stubGlobal("fetch", fetch);
    const refresh = vi.fn();
    render(<FinancialOrderShortcuts orders={[order, { ...order, id: "communication-2", order_id: "order-2", quantity: 3, total_cents: 2100 }]} clientName="Ana" onRefresh={refresh} />);
    const second = screen.getByRole("region", { name: "Pedido order-2" });
    fireEvent.click(within(second).getByRole("button", { name: "Confirmar pagamento" }));
    await waitFor(() => expect(refresh).toHaveBeenCalledOnce());
    expect(confirm.mock.calls[0][0]).toContain("Ana · Evento A");
    expect(confirm.mock.calls[0][0]).toContain("3 foto(s)");
    expect(fetch).toHaveBeenCalledWith("/api/admin/payment-communications/communication-2/decision", expect.objectContaining({ body: JSON.stringify({ decision: "confirmed" }) }));
    expect(fetch).toHaveBeenCalledOnce();
  });
  it("não confirma sem comunicação ou após cancelar a confirmação", () => {
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
    const fetch = vi.fn(); vi.stubGlobal("fetch", fetch);
    const { rerender } = render(<PaymentActions order={{ ...order, can_decide: false }} clientName="Ana" onRefresh={vi.fn()} />);
    expect(screen.queryByRole("button")).toBeNull();
    rerender(<PaymentActions order={order} clientName="Ana" onRefresh={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Confirmar pagamento" }));
    expect(confirm).toHaveBeenCalledOnce(); expect(fetch).not.toHaveBeenCalled();
  });
  it.each([409, 200])("bloqueia cliques duplicados e revalida conflito HTTP %s", async (status) => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    let resolve!: (value: Response) => void;
    const fetch = vi.fn(() => new Promise<Response>((done) => { resolve = done; })); vi.stubGlobal("fetch", fetch);
    const refresh = vi.fn();
    render(<PaymentActions order={order} clientName="Ana" onRefresh={refresh} />);
    const button = screen.getByRole("button", { name: "Confirmar pagamento" });
    fireEvent.click(button); fireEvent.click(button);
    expect(fetch).toHaveBeenCalledOnce();
    resolve(new Response(JSON.stringify({ status: "refused" }), { status }));
    expect(await screen.findByText(/outra sessão/)).toBeTruthy(); expect(refresh).toHaveBeenCalledOnce();
  });
  it("corrige silenciosamente via endpoint existente e trata falha de rede", async () => {
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
    const fetch = vi.fn().mockRejectedValue(new Error("offline")); vi.stubGlobal("fetch", fetch);
    render(<PaymentActions order={{ ...order, can_decide: false, can_correct: true, status: "confirmed" }} clientName="Ana" onRefresh={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Corrigir confirmação" }));
    expect(await screen.findByText(/Não foi possível confirmar o resultado/)).toBeTruthy();
    expect(confirm.mock.calls[0][0]).toContain("Nenhuma mensagem será enviada");
    expect(fetch.mock.calls[0][0]).toBe("/api/admin/payment-communications/communication-1/correction");
    expect(JSON.parse(fetch.mock.calls[0][1].body).idempotency_key).toBeTruthy();
  });
});
