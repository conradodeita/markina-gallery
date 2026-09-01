"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { galleryFontFamily } from "../../../../../gallery-fonts";
import { GalleryPresentation, type GalleryPresentationFolder } from "../../../../../gallery-presentation";

type Folder = { id: string; name: string; photo_count: number; preview_url: string | null; position: number };
type Photo = { id: string; name: string; preview_url: string | null; width: number | null; height: number | null };

export default function AdminGalleryPreviewPage() {
  const { sourceId } = useParams<{ sourceId: string }>();
  const [name, setName] = useState("Galeria");
  const [cover, setCover] = useState<string | null>(null);
  const [folders, setFolders] = useState<Array<Folder & { photos: Photo[] }>>([]);
  const [folderDisplayMode, setFolderDisplayMode] = useState<"individual" | "sequential">("individual");
  const [titleStyle, setTitleStyle] = useState({ color: "#FFFFFF", fontSize: 32, fontFamily: "sans-serif", position: "bottom-left" });
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
      setFolderDisplayMode(editor.gallery.folder_display_mode === "sequential" ? "sequential" : "individual");
      setTitleStyle({ color: editor.gallery.cover_title_color, fontSize: editor.gallery.cover_title_size, fontFamily: editor.gallery.cover_title_font, position: editor.gallery.cover_title_position });
      const rows = await Promise.all((folderData.folders ?? []).map(async (folder: Folder) => {
        const response = await fetch(`/api/admin/photo-folders/${folder.id}/photos`, { credentials: "same-origin" });
        const data = response.ok ? await response.json() : { photos: [] };
        return { ...folder, photos: data.photos ?? [] };
      }));
      setFolders(rows);
    }).catch(() => setFailed(true));
  }, [sourceId]);

  if (failed) return <main className="admin-shell"><p className="notice">Não foi possível abrir a visualização desta galeria.</p></main>;
  const presentationFolders: GalleryPresentationFolder[] = folders.map((folder) => ({ id: folder.id, name: folder.name, photos: folder.photos.filter((photo) => photo.preview_url).map((photo) => ({ id: photo.id, name: photo.name, previewUrl: `/api${photo.preview_url}`, width: photo.width, height: photo.height })) }));
  return <main className="admin-shell gallery-preview-page"><Link href={`/admin/galleries/sources/${sourceId}`}>← Resumo da galeria</Link><GalleryPresentation galleryName={name} coverUrl={cover ? `/api${cover}` : null} folders={presentationFolders} folderDisplayMode={folderDisplayMode} titleStyle={{ color: titleStyle.color, fontSize: titleStyle.fontSize, fontFamily: galleryFontFamily(titleStyle.fontFamily), position: titleStyle.position }} modeLabel={<><strong>Modo fotógrafo</strong><span>Prévia administrativa com prévias protegidas; a cliente vê somente o conteúdo liberado após autenticação.</span></>} emptyDetail="Crie uma pasta e conclua o processamento das fotos para revisar a apresentação da galeria." /></main>;
}
