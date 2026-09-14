"use client";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import styles from "./preview-adjustment-panel.module.css";

type Configuration = { enabled: boolean; strength: number; generation: number; exposure_tenths: number };
type Photo = { id: string; filename: string };
type Progress = {
  counts: { queued: number; processing: number; ready: number; failed: number; cancelled: number };
  photos: Photo[];
  next_cursor: string | null;
};

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/admin/preview-adjustment${path}`, { cache: "no-store", ...init });
  if (!response.ok) throw new Error("Não foi possível concluir. Tente novamente.");
  return response.json();
}

export default function PreviewAdjustmentPanel({ galleryId: gallery }: { galleryId: string }) {
  const [config, setConfig] = useState<Configuration | null>(null);
  const [enabled, setEnabled] = useState(false);
  const [strength, setStrength] = useState(50);
  const [exposure, setExposure] = useState(0);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [photo, setPhoto] = useState("");
  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState(false);
  const [queuing, setQueuing] = useState(false);
  const queueAbort = useRef<AbortController | null>(null);
  const currentGallery = useRef("");

  useEffect(() => {
    currentGallery.current = gallery;
    const controller = new AbortController();
    api<Configuration>(`/galleries/${gallery}/configuration`, { signal: controller.signal }).then((value) => {
      if (controller.signal.aborted) return;
      setConfig(value); setEnabled(value.enabled); setStrength(value.strength); setExposure(value.exposure_tenths);
    }).catch(() => { if (!controller.signal.aborted) setMessage("Ajuste de prévias indisponível."); });
    return () => { controller.abort(); queueAbort.current?.abort(); };
  }, [gallery]);

  const refresh = useCallback(async (signal?: AbortSignal) => {
    if (!gallery) return;
    const result = await api<Progress>(`/galleries/${gallery}`, { signal });
    if (!signal?.aborted && currentGallery.current === gallery) setProgress(result);
  }, [gallery]);

  useEffect(() => {
    if (!gallery || !config) return;
    const controller = new AbortController();
    api<Progress>(`/galleries/${gallery}`, { signal: controller.signal })
      .then((result) => { if (!controller.signal.aborted) setProgress(result); })
      .catch(() => {
        if (!controller.signal.aborted) setMessage("Não foi possível atualizar o progresso.");
      });
    return () => controller.abort();
  }, [gallery, config, refresh]);

  const pending = (progress?.counts.queued ?? 0) + (progress?.counts.processing ?? 0);
  useEffect(() => {
    if (!config?.enabled || !gallery) return;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      refresh(controller.signal).catch(() => {
        if (!controller.signal.aborted) setMessage("Não foi possível atualizar. Use Atualizar progresso.");
      });
    }, pending ? 5000 : 15000);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [config?.enabled, pending, gallery, progress, refresh]);

  async function save(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    queueAbort.current?.abort();
    try {
      const value = await api<Configuration>(`/galleries/${gallery}/configuration`, {
        method: "PATCH", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled, strength, exposure_tenths: exposure }),
      });
      setConfig(value); setPhoto("");
      setMessage(value.enabled
        ? "Ativado para novas fotos. Para fotos existentes, use Processar galeria."
        : "Desligado. As próximas visualizações usam as prévias convencionais.");
    } catch { setMessage("Não foi possível salvar o ajuste de prévias."); }
    finally { setSaving(false); }
  }

  async function enqueueGallery() {
    const controller = new AbortController();
    queueAbort.current = controller;
    setQueuing(true);
    let cursor: string | null = null;
    let total = 0;
    try {
      do {
        const result: { queued: number; next_cursor: string | null } = await api(
          `/galleries/${gallery}/enqueue${cursor ? `?after=${cursor}` : ""}`,
          { method: "POST", signal: controller.signal },
        );
        total += result.queued;
        cursor = result.next_cursor;
        setMessage(`${total} fotos adicionadas à fila.`);
      } while (cursor && !controller.signal.aborted);
      await refresh(controller.signal);
    } catch {
      if (!controller.signal.aborted) setMessage("Agendamento interrompido. Pode tentar novamente sem duplicar fotos.");
    } finally { setQueuing(false); }
  }

  async function morePhotos() {
    if (!progress?.next_cursor) return;
    try {
      const result = await api<Progress>(`/galleries/${gallery}?after=${progress.next_cursor}`);
      if (currentGallery.current !== gallery) return;
      setProgress((previous) => previous ? {
        ...result, photos: [...previous.photos, ...result.photos.filter((item) => !previous.photos.some((p) => p.id === item.id))],
      } : result);
    } catch { setMessage("Não foi possível carregar outras fotos."); }
  }

  return <section className={`admin-card ${styles.panel}`} aria-labelledby="preview-adjustment-title">
    <div>
      <h2 id="preview-adjustment-title">Ajuste automático das prévias</h2>
      <p>Melhora a apresentação para o cliente. Originais e edição final são preservados.</p>
    </div>
    {config ? <>
      <form className={styles.controls} onSubmit={save}>
        <fieldset className={styles.fields} disabled={saving || queuing}>
        <label className={styles.toggle}>
          <input type="checkbox" checked={enabled} onChange={(event) => setEnabled(event.target.checked)} />
          Melhorar prévias automaticamente
        </label>
        <label>Intensidade: {strength}%
          <input type="range" min={10} max={75} step={5} value={strength}
            onChange={(event) => setStrength(Number(event.target.value))} />
        </label>
        <label>Exposição: {(exposure / 10).toFixed(1)} EV
          <input type="range" min={-20} max={20} step={1} value={exposure}
            onChange={(event) => setExposure(Number(event.target.value))} />
          <small>− escurecer · 0 neutro · + clarear</small>
        </label>
        <button className="primary" disabled={saving || queuing}>{saving ? "Salvando…" : "Salvar ajuste de prévias"}</button>
        </fieldset>
      </form>
      <p>{config.enabled ? "Ativo para novas fotos desta galeria." : "Desligado — prévias convencionais."} Salve e processe novamente para atualizar as fotos existentes.</p>
      <p>A exposição é aplicada depois do ajuste automático. Valores altos podem perder detalhes nas áreas claras.</p>
      <div className={styles.controls}>
        <button type="button" className="secondary" disabled={!config.enabled || !gallery || queuing || saving || config.enabled !== enabled || config.strength !== strength || config.exposure_tenths !== exposure}
          onClick={enqueueGallery}>{queuing ? "Adicionando à fila…" : "Processar galeria / tentar falhas"}</button>
        <button type="button" className="secondary" disabled={!gallery}
          onClick={() => refresh().catch(() => setMessage("Não foi possível atualizar o progresso."))}>Atualizar progresso</button>
      </div>
      {config.enabled !== enabled || config.strength !== strength || config.exposure_tenths !== exposure
        ? <p role="status">Salve os ajustes antes de processar.</p> : null}
      {progress ? <>
        <p role="status">{progress.counts.ready} prontas · {progress.counts.queued} na fila · {progress.counts.processing} processando · {progress.counts.failed} falhas</p>
        <p>Se o ajuste falhar, o cliente continua vendo a prévia convencional.</p>
        {config.enabled && progress.photos.length ? <>
          <label className={styles.photoSelect}>Comparar foto<select value={photo} onChange={(event) => setPhoto(event.target.value)}>
            <option value="">Escolha uma foto pronta</option>
            {progress.photos.map((item) => <option key={item.id} value={item.id}>{item.filename}</option>)}
          </select></label>
          {progress.next_cursor ? <button type="button" className="secondary" onClick={morePhotos}>Mais fotos prontas</button> : null}
        </> : null}
      </> : null}
      {photo && config.enabled ? <div className={styles.comparison} key={`${photo}-${config.generation}`}>
        {(["before", "after"] as const).map((version) => <figure key={version}>
          <figcaption>{version === "before" ? "Antes" : "Depois"}</figcaption>
          {/* eslint-disable-next-line @next/next/no-img-element -- Prévia privada autenticada e sem cache público. */}
          <img src={`/api/admin/preview-adjustment/photos/${photo}/${version}?generation=${config.generation}`}
            alt={version === "before" ? "Prévia convencional protegida" : "Prévia ajustada protegida"}
            onError={() => setMessage("Comparação indisponível. Atualize o progresso ou reprocesse a galeria.")} />
        </figure>)}
      </div> : null}
    </> : null}
    {message ? <p role="status">{message}</p> : null}
  </section>;
}
