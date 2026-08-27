"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { StatusBadge, SystemState } from "../../../../ui-kit";

type ClientRow = { client_id: string; name: string; phone: string; registration_status: string | null; derived_gallery_id: string | null };
type Folder = { id: string; name: string; status: string; photo_count: number };
type Summary = { name: string; event_name: string; active: boolean; unlisted_link: string; cover_preview_url: string | null; counts: { folders: number; photos: number; clients: number }; clients: ClientRow[] };

export default function SourceGalleryDetailPage() {
  const { sourceId } = useParams<{ sourceId: string }>();
  const router = useRouter();
  const [folders, setFolders] = useState<Folder[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [failed, setFailed] = useState(false);
  const [copied, setCopied] = useState(false);
  const [message, setMessage] = useState("");
  const linkInput = useRef<HTMLInputElement>(null);

  async function copyUnlistedLink() {
    if (!summary) return;
    try {
      await navigator.clipboard.writeText(summary.unlisted_link);
      setCopied(true);
    } catch {
      linkInput.current?.select();
      setCopied(false);
    }
  }

  async function deleteGallery() {
    if (!window.confirm("Excluir esta galeria do evento? A ação só é permitida enquanto não houver pastas, fotos ou responsáveis vinculados.")) return;
    const response = await fetch(`/api/admin/parent-galleries/${sourceId}`, {
      method: "DELETE",
      credentials: "same-origin",
    });
    if (response.ok) {
      router.push("/admin/galleries");
      return;
    }
    const payload = await response.json().catch(() => null);
    setMessage(payload?.detail ?? "Não foi possível excluir a galeria.");
  }
  useEffect(() => {
    Promise.all([
      fetch(`/api/admin/parent-galleries/${sourceId}/folders`, { credentials: "same-origin" }),
      fetch(`/api/admin/parent-galleries/${sourceId}/summary`, { credentials: "same-origin" }),
    ]).then(async ([folderResponse, summaryResponse]) => {
      if (!folderResponse.ok || !summaryResponse.ok) throw new Error();
      setFolders((await folderResponse.json()).folders ?? []);
      setSummary(await summaryResponse.json());
    }).catch(() => setFailed(true));
  }, [sourceId]);
  if (failed) return <SystemState tone="error" title="Galeria indisponível" detail="Não foi possível consultar seus dados agora." />;
  if (!summary) return <SystemState tone="loading" title="Carregando galeria" detail="Consultando clientes e pastas vinculadas." />;
  return (
    <main className="admin-shell">
      <Link href="/admin/galleries">← Galerias</Link>
      <p className="eyebrow">Galeria do evento · link não listado</p>
      <h1>{summary.name}</h1>
      <p className="intro">{summary.event_name || "Evento sem nome"}. Somente clientes autenticadas e vinculadas recebem pastas liberadas.</p>
      <div className="action-grid"><Link className="mk-button mk-button--primary" href={`/admin/galleries/sources/${sourceId}/edit/ajustes`}>Editar galeria</Link><Link className="mk-button mk-button--secondary" href={`/admin/galleries/sources/${sourceId}/edit/imagens`}>Abrir imagens</Link><button type="button" className="mk-button mk-button--danger" onClick={deleteGallery}>Excluir galeria vazia</button></div>
      <section className="admin-card"><div className="source-summary"><div className="source-summary-cover">{summary.cover_preview_url ? <img src={`/api${summary.cover_preview_url}`} alt="Capa protegida da galeria" /> : "Sem capa definida"}</div><div><h2>Resumo da galeria</h2><p>{summary.counts.folders} pastas · {summary.counts.photos} fotos · {summary.counts.clients} responsáveis vinculados</p><label>Link para compartilhar<input ref={linkInput} readOnly value={summary.unlisted_link} /></label><button type="button" className="secondary" onClick={copyUnlistedLink}>{copied ? "Link copiado" : "Copiar link"}</button></div></div></section>
      <section className="admin-card"><h2>Pastas</h2>{folders.length ? <div className="dashboard-recent">{folders.map((folder) => <div key={folder.id}><div><strong>{folder.name}</strong><small>{folder.photo_count} foto(s)</small></div><StatusBadge tone={folder.status === "released" ? "success" : "warning"}>{folder.status === "released" ? "Liberada" : "Em preparação"}</StatusBadge></div>)}</div> : <SystemState title="Nenhuma pasta" detail="Abra a etapa Imagens para criar a primeira pasta desta galeria." />}</section>
      <section className="admin-card"><h2>Clientes vinculadas</h2>{summary.clients.length ? <div className="dashboard-recent">{summary.clients.map((person) => <div key={person.client_id}><div><strong>{person.name}</strong><small>{person.phone}</small></div>{person.derived_gallery_id ? <Link href={`/admin/galleries/${person.derived_gallery_id}`}>Abrir galeria privada</Link> : <StatusBadge tone="warning">Cadastro pendente</StatusBadge>}</div>)}</div> : <SystemState title="Nenhuma cliente vinculada" detail="O vínculo pode nascer pelo login no link ou pela etapa Clientes." />}</section>
      {message ? <p className="notice" role="alert">{message}</p> : null}
    </main>
  );
}
