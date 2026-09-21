"use client";

import { useEffect, useRef, useState } from "react";
import { facialSearchApi, type FaceRegion } from "./facial-search-client";

export function FaceRegionViewer({ galleryId, photo, onRegion, busy = false, searchStatus }: {
  galleryId: string;
  photo: { id: string; name: string; previewUrl: string; width?: number | null; height?: number | null };
  onRegion: (regionId: string) => void;
  busy?: boolean;
  searchStatus?: string;
}) {
  const [regions, setRegions] = useState<FaceRegion[]>([]);
  const [selecting, setSelecting] = useState(false);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [viewport, setViewport] = useState({ width: 1, height: 1 });
  const [natural, setNatural] = useState({ width: photo.width || 4, height: photo.height || 3 });
  const [message, setMessage] = useState("");
  const stage = useRef<HTMLDivElement>(null);
  const pointers = useRef(new Map<number, { x: number; y: number }>());
  const dragged = useRef(false);
  const fit = Math.min(viewport.width / natural.width, viewport.height / natural.height);
  const width = natural.width * fit, height = natural.height * fit;
  const maxX = Math.max(0, (width * zoom - viewport.width) / 2);
  const maxY = Math.max(0, (height * zoom - viewport.height) / 2);
  const x = Math.max(-maxX, Math.min(maxX, pan.x));
  const y = Math.max(-maxY, Math.min(maxY, pan.y));

  useEffect(() => {
    let active = true;
    facialSearchApi.regions(galleryId, photo.id).then((data) => {
      if (!active) return;
      setRegions(data.regions);
      setSelecting(data.regions.length > 0 && data.regions.length <= data.auto_threshold);
    }).catch(() => { if (active) setMessage("A seleção de rostos está indisponível. Você pode continuar vendo as fotos."); });
    return () => { active = false; };
  }, [galleryId, photo.id]);

  useEffect(() => {
    const element = stage.current;
    if (!element) return;
    const measure = () => setViewport({ width: element.clientWidth || 1, height: element.clientHeight || 1 });
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const visible = regions.filter((region) => {
    const left = (viewport.width - width * zoom) / 2 + x + region.x * width * zoom;
    const top = (viewport.height - height * zoom) / 2 + y + region.y * height * zoom;
    return left < viewport.width && top < viewport.height && left + region.width * width * zoom > 0 && top + region.height * height * zoom > 0;
  }).sort((a, b) => b.width * b.height - a.width * a.height);

  return <section className="face-region-viewer" aria-label="Explorar a fotografia">
    <div className="face-region-controls">
      {regions.length > 0 ? <button type="button" aria-pressed={selecting} onClick={() => setSelecting(!selecting)}>{selecting ? "Ocultar rostos" : "Encontrar uma pessoa nesta foto"}</button> : null}
      <button type="button" aria-label="Diminuir zoom" disabled={zoom <= 1} onClick={() => setZoom(Math.max(1, zoom - .5))}>−</button>
      <output aria-label="Ampliação">{Math.round(zoom * 100)}%</output>
      <button type="button" aria-label="Aumentar zoom" disabled={zoom >= 6} onClick={() => setZoom(Math.min(6, zoom + .5))}>+</button>
      <button type="button" onClick={() => { setZoom(1); setPan({ x: 0, y: 0 }); }}>Ajustar à tela</button>
    </div>
    <div ref={stage} className="face-region-stage" tabIndex={0} aria-label="Fotografia; amplie e arraste para explorar"
      onTouchStart={(event) => event.stopPropagation()} onTouchEnd={(event) => event.stopPropagation()}
      onKeyDown={(event) => {
        if (!event.key.startsWith("Arrow")) return;
        event.preventDefault(); event.stopPropagation();
        setPan({ x: x + (event.key === "ArrowLeft" ? 40 : event.key === "ArrowRight" ? -40 : 0),
          y: y + (event.key === "ArrowUp" ? 40 : event.key === "ArrowDown" ? -40 : 0) });
      }}
      onPointerDown={(event) => {
        dragged.current = false;
        pointers.current.set(event.pointerId, { x: event.clientX, y: event.clientY });
        if (!(event.target instanceof Element && event.target.closest("button"))) event.currentTarget.setPointerCapture(event.pointerId);
      }}
      onPointerMove={(event) => {
        const previous = pointers.current.get(event.pointerId);
        if (!previous) return;
        const dx = event.clientX - previous.x, dy = event.clientY - previous.y;
        if (Math.abs(dx) + Math.abs(dy) > 2) dragged.current = true;
        const other = [...pointers.current.entries()].find(([id]) => id !== event.pointerId)?.[1];
        if (other) {
          const before = Math.hypot(previous.x - other.x, previous.y - other.y);
          const after = Math.hypot(event.clientX - other.x, event.clientY - other.y);
          if (before > 0) setZoom((value) => Math.max(1, Math.min(6, value * after / before)));
        } else setPan({ x: x + dx, y: y + dy });
        pointers.current.set(event.pointerId, { x: event.clientX, y: event.clientY });
      }}
      onPointerUp={(event) => pointers.current.delete(event.pointerId)}
      onPointerCancel={(event) => pointers.current.delete(event.pointerId)}>
      <div className="face-region-image" style={{ width, height, transform: `translate(${x}px, ${y}px) scale(${zoom})` }}>
        {/* Endpoint autenticado; imagem e regiões recebem exatamente a mesma transformação. */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={photo.previewUrl} alt={`Prévia protegida ampliada de ${photo.name}`} draggable={false}
          onLoad={(event) => setNatural({ width: event.currentTarget.naturalWidth, height: event.currentTarget.naturalHeight })} />
        {selecting ? visible.map((region, index) => <button key={region.id} type="button"
          disabled={busy}
          className="face-region-target" aria-label={`Procurar pessoa no rosto ${index + 1}`}
          style={{ left: `${(region.x + region.width / 2) * 100}%`, top: `${(region.y + region.height / 2) * 100}%`,
            width: Math.max(44 / zoom, region.width * width), height: Math.max(44 / zoom, region.height * height) }}
          onClick={(event) => { event.stopPropagation(); if (!dragged.current || event.detail === 0) onRegion(region.id); }}>
          <span style={{ width: region.width * width, height: region.height * height, borderWidth: 1 / zoom }} />
        </button>) : null}
      </div>
    </div>
    {selecting ? <p className="field-hint">Toque no rosto desejado para procurar outras fotos. Amplie para separar rostos próximos.</p> : null}
    {message ? <p role="status">{message}</p> : null}
    {searchStatus ? <p role="status">{["queued", "waiting_index", "validating_reference", "searching", "ranking"].includes(searchStatus) ? "Aguarde, procurando fotos…" : searchStatus === "ready" ? "Resultados prontos." : searchStatus === "no_candidates" ? "Nenhuma possibilidade foi encontrada." : ["failed", "cancelled", "expired", "index_incomplete"].includes(searchStatus) ? "A busca não foi concluída. Toque no rosto para tentar novamente." : searchStatus}</p> : null}
  </section>;
}
