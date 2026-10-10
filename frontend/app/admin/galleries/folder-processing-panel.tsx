"use client";

import { useCallback, useEffect, useId, useRef, useState } from "react";
import { AdminPhotoPreviewDialog, type AdminPhotoPreview } from "./admin-photo-preview-dialog";

type Counts = { queued: number; processing: number; ready?: number; completed?: number; failed: number; cancelled?: number };
type Processing = {
  folder_id: string; folder_name: string; preview_mode: "inherit" | "custom" | "off";
  private_folder: boolean;
  facial_mode: "inherit" | "on" | "off"; preview_strength: number;
  preview_exposure_tenths: number;
  effective_preview: { mode: string; enabled: boolean; strength: number; exposure_tenths: number };
  facial_available: boolean; facial_allowed: boolean; total_photos: number;
  preview_counts: Counts; facial_counts: Counts; comparison_photo_id: string | null;
};

const previewModes = [
  ["inherit", "Herdar da galeria"], ["custom", "Personalizar esta pasta"], ["off", "Desligar nesta pasta"],
] as const;
const facialModes = [
  ["inherit", "Herdar da galeria"], ["on", "Permitir nesta pasta"], ["off", "Pausar novos trabalhos"],
] as const;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/admin/photo-folders/${path}`, {
    credentials: "same-origin", cache: "no-store", ...init,
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(body?.detail ?? "Não foi possível concluir a operação.");
  return body as T;
}

function exposure(value: number) {
  return `${value > 0 ? "+" : ""}${(value / 10).toFixed(1).replace(".", ",")}`;
}

export function FolderProcessingPanel({ folderId, folderName, shared = false, embedded = false }:
  { folderId: string; folderName: string; shared?: boolean; embedded?: boolean }) {
  const id = useId();
  const [open, setOpen] = useState(false);
  const expanded = embedded || open;
  const [data, setData] = useState<Processing | null>(null);
  const [draft, setDraft] = useState<Processing | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [expandedPhoto, setExpandedPhoto] = useState<AdminPhotoPreview | null>(null);
  const saveVersion = useRef(0);

  const load = useCallback(async (signal?: AbortSignal) => {
    const result = await request<Processing>(`${folderId}/processing`, { signal });
    if (signal?.aborted) return;
    setData(result);
    setDraft((current) => current ?? result);
  }, [folderId]);

  useEffect(() => {
    if (!expanded) return;
    const controller = new AbortController();
    void Promise.resolve().then(() => load(controller.signal)).catch((cause) => {
      if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : "Não foi possível carregar o processamento.");
    });
    return () => controller.abort();
  }, [expanded, load]);

  const pending = (data?.preview_counts.queued ?? 0) + (data?.preview_counts.processing ?? 0)
    + (data?.facial_counts.queued ?? 0) + (data?.facial_counts.processing ?? 0);
  useEffect(() => {
    if (!expanded || !pending) return;
    const controller = new AbortController();
    const timer = window.setInterval(() => {
      void load(controller.signal).catch(() => {});
    }, 5000);
    return () => { controller.abort(); window.clearInterval(timer); };
  }, [expanded, pending, load]);

  async function save() {
    if (!draft || busy) return;
    setBusy(true); setError(""); setNotice("");
    try {
      const result = await request<Processing>(`${folderId}/processing`, {
        method: "PATCH", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ preview_mode: draft.preview_mode, facial_mode: draft.facial_mode,
          preview_strength: draft.preview_strength, preview_exposure_tenths: draft.preview_exposure_tenths }),
      });
      setData(result); setDraft(result);
      setNotice("Configuração salva. Fotos existentes podem ser processadas nesta pasta.");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Não foi possível salvar."); }
    finally { setBusy(false); }
  }

  useEffect(() => {
    if (!expanded || !data?.private_folder || !draft
      || (draft.preview_strength === data.preview_strength
        && draft.preview_exposure_tenths === data.preview_exposure_tenths)) return;
    const version = ++saveVersion.current;
    const timer = window.setTimeout(() => {
      setBusy(true); setError(""); setNotice("Aplicando novo ajuste…");
      void request<Processing>(`${folderId}/processing`, {
        method: "PATCH", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ preview_mode: "custom", facial_mode: "on",
          preview_strength: draft.preview_strength,
          preview_exposure_tenths: draft.preview_exposure_tenths }),
      }).then((result) => {
        if (version !== saveVersion.current) return;
        setData(result); setDraft(result);
        setNotice("Ajuste aplicado. As prévias serão refeitas após o reconhecimento facial, a partir das fotos originais.");
      }).catch((cause: unknown) => {
        if (version !== saveVersion.current) return;
        setDraft(data);
        setError(cause instanceof Error ? cause.message : "Não foi possível aplicar o ajuste.");
        setNotice("");
      }).finally(() => {
        if (version === saveVersion.current) setBusy(false);
      });
    }, 300);
    return () => window.clearTimeout(timer);
  }, [data, draft, expanded, folderId]);

  async function process(kind: "preview" | "facial") {
    if (busy) return;
    setBusy(true); setError(""); setNotice("");
    try {
      let cursor: string | null = null;
      let queued = 0;
      let retried = 0;
      do {
        const result: { queued: number; retried?: number; next_cursor: string | null } = await request(
          `${folderId}/processing/${kind}/${kind === "preview" ? "enqueue" : "reprocess"}${cursor ? `?after=${cursor}` : ""}`,
          { method: "POST" },
        );
        queued += result.queued;
        retried += result.retried ?? 0;
        cursor = result.next_cursor;
      } while (cursor);
      await load();
      setNotice(kind === "preview"
        ? `${queued} trabalho(s) de ajuste adicionados à fila desta pasta.`
        : `${queued} novo(s) trabalho(s) facial(is) e ${retried} retentativa(s) nesta pasta.`);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Não foi possível processar a pasta."); }
    finally { setBusy(false); }
  }

  const summary = data
    ? data.private_folder ? "" : `${data.preview_mode === "custom" ? "Prévia personalizada" : data.preview_mode === "off" ? "Prévia desligada" : "Prévia herdada"} · ${data.facial_mode === "off" ? "Face pausada" : data.facial_mode === "on" ? "Face permitida" : "Face herdada"}`
    : "Configuração da pasta";
  return <section className={`folder-processing${data?.private_folder ? " folder-processing--private" : ""}`} aria-label={`Processamento de ${folderName}`}>
    {embedded ? <div className="folder-processing__toggle folder-processing__toggle--static">
      <span className="folder-processing__icon" aria-hidden="true">✦</span>
      <span className="folder-processing__heading"><strong>Processamento da pasta</strong>{summary ? <small>{summary}</small> : null}</span>
    </div> : <button type="button" className="folder-processing__toggle" aria-expanded={open}
      aria-controls={`${id}-content`} onClick={() => { setOpen((value) => !value); setError(""); }}>
      <span className="folder-processing__icon" aria-hidden="true">✦</span>
      <span className="folder-processing__heading"><strong>Processamento da pasta</strong>{summary ? <small>{summary}</small> : null}</span>
      <span className="folder-processing__chevron" aria-hidden="true">{open ? "▴" : "▾"}</span>
    </button>}
    {expanded ? <div id={`${id}-content`} className="folder-processing__body">
      <p className="folder-processing__scope">Ajustes e ações valem somente para “{folderName}”{shared ? " e para todas as clientes atribuídas a esta pasta" : ""}.</p>
      {error ? <p role="alert" className="folder-processing__feedback folder-processing__feedback--error">{error}</p> : null}
      {notice ? <p role="status" className="folder-processing__feedback">{notice}</p> : null}
      {!draft || !data ? error
        ? <button type="button" className="secondary" onClick={() => {
          setError("");
          void load().catch((cause) => setError(cause instanceof Error ? cause.message : "Não foi possível carregar o processamento."));
        }}>Tentar novamente</button>
        : <p role="status">Carregando configuração…</p> : <>
        <div className="folder-processing__cards">
          <div className="folder-processing__card">
            <span className="folder-processing__eyebrow">01 · Processamento automático</span>
            <h4>Reconhecimento facial</h4>
            {data.private_folder ? <p>O reconhecimento facial começa automaticamente após o envio da foto, conforme o gate operacional global.</p> : <>
              <p>A pausa impede novos trabalhos nesta pasta. Índices existentes e buscas já autorizadas são preservados.</p>
              <label htmlFor={`${id}-facial`}>Comportamento da pasta</label>
              <select id={`${id}-facial`} value={draft.facial_mode} onChange={(event) => setDraft({ ...draft, facial_mode: event.target.value as Processing["facial_mode"] })}>
                {facialModes.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
            </>}
            <div className="folder-processing__metric"><strong>{data.facial_counts.completed ?? 0} concluído(s)</strong><span>de {data.total_photos} foto(s) · {data.facial_counts.failed} falha(s)</span></div>
            <progress value={Math.min(data.facial_counts.completed ?? 0, data.total_photos)} max={Math.max(1, data.total_photos)} />
            <button type="button" className="secondary" disabled={busy || !data.facial_available || !data.facial_allowed || !data.total_photos} onClick={() => void process("facial")}>{data.private_folder ? "Refazer reconhecimento" : "Retentar nesta pasta"}</button>
            {!data.facial_available ? <small>Reconhecimento indisponível na galeria ou no ambiente.</small> : null}
          </div>
          <div className="folder-processing__card">
            <span className="folder-processing__eyebrow">02 · Apresentação das fotos</span>
            <h4>Ajuste automático das prévias</h4>
            <p>{data.private_folder ? "Ajuste individual desta pasta, sempre aplicado às fotos originais." : "Parte sempre da prévia convencional; exposição e intensidade da pasta substituem as da galeria, sem somar."}</p>
            {!data.private_folder ? <>
            <label htmlFor={`${id}-preview`}>Comportamento da pasta</label>
            <select id={`${id}-preview`} value={draft.preview_mode} onChange={(event) => setDraft({ ...draft, preview_mode: event.target.value as Processing["preview_mode"] })}>
              {previewModes.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
            </> : null}
            {data.private_folder || draft.preview_mode === "custom" ? <div className="folder-processing__fields">
              <label htmlFor={`${id}-strength`}>Intensidade <strong>{draft.preview_strength}%</strong></label>
              <input id={`${id}-strength`} type="range" min={10} max={75} value={draft.preview_strength} disabled={data.private_folder && busy} onChange={(event) => setDraft({ ...draft, preview_strength: Number(event.target.value) })} />
              <label htmlFor={`${id}-exposure`}>Exposição <strong>{exposure(draft.preview_exposure_tenths)} EV</strong></label>
              <input id={`${id}-exposure`} type="range" min={-20} max={20} value={draft.preview_exposure_tenths} disabled={data.private_folder && busy} onChange={(event) => setDraft({ ...draft, preview_exposure_tenths: Number(event.target.value) })} />
            </div> : <p className="folder-processing__effective">Efetivo: {data.effective_preview.enabled ? `${data.effective_preview.strength}% · ${exposure(data.effective_preview.exposure_tenths)} EV` : "desligado"}</p>}
            <div className="folder-processing__metric"><strong>{data.preview_counts.ready ?? 0} pronta(s)</strong><span>de {data.total_photos} foto(s) · {data.preview_counts.failed} falha(s)</span></div>
            <progress value={Math.min(data.preview_counts.ready ?? 0, data.total_photos)} max={Math.max(1, data.total_photos)} />
            {!data.private_folder ? <button type="button" className="secondary" disabled={busy || !data.effective_preview.enabled || !data.total_photos} onClick={() => void process("preview")}>Processar esta pasta</button> : null}
          </div>
        </div>
        {!data.private_folder ? <div className="folder-processing__footer"><span>Alterações de configuração não reprocessam fotos antigas automaticamente.</span><button type="button" className="primary" disabled={busy} onClick={() => void save()}>{busy ? "Aguarde…" : "Salvar configuração"}</button></div> : null}
        {data.comparison_photo_id ? <div className="folder-processing__comparison"><h4>Antes e depois</h4>
          {(["before", "after"] as const).map((version) => {
            const label = version === "before" ? "Convencional" : "Ajustada";
            const src = `/api/admin/preview-adjustment/photos/${data.comparison_photo_id}/${version}`;
            return <figure key={version}><button type="button" className="photo-preview-button"
              aria-label={`Ampliar versão ${label.toLowerCase()}`} onClick={(event) => setExpandedPhoto({
                src, alt: `Prévia ${label.toLowerCase()} protegida`, name: `${folderName} · ${label}`,
                trigger: event.currentTarget,
              })}><img src={src} alt={`Prévia ${label.toLowerCase()} protegida`} /></button><figcaption>{label}</figcaption></figure>;
          })}
        </div> : null}
      </>}
    </div> : null}
    {expandedPhoto ? <AdminPhotoPreviewDialog preview={expandedPhoto} onClose={() => setExpandedPhoto(null)} /> : null}
  </section>;
}
