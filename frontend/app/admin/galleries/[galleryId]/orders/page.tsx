"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { MarkinaLink, MetricCard, PageHeading, StatusBadge, SystemState } from "../../../../ui-kit";
import { OverviewIcon } from "../../../overview-icon";
import catalogStyles from "../../../catalog.module.css";
import styles from "./gallery-orders.module.css";

type Order = {
  id: string;
  payment_status: "pending" | "confirmed" | "cancelled";
  cart_reopened_at?: string | null;
  total_cents: number;
  payment_group?: { id: string; total_cents: number } | null;
  client_name: string | null;
  created_at: string;
  price_rule: { minimum_quantity: number; maximum_quantity: number | null; unit_price_cents: number } | null;
  sales_message: string | null;
  pix: { copy_paste: string | null; qr_code_payload: string | null; instructions: string | null };
  items: { photo_id: string; name: string; unit_price_cents: number }[];
};

type Filter = "all" | Order["payment_status"];
const statuses = [
  { value: "all", label: "Todos" },
  { value: "pending", label: "Pendentes" },
  { value: "confirmed", label: "Confirmados" },
  { value: "cancelled", label: "Cancelados" },
] as const;

const statusLabels = {
  pending: { tone: "warning", label: "Pendente de confirmação" },
  confirmed: { tone: "success", label: "Confirmado" },
  cancelled: { tone: "neutral", label: "Cancelado" },
} as const;

function money(cents: number) {
  return `R$ ${new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(cents / 100)}`;
}

function matchText(value: string) {
  return value.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLocaleLowerCase("pt-BR");
}

export default function GalleryOrdersPage() {
  const { galleryId } = useParams<{ galleryId: string }>();
  const [result, setResult] = useState<{ galleryId: string; orders: Order[] | null } | null>(null);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<Filter>("all");

  useEffect(() => {
    const controller = new AbortController();
    fetch(`/api/admin/derived-galleries/${galleryId}/orders`, { credentials: "same-origin", signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error("orders request failed");
        const payload = await response.json() as { orders: Order[] };
        if (!controller.signal.aborted) setResult({ galleryId, orders: payload.orders });
      })
      .catch(() => { if (!controller.signal.aborted) setResult({ galleryId, orders: null }); });
    return () => controller.abort();
  }, [galleryId]);

  const current = result?.galleryId === galleryId ? result : null;
  const orders = current?.orders;
  const failed = current?.orders === null;
  const term = matchText(query.trim());
  const confirmed = orders?.filter((order) => order.payment_status === "confirmed") ?? [];
  const visible = orders?.filter((order) => (
    (status === "all" || order.payment_status === status) &&
    (!term || matchText(order.id).includes(term) || matchText(order.client_name ?? "").includes(term))
  )) ?? [];

  return <div className={`${catalogStyles.catalog} ${styles.page}`}>
    <Link className={styles.back} href={`/admin/galleries/${galleryId}`}><span aria-hidden="true">←</span> Voltar para a galeria</Link>
    <PageHeading title="Pedidos da galeria" detail="Confira os pedidos e as regras comerciais registradas no momento da compra." actions={<MarkinaLink href="/admin/payments" variant="secondary">Vendas e pagamentos</MarkinaLink>} />
    <aside className={styles.notice}>
      <OverviewIcon name="task" />
      <div><strong>Histórico comercial preservado</strong><p>Os valores e as instruções listadas são os registrados na compra. A confirmação manual de pagamento é feita em Vendas e pagamentos.</p></div>
    </aside>
    {failed ? <SystemState tone="error" title="Pedidos indisponíveis" detail="Não foi possível carregar os pedidos desta galeria." /> : !orders ? <SystemState tone="loading" title="Carregando pedidos…" detail="Consultando o histórico da galeria." /> : <>
    <section className={catalogStyles.metrics} aria-label="Resumo dos pedidos">
      <MetricCard label="Total de pedidos" value={orders.length} detail="nesta galeria" icon={<OverviewIcon name="collections" />} />
      <MetricCard label="Aguardando confirmação" value={orders.filter((order) => order.payment_status === "pending").length} detail="pedidos pendentes" icon={<OverviewIcon name="task" />} />
      <MetricCard label="Valor confirmado" value={money(confirmed.reduce((total, order) => total + order.total_cents, 0))} detail={`${confirmed.length} pedido(s) confirmado(s)`} icon={<OverviewIcon name="payments" />} />
    </section>
    <section className={styles.filters} aria-label="Filtro dos pedidos">
      <label className={catalogStyles.search}>
        <span id="gallery-orders-search-label">Buscar pedido por cliente ou ID</span>
        <span className={catalogStyles.searchField}><OverviewIcon name="search" /><input aria-labelledby="gallery-orders-search-label" type="search" value={query} onChange={(event) => setQuery(event.target.value)} /></span>
      </label>
      <label className={styles.statusFilter}><span id="gallery-orders-status-label">Situação</span><select aria-labelledby="gallery-orders-status-label" value={status} onChange={(event) => setStatus(event.target.value as Filter)}>
        {statuses.map(({ value, label }) => <option value={value} key={value}>{label}</option>)}
      </select></label>
    </section>
    {!visible.length && (orders.length ? <SystemState title="Nenhum pedido neste filtro" detail="Revise o texto ou a situação selecionada." /> : <SystemState title="Nenhum pedido ainda" detail="Pedidos pendentes e confirmados aparecerão aqui quando forem criados." />)}
    {visible.map((order) => <section className={styles.order} key={order.id}>
      <header><StatusBadge tone={statusLabels[order.payment_status].tone}>{order.cart_reopened_at && order.payment_status === "cancelled" ? "Carrinho reaberto" : statusLabels[order.payment_status].label}</StatusBadge>
      <h2>{order.client_name ?? "Cliente"} · {money(order.total_cents)}</h2></header>
      {order.payment_group ? <p>Subtotal desta galeria. Integra o PIX único {order.payment_group.id.slice(0, 8)} de {money(order.payment_group.total_cents)}.</p> : null}
      <p>Criado em {new Date(order.created_at).toLocaleString("pt-BR")}</p>
      {order.price_rule && <p>Faixa congelada: {order.price_rule.minimum_quantity}–{order.price_rule.maximum_quantity ?? "sem limite"} fotos · {money(order.price_rule.unit_price_cents)} por foto.</p>}
      {order.sales_message && <p>Mensagem comercial: {order.sales_message}</p>}
      {order.payment_status === "pending" && (order.pix.copy_paste || order.pix.qr_code_payload || order.pix.instructions) && <details><summary>Snapshot das instruções PIX</summary>{order.pix.copy_paste && <p>Copia e cola: <code>{order.pix.copy_paste}</code></p>}{order.pix.qr_code_payload && <p>Payload QR: <code>{order.pix.qr_code_payload}</code></p>}{order.pix.instructions && <p>{order.pix.instructions}</p>}</details>}
      <ul className="photo-list" aria-label={`Fotos do pedido ${order.id}`}>{order.items.map((item) => <li key={item.photo_id}>{item.name} · {money(item.unit_price_cents)}</li>)}</ul>
    </section>)}
    </>}
  </div>;
}
