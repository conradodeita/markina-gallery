"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { EmptyState, ValidationHeader } from "../validation-ui";
import { ProtectedPhoto, ProtectedPhotoViewer } from "../protected-photo-viewer";

type Gallery = { id: string; name: string; message: string };
type Order = { id: string; gallery_name: string; items: Array<{ photo_id: string; name: string; preview_url: string }> };
export default function LibraryPage() {
  const [galleries, setGalleries] = useState<Gallery[] | null>(null); const [orders, setOrders] = useState<Order[] | null>(null); const [selected, setSelected] = useState<ProtectedPhoto[]>([]); const [failed, setFailed] = useState(false);
  useEffect(() => { Promise.all([fetch("/api/library", { credentials:"same-origin" }), fetch("/api/library/purchases", { credentials:"same-origin" })]).then(async ([library,purchases]) => { if (!library.ok || !purchases.ok) throw new Error(); setGalleries((await library.json()).galleries ?? []); setOrders((await purchases.json()).orders ?? []); }).catch(() => { setFailed(true); setGalleries([]); setOrders([]); }); }, []);
  if (!galleries || !orders) return <main className="admin-shell">Carregando sua biblioteca…</main>;
  if (failed) return <main className="admin-shell"><h1>Biblioteca indisponível</h1><p className="intro">Não foi possível consultar suas galerias. Tente novamente.</p></main>;
  return <main className="admin-shell"><ValidationHeader role="Área da cliente" version="homologação" /><h1>Suas galerias</h1><p className="intro">Abra uma galeria para revisar fotos, selecionar e favoritar quando permitido.</p><section className="gallery-card-grid">{galleries.length ? galleries.map((gallery) => <Link className="gallery-card" href={`/gallery/${gallery.id}`} key={gallery.id}><span>Galeria privada</span><strong>{gallery.name}</strong><small>{gallery.message || "Toque para revisar suas fotos"}</small><b>Revisar fotos →</b></Link>) : <EmptyState title="Nenhuma galeria ativa" detail="Quando o fotógrafo liberar suas fotos, elas aparecerão aqui." />}</section><section className="admin-card"><h2>Compras confirmadas</h2>{orders.length ? orders.map((order) => <div className="purchase-row" key={order.id}><strong>{order.gallery_name}</strong><span>{order.items.length} foto(s)</span><button className="secondary" onClick={() => setSelected(order.items.map((item) => ({ id:item.photo_id, name:item.name, previewUrl:item.preview_url })))}>Ver prévias</button></div>) : <EmptyState title="Nenhuma compra confirmada" detail="Suas compras futuras ficarão disponíveis neste histórico." />}</section>{selected.length > 0 && <ProtectedPhotoViewer label="Fotos compradas" photos={selected} />}</main>;
}
