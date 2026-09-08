"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { ProtectedPhoto, ProtectedPhotoViewer } from "../../protected-photo-viewer";

type Order = { id: string; client_name: string; gallery_name: string; total_cents: number; items: Array<{ photo_id: string; name: string; preview_url: string }> };

export default function AdminPurchasesPage() {
  const [orders, setOrders] = useState<Order[] | null>(null);
  const [selected, setSelected] = useState<ProtectedPhoto[]>([]);
  useEffect(() => { fetch("/api/admin/purchases", { credentials: "same-origin" }).then(async (response) => { if (!response.ok) throw new Error(); const result = await response.json(); setOrders(result.orders); }).catch(() => setOrders([])); }, []);
  if (orders === null) return <main className="admin-shell">Carregando compras…</main>;
  if (!orders.length) return <main className="admin-shell"><h1>Sem compras confirmadas</h1><Link href="/admin">Voltar para administração</Link></main>;
  return <main className="admin-shell"><p className="eyebrow">Markina Gallery · Fotógrafo</p><h1>Conferência de compras</h1><p className="intro">Apenas o fotógrafo vê estas prévias sem marca-d&apos;água; elas continuam limitadas e não são originais.</p><section className="admin-card">{orders.map((order) => <div className="purchase-row" key={order.id}><div><strong>{order.client_name}</strong><br /><span>{order.gallery_name} · R$ {(order.total_cents / 100).toFixed(2).replace(".", ",")}</span></div><button className="secondary" onClick={() => setSelected(order.items.map((item) => ({ id: item.photo_id, name: item.name, previewUrl: item.preview_url })))}>Conferir {order.items.length} foto(s)</button></div>)}</section>{selected.length > 0 && <ProtectedPhotoViewer label="Conferência administrativa de fotos compradas" photos={selected} />}</main>;
}
