"use client";

import { useState } from "react";

/** Only the client's protected operational/historical routes are accepted. */
export function purchasePreviewUrl(path: string | null): string | null {
  if (!path) return null;
  const local = path.startsWith("/api/") ? path.slice(4) : path;
  if (!/^\/(?:library\/history\/items\/[\w-]+|gallery\/[\w-]+\/photos\/[\w-]+)\/preview$/.test(local)) return null;
  return `/api${local}`;
}

export function PurchasePreview({ path, name, expanded = false }: { path: string | null; name: string; expanded?: boolean }) {
  const [failedPath, setFailedPath] = useState<string | null>(null);
  const url = purchasePreviewUrl(path);
  if (!url || failedPath === url) return <span className="purchase-preview-unavailable" role="status">Prévia indisponível</span>;
  return <img src={url} alt={`Prévia protegida ${expanded ? "ampliada " : ""}de ${name}`} loading={expanded ? "eager" : "lazy"} draggable={false} onError={() => setFailedPath(url)} onContextMenu={(event) => event.preventDefault()} />;
}
