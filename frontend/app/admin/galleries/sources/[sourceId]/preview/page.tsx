"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { galleryFontFamily } from "../../../../../gallery-fonts";
import { GalleryPresentation, type GalleryPresentationFolder } from "../../../../../gallery-presentation";
import { MarkinaLink, SystemState } from "../../../../../ui-kit";
import styles from "./preview.module.css";

type Folder = { id: string; name: string; photo_count: number; preview_url: string | null; position: number };
type Photo = { id: string; name: string; preview_url: string | null; width: number | null; height: number | null };
type Gallery = {
  name: string;
  cover_preview_url: string | null;
  folder_display_mode: "individual" | "sequential";
  cover_title_color: string;
  cover_title_size: number;
  cover_title_font: string;
  cover_title_position: string;
};
type Preview = {
  gallery: Gallery;
  folders: Array<Folder & { photos: Photo[] }>;
  partial: boolean;
};

export default function AdminGalleryPreviewPage() {
  const { sourceId } = useParams<{ sourceId: string }>();
  const [result, setResult] = useState<{ sourceId: string; preview: Preview | null } | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    const init = { credentials: "same-origin", signal: controller.signal } as const;
    Promise.all([
      fetch(`/api/admin/parent-galleries/${sourceId}/editor`, init),
      fetch(`/api/admin/parent-galleries/${sourceId}/folders`, init),
    ]).then(async ([editorResponse, folderResponse]) => {
      if (!editorResponse.ok || !folderResponse.ok) throw new Error();
      const { gallery } = await editorResponse.json() as { gallery: Gallery };
      const { folders = [] } = await folderResponse.json() as { folders?: Folder[] };
      const rows = await Promise.allSettled(folders.map(async (folder) => {
        const response = await fetch(`/api/admin/photo-folders/${folder.id}/photos`, init);
        if (!response.ok) throw new Error();
        const { photos = [] } = await response.json() as { photos?: Photo[] };
        return { ...folder, photos };
      }));
      if (controller.signal.aborted) return;
      setResult({ sourceId, preview: {
        gallery,
        folders: rows.map((row, index) => row.status === "fulfilled" ? row.value : { ...folders[index], photos: [] }),
        partial: rows.some((row) => row.status === "rejected"),
      } });
    }).catch(() => {
      if (!controller.signal.aborted) setResult({ sourceId, preview: null });
    });
    return () => controller.abort();
  }, [sourceId]);

  const current = result?.sourceId === sourceId ? result : null;
  const preview = current?.preview;
  const presentationFolders: GalleryPresentationFolder[] = preview?.folders.map((folder) => ({
    id: folder.id,
    name: folder.name,
    photos: folder.photos.filter((photo) => photo.preview_url).map((photo) => ({
      id: photo.id,
      name: photo.name,
      previewUrl: `/api${photo.preview_url}`,
      width: photo.width,
      height: photo.height,
    })),
  })) ?? [];

  return <div className={styles.page}>
    <nav className={styles.actions} aria-label="Ações da prévia">
      <MarkinaLink href={`/admin/galleries/sources/${sourceId}`} variant="quiet"><span aria-hidden="true">←</span> Resumo da galeria</MarkinaLink>
      <MarkinaLink href={`/admin/galleries/sources/${sourceId}/edit/detalhes`} variant="secondary">Editar apresentação</MarkinaLink>
    </nav>
    {!current ? <SystemState tone="loading" title="Carregando prévia" detail="Consultando a capa e as pastas da galeria." />
      : !preview ? <SystemState tone="error" title="Prévia indisponível" detail="Não foi possível abrir a visualização desta galeria." /> : <>
      {preview.partial && <SystemState tone="error" title="Prévia parcial" detail="Algumas pastas não puderam ser consultadas. Recarregue a página para tentar novamente." />}
      <GalleryPresentation
        galleryName={preview.gallery.name}
        coverUrl={preview.gallery.cover_preview_url ? `/api${preview.gallery.cover_preview_url}` : null}
        folders={presentationFolders}
        folderDisplayMode={preview.gallery.folder_display_mode === "sequential" ? "sequential" : "individual"}
        titleStyle={{ color: preview.gallery.cover_title_color, fontSize: preview.gallery.cover_title_size, fontFamily: galleryFontFamily(preview.gallery.cover_title_font), position: preview.gallery.cover_title_position }}
        modeLabel={<><strong>Modo fotógrafo</strong><span>Prévia administrativa com prévias protegidas; a cliente vê somente o conteúdo liberado após autenticação.</span></>}
        emptyDetail="Crie uma pasta e conclua o processamento das fotos para revisar a apresentação da galeria."
      />
    </>}
  </div>;
}
