"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { type FormEvent, useCallback, useEffect, useRef, useState } from "react";

import { ClientNavigation, notifyCartChanged } from "../../client-navigation";
import { ClientCartLink } from "../../client-cart";
import { PushControl, LogoutButton } from "../../push-control";
import { FacialApiError, facialSearchApi, type FacialSearchResult } from "../../facial-search-client";
import { galleryFontFamily } from "../../gallery-fonts";
import { GalleryPresentation, type GalleryPresentationFolder } from "../../gallery-presentation";
import { SystemState } from "../../ui-kit";
import { FacialSearchPanel } from "../facial-search-panel";
import { FaceRegionViewer } from "../../face-region-viewer";
import { SelectionDeadline } from "../../selection-deadline";

type PublicGallery = { id: string; name: string; event_name: string | null; description: string | null; access_mode: "standard" | "invite_only" | "collective_protected"; photos_url: string; favorites_enabled: boolean; comments_enabled: boolean; folder_display_mode: "individual" | "sequential"; cover_preview_url: string | null; cover_title_font: string; cover_title_color: string; cover_title_size: number; cover_title_position: string; selection_expires_at?: string | null };
type Comment = { id: string; photo_id: string; body: string };
type ReopeningRequest = { id: string; status: "pending" | "approved" | "refused" };
type CommercialState = "available" | "selected" | "awaiting_payment" | "payment_reported" | "purchased" | "selection_finalized";
type PublicPhoto = { id: string; name: string; preview_url: string; folder_id: string; folder_name: string; folder_position: number; width: number | null; height: number | null; selected: boolean; favorited: boolean; commercial_state?: CommercialState; previewUrl: string };
type Cart = {
  quantity: number;
  total_cents?: number | null;
  payment_required?: boolean;
  savings_cents?: number;
  pricing_error?: string;
  items?: Array<{ id: string; name: string }>;
};

export default function PublicGalleryPage() {
  const { galleryId } = useParams<{ galleryId: string }>();
  return <PublicGallery key={galleryId} galleryId={galleryId} />;
}

