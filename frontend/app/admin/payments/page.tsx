"use client";

import { type FormEvent, type KeyboardEvent, useCallback, useEffect, useState } from "react";

import { MarkinaButton, MetricCard, StatusBadge, SystemState } from "../../ui-kit";
import { PaymentActions } from "./payment-actions";

import RemovedHistory from "./removed-history";
import { OrderDeliveryForm, type OrderDelivery } from "./order-delivery";

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

type FinancialStatus = "awaiting_payment" | "reported" | "confirmed" | "not_found" | "overdue" | "verifying" | "exception" | "hold";
type Order = {
  assets_removed?: boolean;
  id: string;
  parent_gallery: { id: string; name: string; removed: boolean };
  gallery: { id: string; name: string; removed: boolean };
  total_cents: number;
  financial_status: FinancialStatus;
  payment_method?: "credit_card" | "pix";
  provider_payment_state?: string;
  provider_payment_id?: string;
  created_at: string;
  selection_expires_at: string | null;
  communications: Communication[];
  communication: Communication | null;
  delivery_statuses: string[];
  folders: Array<{ id: string | null; name: string; items: Array<{ id: string; photo_id: string; name: string; unit_price_cents: number }> }>;
  delivery?: OrderDelivery;
};
type ClientGroup = {
  client: { id: string; name: string };
  totals: {
    orders: number;
    total_cents: number;
    reported_orders: number;
    reported_cents: number;
    confirmed_orders: number;
    confirmed_cents: number;
  };
  orders: Order[];
};
type Dashboard = {
  selections_without_order?: Array<{ client: { id: string; name: string }; gallery: { id: string; name: string }; parent_gallery: { id: string; name: string }; selected_count: number; total_cents: number | null; pricing_available: boolean; created_at: string; folders: Array<{ id: string; name: string; items: Array<{ id: string; name: string }> }> }>;
  summary: {
    clients: number;
    orders: number;
    total_cents: number;
    selected_carts: number;
    selected_cents: number;
    selected_pricing_unavailable: number;
    reported_orders: number;
    reported_cents: number;
    confirmed_orders: number;
    confirmed_cents: number;
    financial_statuses: Record<string, number>;
    failed_messages: number;
  };
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
  client_id?: string;
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
  verifying: { label: "Verificando cartão", tone: "warning" },
  exception: { label: "Pagamento em análise", tone: "danger" },
  hold: { label: "Pagamento em revisão", tone: "dark" },
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
  const [view, setView] = useState("payments");
  return <main className="admin-shell payments-dashboard">
    <p className="eyebrow">Operação financeira · decisão manual</p>
    <h1>Vendas e pagamentos</h1>
    <label className="admin-card">Exibir<select value={view} onChange={(event) => setView(event.target.value)}>
      <option value="payments">Pedidos e pagamentos</option>
      <option value="removed">Histórico de acervo excluído</option>
    </select></label>
    {view === "removed" ? <RemovedHistory /> : <PaymentsDashboard />}
  </main>;
}

