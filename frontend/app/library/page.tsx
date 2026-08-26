"use client";

import { useEffect, useState } from "react";

import { ProtectedPhoto, ProtectedPhotoViewer } from "../protected-photo-viewer";

type Order = { id: string; gallery_name: string; items: Array<{ photo_id: string; name: string; preview_url: string }> };

export default function LibraryPage() {
  const [orders, setOrders] = useState<Order[] | null>(null);
  const [selected, setSelected] = useState<ProtectedPhoto[]>([]);
  useEffect(() => { fetch("/api/library/purchases", { credentials: "same-origin" }).then(async (response) => { if (!response.ok) throw new Error(); const result = await response.json(); setOrders(result.orders); }).catch(() => setOrders([])); }, []);
  if (orders === null) return <main className="admin-shell">Carregando histórico…</main>;
  return <main className="admin-shell"><p className="eyebrow">Markina Gallery · Cliente</p><h1>Histórico de compras</h1><p className="intro">Suas fotos confirmadas ficam disponíveis aqui em prévias protegidas.</p>{orders.length === 0 ? <p className="form-message">Nenhuma compra confirmada ainda.</p> : <section className="admin-card"><h2>Compras confirmadas</h2>{orders.map((order) => <div className="purchase-row" key={order.id}><strong>{order.gallery_name}</strong><span>{order.items.length} foto(s)</span><button className="secondary" onClick={() => setSelected(order.items.map((item) => ({ id: item.photo_id, name: item.name, previewUrl: item.preview_url })))}>Ver fotos</button></div>)}</section>}{selected.length > 0 && <ProtectedPhotoViewer label="Fotos compradas" photos={selected} />}</main>;
}
