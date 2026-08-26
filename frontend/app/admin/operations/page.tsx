"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

type Item = { id: string; name: string };

export default function OperationsPage() {
  const [authorized, setAuthorized] = useState<boolean | null>(null);
  const [clients, setClients] = useState<Item[]>([]);
  const [galleries, setGalleries] = useState<Item[]>([]);
  const [photos, setPhotos] = useState<Item[]>([]);
  const [parentId, setParentId] = useState("");
  const [message, setMessage] = useState("");
  const [uploadStatus, setUploadStatus] = useState("");

  function refresh() {
    fetch("/api/admin/clients", { credentials: "same-origin" }).then(async (response) => setClients((await response.json()).clients ?? []));
    fetch("/api/admin/parent-galleries", { credentials: "same-origin" }).then(async (response) => setGalleries((await response.json()).parent_galleries ?? []));
  }
  function refreshPhotos(galleryId: string) {
    if (!galleryId) { setPhotos([]); return; }
    fetch(`/api/admin/parent-galleries/${galleryId}/photos`, { credentials: "same-origin" }).then(async (response) => setPhotos((await response.json()).photos ?? []));
  }
  useEffect(() => { fetch("/api/admin", { credentials: "same-origin" }).then((response) => { setAuthorized(response.ok); if (response.ok) refresh(); }).catch(() => setAuthorized(false)); }, []);

  async function submit(path: string, payload: object, event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const response = await fetch(`/api${path}`, { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    setMessage(response.ok ? "Salvo com sucesso." : "Não foi possível salvar. Confira os dados.");
    if (response.ok) refresh();
  }
  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const file = data.get("jpeg");
    const selectedParentId = String(data.get("parent") || "");
    if (!(file instanceof File) || !file.size) { setMessage("Escolha um JPEG."); return; }
    const key = `uploads/${Date.now()}-${file.name.replace(/[^a-zA-Z0-9._-]/g, "-")}`;
    const registered = await fetch(`/api/admin/parent-galleries/${selectedParentId}/photos`, { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ filename: file.name, storage_key: key }) });
    if (!registered.ok) { setMessage("Não foi possível registrar a foto."); return; }
    const { id } = await registered.json();
    const imported = await fetch(`/api/admin/photo-assets/${id}/source`, { method: "PUT", credentials: "same-origin", headers: { "Content-Type": "image/jpeg" }, body: file });
    if (!imported.ok) { setMessage("O JPEG não pôde ser importado."); return; }
    event.currentTarget.reset();
    setParentId(selectedParentId);
    refreshPhotos(selectedParentId);
    setMessage("JPEG recebido. As prévias estão sendo processadas.");
    setUploadStatus("queued");
    const timer = window.setInterval(async () => {
      const status = await fetch(`/api/admin/photo-assets/${id}/media-status`, { credentials: "same-origin" });
      if (!status.ok) return;
      const result = await status.json();
      setUploadStatus(result.status);
      if (result.status === "completed" || result.status === "failed") window.clearInterval(timer);
    }, 1500);
  }

  if (authorized === null) return <main className="admin-shell">Carregando operação…</main>;
  if (!authorized) return <main className="admin-shell"><h1>Acesso restrito</h1><Link href="/">Voltar para entrada</Link></main>;
  return <main className="admin-shell"><p className="eyebrow">Markina Gallery · Fotógrafo</p><h1>Nova galeria privada</h1><p className="intro">Cada etapa consulta e grava apenas no backend autorizado.</p><section className="admin-card"><h2>1. Cliente</h2><form className="auth-form" onSubmit={(event) => { const data = new FormData(event.currentTarget); submit("/admin/clients", { full_name: data.get("name"), phone_e164: data.get("phone") }, event); }}><label>Nome completo<input name="name" required /></label><label>WhatsApp internacional<input name="phone" placeholder="+55 11 99999-9999" required /></label><button className="primary">Cadastrar cliente</button></form></section><section className="admin-card"><h2>2. Acervo-mãe</h2><form className="auth-form" onSubmit={(event) => { const data = new FormData(event.currentTarget); submit("/admin/parent-galleries", { name: data.get("name"), event_name: data.get("event") }, event); }}><label>Nome do acervo<input name="name" required /></label><label>Evento<input name="event" /></label><button className="primary">Criar acervo</button></form></section><section className="admin-card"><h2>3. Importar JPEG</h2><form className="auth-form" onSubmit={upload}><label>Acervo<select name="parent" required><option value="">Selecione</option>{galleries.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label>Arquivo JPEG<input name="jpeg" type="file" accept="image/jpeg" required /></label><button className="primary">Enviar para processamento</button></form>{uploadStatus && <p className="form-message" role="status">Processamento: {uploadStatus}</p>}</section><section className="admin-card"><h2>4. Galeria do cliente</h2><form className="auth-form" onSubmit={(event) => { const data = new FormData(event.currentTarget); submit("/admin/derived-galleries", { parent_gallery_id: parentId, client_id: data.get("client"), name: data.get("name"), photo_ids: Array.from(event.currentTarget.querySelectorAll<HTMLInputElement>('input[name="photo"]:checked')).map((input) => input.value), custom_message: data.get("message") || null, favorites_enabled: data.get("favorites") === "on", comments_enabled: data.get("comments") === "on" }, event); }}><label>Cliente<select name="client" required><option value="">Selecione</option>{clients.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label>Acervo<select value={parentId} onChange={(event) => { setParentId(event.target.value); refreshPhotos(event.target.value); }} required><option value="">Selecione</option>{galleries.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label>Nome da galeria<input name="name" required /></label><label>Mensagem ao cliente<input name="message" /></label><fieldset><legend>Fotos atribuídas</legend>{photos.length ? photos.map((item) => <label key={item.id}><input type="checkbox" name="photo" value={item.id} /> {item.name}</label>) : <p className="form-message">Selecione um acervo com fotos cadastradas.</p>}</fieldset><label><input type="checkbox" name="favorites" /> Permitir favoritos</label><label><input type="checkbox" name="comments" /> Permitir comentários</label><button className="primary" disabled={!photos.length}>Criar galeria privada</button></form></section>{message && <p className="form-message" role="status">{message}</p>}</main>;
}
