"use client";

import { useEffect, useState } from "react";
import { PRODUCT_NAME } from "./product-brand";

/** A arte enviada já contém nome e tipografia: texto é somente fallback. */
export function BrandLogo({ src, className = "" }: { src?: string | null; className?: string }) {
  const [remote, setRemote] = useState<string | null>(null);
  const [failed, setFailed] = useState<string | null>(null);
  useEffect(() => {
    if (src !== undefined) return;
    const controller = new AbortController();
    void fetch("/api/branding", { signal:controller.signal })
      .then(response => response.ok ? response.json() : null)
      .then(value => { if (!controller.signal.aborted) setRemote(typeof value?.logo_url === "string" ? value.logo_url : null); })
      .catch(() => {});
    return () => controller.abort();
  }, [src]);
  const url = src === undefined ? remote : src;
  // Branding expõe somente ativos locais; não carregar URL arbitrária.
  const safe = url?.startsWith("/branding/") && !url.includes("..") ? `/api${url}` : null;
  return <span className={`product-logo ${className}`}>
    {safe && failed !== safe
      ? <img src={safe} alt={PRODUCT_NAME} onError={() => setFailed(safe)} />
      : <strong className="product-name">{PRODUCT_NAME}</strong>}
  </span>;
}
