"use client";

import { PRODUCT_NAME } from "../../product-brand";
import { FormEvent, useEffect, useMemo, useState } from "react";
import Link from "next/link";

type Option = { id: string; name: string; event_name?: string; client_id?: string };
type OrderItem = { id: string; photo_id: string; photo_name: string; folder_id: string; folder_name: string; unit_price_cents: number; quantity: number };
type SalesItem = { item_id: string; fotografia_id: string; fotografia_nome: string; pasta_nome: string; total_item: number; galeria_nome: string; pedido_id: string };
type Order = { order_id: string; status: string; confirmed: boolean; client_name: string; client_phone: string; confirmed_at: string; gallery_name: string; payment_method: string; destination: string; total_cents: number; items_total_cents: number; items: OrderItem[] };
type Report = {
  revenue_cents: number; confirmed_order_count: number; sold_photo_count: number;
  average_order_cents: number | null; orders_total: number; orders: Order[];
  purchased_total: number; purchased_photos: SalesItem[];
  selected_not_purchased_total: number; selected_not_purchased_photos: Array<{ client_id: string; gallery_id: string; photo_id: string; abandoned: boolean }>;
  eligible_selection_count: number; converted_selection_count: number; conversion_rate_percent: number | null;
  selection_metrics_available: boolean;
  revenue_by_day: Array<{ date: string; revenue_cents: number }>;
  reconciliations: Array<{ order_id: string; order_total_cents: number; items_total_cents: number; difference_cents: number }>;
  abandoned: Array<{ client_name: string; gallery_name: string; photo_count: number; potential_value_cents: number | null; photos: Array<{ photo_id: string }> }>;
  selected_not_purchased: Array<{ client_id: string; gallery_id: string; photo_id: string; abandoned: boolean }>;
  by_gallery: Array<{ id: string; name: string; total_cents: number }>;
  by_folder: Array<{ id: string; name: string; total_cents: number }>;
};
const PAGE_SIZE = 50;
const money = (cents: number | null) => cents === null ? "Indisponível" : new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(cents / 100);

