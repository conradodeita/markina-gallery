"use client";

import { type FormEvent, type KeyboardEvent, useCallback, useEffect, useRef, useState } from "react";

import { MarkinaButton, MetricCard, StatusBadge, SystemState } from "../../ui-kit";
import { PaymentActions } from "./payment-actions";
import { CartRecoveryActions, type CartRecoveryStatus } from "./cart-recovery";

import RemovedHistory from "./removed-history";
import { OrderDeliveryForm, type OrderDelivery } from "./order-delivery";
import styles from "./payments.module.css";
import { OrderPhotos, type OrderFolder } from "./order-photos";

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
  payment_group?: { id: string; total_cents: number; galleries: Array<{ order_id: string; name: string; total_cents: number }> } | null;
  corrections: Array<{ id: string; created_at: string }>;
  photographer_notification: Delivery | null;
  client_notification: Delivery | null;
};

type FinancialStatus = "reported" | "confirmed" | "confirmed_undelivered" | "awaiting_payment" | "not_found" | "overdue" | "verifying" | "exception" | "hold";
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
  provider_cart_recovery?: CartRecoveryStatus;
  created_at: string;
  selection_expires_at: string | null;
  communications: Communication[];
  communication: Communication | null;
  delivery_statuses: string[];
  folders: OrderFolder[];
  delivery?: OrderDelivery;
};
type ClientGroup = {
  client: { id: string; name: string };
  financial_status: FinancialStatus;
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
  templates: Record<"confirmed" | "refused", string>;
  templates_are_global: boolean;
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
  created_from?: string;
  created_to?: string;
};
const defaultFilters: Filters = { financial_status: "priority" };

const financialPresentation: Record<FinancialStatus, { label: string; tone: "neutral" | "success" | "warning" | "danger" | "dark" }> = {
  reported: { label: "Pagamento comunicado", tone: "warning" },
  confirmed: { label: "Pagamento confirmado", tone: "success" },
  confirmed_undelivered: { label: "Pagamento confirmado - fotos não entregue", tone: "danger" },
  awaiting_payment: { label: "Aguardando pagamento", tone: "neutral" },
  not_found: { label: "Pagamento não localizado", tone: "danger" },
  overdue: { label: "Prazo expirado", tone: "dark" },
  verifying: { label: "Verificando cartão", tone: "warning" },
  exception: { label: "Pagamento em análise", tone: "danger" },
  hold: { label: "Pagamento em revisão", tone: "dark" },
};
const financialColor: Record<FinancialStatus, string> = {
  reported: "var(--payment-status-reported)",
  confirmed: "var(--payment-status-confirmed)",
  confirmed_undelivered: "var(--payment-status-confirmed-undelivered)",
  awaiting_payment: "var(--payment-status-awaiting)",
  not_found: "var(--payment-status-not-found)",
  overdue: "var(--payment-status-overdue)",
  verifying: "var(--payment-status-verifying)",
  exception: "var(--payment-status-exception)",
  hold: "var(--payment-status-hold)",
};
function groupPresentation(group: ClientGroup) {
  return group.orders.length > 0 && group.orders.every((order) => order.provider_payment_state === "exception"
    && Boolean(order.provider_cart_recovery?.reopened_at))
    ? { label: "Carrinho reaberto", tone: "neutral" as const, className: undefined }
    : { ...financialPresentation[group.financial_status], className: `payment-status-badge--${group.financial_status}` };
}
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
  return <main className={`admin-shell payments-dashboard ${styles.page}`}>
    <header className={styles.pageHeading}><div><p className="eyebrow">Operação financeira · decisão manual</p>
    <h1>Vendas e pagamentos</h1></div>
    <label className={styles.mode}>Exibir<select value={view} onChange={(event) => setView(event.target.value)}>
      <option value="payments">Pedidos e pagamentos</option>
      <option value="removed">Histórico de acervo excluído</option>
    </select></label></header>
    {view === "removed" ? <RemovedHistory /> : <PaymentsDashboard />}
  </main>;
}

