"use client";

import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

type Selection = { client: { name: string; phone: string } | null; selection_count: number; payment_status: string; photos: Array<{ id: string; filename: string; preview_url: string; sales_count: number }> };

export default function SelectionPage() {
  const { galleryId } = useParams<{ galleryId: string }>();
  const searchParams = useSearchParams();
  const clientId = searchParams.get("client");
  const clientQuery = clientId ? `?client_id=${encodeURIComponent(clientId)}` : "";
  const [selection, setSelection] = useState<Selection | null>(null);
  useEffect(() => { fetch(`/api/admin/derived-galleries/${galleryId}/selection${clientQuery}`, { credentials: "same-origin" }).then(async response => { if (!response.ok) throw new Error(); setSelection(await response.json()); }).catch(() => setSelection(null)); }, [clientQuery, galleryId]);
  if (!selection) return <main className="admin-shell">Carregando seleção…</main>;
  return <main className="admin-shell"><Link href={`/admin/galleries/${galleryId}`}>← Galeria</Link><p className="eyebrow">Seleção individual</p><h1>{selection.client?.name ?? "Cliente"}</h1><p className="intro">{selection.selection_count} fotos selecionadas · pagamento {selection.payment_status}</p><p><button className="secondary" onClick={() => { window.location.href = `/api/admin/derived-galleries/${galleryId}/selection/export.txt${clientQuery}`; }}>Baixar TXT</button> <button className="secondary" onClick={() => { window.location.href = `/api/admin/derived-galleries/${galleryId}/selection/export.csv${clientQuery}`; }}>Baixar CSV</button></p><section className="photo-card-grid">{selection.photos.map(photo => <article className="photo-card" key={photo.id}><img src={`/api${photo.preview_url}`} alt={`Prévia administrativa de ${photo.filename}`} /><strong>{photo.filename}</strong><small>{photo.sales_count ? `Vendida ${photo.sales_count} vez(es)` : "Ainda não confirmada"}</small></article>)}</section></main>;
}
