"use client";

import { FormEvent, useEffect, useState } from "react";
import { useParams } from "next/navigation";

import { GalleryPresentation, type GalleryPresentationFolder } from "../../gallery-presentation";
import { StatusBadge, SystemState } from "../../ui-kit";

type ReviewPhoto = {
  id: string;
  name: string;
  previewUrl: string;
  folderId: string;
  selected: boolean;
  favorited: boolean;
  purchaseState: string;
};
type ReleasedFolder = { id: string; name: string; position: number; photo_count: number };
type Comment = { id: string; photo_id: string; body: string };
type Review = {
  gallery: {
    name: string;
    message: string;
    selection_expires_at: string | null;
    selection_open: boolean;
    favorites_enabled: boolean;
    comments_enabled: boolean;
  };
  photos: ReviewPhoto[];
};

export default function GalleryPage() {
  const { galleryId } = useParams<{ galleryId: string }>();
  const [review, setReview] = useState<Review | null>(null);
  const [comments, setComments] = useState<Comment[]>([]);
  const [releasedFolders, setReleasedFolders] = useState<ReleasedFolder[]>([]);
  const [activePhotoId, setActivePhotoId] = useState("");
  const [message, setMessage] = useState("");
  const [filter, setFilter] = useState<"all" | "nova" | "visualizada mas não comprada" | "já comprada">("all");
  function load() {
    Promise.all([
      fetch(`/api/gallery/${galleryId}/review`, { credentials: "same-origin" }),
      fetch(`/api/gallery/${galleryId}/folders`, { credentials: "same-origin" }),
    ])
      .then(async ([response, foldersResponse]) => {
        if (!response.ok || !foldersResponse.ok) throw new Error();
        const [result, folderResult] = await Promise.all([response.json(), foldersResponse.json()]);
        setReview({
          ...result,
          photos: result.photos.map(
            (photo: {
              id: string;
              name: string;
              folder_id: string;
              preview_url: string;
              selected: boolean;
              favorited: boolean;
              purchase_state: string;
            }) => ({
              id: photo.id,
              name: photo.name,
              folderId: photo.folder_id,
              previewUrl: `/api${photo.preview_url}`,
              selected: photo.selected,
              favorited: photo.favorited,
              purchaseState: photo.purchase_state,
            }),
          ),
        });
        setReleasedFolders(folderResult.folders ?? []);
        setActivePhotoId((current) => current || result.photos[0]?.id || "");
      })
      .catch(() =>
        setReview({
          gallery: {
            name: "",
            message: "",
            selection_expires_at: null,
            selection_open: false,
            favorites_enabled: false,
            comments_enabled: false,
          },
          photos: [],
        }),
      );
  }
  function loadComments() {
    fetch(`/api/gallery/${galleryId}/comments`, { credentials: "same-origin" })
      .then(async (response) => {
        if (!response.ok) throw new Error();
        setComments((await response.json()).comments);
      })
      .catch(() => setComments([]));
  }
  useEffect(() => {
    load();
    loadComments();
  }, [galleryId]); // eslint-disable-line react-hooks/exhaustive-deps
  async function interaction(
    photo: ReviewPhoto,
    kind: "selection" | "favorite",
  ) {
    const active = kind === "selection" ? photo.selected : photo.favorited;
    const response = await fetch(
      `/api/gallery/${galleryId}/photos/${photo.id}/${kind}`,
      { method: active ? "DELETE" : "POST", credentials: "same-origin" },
    );
    setMessage(
      response.ok
        ? "Alteração salva."
        : "Não foi possível salvar esta alteração.",
    );
    if (response.ok) load();
  }
  async function addComment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const body = new FormData(event.currentTarget).get("body");
    const response = await fetch(
      `/api/gallery/${galleryId}/photos/${activePhotoId}/comments`,
      {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ body }),
      },
    );
    setMessage(
      response.ok
        ? "Comentário enviado."
        : "Não foi possível enviar o comentário.",
    );
    if (response.ok) {
      event.currentTarget.reset();
      loadComments();
    }
  }
  async function removeComment(id: string) {
    const response = await fetch(`/api/gallery/${galleryId}/comments/${id}`, {
      method: "DELETE",
      credentials: "same-origin",
    });
    if (response.ok) loadComments();
  }
  if (review === null)
    return (
      <SystemState
        tone="loading"
        title="Abrindo sua galeria"
        detail="Carregando prévias protegidas."
      />
    );
  if (!review.photos.length)
    return (
      <SystemState title="Nenhuma foto liberada ainda" detail="Quando o fotógrafo concluir uma rodada, ela aparecerá aqui." />
    );
  const activeComments = comments.filter(
    (comment) => comment.photo_id === activePhotoId,
  );
  const counts = review.photos.reduce(
    (result, photo) => ({ ...result, [photo.purchaseState]: (result[photo.purchaseState] ?? 0) + 1 }),
    {} as Record<string, number>,
  );
  const visiblePhotos = filter === "all" ? review.photos : review.photos.filter((photo) => photo.purchaseState === filter);
  const presentationFolders = releasedFolders.map((folder) => ({ id: folder.id, name: folder.name, photos: visiblePhotos.filter((photo) => photo.folderId === folder.id) })).filter((folder) => folder.photos.length);
  return (
    <main className="admin-shell">
      {!review.gallery.selection_open && (
        <p className="notice">
          O prazo para novas seleções terminou. Seu histórico continua
          disponível.
        </p>
      )}
      {review.gallery.selection_expires_at && review.gallery.selection_open && (
        <p className="form-message">
          Seleções até{" "}
          {new Date(review.gallery.selection_expires_at).toLocaleDateString(
            "pt-BR",
          )}
        </p>
      )}
      <nav className="gallery-photo-filters" aria-label="Filtrar fotos">
        {(["all", "nova", "visualizada mas não comprada", "já comprada"] as const).map((value) => (
          <button key={value} type="button" className={filter === value ? "selected" : ""} aria-pressed={filter === value} onClick={() => setFilter(value)}>
            {value === "all" ? "Todas" : value === "nova" ? "Novas fotos" : value === "visualizada mas não comprada" ? "Vistas, não compradas" : "Já compradas"}
            <span>{value === "all" ? review.photos.length : counts[value] ?? 0}</span>
          </button>
        ))}
      </nav>
      {!visiblePhotos.length && <p className="notice">Nenhuma foto nesta categoria.</p>}
      <GalleryPresentation galleryName={review.gallery.name} context={review.gallery.message ? <p>{review.gallery.message}</p> : null} folders={(presentationFolders.length ? presentationFolders : [{ id: "authorized-photos", name: "Fotos liberadas", photos: visiblePhotos }]) as GalleryPresentationFolder<ReviewPhoto>[]} emptyDetail="Nenhuma foto desta categoria está disponível neste momento." renderPhotoDetails={(photo) => <>
            <StatusBadge
              tone={
                photo.purchaseState === "já comprada"
                  ? "success"
                  : photo.purchaseState === "visualizada mas não comprada"
                    ? "warning"
                    : "neutral"
              }
            >
              {photo.purchaseState}
            </StatusBadge>
            <small>
              {photo.selected
                ? "Selecionada"
                : photo.favorited
                  ? "Favorita"
                  : "Disponível para revisão"}
            </small>
            <div className="gallery-presentation-actions">
              <button
                className="secondary"
                disabled={
                  !review.gallery.selection_open ||
                  photo.purchaseState === "já comprada"
                }
                onClick={() => interaction(photo, "selection")}
              >
                {photo.selected ? "Desfazer" : "Selecionar"}
              </button>
              {review.gallery.favorites_enabled && (
                <button
                  className="secondary"
                  onClick={() => interaction(photo, "favorite")}
                >
                  {photo.favorited ? "★" : "☆"}
                </button>
              )}
            </div>
          </>} />
      {review.gallery.comments_enabled && (
        <section className="admin-card">
          <h2>Comentários</h2>
          <label>
            Foto
            <select
              value={activePhotoId}
              onChange={(event) => setActivePhotoId(event.target.value)}
            >
              {review.photos.map((photo) => (
                <option key={photo.id} value={photo.id}>
                  {photo.name}
                </option>
              ))}
            </select>
          </label>
          <form className="auth-form" onSubmit={addComment}>
            <label>
              Comentário
              <input name="body" maxLength={2000} required />
            </label>
            <button className="primary">Enviar comentário</button>
          </form>
          <ul className="photo-list">
            {activeComments.map((comment) => (
              <li key={comment.id}>
                {comment.body}
                <button
                  className="link-button"
                  onClick={() => removeComment(comment.id)}
                >
                  Remover
                </button>
              </li>
            ))}
          </ul>
          {!activeComments.length && (
            <p className="form-message">Nenhum comentário nesta foto.</p>
          )}
        </section>
      )}
      {message && (
        <p className="form-message" role="status">
          {message}
        </p>
      )}
    </main>
  );
}
