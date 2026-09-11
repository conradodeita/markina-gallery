"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { ClientCartLink } from "../../client-cart";
import { facialSearchApi, type FacialSearchResult } from "../../facial-search-client";
import { galleryFontFamily } from "../../gallery-fonts";
import { GalleryPresentation, type GalleryPresentationFolder } from "../../gallery-presentation";
import { SystemState } from "../../ui-kit";
import { FacialSearchPanel } from "../facial-search-panel";

type PublicGallery = { id: string; name: string; event_name: string | null; description: string | null; access_mode: "standard" | "invite_only" | "collective_protected"; photos_url: string; favorites_enabled: boolean; folder_display_mode: "individual" | "sequential"; cover_preview_url: string | null; cover_title_font: string; cover_title_color: string; cover_title_size: number; cover_title_position: string; private_gallery_id?: string | null };
type CommercialState = "available" | "selected" | "awaiting_payment" | "payment_reported" | "purchased";
type PublicPhoto = { id: string; name: string; preview_url: string; folder_id: string; folder_name: string; folder_position: number; width: number | null; height: number | null; selected: boolean; favorited: boolean; commercial_state?: CommercialState; previewUrl: string };
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
  const [favoriteIds, setFavoriteIds] = useState<string[]>([]);
  const [privateGalleryId, setPrivateGalleryId] = useState<string | null>(null);
  const [cart, setCart] = useState<Cart>({ quantity: 0, items: [] });
  const [selectingId, setSelectingId] = useState<string | null>(null);
  const [failedGalleryId, setFailedGalleryId] = useState<string | null>(null);
  const [photoLoad, setPhotoLoad] = useState<{ galleryId: string; status: "loading" | "ready" | "failed" }>({ galleryId, status: "loading" });
  const [message, setMessage] = useState("");
  const [facialResult, setFacialResult] = useState<FacialSearchResult | null>(null);

  useEffect(() => {
    let active = true;

    fetch(`/api/public-galleries/${galleryId}`, { credentials: "same-origin" })
      .then(async (response) => {
        if (!response.ok) throw new Error();
        const result = await response.json() as PublicGallery;
        if (!active) return;
        setGallery(result);
        setFailedGalleryId(null);
        setPrivateGalleryId(result.private_gallery_id ?? null);
      })
      .catch(() => { if (active) setFailedGalleryId(galleryId); });

    fetch(`/api/public-galleries/${galleryId}/photos`, { credentials: "same-origin" })
      .then(async (response) => {
        if (!response.ok) throw new Error();
        const result = await response.json();
        if (!active) return;
        setSelectedIds((result.photos ?? []).filter((photo: PublicPhoto) => photo.selected).map((photo: PublicPhoto) => photo.id));
        setFavoriteIds((result.photos ?? []).filter((photo: PublicPhoto) => photo.favorited).map((photo: PublicPhoto) => photo.id));
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
        setPhotoLoad({ galleryId, status: "ready" });
      })
      .catch(() => {
        if (!active) return;
        setPhotoLoad({ galleryId, status: "failed" });
      });

    return () => { active = false; };
  }, [galleryId]);

  async function toggleSelection(photo: PublicPhoto, fromFacial = false) {
    if (selectingId) return;
    const selected = selectedIds.includes(photo.id);
    if (!selected && photo.commercial_state && !["available", "selected"].includes(photo.commercial_state)) return;
    setSelectingId(photo.id);
    setMessage("");
    try {
      const path = fromFacial && facialResult && !selected
        ? `/api/public-galleries/${galleryId}/facial-searches/${facialResult.id}/candidates/${photo.id}/selection`
        : `/api/public-galleries/${galleryId}/photos/${photo.id}/selection`;
      const response = await fetch(path, {
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

  async function toggleFavorite(photo: PublicPhoto) {
    if (!privateGalleryId || selectingId) return;
    const favorited = favoriteIds.includes(photo.id);
    setSelectingId(photo.id);
    setMessage("");
    try {
      const response = await fetch(`/api/gallery/${privateGalleryId}/photos/${photo.id}/favorite`, {
        method: favorited ? "DELETE" : "POST",
        credentials: "same-origin",
      });
      const payload = await response.json().catch(() => null);
      if (!response.ok) throw new Error(payload?.detail ?? "Não foi possível atualizar o favorito.");
      setFavoriteIds((current) => favorited
        ? current.filter((id) => id !== photo.id)
        : current.includes(photo.id) ? current : [...current, photo.id]);
      setMessage(favorited ? "A foto saiu dos favoritos." : "A foto foi adicionada aos favoritos.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível atualizar o favorito.");
    } finally {
      setSelectingId(null);
    }
  }

  if (failedGalleryId === galleryId) return <main className="admin-shell"><SystemState tone="error" title="Galeria indisponível" detail="Seu acesso não permite abrir esta grade ou a Galeria pública não está mais disponível." /><Link href="/library">Voltar à biblioteca</Link></main>;
  if (!gallery || gallery.id !== galleryId) return <SystemState tone="loading" title="Abrindo Galeria pública" detail="Confirmando seu acesso antes de carregar qualquer prévia." />;

  const photosLoading = photoLoad.galleryId !== galleryId || photoLoad.status === "loading";
  const photosFailed = photoLoad.galleryId === galleryId && photoLoad.status === "failed";

  const folders = [...photos.reduce((grouped, photo) => {
    const folder = grouped.get(photo.folder_id) ?? { id: photo.folder_id, name: photo.folder_name, position: photo.folder_position, photos: [] as PublicPhoto[] };
    folder.photos.push(photo);
    grouped.set(photo.folder_id, folder);
    return grouped;
  }, new Map<string, { id: string; name: string; position: number; photos: PublicPhoto[] }>()).values()]
    .sort((left, right) => left.position - right.position)
    .map(({ id, name, photos: folderPhotos }) => ({ id, name, photos: folderPhotos })) as GalleryPresentationFolder<PublicPhoto>[];
  const candidateByPhoto = (facialResult?.candidates ?? []).reduce((unique, candidate) => {
    const current = unique.get(candidate.photo_id);
    if (!current || candidate.rank < current.rank) unique.set(candidate.photo_id, candidate);
    return unique;
  }, new Map<string, NonNullable<FacialSearchResult["candidates"]>[number]>());
  const candidatePhotos = photos
    .filter((photo) => candidateByPhoto.has(photo.id))
    .sort((left, right) => (candidateByPhoto.get(left.id)?.rank ?? 0) - (candidateByPhoto.get(right.id)?.rank ?? 0));
  const featuredGroups = [
    { id: "best", title: "Melhores resultados encontrados", detail: "Fotos tecnicamente mais nítidas e bem enquadradas aparecem primeiro.", photos: candidatePhotos.filter((photo) => candidateByPhoto.get(photo.id)?.quality_band === "best") },
    { id: "other", title: "Outros resultados encontrados", detail: "Outras possibilidades continuam disponíveis para sua decisão.", photos: candidatePhotos.filter((photo) => candidateByPhoto.get(photo.id)?.quality_band === "other") },
  ];

  async function rejectCandidate(photo: PublicPhoto) {
    if (!facialResult) return;
    try {
      await facialSearchApi.reject(galleryId, facialResult.id, photo.id);
      setFacialResult({ ...facialResult, candidates: (facialResult.candidates ?? []).filter((candidate) => candidate.photo_id !== photo.id) });
      setMessage("Esta possibilidade foi removida somente da sua busca.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível remover este resultado.");
    }
  }

  return (
    <main className="admin-shell public-gallery-shell">
      <nav className="public-gallery-navigation" aria-label="Acessos da cliente">
        <Link href="/library">← Minha biblioteca</Link>
        {privateGalleryId ? <Link className="primary" href={`/gallery/${privateGalleryId}`}>Minha galeria</Link> : null}
      </nav>
      <FacialSearchPanel galleryId={galleryId} result={facialResult} onResult={setFacialResult} />
      {message ? <p className="public-selection-result" role="status">{message}</p> : null}
      {photosLoading ? <SystemState tone="loading" title="Carregando fotos" detail="Você já pode acessar sua galeria enquanto as prévias são preparadas." /> : photosFailed ? <SystemState tone="error" title="Não foi possível carregar as fotos" detail="Atualize a página para tentar novamente. Seus acessos continuam disponíveis acima." /> : <GalleryPresentation galleryName={gallery.name} context={gallery.description || gallery.event_name ? <p>{gallery.description || gallery.event_name}</p> : null} coverUrl={gallery.cover_preview_url ? `/api${gallery.cover_preview_url}` : null} folders={folders} featuredGroups={featuredGroups} folderDisplayMode={gallery.folder_display_mode ?? "individual"} titleStyle={{ color: gallery.cover_title_color, fontFamily: galleryFontFamily(gallery.cover_title_font), fontSize: gallery.cover_title_size, position: gallery.cover_title_position }} emptyDetail="Nenhuma foto disponível." showCopyrightProtectionDialog renderPhotoMarkers={(photo) => {
        const selected = selectedIds.includes(photo.id);
        const favorited = favoriteIds.includes(photo.id);
        const frozenLabel = photo.commercial_state === "purchased" ? "Comprada" : photo.commercial_state === "payment_reported" ? "Pagamento informado" : photo.commercial_state === "awaiting_payment" ? "Aguardando pagamento" : null;
        return <>{frozenLabel ? <span className="gallery-presentation-marker is-purchased">{frozenLabel}</span> : <button type="button" className="gallery-presentation-marker" aria-pressed={selected} disabled={Boolean(selectingId)} onClick={() => toggleSelection(photo)}>{selectingId === photo.id ? (selected ? "Desmarcando…" : "Selecionando…") : selected ? "✓ Desmarcar" : "Selecionar foto"}</button>}{gallery.favorites_enabled && privateGalleryId && selected ? <button type="button" className="gallery-presentation-marker" aria-pressed={favorited} disabled={Boolean(selectingId)} onClick={() => toggleFavorite(photo)}>{favorited ? "★ Favorita" : "☆ Favoritar"}</button> : null}</>;
      }} renderFeaturedPhotoMarkers={(photo) => {
        const selected = selectedIds.includes(photo.id);
        const favorited = favoriteIds.includes(photo.id);
        const frozenLabel = photo.commercial_state === "purchased" ? "Comprada" : photo.commercial_state === "payment_reported" ? "Pagamento informado" : photo.commercial_state === "awaiting_payment" ? "Aguardando pagamento" : null;
        return <>{frozenLabel ? <span className="gallery-presentation-marker is-purchased">{frozenLabel}</span> : <button type="button" className="gallery-presentation-marker" aria-pressed={selected} disabled={Boolean(selectingId)} onClick={() => toggleSelection(photo, true)}>{selectingId === photo.id ? (selected ? "Desmarcando…" : "Selecionando…") : selected ? "✓ Desmarcar" : "Selecionar foto"}</button>}{gallery.favorites_enabled && privateGalleryId && selected ? <button type="button" className="gallery-presentation-marker" aria-pressed={favorited} disabled={Boolean(selectingId)} onClick={() => toggleFavorite(photo)}>{favorited ? "★ Favorita" : "☆ Favoritar"}</button> : null}<button type="button" className="gallery-presentation-marker gallery-presentation-marker--reject" onClick={() => { void rejectCandidate(photo); }}>Não é esta pessoa</button></>;
      }} />}
      {cart.quantity > 0 ? <aside className="selection-summary selection-summary--floating" aria-live="polite" aria-label="Resumo da seleção">
        <div><span>Sua seleção</span><strong>{cart.quantity} foto{cart.quantity === 1 ? "" : "s"}</strong></div>
        <div className="selection-summary__commercial"><span>Total <strong>{cart.total_cents !== undefined ? (cart.total_cents / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" }) : "A calcular"}</strong></span>{cart.savings_cents ? <span className="selection-summary__savings">Você economiza {(cart.savings_cents / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}</span> : null}</div>
        {cart.pricing_error ? <p className="notice">{cart.pricing_error}</p> : null}
        {privateGalleryId ? <ClientCartLink className="primary selection-summary__proceed" count={cart.quantity} href={`/gallery/${privateGalleryId}?mode=review`} /> : null}
      </aside> : null}
    </main>
  );
}
