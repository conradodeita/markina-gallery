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
}: GalleryPresentationProps<TPhoto>) {
  const availableFolders = folders.filter((folder) => folder.photos.length > 0);
  const [activeFolderId, setActiveFolderId] = useState(availableFolders[0]?.id ?? "");
  const [expandedPhotoId, setExpandedPhotoId] = useState<string | null>(null);
  const [protectionMessage, setProtectionMessage] = useState("Prévia protegida: cópias e downloads diretos estão desativados.");
  const dialog = useRef<HTMLDivElement>(null);
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
    function detectScreenshot(event: KeyboardEvent) {
      if (event.key === "PrintScreen") {
        setProtectionMessage("Captura detectada. O navegador não consegue impedir screenshots; a prévia continua identificada pela marca-d’água.");
      }
    }
    window.addEventListener("keyup", detectScreenshot);
    return () => window.removeEventListener("keyup", detectScreenshot);
  }, []);

  function protectPreview(event: { preventDefault: () => void }) {
    event.preventDefault();
    setProtectionMessage("Conteúdo protegido: arraste, menu de contexto e cópia direta estão desativados. A marca-d’água identifica esta prévia.");
  }

  function moveExpanded(step: number) {
    if (!photos.length || expandedIndex < 0) return;
    setExpandedPhotoId(photos[(expandedIndex + step + photos.length) % photos.length].id);
  }

  const heroTitleStyle = {
    color: titleStyle?.color,
    fontFamily: titleStyle?.fontFamily,
    fontSize: titleStyle?.fontSize ? `${titleStyle.fontSize}px` : undefined,
  };

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
            {folder.photos.map((photo) => <article className="gallery-presentation-photo" key={photo.id} style={photoStyle(photo)}>
              <button type="button" className="gallery-presentation-photo-image gallery-protected-media" onClick={() => setExpandedPhotoId(photo.id)} onContextMenu={protectPreview} onCopy={protectPreview} onDragStart={protectPreview} aria-label={`Ampliar prévia protegida de ${photo.name}`}><img src={photo.previewUrl} alt={`Prévia protegida de ${photo.name}`} draggable={false} width={photo.width ?? undefined} height={photo.height ?? undefined} /></button>
              {renderPhotoMarkers ? <div className="gallery-presentation-photo-markers">{renderPhotoMarkers(photo)}</div> : null}
              <div className="gallery-presentation-photo-details"><strong>{photo.name}</strong>{renderPhotoDetails?.(photo)}</div>
            </article>)}
          </div>
        </section>
      )) : <section className="gallery-presentation-empty" role="status"><h2>Nenhuma foto pronta para mostrar</h2><p>{emptyDetail}</p></section>}

      {expandedPhoto ? <div className="gallery-presentation-dialog-backdrop" role="presentation" onMouseDown={() => setExpandedPhotoId(null)}><div ref={dialog} className="gallery-presentation-dialog" role="dialog" aria-modal="true" aria-label={`Prévia ampliada de ${expandedPhoto.name}`} tabIndex={-1} onMouseDown={(event) => event.stopPropagation()} onKeyDown={(event) => { if (event.key === "Escape") setExpandedPhotoId(null); if (event.key === "ArrowLeft") moveExpanded(-1); if (event.key === "ArrowRight") moveExpanded(1); }} onTouchStart={(event) => { touchStartX.current = event.changedTouches[0]?.clientX ?? null; }} onTouchEnd={(event) => { const end = event.changedTouches[0]?.clientX; if (touchStartX.current !== null && end !== undefined && Math.abs(end - touchStartX.current) > 50) moveExpanded(end < touchStartX.current ? 1 : -1); touchStartX.current = null; }}><div className="gallery-presentation-dialog-header"><span>Prévia protegida</span><button type="button" className="gallery-presentation-close" onClick={() => setExpandedPhotoId(null)}>Fechar</button></div><div className="gallery-presentation-dialog-media gallery-protected-media" onContextMenu={protectPreview} onCopy={protectPreview} onDragStart={protectPreview}><img src={expandedPhoto.previewUrl} alt={`Prévia protegida ampliada de ${expandedPhoto.name}`} draggable={false} width={expandedPhoto.width ?? undefined} height={expandedPhoto.height ?? undefined} /></div><div className="gallery-presentation-dialog-footer"><strong>{expandedPhoto.name}</strong>{photos.length > 1 ? <div><button type="button" onClick={() => moveExpanded(-1)}>Anterior</button><button type="button" onClick={() => moveExpanded(1)}>Próxima</button></div> : null}</div></div></div> : null}
    </section>
  );
}
