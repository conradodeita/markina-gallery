"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

type Order = {
  id: string;
  payment_status: "pending" | "confirmed" | "cancelled";
  total_cents: number;
  client_name: string | null;
  created_at: string;
  price_rule: { minimum_quantity: number; maximum_quantity: number | null; unit_price_cents: number } | null;
  sales_message: string | null;
  pix: { copy_paste: string | null; qr_code_payload: string | null; instructions: string | null };
  items: { photo_id: string; name: string; unit_price_cents: number }[];
};

export default function GalleryOrdersPage() {
  const { galleryId } = useParams<{ galleryId: string }>();
  const [orders, setOrders] = useState<Order[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    fetch(`/api/admin/derived-galleries/${galleryId}/orders`, { credentials: "same-origin" })
      .then(async (response) => {
        if (!response.ok) throw new Error("orders request failed");
        setOrders((await response.json()).orders);
      })
      .catch(() => setFailed(true));
  }, [galleryId]);

  if (failed) return <main className="admin-shell"><h1>Pedidos indisponíveis</h1><p className="notice" role="alert">Não foi possível carregar os pedidos desta galeria.</p><Link href={`/admin/galleries/${galleryId}`}>Voltar para a galeria</Link></main>;
  if (!orders) return <main className="admin-shell"><p role="status">Carregando pedidos…</p></main>;
  return <main className="admin-shell">
    <Link href={`/admin/galleries/${galleryId}`}>← Galeria</Link>
    <p className="eyebrow">Vendas · consulta operacional</p>
    <h1>Pedidos da galeria</h1>
    <p className="intro">Esta é uma conferência de snapshots. A confirmação manual de pagamento pertence ao fluxo operacional próprio.</p>
    {!orders.length && <section className="admin-card"><h2>Nenhum pedido ainda</h2><p>Pedidos pendentes e confirmados aparecerão aqui quando forem criados.</p></section>}
    {orders.map((order) => <section className="admin-card" key={order.id}>
      <p className="eyebrow">{order.payment_status === "pending" ? "Pendente de confirmação" : order.payment_status === "confirmed" ? "Confirmado" : "Cancelado"}</p>
      <h2>{order.client_name ?? "Cliente"} · R$ {(order.total_cents / 100).toFixed(2).replace(".", ",")}</h2>
      <p>Criado em {new Date(order.created_at).toLocaleString("pt-BR")}</p>
      {order.price_rule && <p>Faixa congelada: {order.price_rule.minimum_quantity}–{order.price_rule.maximum_quantity ?? "sem limite"} fotos · R$ {(order.price_rule.unit_price_cents / 100).toFixed(2).replace(".", ",")} por foto.</p>}
      {order.sales_message && <p>Mensagem comercial: {order.sales_message}</p>}
      {order.payment_status === "pending" && (order.pix.copy_paste || order.pix.qr_code_payload || order.pix.instructions) && <details><summary>Snapshot das instruções PIX</summary>{order.pix.copy_paste && <p>Copia e cola: <code>{order.pix.copy_paste}</code></p>}{order.pix.qr_code_payload && <p>Payload QR: <code>{order.pix.qr_code_payload}</code></p>}{order.pix.instructions && <p>{order.pix.instructions}</p>}</details>}
      <ul className="photo-list" aria-label={`Fotos do pedido ${order.id}`}>{order.items.map((item) => <li key={item.photo_id}>{item.name} · R$ {(item.unit_price_cents / 100).toFixed(2).replace(".", ",")}</li>)}</ul>
    </section>)}
  </main>;
}
