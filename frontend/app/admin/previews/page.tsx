"use client";

import { type FormEvent, useEffect, useState } from "react";

import { ProtectedPhotoViewer } from "../../protected-photo-viewer";
import { MarkinaButton, MarkinaLink, PageHeading, SystemState } from "../../ui-kit";
import styles from "./previews.module.css";

type Access = "loading" | "authorized" | "denied" | "unavailable";

export default function AdminPreviewsPage() {
  const [access, setAccess] = useState<Access>("loading");
  const [accessRequest, setAccessRequest] = useState(0);
  const [photoId, setPhotoId] = useState("");
  const [activeId, setActiveId] = useState("");
  const [previewRequest, setPreviewRequest] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/admin", { credentials: "same-origin", signal: controller.signal })
      .then((response) => {
        if (controller.signal.aborted) return;
        if (response.status === 401 || response.status === 403) setAccess("denied");
        else setAccess(response.ok ? "authorized" : "unavailable");
      })
      .catch(() => { if (!controller.signal.aborted) setAccess("unavailable"); });
    return () => controller.abort();
  }, [accessRequest]);

  function openPreview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!photoId.trim()) return;
    setActiveId(photoId.trim());
    setPreviewRequest((previous) => previous + 1);
  }

  return <div className={styles.page}>
    <PageHeading title="Conferência de prévias" detail="Consulte o derivado administrativo pelo identificador da foto." />
    {access === "loading" ? <SystemState tone="loading" title="Verificando acesso" detail="Aguarde a confirmação da sessão administrativa." /> : null}
    {access === "denied" ? <div className={styles.state}>
      <SystemState tone="error" title="Acesso restrito" detail="Entre com uma sessão administrativa para consultar a prévia." />
      <MarkinaLink href="/" variant="secondary">Voltar para entrada</MarkinaLink>
    </div> : null}
    {access === "unavailable" ? <div className={styles.state}>
      <SystemState tone="error" title="Não foi possível confirmar o acesso" detail="Repita a consulta antes de abrir a prévia." />
      <MarkinaButton type="button" variant="secondary" onClick={() => {
        setAccess("loading");
        setAccessRequest((previous) => previous + 1);
      }}>Tentar novamente</MarkinaButton>
    </div> : null}
    {access === "authorized" ? <>
      <form className={styles.form} onSubmit={openPreview}>
        <label>Identificador da foto
          <input value={photoId} onChange={(event) => setPhotoId(event.target.value)} placeholder="UUID da foto" spellCheck={false} autoCapitalize="none" required />
        </label>
        <MarkinaButton type="submit" disabled={!photoId.trim()}>Abrir prévia</MarkinaButton>
      </form>
      <div className={styles.workspace}>
        <section className={styles.stage} aria-labelledby="photo-preview-title">
          <h2 id="photo-preview-title">Prévia da foto</h2>
          {activeId ? <ProtectedPhotoViewer key={previewRequest} label="Prévia administrativa" photos={[{ id: activeId, name: `Foto ${activeId}`, previewUrl: `/api/admin/photo-assets/${encodeURIComponent(activeId)}/preview` }]} /> : <SystemState title="Selecione uma foto" detail="Informe o identificador para ver sua prévia." />}
        </section>
        <aside className={styles.viewerInfo} aria-labelledby="photo-preview-policy">
          <h2 id="photo-preview-policy">Sobre a prévia</h2>
          <p>A imagem é exibida sem marca-d&apos;água e com resolução limitada para conferência.</p>
        </aside>
      </div>
    </> : null}
  </div>;
}
