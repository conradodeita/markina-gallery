"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AdminPhotoPreviewDialog, type AdminPhotoPreview } from "./admin-photo-preview-dialog";
import { MarkinaButton, StatusBadge } from "../../ui-kit";

type Configuration = { enabled?: boolean; strength: number; exposure_tenths: number; generation: number; facial_mode: "on" | "off" };
type FacialIndex = {
  state: "waiting" | "processing" | "completed" | "failed";
  progress: { ready: number; total: number };
  queued: number; processing: number; failed: number; waiting_previews?: number; unindexed: number;
  rollout_available?: boolean; rollout?: { available: boolean };
  detected_faces: number;
};
type AdjustmentProgress = {
  total?: number;
  generation?: number;
  counts: { queued: number; processing: number; ready: number; failed: number; cancelled: number };
  photos?: { id: string; filename: string; status: string }[];
};
type Parameters = Pick<Configuration, "strength" | "exposure_tenths">;

type Processing = {
  revision: number; facial_mode: "on" | "off"; preview_strength: number; preview_exposure_tenths: number;
  effective_preview: { enabled: boolean }; facial_available: boolean; facial_allowed: boolean; total_photos: number;
  preview_counts: AdjustmentProgress["counts"]; facial_counts: { completed: number; queued: number; processing: number; failed: number };
  comparison_photo_id: string | null;
  facial_progress: { state: FacialIndex["state"]; total: number; waiting_previews: number; unindexed: number; detected_faces: number };
};

function presentation(result: Processing) {
  return {
    config: { enabled: result.effective_preview.enabled, strength: result.preview_strength,
      exposure_tenths: result.preview_exposure_tenths, generation: result.revision, facial_mode: result.facial_mode },
    face: { state: result.facial_progress.state, progress: { ready: result.facial_counts.completed, total: result.facial_progress.total },
      ...result.facial_counts, waiting_previews: result.facial_progress.waiting_previews, unindexed: result.facial_progress.unindexed,
      rollout_available: result.facial_available && result.facial_allowed,
      detected_faces: result.facial_progress.detected_faces },
    preview: { generation: result.revision, total: result.total_photos, counts: result.preview_counts,
      photos: result.comparison_photo_id ? [{ id: result.comparison_photo_id, filename: "Prévia pronta", status: "ready" }] : [] },
  };
}

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { credentials: "same-origin", cache: "no-store", ...init });
  const payload = await response.json().catch(() => null);
  if (!response.ok) throw new Error(payload?.detail ?? "Não foi possível concluir. Tente novamente.");
  return payload as T;
}

