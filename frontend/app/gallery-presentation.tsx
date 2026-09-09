"use client";

import { type CSSProperties, type ReactNode, useEffect, useMemo, useRef, useState } from "react";

export type GalleryPresentationPhoto = {
  id: string;
  name: string;
  previewUrl: string;
  width?: number | null;
  height?: number | null;
};

export type GalleryPresentationFolder<TPhoto extends GalleryPresentationPhoto = GalleryPresentationPhoto> = {
  id: string;
  name: string;
  photos: TPhoto[];
};

type TitleStyle = {
  color?: string;
  fontFamily?: string;
  fontSize?: number;
  position?: string;
};

type GalleryPresentationProps<TPhoto extends GalleryPresentationPhoto> = {
  galleryName: string;
  context?: ReactNode;
  coverUrl?: string | null;
  folders: GalleryPresentationFolder<TPhoto>[];
  folderDisplayMode?: "individual" | "sequential";
  titleStyle?: TitleStyle;
  eyebrow?: string;
  modeLabel?: ReactNode;
  emptyDetail?: string;
  renderPhotoDetails?: (photo: TPhoto) => ReactNode;
  renderPhotoMarkers?: (photo: TPhoto) => ReactNode;
  featuredGroups?: Array<{ id: string; title: string; detail: string; photos: TPhoto[] }>;
  renderFeaturedPhotoMarkers?: (photo: TPhoto) => ReactNode;
  renderExpandedPhotoContent?: (photo: TPhoto) => ReactNode;
  onExpandedPhotoChange?: (photo: TPhoto | null) => void;
  showCopyrightProtectionDialog?: boolean;
};

type PhotoStyle = CSSProperties & {
  "--photo-aspect": string;
  "--photo-span": number;
};

function photoStyle(photo: GalleryPresentationPhoto): PhotoStyle {
  const validDimensions = Boolean(photo.width && photo.height && photo.width > 0 && photo.height > 0);
  const ratio = validDimensions ? photo.width! / photo.height! : 4 / 3;
  return {
    "--photo-aspect": validDimensions ? `${photo.width} / ${photo.height}` : "4 / 3",
    "--photo-span": ratio >= 1.45 ? 2 : 1,
  };
}

