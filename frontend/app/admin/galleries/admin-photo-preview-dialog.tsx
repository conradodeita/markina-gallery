"use client";

import { useEffect, useRef } from "react";

export type AdminPhotoPreview = {
  src: string;
  alt: string;
  name: string;
  trigger: HTMLElement;
};

export function AdminPhotoPreviewDialog({ preview, onClose }: {
  preview: AdminPhotoPreview; onClose: () => void;
}) {
  const dialog = useRef<HTMLDivElement>(null);

  useEffect(() => {
    dialog.current?.focus();
    return () => { if (preview.trigger.isConnected) preview.trigger.focus(); };
  }, [preview]);

  return <div className="photo-preview-dialog" role="presentation" onMouseDown={onClose}>
    <div ref={dialog} role="dialog" aria-modal="true" aria-label={`Prévia ampliada de ${preview.name}`}
      tabIndex={-1} onKeyDown={(event) => {
        if (event.key === "Escape") onClose();
        if (event.key === "Tab") { event.preventDefault(); dialog.current?.querySelector("button")?.focus(); }
      }}
      onMouseDown={(event) => event.stopPropagation()}>
      <button type="button" className="photo-preview-close" onClick={onClose}>Fechar</button>
      <img src={preview.src} alt={preview.alt} />
      <p>{preview.name}</p>
    </div>
  </div>;
}
