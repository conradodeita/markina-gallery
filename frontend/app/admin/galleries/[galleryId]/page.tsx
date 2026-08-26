"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

type Detail = { id: string; name: string; link: string; selection_expires_at: string | null; cover_preview_url: string | null; responsible: { id: string; name: string; phone: string; selected_count: number; payment_pending: boolean; confirmed_order_count: number } | null; frozen: boolean; blocked: boolean };

export default function GalleryDetailPage() {
  const { galleryId } = useParams<{ galleryId: string }>();
  const [detail, setDetail] = useState<Detail | null>(null);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [message, setMessage] = useState("");
  function load() { setLoading(true); fetch(`/api/admin/derived-galleries/${galleryId}`, { credentials: "same-origin" }).then(async (response) => { if (!response.ok) throw new Error("Falha ao carregar galeria"); setDetail(await response.json()); setFailed(false); }).catch(() => { setDetail(null); setFailed(true); }).finally(() => setLoading(false)); }
  useEffect(() => { queueMicrotask(load); }, [galleryId]); // eslint-disable-line react-hooks/exhaustive-deps
  async function toggle() { if (!detail || !confirm(detail.blocked ? "Liberar o acesso desta galeria privada?" : "Bloquear o acesso desta galeria privada?")) return; const response = await fetch(`/api/admin/derived-galleries/${galleryId}`, { method: "PATCH", credentials: "same-origin", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ access_enabled: detail.blocked }) }); setMessage(response.ok ? "Acesso atualizado." : "Não foi possível atualizar o acesso."); if (response.ok) load(); }
  if (loading) return <main className="admin-shell"><p role="status">Carregando galeria…</p></main>;
  if (failed || !detail) return <main className="admin-shell"><h1>Galeria indisponível</h1><p className="notice" role="alert">Não foi possível carregar os dados desta galeria.</p><Link href="/admin/galleries">Voltar para galerias</Link></main>;
  return <main className="admin-shell"><Link href="/admin/galleries">← Galerias</Link><p className="eyebrow">Acervo-fonte · galeria privada</p><h1>{detail.name}</h1><section className="admin-card">{detail.cover_preview_url ? <img className="detail-cover" src={`/api${detail.cover_preview_url}`} alt="Capa da galeria" /> : null}<p>Link controlado: <code>{detail.link}</code></p><p>{detail.frozen ? "Prazo de seleção expirado" : "Seleção ativa"} · {detail.blocked ? "Acesso bloqueado" : "Acesso liberado"}</p><button className="secondary" onClick={toggle}>{detail.blocked ? "Liberar acesso" : "Bloquear acesso"}</button></section>{detail.responsible ? <section className="admin-card"><h2>{detail.responsible.name}</h2><p>{detail.responsible.phone}</p><p>{detail.responsible.selected_count} fotos selecionadas · {detail.responsible.confirmed_order_count} compras confirmadas</p><Link className="primary" href={`/admin/galleries/${galleryId}/selection`}>Conferir seleção e exportar</Link></section> : null}{message ? <p className="form-message" role="status">{message}</p> : null}</main>;
}
