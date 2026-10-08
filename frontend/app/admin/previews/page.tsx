"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";

import { ProtectedPhotoViewer } from "../../protected-photo-viewer";

export default function AdminPreviewsPage() {
  const [authorized, setAuthorized] = useState<boolean | null>(null);
  const [photoId, setPhotoId] = useState("");
  const [activeId, setActiveId] = useState("");
  useEffect(() => { fetch("/api/admin", { credentials: "same-origin" }).then((response) => setAuthorized(response.ok)).catch(() => setAuthorized(false)); }, []);
  function openPreview(event: FormEvent<HTMLFormElement>) { event.preventDefault(); setActiveId(photoId.trim()); }
  if (authorized === null) return <main className="admin-shell">Carregando área administrativa…</main>;
  if (!authorized) return <main className="admin-shell"><h1>Acesso restrito</h1><Link href="/">Voltar para entrada</Link></main>;
  return <main className="admin-shell"><p className="eyebrow">Markina Gallery · Fotógrafo</p><h1>Conferência de prévias</h1><p className="intro">A prévia administrativa não possui marca-d&apos;água e tem resolução limitada; o original não é disponibilizado.</p><form className="auth-form" onSubmit={openPreview}><label>Identificador da foto<input value={photoId} onChange={(event) => setPhotoId(event.target.value)} placeholder="UUID da foto" required /></label><button className="primary">Abrir prévia</button></form>{activeId && <ProtectedPhotoViewer label="Prévia administrativa" photos={[{ id: activeId, name: `Foto ${activeId}`, previewUrl: `/api/admin/photo-assets/${activeId}/preview` }]} />}</main>;
}
