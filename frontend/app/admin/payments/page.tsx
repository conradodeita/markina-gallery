"use client";

import { useCallback, useEffect, useState } from "react";

import { StatusBadge, SystemState } from "../../ui-kit";

type Delivery = {
  id: string;
  status: "queued" | "processing" | "sent" | "failed";
  attempts: number;
  last_error: string | null;
  can_retry: boolean;
};
type Communication = {
  id: string;
  status: "pending_review" | "confirmed" | "refused";
  order_id: string;
  client_name: string;
  gallery_name: string;
  total_cents: number;
  created_at: string;
  decided_at: string | null;
  photographer_notification: Delivery | null;
  client_notification: Delivery | null;
};

const decisionLabel = {
  pending_review: "Aguardando revisão",
  confirmed: "Pagamento confirmado",
  refused: "Pagamento não localizado",
};

export default function AdminPaymentsPage() {
  const [communications, setCommunications] = useState<Communication[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [message, setMessage] = useState("");

  const load = useCallback(() => {
    fetch("/api/admin/payment-communications", { credentials: "same-origin" })
      .then(async (response) => {
        if (!response.ok) throw new Error();
        setCommunications((await response.json()).communications ?? []);
        setFailed(false);
      })
      .catch(() => setFailed(true));
  }, []);

  useEffect(() => load(), [load]);

  async function decide(id: string, decision: "confirmed" | "refused") {
    const response = await fetch(`/api/admin/payment-communications/${id}/decision`, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision }),
    });
    setMessage(response.ok ? "Decisão registrada. A resposta foi encaminhada à caixa de saída." : "Não foi possível registrar a decisão.");
    if (response.ok) load();
  }

  async function retry(notificationId: string) {
    const response = await fetch(`/api/admin/payment-notifications/${notificationId}/retry`, {
      method: "POST",
      credentials: "same-origin",
    });
    setMessage(response.ok ? "Notificação reenfileirada." : "O limite de tentativas não permite novo envio.");
    if (response.ok) load();
  }

  if (failed) return <SystemState tone="error" title="Pagamentos indisponíveis" detail="Não foi possível carregar as comunicações para revisão." />;
  if (communications === null) return <SystemState tone="loading" title="Carregando pagamentos" detail="Consultando comunicações e entregas transacionais." />;

  return <main className="admin-shell">
    <p className="eyebrow">Operação financeira · decisão manual</p>
    <h1>Pagamentos comunicados</h1>
    <p className="intro">A comunicação da cliente não confirma o PIX. Revise o pedido e registre uma única decisão; a primeira decisão é preservada.</p>
    {!communications.length && <SystemState title="Nenhum pagamento comunicado" detail="As comunicações das clientes aparecerão aqui sem comprovantes ou dados bancários." />}
    {communications.map((communication) => <section className="admin-card" key={communication.id}>
      <StatusBadge tone={communication.status === "confirmed" ? "success" : communication.status === "refused" ? "danger" : "warning"}>{decisionLabel[communication.status]}</StatusBadge>
      <h2>{communication.client_name} · R$ {(communication.total_cents / 100).toFixed(2).replace(".", ",")}</h2>
      <p>{communication.gallery_name} · pedido {communication.order_id.slice(0, 8)}</p>
      <p>Comunicado em {new Date(communication.created_at).toLocaleString("pt-BR")}</p>
      {communication.status === "pending_review" && <div className="dashboard-actions">
        <button className="primary" type="button" onClick={() => decide(communication.id, "confirmed")}>Confirmar pagamento</button>
        <button className="secondary" type="button" onClick={() => decide(communication.id, "refused")}>Pagamento não localizado</button>
      </div>}
      <DeliveryState label="Aviso ao fotógrafo" delivery={communication.photographer_notification} onRetry={retry} />
      {communication.status !== "pending_review" && <DeliveryState label="Resposta à cliente" delivery={communication.client_notification} onRetry={retry} />}
    </section>)}
    {message && <p className="form-message" role="status">{message}</p>}
  </main>;
}

function DeliveryState({ label, delivery, onRetry }: { label: string; delivery: Delivery | null; onRetry: (id: string) => void }) {
  if (!delivery) return <p>{label}: não enfileirado — confira a configuração do ambiente.</p>;
  const status = delivery.status === "sent" ? "entregue" : delivery.status === "failed" ? "falhou" : delivery.status === "processing" ? "enviando" : "na fila";
  return <div className={`upload-status${delivery.status === "failed" ? " upload-status--error" : delivery.status === "sent" ? " upload-status--success" : ""}`}>
    <strong>{label}: {status}</strong>
    <span>{delivery.attempts} tentativa(s){delivery.last_error ? ` · ${delivery.last_error}` : ""}</span>
    {delivery.can_retry && <button className="link-button" type="button" onClick={() => onRetry(delivery.id)}>Tentar enviar novamente</button>}
  </div>;
}