export default function StatisticsPage() {
  const [authorized, setAuthorized] = useState<boolean | null>(null);
  const [csvAllowed, setCsvAllowed] = useState(false);
  const [options, setOptions] = useState<{ clients: Option[]; parent_galleries: Option[]; derived_galleries: Option[]; folders: Option[] }>({ clients: [], parent_galleries: [], derived_galleries: [], folders: [] });
  const [filters, setFilters] = useState<Record<string, string>>({});
  const [applied, setApplied] = useState<Record<string, string>>({});
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState(false);
  const [page, setPage] = useState(0);
  const [purchasedPage, setPurchasedPage] = useState(0);
  const [selectedPage, setSelectedPage] = useState(0);
  const query = useMemo(() => new URLSearchParams(Object.entries(applied).filter(([, value]) => value)).toString(), [applied]);
  const legacyQuery = useMemo(() => new URLSearchParams(Object.entries(applied).filter(([key, value]) => value && ["starts_at", "ends_at", "client_id", "parent_gallery_id", "derived_gallery_id", "event_name"].includes(key))).toString(), [applied]);

  async function load(nextPage = page, queryString = query, nextPurchasedPage = purchasedPage, nextSelectedPage = selectedPage) {
    setReport(null); setError(false);
    try {
      const params = new URLSearchParams(queryString);
      params.set("offset", String(nextPage * PAGE_SIZE)); params.set("limit", String(PAGE_SIZE));
      params.set("purchased_offset", String(nextPurchasedPage * PAGE_SIZE));
      params.set("selected_offset", String(nextSelectedPage * PAGE_SIZE));
      const response = await fetch(`/api/admin/statistics/report?${params}`, { credentials: "same-origin", cache: "no-store" });
      if (!response.ok) throw new Error("statistics request failed");
      setReport(await response.json());
    } catch { setReport(null); setError(true); }
  }
  useEffect(() => {
    fetch("/api/admin", { credentials: "same-origin", cache: "no-store" }).then(async (response) => {
      setAuthorized(response.ok);
      if (response.ok) await load(0, "");
    }).catch(() => setAuthorized(false));
    fetch("/api/admin/statistics/filters", { credentials: "same-origin", cache: "no-store" }).then(async (response) => {
      if (response.ok) {
        const loaded = await response.json();
        setOptions({ clients: loaded.clients ?? [], parent_galleries: loaded.parent_galleries ?? [], derived_galleries: loaded.derived_galleries ?? [], folders: loaded.folders ?? [] });
      }
    }).catch(() => undefined);
    fetch("/api/admin/statistics/csv-access", { credentials: "same-origin", cache: "no-store" }).then(async (response) => {
      if (response.ok) setCsvAllowed((await response.json()).allowed === true);
    }).catch(() => setCsvAllowed(false));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  function apply(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const next = Object.fromEntries(Object.entries(filters).filter(([, value]) => value));
    setApplied(next); setPage(0); setPurchasedPage(0); setSelectedPage(0); load(0, new URLSearchParams(next).toString(), 0, 0);
  }
  function change(name: string, value: string) { setFilters((current) => ({ ...current, [name]: value })); }
  if (authorized === null) return <main className="admin-shell">Carregando estatísticas…</main>;
  if (!authorized) return <main className="admin-shell"><h1>Acesso restrito</h1><Link href="/">Voltar para entrada</Link></main>;

  return <main className="admin-shell">
    <p className="eyebrow">{PRODUCT_NAME} · Fotógrafo</p>
    <h1>Estatísticas</h1>
    <p className="intro">Receita considera pagamentos atualmente confirmados; o sistema não registra reembolsos, frete, descontos ou taxas para calcular valor líquido. Seleções só são abandonadas depois do prazo configurado da galeria e quando não existe pedido associado.</p>
    <form className="filter-grid" onSubmit={apply}>
      <label>De<input type="date" onChange={(e) => change("starts_at", e.target.value ? `${e.target.value}T00:00:00Z` : "")} /></label>
      <label>Até<input type="date" onChange={(e) => change("ends_at", e.target.value ? `${e.target.value}T23:59:59Z` : "")} /></label>
      <label>Cliente<select onChange={(e) => change("client_id", e.target.value)}><option value="">Todos</option>{options.clients.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}</select></label>
      <label>Evento<input list="statistics-events" onChange={(e) => change("event_name", e.target.value)} /><datalist id="statistics-events">{options.parent_galleries.filter((o) => o.event_name).map((o) => <option key={o.id} value={o.event_name} />)}</datalist></label>
      <label>Galeria pública<select onChange={(e) => change("parent_gallery_id", e.target.value)}><option value="">Todas</option>{options.parent_galleries.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}</select></label>
      <label>Galeria privada<select onChange={(e) => change("derived_gallery_id", e.target.value)}><option value="">Todas</option>{options.derived_galleries.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}</select></label>
      <label>Pasta<select onChange={(e) => change("folder_id", e.target.value)}><option value="">Todas</option>{options.folders.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}</select></label>
      <label>Pagamento<select onChange={(e) => change("payment_method", e.target.value)}><option value="">Todos</option><option value="pix">PIX</option><option value="credit_card">Cartão</option><option value="not_required">Sem cobrança</option><option value="unknown">Não identificado</option></select></label>
      <label>Status<select onChange={(e) => change("order_status", e.target.value)}><option value="">Todos</option><option value="confirmed">Confirmado</option><option value="pending">Pendente</option><option value="cancelled">Cancelado</option><option value="not_required">Sem cobrança</option><option value="hold_or_corrected">Em análise/corrigido</option></select></label>
      <button className="primary">Aplicar filtros</button>
    </form>
    {error ? <section className="admin-card" role="alert"><h2>Não foi possível atualizar as estatísticas</h2><p className="form-message">Os indicadores não foram substituídos por zero. Tente novamente mantendo os filtros atuais.</p><button type="button" className="primary" onClick={() => load()}>Tentar novamente</button></section> : report === null ? <p className="form-message">Atualizando indicadores…</p> : <>
      <section className="stat-cards">
        <article><span>Receita confirmada</span><strong>{money(report.revenue_cents)}</strong></article>
        <article><span>Pedidos confirmados</span><strong>{report.confirmed_order_count}</strong></article>
        <article><span>Fotos vendidas</span><strong>{report.sold_photo_count}</strong></article>
        <article><span>Ticket médio por pedido</span><strong>{money(report.average_order_cents)}</strong></article>
        <article><span>Seleções expiradas sem pedido</span><strong>{report.selection_metrics_available ? report.abandoned.reduce((total, item) => total + item.photo_count, 0) : "Sem base"}</strong></article>
        <article><span>Conversão das seleções resolvidas</span><strong>{report.conversion_rate_percent === null ? "Sem base" : `${report.conversion_rate_percent.toFixed(1)}%`}</strong><small>{report.converted_selection_count} fotos compradas / {report.eligible_selection_count} oportunidades resolvidas</small></article>
      </section>
      <section className="admin-card"><h2>Receita por dia</h2>{report.revenue_by_day.length ? <ul>{report.revenue_by_day.map((item) => <li key={item.date}>{new Date(`${item.date}T00:00:00`).toLocaleDateString("pt-BR")} · {money(item.revenue_cents)}</li>)}</ul> : <p className="form-message">Nenhuma venda confirmada no período.</p>}</section>
      <section className="admin-card"><h2>Relatórios</h2><div className="filter-actions"><a className="secondary" href={`/api/admin/statistics/report.html${query ? `?${query}` : ""}`}>Baixar relatório HTML</a>{csvAllowed ? <a className="secondary" href={`/api/admin/statistics/report.csv${query ? `?${query}` : ""}`}>Baixar CSV</a> : null}<a className="secondary" href={`/api/admin/statistics/purchased.txt${legacyQuery ? `?${legacyQuery}` : ""}`}>Fotos compradas (TXT)</a><a className="secondary" href={`/api/admin/statistics/selected-not-purchased.txt${legacyQuery ? `?${legacyQuery}` : ""}`}>Seleções sem compra (TXT)</a></div><p className="form-message">O CSV aparece somente para a conta proprietária e também é revalidado pelo backend. Uma seleção sem preço congelado aparece sem valor potencial. Os TXT mantêm os filtros anteriores de período, cliente e galeria.</p></section>
      <section className="admin-card"><h2>Pedidos e itens</h2>{report.orders.length ? <div className="table-scroll"><table><thead><tr><th>Data</th><th>Cliente</th><th>Galeria</th><th>Status</th><th>Pagamento</th><th>Itens</th><th>Total</th><th>Conciliação</th></tr></thead><tbody>{report.orders.map((order) => <tr key={order.order_id}><td>{order.confirmed_at ? new Date(order.confirmed_at).toLocaleDateString("pt-BR") : "—"}</td><td>{order.client_name}<small>{order.client_phone}</small></td><td>{order.gallery_name}</td><td>{order.status}</td><td>{order.payment_method === "pix" ? "PIX · Nubank" : order.payment_method === "credit_card" ? "Cartão · InfinityPay" : order.payment_method}</td><td><ul>{order.items.map((item) => <li key={item.id}>{item.photo_name} · {item.folder_name || "Sem pasta"} · {money(item.unit_price_cents)}</li>)}</ul></td><td>{money(order.total_cents)}</td><td>{money(order.items_total_cents)}<small>Itens − pedido: {money(order.items_total_cents - order.total_cents)}</small></td></tr>)}</tbody></table></div> : <p className="form-message">Nenhum pedido corresponde aos filtros.</p>}
        <StatisticsPagination label="pedidos" page={page} total={report.orders_total} onChange={(next) => { setPage(next); load(next); }} />
      </section>
      <section className="admin-card"><h2>Fotos compradas</h2>{report.purchased_photos.length ? <ul className="photo-list">{report.purchased_photos.map((item) => <li key={item.item_id}><code>{item.fotografia_id}</code>{item.fotografia_nome} · {item.galeria_nome} · {item.pasta_nome || "Sem pasta"} · {money(item.total_item)}</li>)}</ul> : <p className="form-message">Nenhuma foto comprada no filtro.</p>}<StatisticsPagination label="fotos compradas" page={purchasedPage} total={report.purchased_total} onChange={(next) => { setPurchasedPage(next); load(page, query, next, selectedPage); }} /></section>
      <section className="admin-card"><h2>Selecionadas sem compra</h2>{!report.selection_metrics_available ? <p className="form-message">Indicador indisponível ao filtrar por pasta, pagamento ou status: esses dados de seleção não estão vinculados a esse recorte.</p> : report.selected_not_purchased_photos.length ? <ul className="photo-list">{report.selected_not_purchased_photos.map((item) => <li key={`${item.client_id}-${item.gallery_id}-${item.photo_id}`}><code>{item.photo_id}</code>{item.abandoned ? "Prazo vencido, sem pedido" : "Ainda sem compra"}</li>)}</ul> : <p className="form-message">Nenhuma seleção sem compra no filtro.</p>}{report.selection_metrics_available ? <StatisticsPagination label="seleções sem compra" page={selectedPage} total={report.selected_not_purchased_total} onChange={(next) => { setSelectedPage(next); load(page, query, purchasedPage, next); }} /> : null}</section>
      <section className="admin-card"><h2>Receita por galeria</h2>{report.by_gallery.length ? <ul>{report.by_gallery.map((item) => <li key={item.id}>{item.name}: {money(item.total_cents)}</li>)}</ul> : <p className="form-message">Sem vendas confirmadas no filtro.</p>}</section>
      <section className="admin-card"><h2>Receita por pasta</h2>{report.by_folder.length ? <ul>{report.by_folder.map((item) => <li key={item.id}>{item.name}: {money(item.total_cents)}</li>)}</ul> : <p className="form-message">Sem vendas confirmadas no filtro.</p>}</section>
      <section className="admin-card"><h2>Denominador de conversão</h2><p className="form-message">Conversão usa como denominador fotos selecionadas já resolvidas: compradas ou expiradas sem pedido. Seleções com pedido pendente, cancelado ou sem cobrança permanecem em seu próprio estado e ficam fora desse denominador.</p></section>
      <section className="admin-card"><h2>Seleções abandonadas</h2>{!report.selection_metrics_available ? <p className="form-message">Indicador indisponível ao filtrar por pasta, pagamento ou status.</p> : report.abandoned.length ? <><p>Prazo da galeria vencido e nenhum pedido associado. Valor potencial indisponível quando não existe preço congelado.</p><ul>{report.abandoned.map((item, i) => <li key={`${item.gallery_name}-${item.client_name}-${i}`}>{item.client_name} · {item.gallery_name} · {item.photo_count} fotos · {money(item.potential_value_cents)}<ul>{item.photos.map((photo) => <li key={photo.photo_id}><code>{photo.photo_id}</code></li>)}</ul></li>)}</ul></> : <p className="form-message">Nenhuma seleção expirada sem pedido.</p>}</section>
      <section className="admin-card"><h2>Conciliação</h2>{report.reconciliations.filter((r) => r.difference_cents !== 0).length ? <ul>{report.reconciliations.filter((r) => r.difference_cents !== 0).map((r) => <li key={r.order_id}>Pedido {r.order_id}: registrado {money(r.order_total_cents)}, itens {money(r.items_total_cents)}, diferença {money(r.difference_cents)}</li>)}</ul> : <p className="form-message">Os totais dos itens conciliam com os totais dos pedidos no escopo.</p>}</section>
    </>}
  </main>;
}

function StatisticsPagination({ label, page, total, onChange }: { label: string; page: number; total: number; onChange: (page: number) => void }) {
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  if (pages <= 1) return null;
  return <nav className="statistics-pagination" aria-label={`Paginação de ${label}`}><button type="button" className="secondary" disabled={page === 0} onClick={() => onChange(page - 1)}>Anterior</button><span>Página {page + 1} de {pages}</span><button type="button" className="secondary" onClick={() => onChange(page + 1)} disabled={page >= pages - 1}>Próxima</button></nav>;
}
