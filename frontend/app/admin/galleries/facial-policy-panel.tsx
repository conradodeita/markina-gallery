"use client";

import { useCallback, useEffect, useState } from "react";

import { facialAdminApi, type FacialIndexStatus } from "../../facial-search-client";
import { MarkinaButton, StatusBadge, SystemState } from "../../ui-kit";

const stateLabels: Record<FacialIndexStatus["state"], string> = {
  processing: "Reconhecimento em processamento",
  completed: "Reconhecimento concluído",
  failed: "Reconhecimento falhou",
};

const rolloutLabels: Record<FacialIndexStatus["rollout"]["status"], string> = {
  prepared: "Rollout preparado",
  active: "Disponível nesta galeria",
  suspended: "Rollout suspenso",
  revoked: "Rollout revogado",
  unavailable: "Rollout não disponível",
};

export function FacialPolicyPanel({ galleryId, refreshToken = 0 }: { galleryId: string; refreshToken?: number }) {
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
  }, [load, refreshToken]);

  useEffect(() => {
    if (
      !index
      || index.state !== "processing"
    ) return;
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

  if (loading) return <SystemState tone="loading" title="Reconhecimento em processamento" detail="Consultando o processamento automático desta galeria." />;
  if (!index) return <SystemState tone="error" title="Reconhecimento falhou" detail={error || "Não foi possível consultar o processamento desta galeria."} />;

  const progress = index.progress ?? { ready: 0, total: 0 };
  const coverage = index.coverage ?? { photos_with_faces: 0, total: progress.total, percent: 0, detected_faces: 0 };
  const rollout = index.rollout ?? { status: "unavailable" as const, stage: null, available: false };
  const failures = Array.isArray(index.failures) ? index.failures : [];
  return (
    <section className="facial-admin-panel" aria-labelledby="facial-admin-title">
      <header>
        <div><p className="eyebrow">Processamento automático</p><h3 id="facial-admin-title">Reconhecimento facial</h3></div>
        <StatusBadge tone={index.state === "completed" ? "success" : index.state === "failed" ? "warning" : "neutral"}>{stateLabels[index.state]}</StatusBadge>
      </header>
      <p>Após o upload, as prévias limpas são indexadas uma única vez em segundo plano. A indexação administrativa trata adultos e menores da mesma forma técnica.</p>
      <div className="facial-index-progress" aria-live="polite">
        <div><span>Disponibilidade operacional</span><strong>{rolloutLabels[rollout.status]}</strong></div>
        <small>{rollout.available ? `Etapa ${rollout.stage}` : "O processamento facial não admite novos trabalhos nesta galeria."}</small>
      </div>
      <p className="field-hint">A barra reúne todas as fotos recebidas em todas as pastas desta galeria desde o início do preparo.</p>
      <p className="field-hint">A cliente decide se deseja usar uma foto temporária como filtro e confirma o consentimento no próprio acesso. A seleção manual continua disponível.</p>
      {error ? <p className="form-message form-message--error" role="alert">{error}</p> : null}
      <div className="facial-index-progress" aria-live="polite">
        <div><span>Índice da galeria</span><strong>{progress.ready} de {progress.total} fotos prontas</strong></div>
        <progress value={progress.ready} max={Math.max(progress.total, 1)} aria-label="Progresso da indexação facial" />
        <small>{index.waiting_previews ?? 0} aguardando prévias · {index.unindexed ?? 0} aguardando indexação · {index.processing ?? 0} processando · {index.queued ?? 0} na fila · {index.failed ?? 0} falhas</small>
      </div>
      {progress.total === 0 ? <p className="field-hint">Ainda não há fotos desta galeria para processar.</p> : null}
      <div className="facial-index-progress" aria-live="polite">
        <div><span>Cobertura facial do acervo</span><strong>{coverage.photos_with_faces} de {coverage.total} fotos com rosto · {coverage.percent.toLocaleString("pt-BR")}%</strong></div>
        <progress value={coverage.photos_with_faces} max={Math.max(coverage.total, 1)} aria-label="Cobertura facial do acervo" />
        <small>{coverage.detected_faces} rostos detectados. Fotos sem rosto detectável continuam contando como processamento concluído.</small>
      </div>
      {failures.length ? <div className="facial-index-failures"><strong>Falhas técnicas</strong><ul>{failures.map((failure) => <li key={failure.job_id}>Foto {failure.photo_id.slice(0, 8)} · {failure.error_category}</li>)}</ul></div> : null}
      {failures.length ? <div className="gallery-access-actions"><MarkinaButton type="button" variant="secondary" disabled={busy} onClick={() => void retryFailures()}>{busy ? "Tentando novamente…" : "Tentar falhas novamente"}</MarkinaButton></div> : null}
    </section>
  );
}