function PublicGallery({ galleryId }: { galleryId: string }) {
  const [gallery, setGallery] = useState<PublicGallery | null>(null);
  const [photos, setPhotos] = useState<PublicPhoto[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [favoriteIds, setFavoriteIds] = useState<string[]>([]);
  const [comments, setComments] = useState<Comment[]>([]);
  const [reopening, setReopening] = useState<ReopeningRequest | null>(null);
  const [reopeningBusy, setReopeningBusy] = useState(false);
  const [selectionExpired, setSelectionExpired] = useState(false);
  const [cart, setCart] = useState<Cart>({ quantity: 0, items: [] });
  const [selectingId, setSelectingId] = useState<string | null>(null);
  const [failedGalleryId, setFailedGalleryId] = useState<string | null>(null);
  const [photoLoad, setPhotoLoad] = useState<{ galleryId: string; status: "loading" | "ready" | "failed" }>({ galleryId, status: "loading" });
  const [message, setMessage] = useState("");
  const [facialResult, setFacialResult] = useState<FacialSearchResult | null>(null);
  const [regionPending, setRegionPending] = useState(false);
  const [regionSearchId, setRegionSearchId] = useState<string | null>(null);
  const [regionMessage, setRegionMessage] = useState("");
  const regionRequest = useRef<{ id: string | null; close: () => void } | null>(null);
  const reopeningKey = useRef("");
  const admissionPending = useRef(false);
  const retryAt = useRef(0);
  const mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);

  const receiveFacialResult = useCallback((value: FacialSearchResult | null) => {
    if (admissionPending.current) return;
    if (value && regionRequest.current?.id && value.id !== regionRequest.current.id) return;
    if (!value) regionRequest.current = null;
    setFacialResult(value);
  }, []);

  const searchRegion = useCallback(async (regionId: string, close: () => void) => {
    if (admissionPending.current || Date.now() < retryAt.current) return;
    admissionPending.current = true;
    regionRequest.current = { id: null, close };
    setRegionPending(true);
    setRegionSearchId(null);
    setRegionMessage("Aguarde, procurando fotos…");
    try {
      const created = await facialSearchApi.createFromRegion(galleryId, regionId);
      if (!mounted.current) return;
      regionRequest.current = { id: created.id, close };
      setRegionSearchId(created.id);
      window.sessionStorage.setItem(`markina:facial-search:${galleryId}`, created.id);
      setRegionMessage("");
      setFacialResult(created);
    } catch (cause) {
      if (!mounted.current) return;
      regionRequest.current = null;
      const retry = cause instanceof FacialApiError ? cause.retryAfterSeconds ?? 0 : 0;
      retryAt.current = Date.now() + retry * 1000;
      setRegionMessage(`${cause instanceof Error ? cause.message : "Não foi possível iniciar a busca."}${retry ? ` Tente novamente em ${retry} segundos.` : " Toque no rosto para tentar novamente."}`);
    } finally {
      admissionPending.current = false;
      if (mounted.current) setRegionPending(false);
    }
  }, [galleryId]);

  useEffect(() => {
    const current = regionRequest.current;
    if (!current?.id || facialResult?.id !== current.id || !(["ready", "no_candidates", "failed", "cancelled", "expired", "index_incomplete"].includes(facialResult.status)) || photoLoad.status !== "ready") return;
    regionRequest.current = null;
    if (facialResult.status !== "ready") return;
    current.close();
    window.scrollTo({ top: 0, behavior: "instant" });
  }, [facialResult, photoLoad.status]);

  const [refresh, setRefresh] = useState(0);

  const loadComments = useCallback(async () => {
    try {
      const response = await fetch(`/api/public-galleries/${galleryId}/comments`, { credentials: "same-origin" });
      if (!response.ok) return;
      const payload = await response.json() as { comments: Comment[] };
      if (mounted.current) setComments(payload.comments);
    } catch { /* A navegação das fotos permanece disponível se comentários falharem. */ }
  }, [galleryId]);

  useEffect(() => {
    let active = true;
    fetch(`/api/public-galleries/${galleryId}/comments`, { credentials: "same-origin" })
      .then(async (response) => {
        if (!response.ok) return;
        const payload = await response.json() as { comments: Comment[] };
        if (active) setComments(payload.comments);
      })
      .catch(() => { /* Comentários são opcionais para navegar nas fotos. */ });
    return () => { active = false; };
  }, [galleryId]);

  useEffect(() => {
    let active = true;
    fetch(`/api/public-galleries/${galleryId}/reopening-requests`, { credentials: "same-origin" })
      .then(async (response) => {
        if (!response.ok) throw new Error();
        const payload = await response.json() as { request: ReopeningRequest | null };
        if (active) setReopening(payload.request);
      })
      .catch(() => { if (active) setReopening(null); });
    return () => { active = false; };
  }, [galleryId, refresh]);

  useEffect(() => {
    let active = true;

    fetch(`/api/public-galleries/${galleryId}`, { credentials: "same-origin" })
      .then(async (response) => {
        if (!response.ok) throw new Error();
        const result = await response.json() as PublicGallery;
        if (!active) return;
        setGallery(result);
        setSelectionExpired(Boolean(result.selection_expires_at && Date.now() >= Date.parse(result.selection_expires_at)));
        setFailedGalleryId(null);
      })
      .catch(() => { if (active) setFailedGalleryId(galleryId); });

    return () => { active = false; };
  }, [galleryId, refresh]);

  useEffect(() => {
    let active = true;
    fetch(`/api/public-galleries/${galleryId}/photos`, { credentials: "same-origin" })
      .then(async (response) => {
        if (!response.ok) throw new Error();
        const result = await response.json();
        if (!active) return;
        setSelectedIds((result.photos ?? []).filter((photo: PublicPhoto) => photo.selected).map((photo: PublicPhoto) => photo.id));
        setFavoriteIds((result.photos ?? []).filter((photo: PublicPhoto) => photo.favorited).map((photo: PublicPhoto) => photo.id));
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
      if (payload.gallery_closed || "selection_expires_at" in payload) {
        setGallery((current) => current ? { ...current, selection_expires_at: payload.gallery_closed ? null : payload.selection_expires_at } : current);
        if (!selected) setSelectionExpired(false);
      }
      notifyCartChanged();
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
    if (selectingId) return;
    const favorited = favoriteIds.includes(photo.id);
    setSelectingId(photo.id);
    setMessage("");
    try {
      const response = await fetch(`/api/public-galleries/${galleryId}/photos/${photo.id}/favorite`, {
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

  async function addComment(event: FormEvent<HTMLFormElement>, photo: PublicPhoto) {
    event.preventDefault();
    const form = event.currentTarget;
    const body = new FormData(form).get("body");
    const response = await fetch(`/api/public-galleries/${galleryId}/photos/${photo.id}/comments`, {
      method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ body }),
    });
    setMessage(response.ok ? "Comentário enviado." : "Não foi possível enviar o comentário.");
    if (response.ok) { form.reset(); await loadComments(); }
  }

  async function removeComment(id: string) {
    const response = await fetch(`/api/public-galleries/${galleryId}/comments/${id}`, {
      method: "DELETE", credentials: "same-origin",
    });
    if (response.ok) await loadComments();
  }

  async function requestReopening() {
    if (reopeningBusy || reopening?.status === "pending") return;
    setReopeningBusy(true);
    reopeningKey.current ||= globalThis.crypto?.randomUUID?.() ?? `reopening-${Date.now()}-${galleryId}`;
    try {
      const response = await fetch(`/api/public-galleries/${galleryId}/reopening-requests`, {
        method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ idempotency_key: reopeningKey.current }),
      });
      if (!response.ok) throw new Error("Não foi possível solicitar a reabertura.");
      setReopening(await response.json() as ReopeningRequest);
      setMessage("Solicitação enviada ao fotógrafo. A seleção continua fechada até a aprovação.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível solicitar a reabertura.");
    } finally {
      setReopeningBusy(false);
    }
  }

  function renderPhotoComments(photo: PublicPhoto) {
    const photoComments = comments.filter((comment) => comment.photo_id === photo.id);
    return <section className="gallery-photo-comments" aria-label={`Comentários de ${photo.name}`}>
      <h2>Comentários</h2>
      <form className="auth-form" onSubmit={(event) => { void addComment(event, photo); }}>
        <label>Comentário sobre {photo.name}<input name="body" maxLength={2000} required /></label>
        <button type="submit" className="primary">Enviar comentário</button>
      </form>
      <ul className="photo-list">{photoComments.map((comment) => <li key={comment.id}>
        {comment.body}<button type="button" className="link-button" onClick={() => { void removeComment(comment.id); }}>Remover</button>
      </li>)}</ul>
      {!photoComments.length ? <p className="form-message">Nenhum comentário nesta foto.</p> : null}
    </section>;
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
    { id: "matched", title: "Correspondências", detail: "Confira a pessoa procurada antes de selecionar.", photos: candidatePhotos.filter((photo) => candidateByPhoto.get(photo.id)?.match_class !== "ambiguous") },
    { id: "ambiguous", title: "Possíveis correspondências", detail: "Confira estas possibilidades com atenção.", photos: candidatePhotos.filter((photo) => candidateByPhoto.get(photo.id)?.match_class === "ambiguous") },
  ];


  return (
    <main className="admin-shell public-gallery-shell">
      <nav className="public-gallery-navigation" aria-label="Acessos da cliente">
        <Link href="/library">← Minha biblioteca</Link>
        <PushControl /><LogoutButton />
      </nav>
      <ClientNavigation />
      <FacialSearchPanel galleryId={galleryId} result={facialResult} onResult={receiveFacialResult} />
      {regionMessage ? <p role="status">{regionMessage}</p> : null}
      {message ? <p className="public-selection-result" role="status">{message}</p> : null}
      <SelectionDeadline expiresAt={gallery.selection_expires_at} onRevalidate={() => setRefresh((value) => value + 1)} />
      {selectionExpired ? <section className="admin-card gallery-reopening" aria-live="polite">
        <h2>Prazo de seleção encerrado</h2>
        {reopening?.status === "pending" ? <p>Reabertura solicitada. Aguarde a resposta do fotógrafo.</p> : <button className="primary" type="button" disabled={reopeningBusy} onClick={() => { void requestReopening(); }}>{reopeningBusy ? "Solicitando…" : "Solicitar reabertura da galeria"}</button>}
      </section> : null}
      {photosLoading ? <SystemState tone="loading" title="Carregando fotos" detail="Você já pode acessar sua galeria enquanto as prévias são preparadas." /> : photosFailed ? <SystemState tone="error" title="Não foi possível carregar as fotos" detail="Atualize a página para tentar novamente. Seus acessos continuam disponíveis acima." /> : <GalleryPresentation galleryName={gallery.name} context={gallery.description || gallery.event_name ? <p>{gallery.description || gallery.event_name}</p> : null} coverUrl={gallery.cover_preview_url ? `/api${gallery.cover_preview_url}` : null} folders={folders} onExpandedPhotoChange={(photo) => { if (photo) void fetch(`/api/public-galleries/${galleryId}/photos/${photo.id}/view`, { method: "POST", credentials: "same-origin" }); }} renderExpandedPhotoContent={gallery.comments_enabled ? renderPhotoComments : undefined} renderExpandedMedia={(photo, close) => <FaceRegionViewer key={photo.id} galleryId={galleryId} photo={photo} onRegion={(id) => { void searchRegion(id, close); }} busy={regionPending} searchResult={facialResult?.id === regionSearchId ? facialResult : null} searchStatus={regionMessage || (facialResult ? facialResult.status : "")} />} featuredGroups={featuredGroups} separateFeaturedPhotos={Boolean(facialResult?.status === "ready")} folderDisplayMode={gallery.folder_display_mode ?? "individual"} titleStyle={{ color: gallery.cover_title_color, fontFamily: galleryFontFamily(gallery.cover_title_font), fontSize: gallery.cover_title_size, position: gallery.cover_title_position }} emptyDetail="Nenhuma foto disponível." showCopyrightProtectionDialog renderPhotoMarkers={(photo) => {
        const selected = selectedIds.includes(photo.id);
        const favorited = favoriteIds.includes(photo.id);
        const frozenLabel = photo.commercial_state === "selection_finalized" ? "Seleção finalizada" : photo.commercial_state === "purchased" ? "Comprada" : photo.commercial_state === "payment_reported" ? "Pagamento informado" : photo.commercial_state === "awaiting_payment" ? "Aguardando pagamento" : null;
        return <>{frozenLabel ? <span className="gallery-presentation-marker gallery-presentation-marker--status is-purchased">{frozenLabel}</span> : <button type="button" className="gallery-presentation-marker" aria-pressed={selected} disabled={Boolean(selectingId) || (selectionExpired && !selected)} onClick={() => toggleSelection(photo)}>{selectingId === photo.id ? (selected ? "Desmarcando…" : "Selecionando…") : selected ? "✓ Desmarcar" : "Selecionar foto"}</button>}{gallery.favorites_enabled && selected ? <button type="button" className="gallery-presentation-marker gallery-presentation-marker--favorite" aria-label={favorited ? "Remover dos favoritos" : "Favoritar"} title={favorited ? "Remover dos favoritos" : "Favoritar"} aria-pressed={favorited} disabled={Boolean(selectingId)} onClick={() => toggleFavorite(photo)}>{favorited ? "♥" : "♡"}</button> : null}</>;
      }} renderFeaturedPhotoMarkers={(photo) => {
        const selected = selectedIds.includes(photo.id);
        const favorited = favoriteIds.includes(photo.id);
        const frozenLabel = photo.commercial_state === "selection_finalized" ? "Seleção finalizada" : photo.commercial_state === "purchased" ? "Comprada" : photo.commercial_state === "payment_reported" ? "Pagamento informado" : photo.commercial_state === "awaiting_payment" ? "Aguardando pagamento" : null;
        return <>{frozenLabel ? <span className="gallery-presentation-marker gallery-presentation-marker--status is-purchased">{frozenLabel}</span> : <button type="button" className="gallery-presentation-marker" aria-pressed={selected} disabled={Boolean(selectingId) || (selectionExpired && !selected)} onClick={() => toggleSelection(photo, true)}>{selectingId === photo.id ? (selected ? "Desmarcando…" : "Selecionando…") : selected ? "✓ Desmarcar" : "Selecionar foto"}</button>}{gallery.favorites_enabled && selected ? <button type="button" className="gallery-presentation-marker gallery-presentation-marker--favorite" aria-label={favorited ? "Remover dos favoritos" : "Favoritar"} title={favorited ? "Remover dos favoritos" : "Favoritar"} aria-pressed={favorited} disabled={Boolean(selectingId)} onClick={() => toggleFavorite(photo)}>{favorited ? "♥" : "♡"}</button> : null}</>;
      }} />}
      {cart.quantity > 0 ? <aside className="selection-summary selection-summary--floating" aria-live="polite" aria-label="Resumo da seleção">
        <div><span>Sua seleção</span><strong>{cart.quantity} foto{cart.quantity === 1 ? "" : "s"}</strong></div>
        {cart.payment_required !== false ? <div className="selection-summary__commercial"><span>Total <strong>{cart.total_cents != null ? (cart.total_cents / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" }) : "A calcular"}</strong></span>{cart.savings_cents ? <span className="selection-summary__savings">Você economiza {(cart.savings_cents / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}</span> : null}</div> : null}
        {cart.pricing_error ? <p className="notice">{cart.pricing_error}</p> : null}
        <ClientCartLink className="primary selection-summary__proceed" count={cart.quantity} href="/library/cart" />
      </aside> : null}
    </main>
  );
}
