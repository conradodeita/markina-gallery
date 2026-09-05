"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { galleryFontFamily } from "../../gallery-fonts";
import { GalleryPresentation, type GalleryPresentationFolder } from "../../gallery-presentation";
import { SystemState } from "../../ui-kit";

type PublicGallery = { id: string; name: string; event_name: string | null; description: string | null; access_mode: "standard" | "invite_only" | "collective_protected"; photos_url: string; folder_display_mode: "individual" | "sequential"; cover_preview_url: string | null; cover_title_font: string; cover_title_color: string; cover_title_size: number; cover_title_position: string };
type PublicPhoto = { id: string; name: string; preview_url: string; folder_id: string; folder_name: string; folder_position: number; width: number | null; height: number | null; selected: boolean; previewUrl: string };
type Cart = {
  quantity: number;
  total_cents?: number;
  savings_cents?: number;
  pricing_error?: string;
  items?: Array<{ id: string; name: string }>;
};

export default function PublicGalleryPage() {
  const { galleryId } = useParams<{ galleryId: string }>();
  const [gallery, setGallery] = useState<PublicGallery | null>(null);
  const [photos, setPhotos] = useState<PublicPhoto[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [privateGalleryId, setPrivateGalleryId] = useState<string | null>(null);
  const [cart, setCart] = useState<Cart>({ quantity: 0, items: [] });
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
      const result = await photosResponse.json();
      setSelectedIds((result.photos ?? []).filter((photo: PublicPhoto) => photo.selected).map((photo: PublicPhoto) => photo.id));
      setPrivateGalleryId(result.private_gallery_id ?? null);
      setCart(result.cart ?? { quantity: 0, items: [] });
      setPhotos((result.photos ?? []).map((photo: Omit<PublicPhoto, "previewUrl">) => ({
        ...photo,
        folder_id: photo.folder_id ?? "public-photos",
        folder_name: photo.folder_name ?? "Fotos disponíveis",
        folder_position: photo.folder_position ?? 0,
        width: photo.width ?? null,
        height: photo.height ?? null,
        previewUrl: `/api${photo.preview_url}`,
      })));
    }).catch(() => setFailed(true));
  }, [galleryId]);

  async function toggleSelection(photo: PublicPhoto) {
    if (selectingId) return;
    const selected = selectedIds.includes(photo.id);
    setSelectingId(photo.id);
    setMessage("");
    try {
      const response = await fetch(`/api/public-galleries/${galleryId}/photos/${photo.id}/selection`, {
        method: selected ? "DELETE" : "POST",
        credentials: "same-origin",
      });
      const payload = await response.json().catch(() => null);
      if (!response.ok) throw new Error(payload?.detail ?? "Não foi possível selecionar esta foto.");
      setSelectedIds((current) => selected
        ? current.filter((id) => id !== photo.id)
        : current.includes(photo.id) ? current : [...current, photo.id]);
      setPrivateGalleryId(payload.private_gallery_id ?? null);
      setCart(payload.cart ?? { quantity: selected ? Math.max(0, cart.quantity - 1) : cart.quantity + 1, items: [] });
      setMessage(selected
        ? "A foto foi removida da sua seleção."
        : payload.gallery_created ? "Sua seleção foi iniciada e ficará salva nesta galeria." : "A foto foi adicionada à sua seleção.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível selecionar esta foto.");
    } finally {
      setSelectingId(null);
    }
  }

  if (failed) return <main className="admin-shell"><SystemState tone="error" title="Galeria indisponível" detail="Seu acesso não permite abrir esta grade ou a Galeria pública não está mais disponível." /><Link href="/library">Voltar à biblioteca</Link></main>;
  if (!gallery) return <SystemState tone="loading" title="Abrindo Galeria pública" detail="Confirmando seu acesso antes de carregar qualquer prévia." />;

  const folders = [...photos.reduce((grouped, photo) => {
    const folder = grouped.get(photo.folder_id) ?? { id: photo.folder_id, name: photo.folder_name, position: photo.folder_position, photos: [] as PublicPhoto[] };
    folder.photos.push(photo);
    grouped.set(photo.folder_id, folder);
    return grouped;
  }, new Map<string, { id: string; name: string; position: number; photos: PublicPhoto[] }>()).values()]
    .sort((left, right) => left.position - right.position)
    .map(({ id, name, photos: folderPhotos }) => ({ id, name, photos: folderPhotos })) as GalleryPresentationFolder<PublicPhoto>[];

  return (
    <main className="admin-shell public-gallery-shell">
      <Link href="/library">← Sua biblioteca</Link>
      {privateGalleryId && message ? <div className="public-selection-result" role="status"><span>{message}</span><Link href={`/gallery/${privateGalleryId}`}>Revisar seleção</Link></div> : message ? <p className="notice" role="alert">{message}</p> : null}
      <GalleryPresentation galleryName={gallery.name} eyebrow="Galeria pública autorizada" context={<p>{gallery.description || gallery.event_name || "Escolha suas fotos e retome sua seleção nesta mesma galeria quando quiser."}</p>} coverUrl={gallery.cover_preview_url ? `/api${gallery.cover_preview_url}` : null} folders={folders} folderDisplayMode={gallery.folder_display_mode ?? "individual"} titleStyle={{ color: gallery.cover_title_color, fontFamily: galleryFontFamily(gallery.cover_title_font), fontSize: gallery.cover_title_size, position: gallery.cover_title_position }} modeLabel={<><strong>Acesso confirmado</strong><span>Suas escolhas ficam salvas nesta galeria e permanecem disponíveis quando você voltar.</span></>} emptyDetail="Esta Galeria pública está autorizada, mas ainda não possui fotos disponíveis para escolha." renderPhotoMarkers={(photo) => {
        const selected = selectedIds.includes(photo.id);
        return <button type="button" className="gallery-presentation-marker" aria-pressed={selected} disabled={Boolean(selectingId)} onClick={() => toggleSelection(photo)}>{selectingId === photo.id ? (selected ? "Desmarcando…" : "Selecionando…") : selected ? "✓ Desmarcar" : "Selecionar foto"}</button>;
      }} />
      {cart.quantity > 0 ? <aside className="selection-summary selection-summary--floating" aria-live="polite" aria-label="Resumo da seleção">
        <div><span>Sua seleção</span><strong>{cart.quantity} foto{cart.quantity === 1 ? "" : "s"}</strong></div>
        <div className="selection-summary__commercial"><span>Total <strong>{cart.total_cents !== undefined ? (cart.total_cents / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" }) : "A calcular"}</strong></span>{cart.savings_cents ? <span className="selection-summary__savings">Você economiza {(cart.savings_cents / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}</span> : null}</div>
        {cart.pricing_error ? <p className="notice">{cart.pricing_error}</p> : null}
        {privateGalleryId ? <Link className="primary" href={`/gallery/${privateGalleryId}`}>Revisar seleção</Link> : null}
      </aside> : null}
    </main>
  );
}
