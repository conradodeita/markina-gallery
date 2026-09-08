"use client";

import { useEffect, useState } from "react";

export type ProtectedPhoto = { id: string; name: string; previewUrl: string };

function PreviewImage({ photo }: { photo: ProtectedPhoto }) {
  const [state, setState] = useState<"loading" | "ready" | "unavailable">("loading");
  const previewUrl = photo.previewUrl.startsWith("/api/")
    ? photo.previewUrl
    : `/api${photo.previewUrl}`;
  return <div className="viewer-stage" aria-live="polite">
    {state === "loading" && <p className="viewer-state">Carregando prévia protegida…</p>}
    {state === "unavailable" && <p className="viewer-state">Esta prévia está indisponível no momento.</p>}
    {/* A imagem passa pelo endpoint autenticado; otimização externa não preservaria a sessão. */}
    {/* eslint-disable-next-line @next/next/no-img-element */}
    <img
      alt={photo.name}
      className={state === "ready" ? "viewer-image" : "viewer-image is-hidden"}
      src={previewUrl}
      onLoad={() => setState("ready")}
      onError={() => setState("unavailable")}
    />
  </div>;
}

export function ProtectedPhotoViewer({ photos, label }: { photos: ProtectedPhoto[]; label: string }) {
  const [current, setCurrent] = useState(0);
  const active = photos[current];

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "ArrowLeft") setCurrent((index) => Math.max(0, index - 1));
      if (event.key === "ArrowRight") setCurrent((index) => Math.min(photos.length - 1, index + 1));
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [photos.length]);

  if (!active) return <p className="form-message">Nenhuma foto está disponível nesta galeria.</p>;

  return <section className="protected-viewer" aria-label={label}>
    <PreviewImage key={active.id} photo={active} />
    <div className="viewer-controls">
      <button className="secondary" disabled={current === 0} onClick={() => setCurrent(current - 1)}>Anterior</button>
      <p><strong>{active.name}</strong><br /><span>{current + 1} de {photos.length}</span></p>
      <button className="secondary" disabled={current === photos.length - 1} onClick={() => setCurrent(current + 1)}>Próxima</button>
    </div>
    <p className="viewer-hint">Use as setas do teclado para navegar. A prévia é protegida e não é o arquivo original.</p>
  </section>;
}
