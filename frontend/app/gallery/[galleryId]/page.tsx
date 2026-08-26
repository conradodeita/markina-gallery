"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

import { ProtectedPhoto, ProtectedPhotoViewer } from "../../protected-photo-viewer";

export default function GalleryPage() {
  const { galleryId } = useParams<{ galleryId: string }>();
  const [photos, setPhotos] = useState<ProtectedPhoto[] | null>(null);

  useEffect(() => {
    fetch(`/api/gallery/${galleryId}/photos`, { credentials: "same-origin" })
      .then(async (response) => {
        if (!response.ok) throw new Error();
        const result = await response.json();
        setPhotos(result.photos.map((photo: { id: string; name: string; preview_url: string }) => ({ ...photo, previewUrl: photo.preview_url })));
      })
      .catch(() => setPhotos([]));
  }, [galleryId]);

  if (photos === null) return <main className="admin-shell">Carregando galeria…</main>;
  if (!photos.length) return <main className="admin-shell"><h1>Galeria indisponível</h1><p className="intro">Verifique se o acesso está ativo ou tente novamente mais tarde.</p></main>;
  return <main className="admin-shell"><p className="eyebrow">Markina Gallery · Galeria privada</p><h1>Suas fotos</h1><ProtectedPhotoViewer label="Prévia da foto selecionada" photos={photos} /></main>;
}
