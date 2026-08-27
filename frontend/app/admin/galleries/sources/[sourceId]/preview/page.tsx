"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

type Folder = { id: string; name: string; photo_count: number; preview_url: string | null; position: number };
type Photo = { id: string; name: string; preview_url: string | null };

export default function AdminGalleryPreviewPage() {
  const { sourceId } = useParams<{ sourceId: string }>();
  const [name, setName] = useState("Galeria");
  const [cover, setCover] = useState<string | null>(null);
  const [folders, setFolders] = useState<Array<Folder & { photos: Photo[] }>>([]);
  const [mode, setMode] = useState("individual");
  const [titleStyle, setTitleStyle] = useState({ color: "#FFFFFF", fontSize: 32, position: "bottom-left" });
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    Promise.all([
      fetch(`/api/admin/parent-galleries/${sourceId}/editor`, { credentials: "same-origin" }),
      fetch(`/api/admin/parent-galleries/${sourceId}/folders`, { credentials: "same-origin" }),
    ]).then(async ([editorResponse, folderResponse]) => {
      if (!editorResponse.ok || !folderResponse.ok) throw new Error();
      const editor = await editorResponse.json();
      const folderData = await folderResponse.json();
      setName(editor.gallery.name);
      setCover(editor.gallery.cover_preview_url);
      setMode(editor.gallery.folder_display_mode);
      setTitleStyle({ color: editor.gallery.cover_title_color, fontSize: editor.gallery.cover_title_size, position: editor.gallery.cover_title_position });
      const rows = await Promise.all((folderData.folders ?? []).map(async (folder: Folder) => {
        const response = await fetch(`/api/admin/photo-folders/${folder.id}/photos`, { credentials: "same-origin" });
        const data = response.ok ? await response.json() : { photos: [] };
        return { ...folder, photos: data.photos ?? [] };
      }));
      setFolders(rows);
    }).catch(() => setFailed(true));
  }, [sourceId]);

  if (failed) return <main className="admin-shell"><p className="notice">Não foi possível abrir a visualização desta galeria.</p></main>;
  const positionClass = `title-${titleStyle.position}`;
  return <main className="admin-shell gallery-preview-page"><Link href={`/admin/galleries/sources/${sourceId}`}>← Resumo da galeria</Link><div className="admin-preview-warning" role="status"><strong>Modo fotógrafo</strong><span>Esta é uma visualização administrativa com prévias protegidas. O cliente verá apenas o conteúdo liberado após autenticação.</span></div><section className="gallery-preview-hero">{cover ? <img src={`/api${cover}`} alt={`Capa de ${name}`} /> : <div>Sem capa definida</div>}<h1 className={positionClass} style={{ color: titleStyle.color, fontSize: `${titleStyle.fontSize}px` }}>{name}</h1></section>{mode === "sequential" ? folders.map((folder) => <section className="gallery-preview-folder" key={folder.id}><h2>{folder.name}</h2><div className="folder-photo-grid">{folder.photos.map((photo) => photo.preview_url ? <figure key={photo.id}><img src={`/api${photo.preview_url}`} alt={photo.name} /><figcaption>{photo.name}</figcaption></figure> : null)}</div></section>) : <div className="gallery-preview-folder-grid">{folders.map((folder) => <section className="gallery-preview-folder" key={folder.id}><h2>{folder.name}</h2><p>{folder.photo_count} foto(s)</p>{folder.preview_url ? <img src={`/api${folder.preview_url}`} alt={`Prévia da pasta ${folder.name}`} /> : null}</section>)}</div>}</main>;
}
