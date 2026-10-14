"use client";

import { useState } from "react";

export function GalleryCardPreview({ src, name, protectedPhoto = false }: { src: string | null; name: string; protectedPhoto?: boolean }) {
  const [failedSrc, setFailedSrc] = useState<string | null>(null);
  return <div className="gallery-card-preview">
    {src && src !== failedSrc ? <img src={src} alt={`Capa de ${name}`} loading="lazy" draggable={false} onError={() => setFailedSrc(src)} onContextMenu={protectedPhoto ? (event) => event.preventDefault() : undefined} /> : <span className="gallery-card-preview-empty">Prévia indisponível</span>}
  </div>;
}

export function galleryCoverUrl(path: string | null | undefined): string | null {
  if (!path) return null;
  const local = path.startsWith("/api/") ? path.slice(4) : path;
  return /^\/(?:public-galleries|gallery)\/[\w-]+\/cover-preview$/.test(local) ? `/api${local}` : null;
}