export function GalleryPresentation<TPhoto extends GalleryPresentationPhoto>({
  galleryName,
  context,
  coverUrl,
  folders,
  folderDisplayMode = "individual",
  titleStyle,
  eyebrow = "Galeria privada",
  modeLabel,
  emptyDetail = "Quando houver prévias protegidas disponíveis, elas aparecerão aqui.",
  renderPhotoDetails,
  renderPhotoMarkers,
  featuredGroups = [],
  renderFeaturedPhotoMarkers,
  renderExpandedPhotoContent,
  onExpandedPhotoChange,
  showCopyrightProtectionDialog = false,
}: GalleryPresentationProps<TPhoto>) {
  const availableFolders = folders.filter((folder) => folder.photos.length > 0);
  const [activeFolderId, setActiveFolderId] = useState(availableFolders[0]?.id ?? "");
  const [expandedPhotoId, setExpandedPhotoId] = useState<string | null>(null);
  const [protectionMessage, setProtectionMessage] = useState("Prévia protegida: cópias e downloads diretos estão desativados.");
  const [copyrightDialogOpen, setCopyrightDialogOpen] = useState(false);
  const dialog = useRef<HTMLDivElement>(null);
  const copyrightDialog = useRef<HTMLDivElement>(null);
  const touchStartX = useRef<number | null>(null);
  const photos = useMemo(() => availableFolders.flatMap((folder) => folder.photos), [availableFolders]);
  const activeFolder = availableFolders.find((folder) => folder.id === activeFolderId) ?? availableFolders[0];
  const visibleFolders = folderDisplayMode === "sequential" ? availableFolders : activeFolder ? [activeFolder] : [];
  const expandedIndex = photos.findIndex((photo) => photo.id === expandedPhotoId);
  const expandedPhoto = expandedIndex >= 0 ? photos[expandedIndex] : null;

  useEffect(() => {
    if (expandedPhoto) dialog.current?.focus();
  }, [expandedPhoto]);

  useEffect(() => {
    if (copyrightDialogOpen) copyrightDialog.current?.focus();
  }, [copyrightDialogOpen]);

  useEffect(() => {
    function detectScreenshot(event: KeyboardEvent) {
      if (event.key === "PrintScreen") {
        setProtectionMessage("Captura detectada. O navegador não consegue impedir screenshots; a prévia continua identificada pela marca-d’água.");
        if (showCopyrightProtectionDialog) {
          setExpandedPhotoId(null);
          onExpandedPhotoChange?.(null);
          setCopyrightDialogOpen(true);
        }
      }
    }
    function detectSaveShortcut(event: KeyboardEvent) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") {
        event.preventDefault();
        setProtectionMessage("Conteúdo protegido: o download direto está desativado. A marca-d’água identifica esta prévia.");
        if (showCopyrightProtectionDialog) {
          setExpandedPhotoId(null);
          onExpandedPhotoChange?.(null);
          setCopyrightDialogOpen(true);
        }
      }
    }
    window.addEventListener("keyup", detectScreenshot);
    window.addEventListener("keydown", detectSaveShortcut);
    return () => {
      window.removeEventListener("keyup", detectScreenshot);
      window.removeEventListener("keydown", detectSaveShortcut);
    };
  }, [showCopyrightProtectionDialog, onExpandedPhotoChange]);

  function showCopyrightWarning() {
    if (!showCopyrightProtectionDialog) return;
    closeExpanded();
    setCopyrightDialogOpen(true);
  }

  function protectPreview(event: { preventDefault: () => void }) {
    event.preventDefault();
    setProtectionMessage("Conteúdo protegido: arraste, menu de contexto e cópia direta estão desativados. A marca-d’água identifica esta prévia.");
    showCopyrightWarning();
  }

  function openExpanded(photo: TPhoto) {
    setExpandedPhotoId(photo.id);
    onExpandedPhotoChange?.(photo);
  }

  function closeExpanded() {
    setExpandedPhotoId(null);
    onExpandedPhotoChange?.(null);
  }

  function moveExpanded(step: number) {
    if (!photos.length || expandedIndex < 0) return;
    openExpanded(photos[(expandedIndex + step + photos.length) % photos.length]);
  }

  const heroTitleStyle = {
    color: titleStyle?.color,
    fontFamily: titleStyle?.fontFamily,
    fontSize: titleStyle?.fontSize ? `${titleStyle.fontSize}px` : undefined,
  };
  const renderPhoto = (photo: TPhoto, markers = renderPhotoMarkers) => <article className="gallery-presentation-photo" key={photo.id} style={photoStyle(photo)}>
    <button type="button" className="gallery-presentation-photo-image gallery-protected-media" onClick={() => openExpanded(photo)} onContextMenu={protectPreview} onCopy={protectPreview} onDragStart={protectPreview} aria-label={`Ampliar prévia protegida de ${photo.name}`}><img src={photo.previewUrl} alt={`Prévia protegida de ${photo.name}`} draggable={false} width={photo.width ?? undefined} height={photo.height ?? undefined} /></button>
    {markers ? <div className="gallery-presentation-photo-markers">{markers(photo)}</div> : null}
    <div className="gallery-presentation-photo-details"><strong>{photo.name}</strong>{renderPhotoDetails?.(photo)}</div>
  </article>;

  return (
    <section className="gallery-presentation" aria-label={`Apresentação de ${galleryName}`}>
      <header className="gallery-presentation-header">
        <div className="gallery-presentation-intro">
          <p className="eyebrow">{eyebrow}</p>
          <h1>{galleryName}</h1>
          {context ? <div className="gallery-presentation-context">{context}</div> : null}
        </div>
        {modeLabel ? <aside className="gallery-presentation-mode" aria-label="Contexto da visualização">{modeLabel}</aside> : null}
      </header>

      <p className="gallery-protection-notice" role="status" aria-live="polite"><span aria-hidden="true">◈</span>{protectionMessage}</p>

      <div className="gallery-presentation-hero gallery-protected-media" onContextMenu={protectPreview} onCopy={protectPreview} onDragStart={protectPreview}>
        {coverUrl ? <img src={coverUrl} alt={`Capa de ${galleryName}`} draggable={false} /> : <div className="gallery-presentation-hero-empty" role="status">Capa ainda não definida</div>}
        <div className={`gallery-presentation-title title-${titleStyle?.position ?? "bottom-left"}`} style={heroTitleStyle}>
          <span>Apresentação</span>
          <strong>{galleryName}</strong>
        </div>
      </div>

      {featuredGroups.some((group) => group.photos.length) ? <section className="gallery-featured-results" aria-labelledby="gallery-featured-title"><header><p className="eyebrow">Filtro da sua busca</p><h2 id="gallery-featured-title">Possibilidades encontradas</h2><p>Confira os resultados e selecione apenas as fotos que desejar. O acervo completo continua abaixo.</p></header>{featuredGroups.filter((group) => group.photos.length).map((group) => <section key={group.id} aria-labelledby={`featured-${group.id}`}><div className="gallery-presentation-collection-heading"><div><h3 id={`featured-${group.id}`}>{group.title}</h3><p>{group.detail}</p></div><span>{group.photos.length} foto{group.photos.length === 1 ? "" : "s"}</span></div><div className="gallery-presentation-grid">{group.photos.map((photo) => renderPhoto(photo, renderFeaturedPhotoMarkers ?? renderPhotoMarkers))}</div></section>)}</section> : null}

      {folderDisplayMode === "individual" && availableFolders.length > 1 ? (
        <section className="gallery-presentation-folder-section" aria-labelledby="gallery-folders-title">
          <div><p className="eyebrow">Navegação</p><h2 id="gallery-folders-title">Coleções</h2></div>
          <nav className="gallery-presentation-folders" aria-label="Pastas da galeria">
            {availableFolders.map((folder) => <button key={folder.id} type="button" aria-pressed={activeFolder?.id === folder.id} onClick={() => setActiveFolderId(folder.id)}>{folder.name}<span>{folder.photos.length}</span></button>)}
          </nav>
        </section>
      ) : null}

      {visibleFolders.length ? visibleFolders.map((folder) => (
        <section className="gallery-presentation-collection" aria-labelledby={`folder-${folder.id}`} key={folder.id}>
          <div className="gallery-presentation-collection-heading"><div><p className="eyebrow">Fotos protegidas</p><h2 id={`folder-${folder.id}`}>{folder.name}</h2></div><span>{folder.photos.length} foto{folder.photos.length === 1 ? "" : "s"}</span></div>
          <div className="gallery-presentation-grid">
            {folder.photos.map((photo) => renderPhoto(photo))}
          </div>
        </section>
      )) : <section className="gallery-presentation-empty" role="status"><h2>Nenhuma foto pronta para mostrar</h2><p>{emptyDetail}</p></section>}

      {copyrightDialogOpen ? <div className="mk-dialog-backdrop" role="presentation" onMouseDown={() => setCopyrightDialogOpen(false)}><div ref={copyrightDialog} className="mk-dialog gallery-copyright-dialog" role="dialog" aria-modal="true" aria-labelledby="gallery-copyright-title" aria-describedby="gallery-copyright-law gallery-copyright-request gallery-copyright-thanks" tabIndex={-1} onMouseDown={(event) => event.stopPropagation()} onKeyDown={(event) => { if (event.key === "Escape") setCopyrightDialogOpen(false); }}><p className="eyebrow">Proteção da obra fotográfica</p><h2 id="gallery-copyright-title">Conteúdo protegido por direitos autorais</h2><p id="gallery-copyright-law">Nossas fotos são protegidas por direitos autorais, conforme estabelecido na <strong>Lei nº 9.610/98</strong>, especialmente em seu <strong>artigo 79</strong>.</p><p id="gallery-copyright-request">Pedimos que não copie ou compartilhe as imagens sem nossa autorização prévia.</p><p id="gallery-copyright-thanks"><strong>Agradecemos pela sua compreensão!</strong></p><div className="mk-dialog__actions"><button type="button" className="mk-button mk-button--primary" onClick={() => setCopyrightDialogOpen(false)}>Entendi</button></div></div></div> : null}

      {expandedPhoto ? (
        <div className="gallery-presentation-dialog-backdrop" role="presentation" onMouseDown={closeExpanded}>
          <div
            ref={dialog}
            className="gallery-presentation-dialog"
            role="dialog"
            aria-modal="true"
            aria-label={`Prévia ampliada de ${expandedPhoto.name}`}
            tabIndex={-1}
            onMouseDown={(event) => event.stopPropagation()}
            onKeyDown={(event) => {
              if (event.key === "Escape") closeExpanded();
              if (event.key === "ArrowLeft") moveExpanded(-1);
              if (event.key === "ArrowRight") moveExpanded(1);
            }}
            onTouchStart={(event) => { touchStartX.current = event.changedTouches[0]?.clientX ?? null; }}
            onTouchEnd={(event) => {
              const end = event.changedTouches[0]?.clientX;
              if (touchStartX.current !== null && end !== undefined && Math.abs(end - touchStartX.current) > 50) moveExpanded(end < touchStartX.current ? 1 : -1);
              touchStartX.current = null;
            }}
          >
            <div className="gallery-presentation-dialog-header">
              <span>Prévia protegida</span>
              <button type="button" className="gallery-presentation-close" onClick={closeExpanded}>Fechar</button>
            </div>
            <div className="gallery-presentation-dialog-media gallery-protected-media" onContextMenu={protectPreview} onCopy={protectPreview} onDragStart={protectPreview}>
              <img src={expandedPhoto.previewUrl} alt={`Prévia protegida ampliada de ${expandedPhoto.name}`} draggable={false} width={expandedPhoto.width ?? undefined} height={expandedPhoto.height ?? undefined} />
            </div>
            {renderExpandedPhotoContent ? <div className="gallery-presentation-dialog-context">{renderExpandedPhotoContent(expandedPhoto)}</div> : null}
            <div className="gallery-presentation-dialog-footer">
              <strong>{expandedPhoto.name}</strong>
              {photos.length > 1 ? <div><button type="button" onClick={() => moveExpanded(-1)}>Anterior</button><button type="button" onClick={() => moveExpanded(1)}>Próxima</button></div> : null}
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}