function PaymentsDashboard() {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [filters, setFilters] = useState<Filters>({ ...defaultFilters });
  const [draftFilters, setDraftFilters] = useState<Filters>({ ...defaultFilters });
  const [clientQuery, setClientQuery] = useState("");
  const [selectedClientId, setSelectedClientId] = useState("");
  const [advancedFiltersOpen, setAdvancedFiltersOpen] = useState(false);
  const [failed, setFailed] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [adminHeaderHeight, setAdminHeaderHeight] = useState(68);
  const [busyAction, setBusyAction] = useState("");
  const [message, setMessage] = useState("");
  const [reopenings, setReopenings] = useState<Reopening[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [exportMessage, setExportMessage] = useState("");
  const loadRequest = useRef<AbortController | null>(null);
  const exportRequest = useRef<AbortController | null>(null);
  const loadedPages = useRef(1);

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

  const load = useCallback(async (nextFilters: Filters, cursor?: string | null, append = false, pages = 1) => {
    loadRequest.current?.abort();
    const controller = new AbortController();
    loadRequest.current = controller;
    setFailed(false);
    setRefreshing(!append);
    if (append) setLoadingMore(true);
    try {
      const response = await fetch(requestPath(nextFilters, cursor), { credentials: "same-origin", signal: controller.signal });
      if (!response.ok) throw new Error();
      let payload = await response.json() as Dashboard;
      let fetchedPages = 1;
      while (fetchedPages < pages && payload.page.next_cursor && !controller.signal.aborted) {
        const next = await fetch(requestPath(nextFilters, payload.page.next_cursor), { credentials: "same-origin", signal: controller.signal });
        if (!next.ok) throw new Error();
        const page = await next.json() as Dashboard;
        payload = { ...payload, groups: [...payload.groups, ...page.groups], page: page.page };
        fetchedPages++;
      }
      if (controller.signal.aborted) return;
      loadedPages.current = append ? loadedPages.current + fetchedPages : fetchedPages;
      setDashboard((current) => append && current ? {
        ...payload,
        groups: [...current.groups, ...payload.groups],
      } : payload);
      setFailed(false);
    } catch {
      if (!controller.signal.aborted) setFailed(true);
    } finally {
      if (!controller.signal.aborted) { setLoadingMore(false); setRefreshing(false); }
    }
  }, []);

  useEffect(() => {
    let active = true;
    queueMicrotask(() => { if (active) void load(defaultFilters); });
    return () => { active = false; loadRequest.current?.abort(); exportRequest.current?.abort(); };
  }, [load]);
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
      created_from: dateBoundary(data.get("created_from"), false),
      created_to: dateBoundary(data.get("created_to"), true),
    };
    setFilters(nextFilters);
    setDraftFilters(nextFilters);
    void load(nextFilters);
  }

  function clearFilters() {
    setFilters({ ...defaultFilters });
    setDraftFilters({ ...defaultFilters });
    setClientQuery("");
    setSelectedClientId("");
    void load(defaultFilters);
  }

  function selectClient(suggestion: ClientSuggestion) {
    setClientQuery(suggestion.name); setSelectedClientId(suggestion.id);
    const next = { ...filters, query: suggestion.name, client_id: suggestion.id };
    setFilters(next); setDraftFilters(next);
    void load(next);
  }

  async function exportCsv() {
    if (exportRequest.current) return;
    const controller = new AbortController(); exportRequest.current = controller;
    setExporting(true); setExportMessage("");
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => { if (value) params.set(key, value); });
    try {
      const response = await fetch(`/api/admin/payment-communications/export.csv?${params}`, { credentials: "same-origin", signal: controller.signal });
      if (response.status === 204) { setExportMessage("Nenhum pedido nos filtros aplicados para exportar."); return; }
      if (!response.ok) throw new Error();
      const blob = await response.blob();
      if (controller.signal.aborted) return;
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url; link.download = "pick-your-pic-vendas-pagamentos.csv";
      document.body.append(link); link.click(); link.remove(); URL.revokeObjectURL(url);
      setExportMessage("CSV exportado com todos os pedidos dos filtros aplicados.");
    } catch { if (!controller.signal.aborted) setExportMessage("Não foi possível exportar o CSV. Tente novamente."); }
    finally { exportRequest.current = null; if (!controller.signal.aborted) setExporting(false); }
  }

  if (failed && !dashboard) return <SystemState tone="error" title="Pagamentos indisponíveis" detail="Não foi possível carregar os pedidos e as comunicações para revisão." />;
  if (!dashboard) return <SystemState tone="loading" title="Carregando pagamentos" detail="Consultando pedidos, decisões e entregas transacionais." />;

  const hasFilters = filters.financial_status !== "priority" || Object.entries(filters).some(([key, value]) => key !== "financial_status" && Boolean(value));
  return <section>
    <p className="intro">A comunicação da cliente não confirma o PIX. Revise cada pedido e registre uma única decisão; o histórico comercial permanece mesmo quando a galeria é removida.</p>

    <div className="payment-dashboard-body">
      <div className="payment-filter-sticky" style={{ top: `${adminHeaderHeight}px` }}>
        <ClientAutocomplete
          value={clientQuery}
          selectedClientId={selectedClientId}
          onChange={(value) => { setClientQuery(value); setSelectedClientId(""); }}
          onSelect={selectClient}
        />
        <div className="payment-filter-bar__actions">
          <MarkinaButton type="submit" form="payment-dashboard-filter">Aplicar</MarkinaButton>
          <MarkinaButton variant="secondary" disabled={exporting} onClick={() => void exportCsv()}>{exporting ? "Exportando…" : "Exportar CSV"}</MarkinaButton>
        </div>
      </div>
      <form id="payment-dashboard-filter" className="payment-filter-form" onSubmit={applyFilters}>
      <details className="admin-card payment-filters" open={advancedFiltersOpen || undefined} onToggle={(event) => setAdvancedFiltersOpen(event.currentTarget.open)}>
        <summary>Mais filtros {hasFilters ? "· filtros ativos" : ""}</summary>
        <div>
        <div className="filter-grid">
          <label>Galeria pública<select name="parent_gallery_id" value={draftFilters.parent_gallery_id ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, parent_gallery_id: event.target.value })}><option value="">Todas</option>{dashboard.facets.parent_galleries.map((gallery) => <option key={gallery.id} value={gallery.id}>{gallery.name} ({gallery.count})</option>)}</select></label>
          <label>Situação financeira<select name="financial_status" value={draftFilters.financial_status ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, financial_status: event.target.value })}><option value="priority">Pendências prioritárias</option><option value="">Todos</option>{Object.entries(financialPresentation).map(([value, presentation]) => <option key={value} value={value} style={{ color: financialColor[value as FinancialStatus] }}>{presentation.label}</option>)}</select></label>
          <label>De<input type="date" name="created_from" value={draftFilters.created_from?.slice(0, 10) ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, created_from: event.target.value })} /></label>
          <label>Até<input type="date" name="created_to" value={draftFilters.created_to?.slice(0, 10) ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, created_to: event.target.value })} /></label>
          <div className="payment-filter-actions"><MarkinaButton type="submit">Aplicar filtros</MarkinaButton>{hasFilters ? <MarkinaButton type="button" variant="secondary" onClick={clearFilters}>Limpar filtros</MarkinaButton> : null}</div>
        </div>
        </div>
      </details>
      </form>
      {refreshing ? <p role="status">Atualizando resultados…</p> : null}
      {exportMessage ? <p className="form-message" role="status">{exportMessage}</p> : null}

    <section aria-label="Resumo de pagamentos" className="payment-summary">
      <MetricCard label="Clientes no resultado" value={dashboard.summary.clients} detail="Com atividade no filtro atual" />
      <MetricCard label="Valor das fotos selecionadas" value={money(dashboard.summary.selected_cents)} detail={`${dashboard.summary.selected_carts} carrinho(s) sem pagamento comunicado${dashboard.summary.selected_pricing_unavailable ? ` · ${dashboard.summary.selected_pricing_unavailable} sem preço disponível` : ""}`} />
      <MetricCard label="Valor dos pedidos" value={money(dashboard.summary.reported_cents)} detail={`${dashboard.summary.reported_orders} pagamento(s) comunicado(s)`} tone="warning" />
      <MetricCard label="Receita confirmada" value={money(dashboard.summary.confirmed_cents)} detail={`${dashboard.summary.confirmed_orders} depósito(s) confirmado(s)`} tone="success" />
    </section>


    {reopenings.length ? <section className="admin-card"><div className="section-heading"><div><h2>Solicitações de reabertura</h2><p>A aprovação define um novo prazo para todos os membros daquela galeria privada.</p></div><StatusBadge tone="warning">{reopenings.filter((item) => item.status === "pending").length} pendente(s)</StatusBadge></div><div className="payment-orders">{reopenings.map((item) => <article className="payment-order" key={item.id}><div className="payment-order__heading"><div><StatusBadge tone={item.status === "pending" ? "warning" : item.status === "approved" ? "success" : "danger"}>{item.status === "pending" ? "Aguardando decisão" : item.status === "approved" ? "Reaberta" : "Recusada"}</StatusBadge><h3>{item.gallery_name}</h3><p>Solicitada em {new Date(item.created_at).toLocaleString("pt-BR")} · aviso {deliveryLabels[item.notification.status] ?? item.notification.status}</p></div></div>{item.status === "pending" ? <div className="dashboard-actions"><MarkinaButton disabled={busyAction === `reopening:${item.id}`} onClick={() => void decideReopening(item, "approved")}>Definir novo prazo</MarkinaButton><MarkinaButton variant="secondary" disabled={busyAction === `reopening:${item.id}`} onClick={() => void decideReopening(item, "refused")}>Recusar</MarkinaButton></div> : null}{item.notification.can_retry ? <MarkinaButton variant="secondary" disabled={busyAction === `reopening-notice:${item.id}`} onClick={() => void retryReopening(item)}>Tentar aviso novamente</MarkinaButton> : null}</article>)}</div></section> : null}

    {failed ? <p className="form-message form-message--error" role="alert">Não foi possível atualizar. Os dados carregados continuam visíveis.</p> : null}
    {!dashboard.groups.length ? <SystemState title={filters.financial_status === "priority" && !hasFilters ? "Nenhuma pendência prioritária" : hasFilters ? "Nenhum pagamento neste filtro" : "Nenhum pedido ainda"} detail="Ajuste os filtros ou selecione Todos para consultar outras situações." /> : null}
    {!dashboard.groups.length && hasFilters ? <MarkinaButton variant="secondary" onClick={clearFilters}>Limpar filtros</MarkinaButton> : null}

    <div className="payment-client-groups">
      {dashboard.groups.map((group) => <section className={`admin-card payment-client-card payment-client-card--${group.financial_status}`} key={group.client.id}>
        <header><div><p className="eyebrow">Cliente · {group.totals.orders} pedido(s)</p>
          <StatusBadge tone={groupPresentation(group).tone} className={groupPresentation(group).className}>{groupPresentation(group).label}</StatusBadge>
          <h2>{group.client.name}</h2></div><div className="payment-client-total"><span>Pedidos comunicados · {group.totals.reported_orders}</span><strong>{money(group.totals.reported_cents)}</strong><span>Receita confirmada · {money(group.totals.confirmed_cents)}</span></div></header>
        <div className="payment-orders">
          {group.orders.map((order, index) => <OrderCard key={order.id} order={order} clientId={group.client.id} clientName={group.client.name}
            showCartRecovery={!group.orders.slice(0, index).some((previous) => previous.provider_payment_id === order.provider_payment_id)}
            onCartRecoveryRefresh={() => load(filters, undefined, false, loadedPages.current)} onRefresh={() => load(filters)} />)}
        </div>
      </section>)}
    </div>

    {dashboard.page.next_cursor ? <div className="payment-pagination"><MarkinaButton variant="secondary" disabled={loadingMore} onClick={() => void load(filters, dashboard.page.next_cursor, true)}>{loadingMore ? "Carregando…" : "Carregar mais clientes"}</MarkinaButton></div> : null}
    {dashboard.selections_without_order?.length ? <section className="admin-card payment-open-selections"><div className="section-heading"><div><h2>Seleções em aberto</h2><p>Fotos selecionadas sem pedido preparado; aparecem depois dos estados financeiros.</p></div><StatusBadge tone="neutral" className="payment-status-badge--cart">{dashboard.selections_without_order.length}</StatusBadge></div><div className="payment-orders">{dashboard.selections_without_order.map((selection) => <article className="payment-order payment-order--cart" key={`${selection.gallery.id}:${selection.client.id}`}><div className="payment-order__heading"><div><StatusBadge tone="neutral" className="payment-status-badge--cart">No carrinho</StatusBadge><h3>{selection.client.name}</h3><p>{selection.gallery.name} · {selection.parent_gallery.name}</p></div><div className="payment-client-total"><strong>{selection.total_cents === null ? "Preço indisponível" : money(selection.total_cents)}</strong><span>{selection.selected_count} foto(s)</span></div></div><details><summary>Ver seleção por pasta</summary>{selection.folders.map((folder) => <section key={folder.id}><h4>{folder.name}</h4><ul>{folder.items.map((item) => <li key={item.id}>{item.name}</li>)}</ul></section>)}</details></article>)}</div></section> : null}
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

