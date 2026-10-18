"use client";

import { useCallback, useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { MarkinaButton } from "../../ui-kit";
import styles from "./payments.module.css";

export type OrderPhoto = {
  id: string; photo_id: string; name: string; unit_price_cents: number;
  thumbnail_url?: string | null; preview_url?: string | null;
};
export type OrderFolder = { id: string | null; name: string; items: OrderPhoto[] };
const money = (cents: number) => (cents / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const apiUrl = (url: string) => url.startsWith("/api/") ? url : `/api${url}`;

function Thumbnail({ photo, onOpen }: { photo: OrderPhoto; onOpen: () => void }) {
  const [state, setState] = useState("loading");
  if (!photo.thumbnail_url || !photo.preview_url) return <span className={styles.thumbnail}>Sem prévia</span>;
  return <button type="button" className={styles.thumbnail} aria-label={`Ampliar ${photo.name}`} onClick={onOpen}>
    {/* Endpoint autenticado; nenhum otimizador externo ou arquivo original. */}
    {/* eslint-disable-next-line @next/next/no-img-element */}
    <img src={apiUrl(photo.thumbnail_url)} alt="" width={64} height={64} loading="lazy" decoding="async"
      hidden={state === "failed"} className={state === "loading" ? styles.loadingImage : undefined}
      onLoad={() => setState("ready")} onError={() => setState("failed")} />
    {state !== "ready" ? <span>{state === "failed" ? "Prévia indisponível" : "Carregando…"}</span> : null}
  </button>;
}

function EnlargedPhoto({ photo }: { photo?: OrderPhoto }) {
  const [state, setState] = useState("loading");
  return <div className={styles.lightboxStage} aria-live="polite">
    {(!photo?.preview_url || state === "failed") ? <p>Prévia indisponível.</p> : <>
      {state === "loading" ? <p>Carregando prévia…</p> : null}
      {/* Trocar a foto desmonta a imagem anterior; nenhum pré-carregamento das próximas. */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={apiUrl(photo.preview_url)} alt={photo.name} hidden={state !== "ready"}
        onLoad={() => setState("ready")} onError={() => setState("failed")} />
    </>}
  </div>;
}

function OrderLightbox({ photos, initial, onClose }: { photos: OrderPhoto[]; initial: number; onClose: () => void }) {
  const [current, setCurrent] = useState(initial);
  const dialog = useRef<HTMLDialogElement>(null);
  const closeButton = useRef<HTMLButtonElement>(null);
  const titleId = useId();
  const active = photos[current];

  useEffect(() => {
    const trigger = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const modal = dialog.current;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    modal?.showModal();
    closeButton.current?.focus();
    return () => {
      modal?.close(); document.body.style.overflow = overflow;
      if (trigger?.isConnected) trigger.focus({ preventScroll: true });
    };
  }, []);

  return createPortal(<dialog ref={dialog} className={styles.lightbox} aria-labelledby={titleId}
    onCancel={(event) => { event.preventDefault(); onClose(); }}
    onClick={(event) => { if (event.target === event.currentTarget) onClose(); }}
    onKeyDown={(event) => {
      if (event.key === "Tab") {
        const controls = [...event.currentTarget.querySelectorAll<HTMLButtonElement>("button:not(:disabled)")];
        const first = controls[0], last = controls.at(-1);
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
      }
      if (event.key === "ArrowLeft") { event.preventDefault(); setCurrent((value) => Math.max(0, value - 1)); }
      if (event.key === "ArrowRight") { event.preventDefault(); setCurrent((value) => Math.min(photos.length - 1, value + 1)); }
    }}>
    <div className={styles.lightboxContent}>
      <header><div><h2 id={titleId}>Fotografias do pedido</h2><p>{active?.name ?? "Prévia indisponível"}</p></div>
        <button ref={closeButton} type="button" className="mk-button mk-button--secondary" aria-label="Fechar fotografia" onClick={onClose}>Fechar ×</button>
      </header>
      <EnlargedPhoto key={active?.id ?? "unavailable"} photo={active} />
      <footer><MarkinaButton variant="secondary" disabled={current <= 0} onClick={() => setCurrent(current - 1)}>Anterior</MarkinaButton>
        <span>{current + 1} de {photos.length}</span>
        <MarkinaButton variant="secondary" disabled={current >= photos.length - 1} onClick={() => setCurrent(current + 1)}>Próxima</MarkinaButton>
      </footer>
    </div>
  </dialog>, document.body);
}

export function OrderPhotos({ folders }: { folders: OrderFolder[] }) {
  const [selected, setSelected] = useState<number | null>(null);
  const close = useCallback(() => setSelected(null), []);
  const photos = folders.flatMap((folder) => folder.items);
  return <>
    {folders.map((folder) => <section key={folder.id ?? folder.name}><h5>{folder.name}</h5>
      <ul className={styles.photoList}>{folder.items.map((photo) => <li key={photo.id}>
        <Thumbnail photo={photo} onOpen={() => setSelected(photos.findIndex((item) => item.id === photo.id))} />
        <div><strong>{photo.name}</strong><span>{money(photo.unit_price_cents)}</span></div>
      </li>)}</ul>
    </section>)}
    {selected !== null ? <OrderLightbox photos={photos} initial={selected} onClose={close} /> : null}
  </>;
}
