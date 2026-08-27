"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { StatusBadge, SystemState } from "../../../../ui-kit";

type ClientRow = { client_id: string; name: string; phone: string; registration_status: string | null; derived_gallery_id: string | null };
type Folder = { id: string; name: string; status: string; photo_count: number };
type Editor = { gallery: { name: string; event_name: string; description: string; active: boolean; unlisted_link: string } };

export default function SourceGalleryDetailPage() {
  const { sourceId } = useParams<{ sourceId: string }>();
  const [clients, setClients] = useState<ClientRow[] | null>(null);
  const [folders, setFolders] = useState<Folder[]>([]);
  const [editor, setEditor] = useState<Editor | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    Promise.all([
      fetch(`/api/admin/parent-galleries/${sourceId}/clients`, { credentials: "same-origin" }),
      fetch(`/api/admin/parent-galleries/${sourceId}/folders`, { credentials: "same-origin" }),
      fetch(`/api/admin/parent-galleries/${sourceId}/editor`, { credentials: "same-origin" }),
    ]).then(async ([clientResponse, folderResponse, editorResponse]) => {
      if (!clientResponse.ok || !folderResponse.ok || !editorResponse.ok) throw new Error();
      setClients((await clientResponse.json()).clients ?? []);
      setFolders((await folderResponse.json()).folders ?? []);
      setEditor(await editorResponse.json());
    }).catch(() => setFailed(true));
  }, [sourceId]);
  if (failed) return <SystemState tone="error" title="Galeria indisponível" detail="Não foi possível consultar seus dados agora." />;
  if (!clients || !editor) return <SystemState tone="loading" title="Carregando galeria" detail="Consultando clientes e pastas vinculadas." />;
  return (
    <main className="admin-shell">
      <Link href="/admin/galleries">← Galerias</Link>
      <p className="eyebrow">Galeria-mãe não listada</p>
      <h1>{editor.gallery.name}</h1>
      <p className="intro">{editor.gallery.event_name || "Evento sem nome"}. Somente clientes autenticadas e vinculadas recebem pastas liberadas.</p>
      <div className="action-grid"><Link className="mk-button mk-button--primary" href={`/admin/galleries/sources/${sourceId}/edit/ajustes`}>Editar galeria</Link><Link className="mk-button mk-button--secondary" href={`/admin/galleries/sources/${sourceId}/edit/imagens`}>Abrir imagens</Link></div>
      <section className="admin-card"><h2>Pastas</h2>{folders.length ? <div className="dashboard-recent">{folders.map((folder) => <div key={folder.id}><div><strong>{folder.name}</strong><small>{folder.photo_count} foto(s)</small></div><StatusBadge tone={folder.status === "released" ? "success" : "warning"}>{folder.status === "released" ? "Liberada" : "Em preparação"}</StatusBadge></div>)}</div> : <SystemState title="Nenhuma pasta" detail="Abra a etapa Imagens para criar a primeira pasta desta galeria." />}</section>
      <section className="admin-card"><h2>Clientes vinculadas</h2>{clients.length ? <div className="dashboard-recent">{clients.map((person) => <div key={person.client_id}><div><strong>{person.name}</strong><small>{person.phone}</small></div>{person.derived_gallery_id ? <Link href={`/admin/galleries/${person.derived_gallery_id}`}>Abrir galeria privada</Link> : <StatusBadge tone="warning">Cadastro pendente</StatusBadge>}</div>)}</div> : <SystemState title="Nenhuma cliente vinculada" detail="O vínculo pode nascer pelo login no link ou pela etapa Clientes." />}</section>
    </main>
  );
}
