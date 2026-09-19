"use client";

import { useRef, useState } from "react";
import { MarkinaButton, StatusBadge } from "../../ui-kit";

export type FinancialOrder = {
  id: string;
  order_id: string;
  gallery_name: string;
  total_cents: number;
  quantity?: number;
  created_at: string;
  status: "pending_review" | "confirmed" | "refused";
  can_decide: boolean;
  can_correct: boolean;
};

const money = (value: number) => (value / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

export function PaymentActions({ order, clientName, onRefresh }: { order: FinancialOrder; clientName: string; onRefresh: () => void | Promise<void> }) {
  const locked = useRef(false);
  const correctionKey = useRef<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function act(action: "confirmed" | "refused" | "correction") {
    if (locked.current || (action === "correction" ? !order.can_correct : !order.can_decide)) return;
    const label = action === "confirmed" ? "Confirmar pagamento" : action === "refused" ? "Pagamento não localizado" : "Corrigir confirmação";
    const context = `${clientName} · ${order.gallery_name}\nPedido ${order.order_id} · ${order.quantity === undefined ? "" : `${order.quantity} foto(s) · `}${money(order.total_cents)}`;
    if (!window.confirm(`${label}?\n${context}${action === "correction" ? "\nO pagamento voltará para revisão. Nenhuma mensagem será enviada à cliente." : ""}`)) return;
    locked.current = true; setBusy(true); setMessage("");
    try {
      if (action === "correction") correctionKey.current ??= crypto.randomUUID();
      const response = await fetch(`/api/admin/payment-communications/${order.id}/${action === "correction" ? "correction" : "decision"}`, {
        method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(action === "correction" ? { idempotency_key: correctionKey.current } : { decision: action }),
      });
      const result = await response.json().catch(() => null);
      const expectedStatus = action === "correction" ? "pending_review" : action;
      const conflict = response.status === 409 || (response.ok && result?.status && result.status !== expectedStatus);
      setMessage(conflict ? "Pedido atualizado por outra sessão. Confira o estado atual." : response.ok ? (action === "correction" ? "Confirmação corrigida. Nenhuma mensagem enviada." : "Decisão registrada.") : "Não foi possível registrar a decisão. Atualize e tente novamente.");
      if (response.ok) correctionKey.current = null;
      await onRefresh();
    } catch {
      setMessage("Não foi possível confirmar o resultado. Atualize o pedido antes de tentar novamente.");
    } finally { locked.current = false; setBusy(false); }
  }

  return <div className="payment-shortcut-actions">
    <div className="dashboard-actions">
      {order.can_decide ? <><MarkinaButton type="button" disabled={busy} onClick={() => void act("confirmed")}>Confirmar pagamento</MarkinaButton><MarkinaButton type="button" variant="secondary" disabled={busy} onClick={() => void act("refused")}>Pagamento não localizado</MarkinaButton></> : null}
      {order.can_correct ? <MarkinaButton type="button" variant="secondary" disabled={busy} onClick={() => void act("correction")}>Corrigir confirmação</MarkinaButton> : null}
    </div>
    {message ? <p role="status">{message}</p> : null}
  </div>;
}

export function FinancialOrderShortcuts({ orders = [], clientName, onRefresh }: { orders?: FinancialOrder[]; clientName: string; onRefresh: () => void | Promise<void> }) {
  const [templates, setTemplates] = useState<Record<string, string> | null>(null);
  const [previewError, setPreviewError] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  async function loadTemplates() {
    if (templates || previewLoading) return;
    setPreviewLoading(true); setPreviewError(false);
    try {
      const response = await fetch("/api/admin/payment-message-templates", { credentials: "same-origin" });
      if (!response.ok) throw new Error();
      setTemplates((await response.json()).templates);
    } catch { setPreviewError(true); }
    finally { setPreviewLoading(false); }
  }
  if (!orders.length) return null;
  return <div className="financial-order-shortcuts" aria-label={`Pagamentos de ${clientName}`}>
    {orders.map((order) => <section key={order.order_id} aria-label={`Pedido ${order.order_id}`} className={`financial-order-shortcut financial-order-shortcut--${order.status}`}>
      <StatusBadge tone={order.status === "pending_review" ? "warning" : order.status === "confirmed" ? "success" : "danger"}>{order.status === "pending_review" ? "Pagamento comunicado" : order.status === "confirmed" ? "Pagamento confirmado" : "Pagamento não localizado"}</StatusBadge>
      <strong>Pedido {order.order_id.slice(0, 8)} · {order.quantity} foto(s) · {money(order.total_cents)}</strong>
      <time dateTime={order.created_at}>Informado em {new Date(order.created_at).toLocaleString("pt-BR")}</time>
      <PaymentActions order={order} clientName={clientName} onRefresh={onRefresh} />
    </section>)}
    <details onToggle={(event) => { if (event.currentTarget.open) void loadTemplates(); }}>
      <summary>Prévia das mensagens globais</summary>
      {templates ? <><p>Confirmado: {templates.confirmed}</p><p>Não localizado: {templates.refused}</p></> : <p>{previewError ? "Prévia indisponível. Consulte Notificações." : "Carregando prévia…"}</p>}
      <a className="gallery-client-open" href="/admin/notifications#payment_confirmed">Editar em Notificações · afeta todos os clientes</a>
    </details>
  </div>;
}
