"use client";

import { useCallback, useEffect, useState } from "react";

import { facialAdminApi, type FacialIndexStatus } from "../../facial-search-client";
import { MarkinaButton, StatusBadge, SystemState } from "../../ui-kit";

const stateLabels: Record<FacialIndexStatus["state"], string> = {
  disabled: "Indisponível no ambiente",
  empty: "Sem fotos elegíveis",
  pending: "Preparando",
  processing: "Processando",
  ready: "Pronto",
  partial: "Parcial",
  failed: "Com falhas",
};

export function FacialPolicyPanel({ galleryId }: { galleryId: string }) {
  const [index, setIndex] = useState<FacialIndexStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      setIndex(await facialAdminApi.index(galleryId));
      setError("");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Não foi possível consultar o reconhecimento facial.");
    } finally {
      setLoading(false);
    }
  }, [galleryId]);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  useEffect(() => {
    if (!index || (!index.queued && !index.processing)) return;
    const timer = window.setTimeout(() => void load(), 1800);
    return () => window.clearTimeout(timer);
  }, [index, load]);

  async function retryFailures() {
    if (!index || busy || !index.failures.length) return;
    setBusy(true);
    setError("");
    try {
      await facialAdminApi.retry(galleryId, index.failures.map((failure) => failure.job_id));
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Não foi possível retentar o processamento facial.");
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <SystemState tone="loading" title="Consultando reconhecimento facial" detail="Verificando o processamento automático desta galeria." />;
  if (!index) return <SystemState tone="error" title="Reconhecimento facial indisponível" detail={error || "O estado seguro não está disponível neste ambiente."} />;

  const progress = index.progress ?? { ready: 0, total: 0 };
  const failures = Array.isArray(index.failures) ? index.failures : [];
  return (
    <section className="facial-admin-panel" aria-labelledby="facial-admin-title">
      <header>
        <div><p className="eyebrow">Processamento automático</p><h3 id="facial-admin-title">Reconhecimento facial</h3></div>
        <StatusBadge tone={index.state === "ready" ? "success" : index.state === "failed" || index.state === "partial" ? "warning" : "neutral"}>{stateLabels[index.state]}</StatusBadge>
      </header>
      <p>Após o upload, as prévias limpas são indexadas uma única vez em segundo plano. Não é necessário preparar ou ativar esta galeria.</p>
      <p className="field-hint">A cliente decide se deseja usar uma foto temporária como filtro e confirma o consentimento no próprio acesso. A seleção manual continua disponível.</p>
      {error ? <p className="form-message form-message--error" role="alert">{error}</p> : null}
      <div className="facial-index-progress" aria-live="polite">
        <div><span>Índice da galeria</span><strong>{progress.ready} de {progress.total} fotos prontas</strong></div>
        <progress value={progress.ready} max={Math.max(progress.total, 1)} aria-label="Progresso da indexação facial" />
        <small>{index.processing ?? 0} processando · {index.queued ?? 0} na fila · {index.failed ?? 0} falhas</small>
      </div>
      {failures.length ? <div className="facial-index-failures"><strong>Falhas técnicas</strong><ul>{failures.map((failure) => <li key={failure.job_id}>Foto {failure.photo_id.slice(0, 8)} · {failure.category}</li>)}</ul></div> : null}
      {failures.length ? <div className="gallery-access-actions"><MarkinaButton type="button" variant="secondary" disabled={busy} onClick={() => void retryFailures()}>{busy ? "Tentando novamente…" : "Tentar falhas novamente"}</MarkinaButton></div> : null}
    </section>
  );
}
