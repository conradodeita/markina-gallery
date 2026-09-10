"use client";

import { type FormEvent, useCallback, useEffect, useState } from "react";

import { MarkinaButton, MetricCard, StatusBadge, SystemState } from "../../ui-kit";

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
  gallery_removed: boolean;
  total_cents: number;
  created_at: string;
  decided_at: string | null;
  can_decide: boolean;
  can_correct: boolean;
  corrections: Array<{ id: string; created_at: string }>;
  photographer_notification: Delivery | null;
  client_notification: Delivery | null;
};

type FinancialStatus = "awaiting_payment" | "reported" | "confirmed" | "not_found" | "overdue";
type Order = {
  id: string;
  parent_gallery: { id: string; name: string; removed: boolean };
  gallery: { id: string; name: string; removed: boolean };
  total_cents: number;
  financial_status: FinancialStatus;
  created_at: string;
  selection_expires_at: string | null;
  communications: Communication[];
  communication: Communication | null;
  delivery_statuses: string[];
  folders: Array<{ id: string | null; name: string; items: Array<{ id: string; photo_id: string; name: string; unit_price_cents: number }> }>;
  payment_message_snapshot: string | null;
};
type ClientGroup = {
  client: { id: string; name: string };
  totals: { orders: number; total_cents: number };
  orders: Order[];
};
type Dashboard = {
  templates: Record<"confirmed" | "refused", string>;
  templates_are_global: boolean;
  selections_without_order?: Array<{ client: { id: string; name: string }; gallery: { id: string; name: string }; parent_gallery: { id: string; name: string }; selected_count: number; created_at: string; folders: Array<{ id: string; name: string; items: Array<{ id: string; name: string }> }> }>;
  summary: { clients: number; orders: number; total_cents: number; financial_statuses: Record<string, number>; failed_messages: number };
  facets: {
    parent_galleries: Array<{ id: string; name: string; count: number }>;
    financial_statuses: Record<string, number>;
    delivery_statuses: Record<string, number>;
  };
  groups: ClientGroup[];
  page: { next_cursor: string | null; limit: number };
};
type Reopening = { id: string; gallery_id: string; gallery_name: string; status: "pending" | "approved" | "refused"; created_at: string; approved_until: string | null; notification: { id: string | null; status: string; attempts: number; can_retry: boolean } };
type Filters = {
  query?: string;
  parent_gallery_id?: string;
  financial_status?: string;
  delivery_status?: string;
  created_from?: string;
  created_to?: string;
};

const financialPresentation: Record<FinancialStatus, { label: string; tone: "neutral" | "success" | "warning" | "danger" | "dark" }> = {
  awaiting_payment: { label: "Aguardando pagamento", tone: "neutral" },
  reported: { label: "Pagamento comunicado", tone: "warning" },
  confirmed: { label: "Pagamento confirmado", tone: "success" },
  not_found: { label: "Pagamento não localizado", tone: "danger" },
  overdue: { label: "Prazo expirado", tone: "dark" },
};
const decisionLabel = {
  pending_review: "Aguardando revisão",
  confirmed: "Pagamento confirmado",
  refused: "Pagamento não localizado",
};
const deliveryLabels: Record<string, string> = {
  none: "Sem mensagem",
  queued: "Na fila",
  processing: "Enviando",
  sent: "Entregue",
  failed: "Falha de mensagem",
};

function money(value: number) {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(value / 100);
}

function dateBoundary(value: FormDataEntryValue | null, end: boolean) {
  if (!value) return undefined;
  return `${String(value)}T${end ? "23:59:59.999" : "00:00:00.000"}Z`;
}

function requestPath(filters: Filters, cursor?: string | null) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => { if (value) params.set(key, value); });
  if (cursor) params.set("cursor", cursor);
  params.set("limit", "12");
  return `/api/admin/payment-communications?${params.toString()}`;
}

