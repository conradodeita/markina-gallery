"use client";

import { type ReactNode, useEffect, useMemo, useRef, useState } from "react";

export type GalleryPresentationPhoto = {
  id: string;
  name: string;
  previewUrl: string;
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
  titleStyle?: TitleStyle;
  modeLabel?: ReactNode;
  emptyDetail?: string;
  renderPhotoDetails?: (photo: TPhoto) => ReactNode;
};

export function GalleryPresentation<TPhoto extends GalleryPresentationPhoto>({
  galleryName,
  context,
  coverUrl,
  folders,
  titleStyle,
  modeLabel,
  emptyDetail = "Quando houver prévias protegidas disponíveis, elas aparecerão aqui.",
  renderPhotoDetails,
}: GalleryPresentationProps<TPhoto>) {
  const availableFolders = folders.filter((folder) => folder.photos.length > 0);
  const [activeFolderId, setActiveFolderId] = useState(availableFolders[0]?.id ?? "");
  const [expandedPhotoId, setExpandedPhotoId] = useState<string | null>(null);
  const dialog = useRef<HTMLDivElement>(null);
  const photos = useMemo(() => availableFolders.flatMap((folder) => folder.photos), [availableFolders]);
  const activeFolder = availableFolders.find((folder) => folder.id === activeFolderId) ?? availableFolders[0];
  const expandedIndex = photos.findIndex((photo) => photo.id === expandedPhotoId);
  const expandedPhoto = expandedIndex >= 0 ? photos[expandedIndex] : null;

  useEffect(() => {
    if (expandedPhoto) dialog.current?.focus();
  }, [expandedPhoto]);

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
      {modeLabel ? <div className="gallery-presentation-mode">{modeLabel}</div> : null}
      <header className="gallery-presentation-hero">
        {coverUrl ? <img src={coverUrl} alt={`Capa de ${galleryName}`} /> : <div className="gallery-presentation-hero-empty" role="status">Capa ainda não definida</div>}
        <div className={`gallery-presentation-title title-${titleStyle?.position ?? "bottom-left"}`} style={heroTitleStyle}>
          <p className="eyebrow">Galeria privada</p>
          <h1>{galleryName}</h1>
          {context ? <div className="gallery-presentation-context">{context}</div> : null}
        </div>
      </header>

      {availableFolders.length > 1 ? (
        <nav className="gallery-presentation-folders" aria-label="Pastas da galeria">
          {availableFolders.map((folder) => <button key={folder.id} type="button" aria-pressed={activeFolder?.id === folder.id} onClick={() => setActiveFolderId(folder.id)}>{folder.name}<span>{folder.photos.length}</span></button>)}
        </nav>
      ) : null}

      {activeFolder ? (
        <section className="gallery-presentation-collection" aria-labelledby={`folder-${activeFolder.id}`}>
          <div className="gallery-presentation-collection-heading"><div><p className="eyebrow">Fotos protegidas</p><h2 id={`folder-${activeFolder.id}`}>{activeFolder.name}</h2></div><span>{activeFolder.photos.length} foto{activeFolder.photos.length === 1 ? "" : "s"}</span></div>
          <div className="gallery-presentation-grid">
            {activeFolder.photos.map((photo) => <article className="gallery-presentation-photo" key={photo.id}><button type="button" className="gallery-presentation-photo-image" onClick={() => setExpandedPhotoId(photo.id)} aria-label={`Ampliar prévia protegida de ${photo.name}`}><img src={photo.previewUrl} alt={`Prévia protegida de ${photo.name}`} /></button><div className="gallery-presentation-photo-details"><strong>{photo.name}</strong>{renderPhotoDetails?.(photo)}</div></article>)}
          </div>
        </section>
      ) : <section className="gallery-presentation-empty" role="status"><h2>Nenhuma foto pronta para mostrar</h2><p>{emptyDetail}</p></section>}

      {expandedPhoto ? <div className="gallery-presentation-dialog-backdrop" role="presentation" onMouseDown={() => setExpandedPhotoId(null)}><div ref={dialog} className="gallery-presentation-dialog" role="dialog" aria-modal="true" aria-label={`Prévia ampliada de ${expandedPhoto.name}`} tabIndex={-1} onMouseDown={(event) => event.stopPropagation()} onKeyDown={(event) => { if (event.key === "Escape") setExpandedPhotoId(null); if (event.key === "ArrowLeft") moveExpanded(-1); if (event.key === "ArrowRight") moveExpanded(1); }}><button type="button" className="gallery-presentation-close" onClick={() => setExpandedPhotoId(null)}>Fechar</button><img src={expandedPhoto.previewUrl} alt={`Prévia protegida ampliada de ${expandedPhoto.name}`} /><div className="gallery-presentation-dialog-footer"><strong>{expandedPhoto.name}</strong>{photos.length > 1 ? <div><button type="button" onClick={() => moveExpanded(-1)}>Anterior</button><button type="button" onClick={() => moveExpanded(1)}>Próxima</button></div> : null}</div></div></div> : null}
    </section>
  );
}
