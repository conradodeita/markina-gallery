"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { MarkinaButton, PageHeading, StatusBadge, SystemState } from "../../ui-kit";

type PublicGallery = { id: string; name: string; event_name: string | null; description: string | null; access_mode: "standard" | "invite_only" | "collective_protected"; photos_url: string };
type PublicPhoto = { id: string; name: string; preview_url: string };

export default function PublicGalleryPage() {
  const { galleryId } = useParams<{ galleryId: string }>();
  const [gallery, setGallery] = useState<PublicGallery | null>(null);
  const [photos, setPhotos] = useState<PublicPhoto[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [privateGalleryId, setPrivateGalleryId] = useState<string | null>(null);
  const [selectingId, setSelectingId] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    Promise.all([
      fetch(`/api/public-galleries/${galleryId}`, { credentials: "same-origin" }),
      fetch(`/api/public-galleries/${galleryId}/photos`, { credentials: "same-origin" }),
    ]).then(async ([galleryResponse, photosResponse]) => {
      if (!galleryResponse.ok || !photosResponse.ok) throw new Error();
      setGallery(await galleryResponse.json());
      setPhotos((await photosResponse.json()).photos ?? []);
    }).catch(() => setFailed(true));
  }, [galleryId]);

  async function selectPhoto(photo: PublicPhoto) {
    if (selectingId || selectedIds.includes(photo.id)) return;
    setSelectingId(photo.id);
    setMessage("");
    try {
      const response = await fetch(`/api/public-galleries/${galleryId}/photos/${photo.id}/selection`, {
        method: "POST",
        credentials: "same-origin",
      });
      const payload = await response.json().catch(() => null);
      if (!response.ok) throw new Error(payload?.detail ?? "Não foi possível selecionar esta foto.");
      setSelectedIds((current) => [...current, photo.id]);
      setPrivateGalleryId(payload.private_gallery_id);
      setMessage(payload.gallery_created ? "Sua galeria privada foi criada com esta seleção." : "A foto foi adicionada à sua galeria privada.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível selecionar esta foto.");
    } finally {
      setSelectingId(null);
    }
  }

  if (failed) return <main className="admin-shell"><SystemState tone="error" title="Galeria indisponível" detail="Seu acesso não permite abrir esta grade ou a Galeria pública não está mais disponível." /><Link href="/library">Voltar à biblioteca</Link></main>;
  if (!gallery) return <SystemState tone="loading" title="Abrindo Galeria pública" detail="Confirmando seu acesso antes de carregar qualquer prévia." />;

  return (
    <main className="admin-shell public-gallery-shell">
      <Link href="/library">← Sua biblioteca</Link>
      <PageHeading eyebrow="Galeria pública autorizada" title={gallery.name} detail={gallery.description || gallery.event_name || "Escolha suas fotos para criar ou ampliar sua galeria privada."} actions={<StatusBadge tone="success">Acesso confirmado</StatusBadge>} />
      {privateGalleryId ? <div className="public-selection-result" role="status"><span>{message}</span><Link href={`/gallery/${privateGalleryId}`}>Abrir minha galeria privada</Link></div> : message ? <p className="notice" role="alert">{message}</p> : null}
      {photos.length ? <section className="public-photo-grid" aria-label="Fotos disponíveis nesta Galeria pública">{photos.map((photo) => {
        const selected = selectedIds.includes(photo.id);
        return <article key={photo.id}><img src={`/api${photo.preview_url}`} alt={`Prévia protegida de ${photo.name}`} draggable={false} onContextMenu={(event) => event.preventDefault()} /><div><strong>{photo.name}</strong><MarkinaButton type="button" disabled={selected || Boolean(selectingId)} onClick={() => selectPhoto(photo)}>{selectingId === photo.id ? "Selecionando…" : selected ? "Selecionada" : "Selecionar foto"}</MarkinaButton></div></article>;
      })}</section> : <SystemState title="Nenhuma foto liberada" detail="Esta Galeria pública está autorizada, mas ainda não possui fotos disponíveis para escolha." />}
    </main>
  );
}