export default function AdminPaymentsPage() {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [filters, setFilters] = useState<Filters>({});
  const [failed, setFailed] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [busyAction, setBusyAction] = useState("");
  const [message, setMessage] = useState("");
  const [reopenings, setReopenings] = useState<Reopening[]>([]);

  const load = useCallback(async (nextFilters: Filters, cursor?: string | null, append = false) => {
    if (append) setLoadingMore(true);
    try {
      const response = await fetch(requestPath(nextFilters, cursor), { credentials: "same-origin" });
      if (!response.ok) throw new Error();
      const payload = await response.json() as Dashboard;
      setDashboard((current) => append && current ? {
        ...payload,
        groups: [...current.groups, ...payload.groups],
      } : payload);
      setFailed(false);
    } catch {
      setFailed(true);
    } finally {
      setLoadingMore(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    fetch(requestPath({}), { credentials: "same-origin" })
      .then(async (response) => {
        if (!response.ok) throw new Error();
        const payload = await response.json() as Dashboard;
        if (active) {
          setDashboard(payload);
          setFailed(false);
        }
      })
      .catch(() => { if (active) setFailed(true); });
    return () => { active = false; };
  }, []);
  const loadReopenings = useCallback(() => fetch("/api/admin/gallery-reopening-requests", { credentials: "same-origin" }).then(async (response) => { if (!response.ok) throw new Error(); setReopenings((await response.json()).requests ?? []); }).catch(() => setReopenings([])), []);
  useEffect(() => { void loadReopenings(); }, [loadReopenings]);

  async function decide(id: string, decision: "confirmed" | "refused") {
    setBusyAction(`decision:${id}`);
    const response = await fetch(`/api/admin/payment-communications/${id}/decision`, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision }),
    });
    setMessage(response.ok ? "Decisão registrada. A resposta foi encaminhada à caixa de saída." : "Não foi possível registrar a decisão.");
    if (response.ok) await load(filters);
    setBusyAction("");
  }

  async function retry(notificationId: string) {
    setBusyAction(`retry:${notificationId}`);
    const response = await fetch(`/api/admin/payment-notifications/${notificationId}/retry`, {
      method: "POST",
      credentials: "same-origin",
    });
    setMessage(response.ok ? "Notificação reenfileirada." : "O limite de tentativas não permite novo envio.");
    if (response.ok) await load(filters);
    setBusyAction("");
  }
  async function correct(id: string) {
    if (!window.confirm("Corrigir esta confirmação e devolver o pagamento para revisão? Nenhuma mensagem será enviada à cliente.")) return;
    setBusyAction(`correction:${id}`);
    const response = await fetch(`/api/admin/payment-communications/${id}/correction`, { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ idempotency_key: crypto.randomUUID() }) });
    setMessage(response.ok ? "Confirmação corrigida. O pagamento voltou para revisão sem enviar nova mensagem." : "Não foi possível corrigir a confirmação.");
    if (response.ok) await load(filters); setBusyAction("");
  }
  async function decideReopening(item: Reopening, decision: "approved" | "refused") {
    let selection_expires_at: string | null = null;
    if (decision === "approved") { const value = window.prompt("Novo prazo (AAAA-MM-DD):"); if (!value) return; selection_expires_at = `${value}T23:59:59.000Z`; }
    setBusyAction(`reopening:${item.id}`);
    const response = await fetch(`/api/admin/gallery-reopening-requests/${item.id}/decision`, { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ decision, selection_expires_at }) });
    setMessage(response.ok ? (decision === "approved" ? "Galeria reaberta para todos os membros." : "Solicitação recusada; a galeria permanece congelada.") : "Não foi possível registrar a decisão de reabertura.");
    if (response.ok) { await loadReopenings(); await load(filters); } setBusyAction("");
  }
  async function retryReopening(item: Reopening) {
    if (!item.notification.id) return;
    setBusyAction(`reopening-notice:${item.id}`);
    const response = await fetch(`/api/admin/gallery-reopening-notifications/${item.notification.id}/retry`, { method: "POST", credentials: "same-origin" });
    setMessage(response.ok ? "Aviso de reabertura reenfileirado." : "Não foi possível reenfileirar o aviso.");
    if (response.ok) await loadReopenings(); setBusyAction("");
  }

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const nextFilters: Filters = {
      query: String(data.get("query") ?? "").trim() || undefined,
      parent_gallery_id: String(data.get("parent_gallery_id") ?? "") || undefined,
      financial_status: String(data.get("financial_status") ?? "") || undefined,
      delivery_status: String(data.get("delivery_status") ?? "") || undefined,
      created_from: dateBoundary(data.get("created_from"), false),
      created_to: dateBoundary(data.get("created_to"), true),
    };
    setFilters(nextFilters);
    setDashboard(null);
    void load(nextFilters);
  }

  function clearFilters() {
    setFilters({});
    setDashboard(null);
    void load({});
  }

  if (failed && !dashboard) return <SystemState tone="error" title="Pagamentos indisponíveis" detail="Não foi possível carregar os pedidos e as comunicações para revisão." />;
  if (!dashboard) return <SystemState tone="loading" title="Carregando pagamentos" detail="Consultando pedidos, decisões e entregas transacionais." />;

  const hasFilters = Object.values(filters).some(Boolean);
  return <main className="admin-shell payments-dashboard">
    <p className="eyebrow">Operação financeira · decisão manual</p>
    <h1>Vendas e pagamentos</h1>
    <p className="intro">A comunicação da cliente não confirma o PIX. Revise cada pedido e registre uma única decisão; o histórico comercial permanece mesmo quando a galeria é removida.</p>

    <section aria-label="Resumo de pagamentos" className="payment-summary">
      <MetricCard label="Clientes no resultado" value={dashboard.summary.clients} detail={`${dashboard.summary.orders} pedido(s)`} />
      <MetricCard label="Valor dos pedidos" value={money(dashboard.summary.total_cents)} detail="Soma do filtro atual" />
      <MetricCard label="Aguardando revisão" value={dashboard.summary.financial_statuses.reported ?? 0} detail="Pagamentos comunicados" tone="warning" />
      <MetricCard label="Falhas de mensagem" value={dashboard.summary.failed_messages} detail="Entregas que exigem atenção" tone={dashboard.summary.failed_messages ? "danger" : "success"} />
    </section>

    <section className="admin-card"><div className="section-heading"><div><h2>Mensagem global após conferência</h2><p>Qualquer edição afeta todas as clientes. O texto efetivamente usado fica salvo no pedido.</p></div><a className="mk-button mk-button--secondary" href="/admin/settings#payment-messages">Editar em Configurações</a></div><details><summary>Ver prévias</summary><p><strong>Pagamento confirmado:</strong> {dashboard.templates?.confirmed ?? "Olá {{cliente}}, o pagamento do pedido {{pedido}} foi confirmado."}</p><p><strong>Pagamento não localizado:</strong> {dashboard.templates?.refused ?? "Olá {{cliente}}, o pagamento do pedido {{pedido}} ainda não foi localizado."}</p></details></section>

    {reopenings.length ? <section className="admin-card"><div className="section-heading"><div><h2>Solicitações de reabertura</h2><p>A aprovação define um novo prazo para todos os membros daquela galeria privada.</p></div><StatusBadge tone="warning">{reopenings.filter((item) => item.status === "pending").length} pendente(s)</StatusBadge></div><div className="payment-orders">{reopenings.map((item) => <article className="payment-order" key={item.id}><div className="payment-order__heading"><div><StatusBadge tone={item.status === "pending" ? "warning" : item.status === "approved" ? "success" : "danger"}>{item.status === "pending" ? "Aguardando decisão" : item.status === "approved" ? "Reaberta" : "Recusada"}</StatusBadge><h3>{item.gallery_name}</h3><p>Solicitada em {new Date(item.created_at).toLocaleString("pt-BR")} · aviso {deliveryLabels[item.notification.status] ?? item.notification.status}</p></div></div>{item.status === "pending" ? <div className="dashboard-actions"><MarkinaButton disabled={busyAction === `reopening:${item.id}`} onClick={() => void decideReopening(item, "approved")}>Definir novo prazo</MarkinaButton><MarkinaButton variant="secondary" disabled={busyAction === `reopening:${item.id}`} onClick={() => void decideReopening(item, "refused")}>Recusar</MarkinaButton></div> : null}{item.notification.can_retry ? <MarkinaButton variant="secondary" disabled={busyAction === `reopening-notice:${item.id}`} onClick={() => void retryReopening(item)}>Tentar aviso novamente</MarkinaButton> : null}</article>)}</div></section> : null}

    {dashboard.selections_without_order?.length ? <section className="admin-card"><div className="section-heading"><div><h2>Seleções sem pedido</h2><p>Clientes que já escolheram fotos, mas ainda não avançaram para o pedido.</p></div><StatusBadge>{dashboard.selections_without_order.length}</StatusBadge></div><div className="payment-orders">{dashboard.selections_without_order.map((selection) => <article className="payment-order" key={`${selection.gallery.id}:${selection.client.id}`}><div className="payment-order__heading"><div><StatusBadge tone="neutral">Seleção em aberto</StatusBadge><h3>{selection.client.name}</h3><p>{selection.gallery.name} · {selection.parent_gallery.name}</p></div><strong>{selection.selected_count} foto(s)</strong></div><details><summary>Ver seleção por pasta</summary>{selection.folders.map((folder) => <section key={folder.id}><h4>{folder.name}</h4><ul>{folder.items.map((item) => <li key={item.id}>{item.name}</li>)}</ul></section>)}</details></article>)}</div></section> : null}

    <details className="admin-card payment-filters" open={hasFilters || undefined}>
      <summary>Filtros {hasFilters ? "ativos" : ""}</summary>
      <form className="filter-grid" onSubmit={applyFilters}>
        <label>Cliente<input name="query" defaultValue={filters.query ?? ""} placeholder="Nome da cliente" /></label>
        <label>Galeria pública<select name="parent_gallery_id" defaultValue={filters.parent_gallery_id ?? ""}><option value="">Todas</option>{dashboard.facets.parent_galleries.map((gallery) => <option key={gallery.id} value={gallery.id}>{gallery.name} ({gallery.count})</option>)}</select></label>
        <label>Situação financeira<select name="financial_status" defaultValue={filters.financial_status ?? ""}><option value="">Todas</option>{Object.entries(financialPresentation).map(([value, presentation]) => <option key={value} value={value}>{presentation.label}</option>)}</select></label>
        <label>Entrega de mensagem<select name="delivery_status" defaultValue={filters.delivery_status ?? ""}><option value="">Todas</option>{Object.entries(deliveryLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
        <label>De<input type="date" name="created_from" defaultValue={filters.created_from?.slice(0, 10) ?? ""} /></label>
        <label>Até<input type="date" name="created_to" defaultValue={filters.created_to?.slice(0, 10) ?? ""} /></label>
        <div className="payment-filter-actions"><MarkinaButton type="submit">Aplicar filtros</MarkinaButton>{hasFilters ? <MarkinaButton type="button" variant="secondary" onClick={clearFilters}>Limpar filtros</MarkinaButton> : null}</div>
      </form>
    </details>

    {failed ? <p className="form-message form-message--error" role="alert">Não foi possível atualizar. Os dados carregados continuam visíveis.</p> : null}
    {!dashboard.groups.length ? <SystemState title={hasFilters ? "Nenhum pagamento neste filtro" : "Nenhum pedido ainda"} detail={hasFilters ? "Limpe os filtros para voltar a ver todos os pedidos." : "Pedidos e comunicações aparecerão aqui sem comprovantes ou dados bancários."} /> : null}
    {!dashboard.groups.length && hasFilters ? <MarkinaButton variant="secondary" onClick={clearFilters}>Limpar filtros</MarkinaButton> : null}

    <div className="payment-client-groups">
      {dashboard.groups.map((group) => <section className="admin-card payment-client-card" key={group.client.id}>
        <header><div><p className="eyebrow">Cliente</p><h2>{group.client.name}</h2></div><div className="payment-client-total"><strong>{money(group.totals.total_cents)}</strong><span>{group.totals.orders} pedido(s)</span></div></header>
        <div className="payment-orders">
          {group.orders.map((order) => <OrderCard key={order.id} order={order} busyAction={busyAction} onDecide={decide} onCorrect={correct} onRetry={retry} />)}
        </div>
      </section>)}
    </div>

    {dashboard.page.next_cursor ? <div className="payment-pagination"><MarkinaButton variant="secondary" disabled={loadingMore} onClick={() => void load(filters, dashboard.page.next_cursor, true)}>{loadingMore ? "Carregando…" : "Carregar mais clientes"}</MarkinaButton></div> : null}
    {message ? <p className="form-message" role="status">{message}</p> : null}
  </main>;
}

function OrderCard({ order, busyAction, onDecide, onCorrect, onRetry }: { order: Order; busyAction: string; onDecide: (id: string, decision: "confirmed" | "refused") => Promise<void>; onCorrect: (id: string) => Promise<void>; onRetry: (id: string) => Promise<void> }) {
  const presentation = financialPresentation[order.financial_status];
  const communication = order.communication;
  return <article className={`payment-order payment-order--${order.financial_status}`}>
    <div className="payment-order__heading"><div><StatusBadge tone={presentation.tone}>{presentation.label}</StatusBadge><h3>{order.gallery.name}{order.gallery.removed ? " · Galeria removida" : ""}</h3><p>{order.parent_gallery.name} · pedido {order.id.slice(0, 8)}</p></div><strong>{money(order.total_cents)}</strong></div>
    <details>
      <summary>Ver pedido e mensagens</summary>
      <dl className="payment-order__facts"><div><dt>Criado em</dt><dd>{new Date(order.created_at).toLocaleString("pt-BR")}</dd></div><div><dt>Galeria pública</dt><dd>{order.parent_gallery.name}{order.parent_gallery.removed ? " (removida)" : ""}</dd></div>{order.selection_expires_at ? <div><dt>Prazo</dt><dd>{new Date(order.selection_expires_at).toLocaleDateString("pt-BR")}</dd></div> : null}</dl>
      {order.folders?.length ? <div>{order.folders.map((folder) => <section key={folder.id ?? folder.name}><h4>{folder.name}</h4><ul>{folder.items.map((item) => <li key={item.id}>{item.name} · {money(item.unit_price_cents)}</li>)}</ul></section>)}</div> : null}
      {!communication ? <p>A cliente ainda não comunicou o pagamento.</p> : <>
        <p><strong>{decisionLabel[communication.status]}</strong> · comunicado em {new Date(communication.created_at).toLocaleString("pt-BR")}</p>
        {communication.can_decide ? <div className="dashboard-actions"><MarkinaButton disabled={busyAction === `decision:${communication.id}`} onClick={() => void onDecide(communication.id, "confirmed")}>Confirmar pagamento</MarkinaButton><MarkinaButton variant="secondary" disabled={busyAction === `decision:${communication.id}`} onClick={() => void onDecide(communication.id, "refused")}>Pagamento não localizado</MarkinaButton></div> : null}
        {communication.can_correct ? <MarkinaButton variant="secondary" disabled={busyAction === `correction:${communication.id}`} onClick={() => void onCorrect(communication.id)}>Corrigir confirmação</MarkinaButton> : null}
        {order.payment_message_snapshot ? <details><summary>Mensagem enviada nesta confirmação</summary><p>{order.payment_message_snapshot}</p></details> : null}
        <DeliveryState label="Aviso ao fotógrafo" delivery={communication.photographer_notification} busyAction={busyAction} onRetry={onRetry} />
        {communication.status !== "pending_review" ? <DeliveryState label="Resposta à cliente" delivery={communication.client_notification} busyAction={busyAction} onRetry={onRetry} /> : null}
      </>}
    </details>
  </article>;
}

function DeliveryState({ label, delivery, busyAction, onRetry }: { label: string; delivery: Delivery | null; busyAction: string; onRetry: (id: string) => Promise<void> }) {
  if (!delivery) return <p>{label}: não enfileirado — confira a configuração do ambiente.</p>;
  const status = deliveryLabels[delivery.status] ?? delivery.status;
  return <div className={`upload-status${delivery.status === "failed" ? " upload-status--error" : delivery.status === "sent" ? " upload-status--success" : ""}`}>
    <strong>{label}: {status.toLocaleLowerCase("pt-BR")}</strong>
    <span>{delivery.attempts} tentativa(s){delivery.last_error ? ` · ${delivery.last_error}` : ""}</span>
    {delivery.can_retry ? <button className="link-button" type="button" disabled={busyAction === `retry:${delivery.id}`} onClick={() => void onRetry(delivery.id)}>Tentar enviar novamente</button> : null}
  </div>;
}
