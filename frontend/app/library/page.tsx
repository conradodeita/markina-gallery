"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ProtectedPhoto, ProtectedPhotoViewer } from "../protected-photo-viewer";

type Gallery = { id: string; name: string; message: string };
type Order = { id: string; gallery_name: string; items: Array<{ photo_id: string; name: string; preview_url: string }> };

export default function LibraryPage() {
  const [galleries, setGalleries] = useState<Gallery[] | null>(null);
  const [orders, setOrders] = useState<Order[] | null>(null);
  const [selected, setSelected] = useState<ProtectedPhoto[]>([]);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    Promise.all([fetch("/api/library", { credentials: "same-origin" }), fetch("/api/library/purchases", { credentials: "same-origin" })]).then(async ([library, purchases]) => {
      if (!library.ok || !purchases.ok) throw new Error();
      setGalleries((await library.json()).galleries ?? []);
      setOrders((await purchases.json()).orders ?? []);
    }).catch(() => { setFailed(true); setGalleries([]); setOrders([]); });
  }, []);
  if (galleries === null || orders === null) return <main className="admin-shell">Carregando biblioteca…</main>;
  if (failed) return <main className="admin-shell"><h1>Biblioteca indisponível</h1><p className="intro">Não foi possível consultar suas galerias. Tente novamente em instantes.</p></main>;
  return <main className="admin-shell"><p className="eyebrow">Markina Gallery · Cliente</p><h1>Minha biblioteca</h1><p className="intro">Suas galerias ativas e compras confirmadas, sempre consultadas no seu acesso autorizado.</p><section className="admin-card"><h2>Galerias para revisar</h2>{galleries.length === 0 ? <p className="form-message">Nenhuma galeria ativa no momento.</p> : galleries.map((gallery) => <div className="purchase-row" key={gallery.id}><div><strong>{gallery.name}</strong>{gallery.message && <p>{gallery.message}</p>}</div><Link className="secondary" href={`/gallery/${gallery.id}`}>Abrir galeria</Link></div>)}</section><section className="admin-card"><h2>Compras confirmadas</h2>{orders.length === 0 ? <p className="form-message">Nenhuma compra confirmada ainda.</p> : orders.map((order) => <div className="purchase-row" key={order.id}><strong>{order.gallery_name}</strong><span>{order.items.length} foto(s)</span><button className="secondary" onClick={() => setSelected(order.items.map((item) => ({ id: item.photo_id, name: item.name, previewUrl: item.preview_url })))}>Ver fotos</button></div>)}</section>{selected.length > 0 && <ProtectedPhotoViewer label="Fotos compradas" photos={selected} />}</main>;
}