function PaymentsDashboard() {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [filters, setFilters] = useState<Filters>({});
  const [clientQuery, setClientQuery] = useState("");
  const [selectedClientId, setSelectedClientId] = useState("");
  const [advancedFiltersOpen, setAdvancedFiltersOpen] = useState(false);
  const [failed, setFailed] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [adminHeaderHeight, setAdminHeaderHeight] = useState(68);
  const [busyAction, setBusyAction] = useState("");
  const [message, setMessage] = useState("");
  const [reopenings, setReopenings] = useState<Reopening[]>([]);

  useEffect(() => {
    const header = document.querySelector<HTMLElement>(".admin-topbar");
    if (!header) return;
    const updateHeight = () => setAdminHeaderHeight(Math.ceil(header.getBoundingClientRect().height));
    const frame = window.requestAnimationFrame(updateHeight);
    const observer = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(updateHeight);
    observer?.observe(header);
    window.addEventListener("resize", updateHeight);
    return () => {
      observer?.disconnect();
      window.cancelAnimationFrame(frame);
      window.removeEventListener("resize", updateHeight);
    };
  }, []);

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
  useEffect(() => {
    const refresh = () => { void load(filters); };
    window.addEventListener("focus", refresh);
    return () => window.removeEventListener("focus", refresh);
  }, [filters, load]);

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
      query: clientQuery.trim() || undefined,
      client_id: selectedClientId || undefined,
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
    setClientQuery("");
    setSelectedClientId("");
    setDashboard(null);
    void load({});
  }

  if (failed && !dashboard) return <SystemState tone="error" title="Pagamentos indisponíveis" detail="Não foi possível carregar os pedidos e as comunicações para revisão." />;
  if (!dashboard) return <SystemState tone="loading" title="Carregando pagamentos" detail="Consultando pedidos, decisões e entregas transacionais." />;

  const hasFilters = Object.values(filters).some(Boolean);
  return <section>
    <p className="intro">A comunicação da cliente não confirma o PIX. Revise cada pedido e registre uma única decisão; o histórico comercial permanece mesmo quando a galeria é removida.</p>

    <div className="payment-dashboard-body">
      <div className="payment-filter-sticky" style={{ top: `${adminHeaderHeight}px` }}>
        <ClientAutocomplete
          value={clientQuery}
          selectedClientId={selectedClientId}
          onChange={(value) => { setClientQuery(value); setSelectedClientId(""); }}
          onSelect={(suggestion) => { setClientQuery(suggestion.name); setSelectedClientId(suggestion.id); }}
        />
        <div className="payment-filter-bar__actions">
          <MarkinaButton type="submit" form="payment-dashboard-filter">Aplicar</MarkinaButton>
        </div>
      </div>
      <form id="payment-dashboard-filter" className="payment-filter-form" onSubmit={applyFilters}>
      <details className="admin-card payment-filters" open={advancedFiltersOpen || undefined} onToggle={(event) => setAdvancedFiltersOpen(event.currentTarget.open)}>
        <summary>Mais filtros {hasFilters ? "· filtros ativos" : ""}</summary>
        <div>
        <div className="filter-grid">
          <label>Galeria pública<select name="parent_gallery_id" defaultValue={filters.parent_gallery_id ?? ""}><option value="">Todas</option>{dashboard.facets.parent_galleries.map((gallery) => <option key={gallery.id} value={gallery.id}>{gallery.name} ({gallery.count})</option>)}</select></label>
          <label>Situação financeira<select name="financial_status" defaultValue={filters.financial_status ?? ""}><option value="">Todas</option>{Object.entries(financialPresentation).map(([value, presentation]) => <option key={value} value={value}>{presentation.label}</option>)}</select></label>
          <label>Entrega de mensagem<select name="delivery_status" defaultValue={filters.delivery_status ?? ""}><option value="">Todas</option>{Object.entries(deliveryLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
          <label>De<input type="date" name="created_from" defaultValue={filters.created_from?.slice(0, 10) ?? ""} /></label>
          <label>Até<input type="date" name="created_to" defaultValue={filters.created_to?.slice(0, 10) ?? ""} /></label>
          <div className="payment-filter-actions"><MarkinaButton type="submit">Aplicar filtros</MarkinaButton>{hasFilters ? <MarkinaButton type="button" variant="secondary" onClick={clearFilters}>Limpar filtros</MarkinaButton> : null}</div>
        </div>
        </div>
      </details>
      </form>

    <section aria-label="Resumo de pagamentos" className="payment-summary">
      <MetricCard label="Clientes no resultado" value={dashboard.summary.clients} detail="Com atividade no filtro atual" />
      <MetricCard label="Valor das fotos selecionadas" value={money(dashboard.summary.selected_cents)} detail={`${dashboard.summary.selected_carts} carrinho(s) sem pagamento comunicado${dashboard.summary.selected_pricing_unavailable ? ` · ${dashboard.summary.selected_pricing_unavailable} sem preço disponível` : ""}`} />
      <MetricCard label="Valor dos pedidos" value={money(dashboard.summary.reported_cents)} detail={`${dashboard.summary.reported_orders} pagamento(s) comunicado(s)`} tone="warning" />
      <MetricCard label="Receita confirmada" value={money(dashboard.summary.confirmed_cents)} detail={`${dashboard.summary.confirmed_orders} depósito(s) confirmado(s)`} tone="success" />
      <MetricCard label="Falhas de mensagem" value={dashboard.summary.failed_messages} detail="Entregas que exigem atenção" tone={dashboard.summary.failed_messages ? "danger" : "success"} />
    </section>

    {reopenings.length ? <section className="admin-card"><div className="section-heading"><div><h2>Solicitações de reabertura</h2><p>A aprovação define um novo prazo para todos os membros daquela galeria privada.</p></div><StatusBadge tone="warning">{reopenings.filter((item) => item.status === "pending").length} pendente(s)</StatusBadge></div><div className="payment-orders">{reopenings.map((item) => <article className="payment-order" key={item.id}><div className="payment-order__heading"><div><StatusBadge tone={item.status === "pending" ? "warning" : item.status === "approved" ? "success" : "danger"}>{item.status === "pending" ? "Aguardando decisão" : item.status === "approved" ? "Reaberta" : "Recusada"}</StatusBadge><h3>{item.gallery_name}</h3><p>Solicitada em {new Date(item.created_at).toLocaleString("pt-BR")} · aviso {deliveryLabels[item.notification.status] ?? item.notification.status}</p></div></div>{item.status === "pending" ? <div className="dashboard-actions"><MarkinaButton disabled={busyAction === `reopening:${item.id}`} onClick={() => void decideReopening(item, "approved")}>Definir novo prazo</MarkinaButton><MarkinaButton variant="secondary" disabled={busyAction === `reopening:${item.id}`} onClick={() => void decideReopening(item, "refused")}>Recusar</MarkinaButton></div> : null}{item.notification.can_retry ? <MarkinaButton variant="secondary" disabled={busyAction === `reopening-notice:${item.id}`} onClick={() => void retryReopening(item)}>Tentar aviso novamente</MarkinaButton> : null}</article>)}</div></section> : null}

    {dashboard.selections_without_order?.length ? <section className="admin-card"><div className="section-heading"><div><h2>Seleções em aberto</h2><p>Fotos que continuam no carrinho e ainda não tiveram pagamento comunicado.</p></div><StatusBadge>{dashboard.selections_without_order.length}</StatusBadge></div><div className="payment-orders">{dashboard.selections_without_order.map((selection) => <article className="payment-order" key={`${selection.gallery.id}:${selection.client.id}`}><div className="payment-order__heading"><div><StatusBadge tone="neutral">No carrinho</StatusBadge><h3>{selection.client.name}</h3><p>{selection.gallery.name} · {selection.parent_gallery.name}</p></div><div className="payment-client-total"><strong>{selection.total_cents === null ? "Preço indisponível" : money(selection.total_cents)}</strong><span>{selection.selected_count} foto(s)</span></div></div><details><summary>Ver seleção por pasta</summary>{selection.folders.map((folder) => <section key={folder.id}><h4>{folder.name}</h4><ul>{folder.items.map((item) => <li key={item.id}>{item.name}</li>)}</ul></section>)}</details></article>)}</div></section> : null}

    {failed ? <p className="form-message form-message--error" role="alert">Não foi possível atualizar. Os dados carregados continuam visíveis.</p> : null}
    {!dashboard.groups.length ? <SystemState title={hasFilters ? "Nenhum pagamento neste filtro" : "Nenhum pedido ainda"} detail={hasFilters ? "Limpe os filtros para voltar a ver todos os pedidos." : "Pedidos e comunicações aparecerão aqui sem comprovantes ou dados bancários."} /> : null}
    {!dashboard.groups.length && hasFilters ? <MarkinaButton variant="secondary" onClick={clearFilters}>Limpar filtros</MarkinaButton> : null}

    <div className="payment-client-groups">
      {dashboard.groups.map((group) => <section className="admin-card payment-client-card" key={group.client.id}>
        <header><div><p className="eyebrow">Cliente</p><h2>{group.client.name}</h2></div><div className="payment-client-total"><span>Pedidos comunicados · {group.totals.reported_orders}</span><strong>{money(group.totals.reported_cents)}</strong><span>Receita confirmada · {money(group.totals.confirmed_cents)}</span></div></header>
        <div className="payment-orders">
          {group.orders.map((order) => <OrderCard key={order.id} order={order} clientId={group.client.id} onRefresh={() => load(filters)} />)}
        </div>
      </section>)}
    </div>

    {dashboard.page.next_cursor ? <div className="payment-pagination"><MarkinaButton variant="secondary" disabled={loadingMore} onClick={() => void load(filters, dashboard.page.next_cursor, true)}>{loadingMore ? "Carregando…" : "Carregar mais clientes"}</MarkinaButton></div> : null}
    {message ? <p className="form-message" role="status">{message}</p> : null}
    </div>
  </section>;
}

type ClientSuggestion = { id: string; name: string };

function ClientAutocomplete({
  value,
  selectedClientId,
  onChange,
  onSelect,
}: {
  value: string;
  selectedClientId: string;
  onChange: (value: string) => void;
  onSelect: (suggestion: ClientSuggestion) => void;
}) {
  const [suggestions, setSuggestions] = useState<ClientSuggestion[]>([]);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [status, setStatus] = useState("");
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const query = value.trim();
    if (query.length < 2 || selectedClientId) return;
    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      setStatus("Buscando clientes…");
      try {
        const parameters = new URLSearchParams({ query, limit: "8" });
        const response = await fetch(`/api/admin/clients?${parameters.toString()}`, {
          credentials: "same-origin",
          signal: controller.signal,
        });
        if (!response.ok) throw new Error("Não foi possível carregar sugestões.");
        const payload = await response.json() as { clients?: ClientSuggestion[] };
        if (!controller.signal.aborted) {
          const matches = (payload.clients ?? []).map(({ id, name }) => ({ id, name }));
          setSuggestions(matches);
          setStatus(matches.length ? "" : "Nenhuma cliente encontrada.");
          setOpen(true);
          setActiveIndex(-1);
        }
      } catch {
        if (!controller.signal.aborted) {
          setSuggestions([]);
          setStatus("Não foi possível carregar sugestões de clientes.");
          setOpen(true);
        }
      }
    }, 180);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [value, selectedClientId]);

  function choose(suggestion: ClientSuggestion) {
    onSelect(suggestion);
    setSuggestions([]);
    setStatus("");
    setActiveIndex(-1);
    setOpen(false);
  }

  function handleChange(value: string) {
    setSuggestions([]);
    setStatus("");
    setActiveIndex(-1);
    setOpen(false);
    onChange(value);
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "ArrowDown" && suggestions.length) {
      event.preventDefault();
      setOpen(true);
      setActiveIndex((current) => (current + 1) % suggestions.length);
    } else if (event.key === "ArrowUp" && suggestions.length) {
      event.preventDefault();
      setOpen(true);
      setActiveIndex((current) => (current <= 0 ? suggestions.length - 1 : current - 1));
    } else if (event.key === "Enter" && open && activeIndex >= 0) {
      event.preventDefault();
      choose(suggestions[activeIndex]);
    } else if (event.key === "Escape") {
      setOpen(false);
      setActiveIndex(-1);
    }
  }

  return <div className="payment-client-autocomplete">
    <label htmlFor="payment-client-query">Cliente / telefone</label>
    <input
      id="payment-client-query"
      name="query"
      form="payment-dashboard-filter"
      type="search"
      autoComplete="off"
      placeholder="Nome ou telefone"
      value={value}
      role="combobox"
      aria-autocomplete="list"
      aria-expanded={open}
      aria-controls="payment-client-suggestions"
      aria-activedescendant={activeIndex >= 0 ? `payment-client-suggestion-${activeIndex}` : undefined}
      onChange={(event) => handleChange(event.target.value)}
      onKeyDown={handleKeyDown}
    />
    {open ? <ul id="payment-client-suggestions" className="payment-client-suggestions" role="listbox" aria-label="Clientes correspondentes">
      {suggestions.map((suggestion, index) => <li key={suggestion.id} role="presentation">
        <button
          id={`payment-client-suggestion-${index}`}
          type="button"
          role="option"
          aria-selected={index === activeIndex}
          onMouseDown={(event) => event.preventDefault()}
          onClick={() => choose(suggestion)}
        >{suggestion.name}</button>
      </li>)}
      {status ? <li className="payment-client-suggestion-status" role="option" aria-selected="false">{status}</li> : null}
    </ul> : null}
    <span className="sr-only" aria-live="polite">{status || (selectedClientId ? "Cliente selecionada; filtro exato ativo." : "")}</span>
  </div>;
}