/** O chamador usa key=folderId para que respostas e rascunhos não migrem entre pastas. */
export function FolderProcessingPanel({ folderId, folderName, uploading = false }: {
  folderId: string; folderName: string; uploading?: boolean;
}) {
  const [configuration, setConfiguration] = useState<Configuration | null>(null);
  const [facial, setFacial] = useState<FacialIndex | null>(null);
  const [adjustment, setAdjustment] = useState<AdjustmentProgress | null>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [comparison, setComparison] = useState("");
  const [expandedPhoto, setExpandedPhoto] = useState<AdminPhotoPreview | null>(null);
  const active = useRef(true);
  const saved = useRef<Configuration | null>(null);
  const draft = useRef<Configuration | null>(null);
  const pending = useRef<Parameters | null>(null);
  const running = useRef(false);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const persistNext = useRef<() => void>(() => {});

  const load = useCallback(async (signal?: AbortSignal) => {
    const result = await api<Processing>(`/api/admin/photo-folders/${folderId}/processing`, { signal });
    const { config, face, preview } = presentation(result);
    if (!active.current || signal?.aborted) return;
    if (!pending.current && !running.current && config.generation >= (saved.current?.generation ?? 0)) {
      saved.current = config; draft.current = config; setConfiguration(config);
    }
    if (config.generation < (saved.current?.generation ?? 0) || pending.current || running.current) return;
    setFacial(face);
    if (preview.generation === undefined || preview.generation >= (saved.current?.generation ?? 0)) setAdjustment(preview);
  }, [folderId]);

  const persist = useCallback(async () => {
    if (running.current || !pending.current) return;
    const parameters = pending.current;
    pending.current = null;
    running.current = true;
    if (active.current) { setBusy(true); setMessage("Aplicando ajuste às fotos desta pasta…"); setComparison(""); }
    try {
      const result = await api<Processing>(`/api/admin/photo-folders/${folderId}/processing`, {
        method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ preview_mode: "custom", facial_mode: saved.current?.facial_mode ?? "on", preview_strength: parameters.strength, preview_exposure_tenths: parameters.exposure_tenths }),
      });
      const { config: value, preview } = presentation(result);
      saved.current = value;
      if (active.current) {
        if (!pending.current) { draft.current = value; setConfiguration(value); setAdjustment(preview); }
        setMessage("Ajuste atualizado. As prévias estão sendo refeitas a partir das fotos originais.");
      }
    } catch (error) {
      if (active.current) {
        if (!pending.current) { draft.current = saved.current; setConfiguration(saved.current); }
        setMessage(error instanceof Error ? error.message : "Não foi possível salvar o ajuste.");
      }
    } finally {
      running.current = false;
      if (active.current) { setBusy(false); void load().catch(() => {}); }
      if (pending.current) persistNext.current();
    }
  }, [folderId, load]);

  useEffect(() => {
    persistNext.current = () => { void persist(); };
    active.current = true;
    return () => {
      active.current = false;
      if (saveTimer.current) clearTimeout(saveTimer.current);
      // A troca de pasta não perde a última alteração já feita pelo fotógrafo.
      void persist();
    };
  }, [persist]);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal).catch((error: unknown) => {
      if (!controller.signal.aborted) setMessage(error instanceof Error ? error.message : "Processamento indisponível.");
    });
    return () => controller.abort();
  }, [load, uploading]);

  const facialAvailable = facial?.rollout_available ?? facial?.rollout?.available ?? false;
  const hasPendingWork = uploading || Boolean(
    facial?.queued || facial?.processing || facial?.waiting_previews
    || (facial?.unindexed && facialAvailable) || adjustment?.counts?.queued || adjustment?.counts?.processing,
  );
  useEffect(() => {
    if (!hasPendingWork) return;
    const controller = new AbortController();
    let inFlight = false;
    const timer = setInterval(() => {
      if (inFlight) return;
      inFlight = true;
      void load(controller.signal).catch(() => {
        if (!controller.signal.aborted) setMessage("Não foi possível atualizar o progresso. Tentaremos novamente.");
      }).finally(() => { inFlight = false; });
    }, 3000);
    return () => { clearInterval(timer); controller.abort(); };
  }, [hasPendingWork, load]);

  function change(parameters: Parameters) {
    if (!draft.current) return;
    const value = { ...draft.current, ...parameters };
    draft.current = value; setConfiguration(value); pending.current = parameters; setComparison("");
    setAdjustment((current) => current ? { ...current, photos: [] } : current);
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(() => { void persist(); }, 300);
  }

  async function retryFacial() {
    setRetrying(true);
    try {
      let cursor: string | null = null;
      do {
        const result: { next_cursor: string | null } = await api(`/api/admin/photo-folders/${folderId}/processing/facial/reprocess${cursor ? `?after=${cursor}` : ""}`, { method: "POST" });
        cursor = result.next_cursor;
      } while (cursor);
      if (active.current) { setMessage("Retentativa do reconhecimento iniciada."); await load(); }
    } catch (error) { if (active.current) setMessage(error instanceof Error ? error.message : "Não foi possível refazer o reconhecimento."); }
    finally { if (active.current) setRetrying(false); }
  }

  const total = facial?.progress?.total ?? 0;
  const ready = facial?.progress?.ready ?? 0;
  const counts = adjustment?.counts;
  const adjustmentTotal = adjustment?.total ?? (counts ? counts.ready + counts.queued + counts.processing + counts.failed : 0);
  const readyPhotos = adjustment?.photos?.filter((photo) => photo.status === "ready") ?? [];

  return <section className="admin-card folder-processing" aria-label={`Processamento de ${folderName}`}>
    <header className="section-heading"><div><p className="eyebrow">Processamento da pasta</p><h3>{folderName}</h3></div>
      <StatusBadge tone={facial?.failed || counts?.failed ? "warning" : "neutral"}>{busy ? "Atualizando ajuste" : !facial ? "Carregando" : hasPendingWork ? "Em andamento" : !facialAvailable && ready < total ? "Aguardando disponibilidade" : "Atualizado"}</StatusBadge>
    </header>
    <div className="folder-processing__mechanism">
      <h4>Reconhecimento facial</h4>
      <progress max={100} value={total ? Math.round(ready * 100 / total) : 0} aria-label="Progresso do reconhecimento facial" />
      <p><strong>{ready} de {total} fotos prontas</strong>{facial ? ` · ${facial.detected_faces} rostos detectados` : ""}</p>
      {facial && !facialAvailable && ready < total ? <p>O reconhecimento aguarda disponibilidade operacional global.</p> : null}
      {facial?.failed ? <p>{facial.failed} falha(s) aguardam retentativa.</p> : null}
      {facial?.failed && facialAvailable ? <MarkinaButton type="button" variant="secondary" disabled={retrying} onClick={() => void retryFacial()}>Refazer reconhecimento</MarkinaButton> : null}
    </div>
    <div className="folder-processing__mechanism">
      <h4>Ajuste automático das prévias</h4>
      {configuration?.enabled === false ? <p>O ajuste está desligado para esta pasta. Alterar os parâmetros o ativa.</p> : null}
      {configuration ? <div className="folder-preview-controls">
        <label>Intensidade: {configuration.strength}%<input aria-label="Intensidade do ajuste" type="range" min={10} max={75} step={5} value={configuration.strength}
          onChange={(event) => change({ strength: Number(event.target.value), exposure_tenths: configuration.exposure_tenths })} /></label>
        <label>Exposição: {(configuration.exposure_tenths / 10).toFixed(1)} EV<input aria-label="Exposição do ajuste" type="range" min={-20} max={20} step={1} value={configuration.exposure_tenths}
          onChange={(event) => change({ strength: configuration.strength, exposure_tenths: Number(event.target.value) })} /></label>
      </div> : <p role="status">Carregando configuração…</p>}
      <progress max={100} value={adjustmentTotal ? Math.round((counts?.ready ?? 0) * 100 / adjustmentTotal) : 0} aria-label="Progresso do ajuste automático das prévias" />
      <p><strong>{counts?.ready ?? 0} de {adjustmentTotal} prévias prontas</strong></p>
      {counts?.failed ? <p>{counts.failed} falha(s); a prévia convencional permanece disponível.</p> : null}
      <small>Alterações são aplicadas automaticamente somente a esta pasta.</small>
    </div>
    {readyPhotos.length ? <details><summary>Comparar prévias</summary>
      <label>Comparar foto<select value={comparison} onChange={(event) => setComparison(event.target.value)}><option value="">Escolha uma foto pronta</option>{readyPhotos.map((photo) => <option key={photo.id} value={photo.id}>{photo.filename}</option>)}</select></label>
      {comparison ? <div className="folder-preview-comparison">{(["before", "after"] as const).map((version) => <figure key={version}>
        <figcaption>{version === "before" ? "Convencional" : "Ajustada"}</figcaption>
        <button type="button" className="photo-preview-button" aria-label={`Ampliar versão ${version === "before" ? "convencional" : "ajustada"}`} onClick={(event) => setExpandedPhoto({
          src: `/api/admin/preview-adjustment/photos/${comparison}/${version}`,
          alt: version === "before" ? "Prévia convencional protegida" : "Prévia ajustada protegida",
          name: folderName, trigger: event.currentTarget,
        })}>
          {/* eslint-disable-next-line @next/next/no-img-element -- Comparação autenticada. */}
          <img src={`/api/admin/preview-adjustment/photos/${comparison}/${version}`} alt={version === "before" ? "Prévia convencional protegida" : "Prévia ajustada protegida"} />
        </button>
      </figure>)}</div> : null}
    </details> : null}
    {message ? <p className="form-message" role="status">{message}</p> : null}
    {!configuration && message ? <MarkinaButton type="button" onClick={() => void load().catch((error: unknown) => setMessage(error instanceof Error ? error.message : "Processamento indisponível."))}>Tentar novamente</MarkinaButton> : null}
    {expandedPhoto ? <AdminPhotoPreviewDialog preview={expandedPhoto} onClose={() => setExpandedPhoto(null)} /> : null}
  </section>;
}