function OrderCard({ order, clientId, clientName, showCartRecovery, onCartRecoveryRefresh, onRefresh }: {
  order: Order; clientId: string; clientName: string; showCartRecovery: boolean;
  onCartRecoveryRefresh: () => Promise<void>; onRefresh: () => Promise<void>;
}) {
  const [expanded, setExpanded] = useState(false);
  const presentation = order.provider_cart_recovery?.reopened_at
    ? { label: "Carrinho reaberto", tone: "neutral" as const } : financialPresentation[order.financial_status];
  const communication = order.communication;
  const paymentGroup = communication?.payment_group;
  const quantity = order.folders.reduce((total, folder) => total + folder.items.length, 0);
  const canDownloadPurchasedPhotos = (order.financial_status === "confirmed" || order.financial_status === "confirmed_undelivered") && !order.assets_removed && !order.gallery.removed;
  const downloadPurchasedPhotos = canDownloadPurchasedPhotos
    ? <a className="mk-button mk-button--secondary" href={`/api/admin/parent-galleries/${encodeURIComponent(order.parent_gallery.id)}/clients/${encodeURIComponent(clientId)}/selection/export.html`}>Baixar fotos compradas</a>
    : null;
  return <article className={`payment-order payment-order--${order.financial_status}`}>
    {order.assets_removed ? <p>Acervo removido ou revisão indisponível. Nomes, valores e estado financeiro preservados.</p> : null}
    <div className="payment-order__heading"><div><StatusBadge tone={presentation.tone} className={order.provider_cart_recovery?.reopened_at ? undefined : `payment-status-badge--${order.financial_status}`}>{presentation.label}</StatusBadge><h3>{order.gallery.name}{order.gallery.removed ? " · Galeria removida" : ""}</h3><p>{paymentGroup ? <>Compra {paymentGroup.id.slice(0, 8)} · Pedido {order.id.slice(0, 8)}</> : <>Pedido {order.id.slice(0, 8)}</>} · {order.parent_gallery.name}{order.payment_method === "credit_card" ? " · cartão de crédito" : ""} · {quantity} foto(s)</p></div><strong>{money(order.total_cents)}</strong></div>
    <details onToggle={(event) => setExpanded(event.currentTarget.open)}>
      <summary>Ver pedido e entrega</summary>
      <div className={styles.orderDetail}>
      <dl className="payment-order__facts"><div><dt>Criado em</dt><dd>{new Date(order.created_at).toLocaleString("pt-BR")}</dd></div><div><dt>Galeria pública</dt><dd>{order.parent_gallery.name}{order.parent_gallery.removed ? " (removida)" : ""}</dd></div>{order.selection_expires_at ? <div><dt>Prazo</dt><dd>{new Date(order.selection_expires_at).toLocaleDateString("pt-BR")}</dd></div> : null}</dl>
      <section className={styles.photoSection} aria-label="Fotografias do pedido"><h4>Fotografias do pedido <span>· {quantity}</span></h4>
      {expanded && order.folders?.length ? <OrderPhotos folders={order.folders} /> : !order.folders?.length ? <p>Nenhuma fotografia disponível.</p> : null}
      <p className={styles.photoTotal}>Total do pedido <strong>{money(order.total_cents)}</strong></p></section>
      <section className={styles.paymentSection} aria-label="Pagamento do pedido"><h4>Pagamento</h4>
      {order.payment_method === "credit_card" ? <>
        <p>Estado da compra de cartão: {order.provider_payment_state ?? "indisponível"}{order.provider_payment_id ? ` · compra ${order.provider_payment_id.slice(0, 8)}` : ""}. A confirmação não usa a decisão manual do PIX.</p>
        {showCartRecovery && order.provider_payment_id && order.provider_cart_recovery && !isConfirmedFinancialStatus(order.financial_status)
          ? <CartRecoveryActions paymentId={order.provider_payment_id} state={order.provider_payment_state}
            status={order.provider_cart_recovery} clientName={clientName} onRefresh={onCartRecoveryRefresh} /> : null}
        {downloadPurchasedPhotos ? <div className="dashboard-actions">{downloadPurchasedPhotos}</div> : null}
      </> : !communication ? <p>A cliente ainda não comunicou o pagamento.</p> : <>
        <p><strong>{decisionLabel[communication.status]}</strong> · comunicado em {new Date(communication.created_at).toLocaleString("pt-BR")}</p>
        <div className="dashboard-actions">
          <PaymentActions order={{ ...communication, quantity }} clientName={communication.client_name} onRefresh={onRefresh} />
          {downloadPurchasedPhotos}
        </div>
      </>}
      </section>
      <section className={styles.deliverySection} aria-label="Entrega do pedido"><h4>Entrega</h4><p>{order.delivery?.album_url && isConfirmedFinancialStatus(order.financial_status) ? "Fotos disponíveis" : "Fotos indisponíveis"}</p>
      <OrderDeliveryForm orderId={order.id} delivery={order.delivery ?? { album_url: null, version: 0, can_send: false, can_resend: false }} onRefresh={onRefresh} />
      </section></div>
    </details>
  </article>;
}

function isConfirmedFinancialStatus(status: FinancialStatus) {
  return status === "confirmed" || status === "confirmed_undelivered";
}