function OrderCard({ order, clientId, onRefresh }: { order: Order; clientId: string; onRefresh: () => Promise<void> }) {
  const presentation = financialPresentation[order.financial_status];
  const communication = order.communication;
  const canDownloadPurchasedPhotos = order.financial_status === "confirmed" && !order.assets_removed && !order.gallery.removed;
  const downloadPurchasedPhotos = canDownloadPurchasedPhotos ? <a className="mk-button mk-button--secondary" href={`/api/admin/parent-galleries/${encodeURIComponent(order.parent_gallery.id)}/clients/${encodeURIComponent(clientId)}/selection/export.html`}>Baixar fotos compradas</a> : null;
  return <article className={`payment-order payment-order--${order.financial_status}`}>
    {order.assets_removed ? <p>Acervo removido ou revisão indisponível. Nomes, valores e estado financeiro preservados.</p> : null}
    <div className="payment-order__heading"><div><StatusBadge tone={presentation.tone}>{presentation.label}</StatusBadge><h3>{order.gallery.name}{order.gallery.removed ? " · Galeria removida" : ""}</h3><p>{order.parent_gallery.name} · pedido {order.id.slice(0, 8)}{order.payment_method === "credit_card" ? " · cartão de crédito" : ""}</p></div><strong>{money(order.total_cents)}</strong></div>
    <details>
      <summary>Ver pedido e entrega</summary>
      <dl className="payment-order__facts"><div><dt>Criado em</dt><dd>{new Date(order.created_at).toLocaleString("pt-BR")}</dd></div><div><dt>Galeria pública</dt><dd>{order.parent_gallery.name}{order.parent_gallery.removed ? " (removida)" : ""}</dd></div>{order.selection_expires_at ? <div><dt>Prazo</dt><dd>{new Date(order.selection_expires_at).toLocaleDateString("pt-BR")}</dd></div> : null}</dl>
      {order.folders?.length ? <div>{order.folders.map((folder) => <section key={folder.id ?? folder.name}><h4>{folder.name}</h4><ul>{folder.items.map((item) => <li key={item.id}>{item.name} · {money(item.unit_price_cents)}</li>)}</ul></section>)}</div> : null}
      {order.payment_method === "credit_card" ? <><p>Estado da compra de cartão: {order.provider_payment_state ?? "indisponível"}{order.provider_payment_id ? ` · compra ${order.provider_payment_id.slice(0, 8)}` : ""}. A confirmação não usa a decisão manual do PIX.</p>{downloadPurchasedPhotos ? <div className="dashboard-actions">{downloadPurchasedPhotos}</div> : null}</> : !communication ? <p>A cliente ainda não comunicou o pagamento.</p> : <>
        <p><strong>{decisionLabel[communication.status]}</strong> · comunicado em {new Date(communication.created_at).toLocaleString("pt-BR")}</p>
        <div className="dashboard-actions">
          <PaymentActions order={{ ...communication, quantity: order.folders.reduce((total, folder) => total + folder.items.length, 0) }} clientName={communication.client_name} onRefresh={onRefresh} />
          {downloadPurchasedPhotos}
        </div>
      </>}
      <OrderDeliveryForm orderId={order.id} delivery={order.delivery ?? { album_url: null, version: 0, can_send: false, can_resend: false }} onRefresh={onRefresh} />
    </details>
  </article>;
}
