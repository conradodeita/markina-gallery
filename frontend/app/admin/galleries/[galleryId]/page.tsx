"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

type GalleryClient = {
  id: string;
  name: string;
  phone: string;
  selected_count: number;
  payment_pending: boolean;
  confirmed_order_count: number;
};

type Detail = {
  id: string;
  parent_gallery_id: string;
  name: string;
  link: string | null;
  custom_message: string;
  favorites_enabled: boolean;
  comments_enabled: boolean;
  selection_expires_at: string | null;
  cover_preview_url: string | null;
  client: GalleryClient | null;
  responsible?: GalleryClient | null;
  frozen: boolean;
  blocked: boolean;
};

type ClientOption = { id: string; name: string };

export default function GalleryDetailPage() {
  const { galleryId } = useParams<{ galleryId: string }>();
  const router = useRouter();
  const [detail, setDetail] = useState<Detail | null>(null);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [message, setMessage] = useState("");
  const [clients, setClients] = useState<ClientOption[]>([]);

  function load() {
    setLoading(true);
    Promise.all([
      fetch(`/api/admin/derived-galleries/${galleryId}`, { credentials: "same-origin" }),
      fetch("/api/admin/clients", { credentials: "same-origin" }),
    ])
      .then(async ([detailResponse, clientsResponse]) => {
        if (!detailResponse.ok || !clientsResponse.ok) throw new Error("Falha ao carregar galeria");
        setDetail(await detailResponse.json());
        setClients((await clientsResponse.json()).clients ?? []);
        setFailed(false);
      })
      .catch(() => {
        setDetail(null);
        setFailed(true);
      })
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    queueMicrotask(load);
  }, [galleryId]); // eslint-disable-line react-hooks/exhaustive-deps

  async function toggle() {
    if (!detail || !confirm(detail.blocked ? "Liberar o acesso desta galeria privada?" : "Bloquear o acesso desta galeria privada?")) return;
    const response = await fetch(`/api/admin/derived-galleries/${galleryId}`, {
      method: "PATCH",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ access_enabled: detail.blocked }),
    });
    setMessage(response.ok ? "Acesso atualizado." : "Não foi possível atualizar o acesso.");
    if (response.ok) load();
  }

  async function remove() {
    if (!confirm("Excluir esta galeria privada? Seleções e compras preservadas podem impedir a exclusão.")) return;
    const response = await fetch(`/api/admin/derived-galleries/${galleryId}`, {
      method: "DELETE",
      credentials: "same-origin",
    });
    if (response.ok) router.push("/admin/galleries");
    else setMessage("A galeria possui referências ou histórico que impedem a exclusão direta.");
  }

  async function saveName(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const response = await fetch(`/api/admin/derived-galleries/${galleryId}`, {
      method: "PATCH",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: data.get("name") }),
    });
    setMessage(response.ok ? "Nome salvo." : "Não foi possível salvar o nome.");
    if (response.ok) load();
  }

  async function clone(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const response = await fetch(`/api/admin/derived-galleries/${galleryId}/clone`, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        client_id: data.get("client"),
        name: data.get("name") || null,
        idempotency_key: crypto.randomUUID(),
      }),
    });
    setMessage(response.ok ? "Galeria privada criada." : "Não foi possível criar a galeria privada.");
  }

  if (loading) return <main className="admin-shell"><p role="status">Carregando galeria…</p></main>;
  if (failed || !detail) return <main className="admin-shell"><h1>Galeria indisponível</h1><p className="notice" role="alert">Não foi possível carregar os dados desta galeria.</p><Link href="/admin/galleries">Voltar para galerias</Link></main>;

  const galleryClient = detail.client ?? detail.responsible ?? null;

  return (
    <main className="admin-shell">
      <Link href="/admin/galleries">← Galerias</Link>
      <p className="eyebrow">Galeria pública · galeria privada</p>
      <h1>{detail.name}</h1>
      <section className="admin-card">
        {detail.cover_preview_url ? <img className="detail-cover" src={`/api${detail.cover_preview_url}`} alt="Capa da galeria" /> : null}
        <p>{detail.frozen ? "Prazo de seleção expirado" : "Seleção ativa"} · {detail.blocked ? "Acesso bloqueado" : "Acesso liberado"}</p>
        <button className="secondary" onClick={toggle}>{detail.blocked ? "Liberar acesso" : "Bloquear acesso"}</button>
        <Link className="secondary" href={`/admin/galleries/sources/${detail.parent_gallery_id}/edit/vendas`}>Preço, PIX e regras herdadas</Link>
        <Link className="secondary" href={`/admin/galleries/${galleryId}/orders`}>Pedidos</Link>
        <button className="link-button" onClick={remove}>Excluir galeria privada</button>
      </section>
      {galleryClient ? (
        <section className="admin-card">
          <h2>{galleryClient.name}</h2>
          <p>{galleryClient.phone}</p>
          <p>{galleryClient.selected_count} fotos selecionadas · {galleryClient.confirmed_order_count} compras confirmadas</p>
          <Link className="primary" href={`/admin/galleries/${galleryId}/selection`}>Conferir seleção e exportar</Link>
        </section>
      ) : null}
      <section className="admin-card">
        <h2>Ajustes da galeria privada</h2>
        <form className="auth-form" onSubmit={saveName}>
          <label>Nome<input name="name" defaultValue={detail.name} required /></label>
          <button className="primary">Salvar nome</button>
        </form>
        <p>Mensagem, prazo, favoritos, comentários, preço e PIX são herdados da Galeria pública.</p>
        {detail.custom_message ? <p><strong>Mensagem vigente:</strong> {detail.custom_message}</p> : null}
      </section>
      <section className="admin-card">
        <h2>Criar galeria privada para outra cliente</h2>
        <form className="auth-form" onSubmit={clone}>
          <label>Cliente<select name="client" required><option value="">Selecione</option>{clients.filter((client) => client.id !== galleryClient?.id).map((client) => <option key={client.id} value={client.id}>{client.name}</option>)}</select></label>
          <label>Nome opcional<input name="name" placeholder={detail.name} /></label>
          <button className="secondary">Criar galeria privada</button>
        </form>
      </section>
      {message ? <p className="form-message" role="status">{message}</p> : null}
    </main>
  );
}
