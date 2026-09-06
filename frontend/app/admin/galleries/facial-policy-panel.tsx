"use client";

import { useCallback, useEffect, useState } from "react";

import { facialAdminApi, type FacialIndexStatus, type FacialPolicy } from "../../facial-search-client";
import { MarkinaButton, StatusBadge, SystemState } from "../../ui-kit";

const requirementLabels: Record<string, string> = {
  policy: "política ainda não preparada",
  kill_switch: "recurso desligado no ambiente",
  environment: "credenciais de outro ambiente",
  legal_notice_version: "aviso jurídico divergente",
  legal_basis_reference: "base legal não configurada",
  retention_policy_version: "retenção não aprovada",
  minor_policy_version: "política infantil não aprovada",
  model_version: "modelo divergente",
  quality_version: "qualidade divergente",
  calibration_version: "calibração divergente",
  encryption_key: "chave de criptografia ausente",
  minor_gate: "processamento infantil precisa permanecer bloqueado",
};

export function FacialPolicyPanel({ galleryId }: { galleryId: string }) {
  const [policy, setPolicy] = useState<FacialPolicy | null>(null);
  const [index, setIndex] = useState<FacialIndexStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const [nextPolicy, nextIndex] = await Promise.all([
        facialAdminApi.policy(galleryId),
        facialAdminApi.index(galleryId),
      ]);
      setPolicy(nextPolicy);
      setIndex(nextIndex);
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

  async function mutate(action: "prepare" | "activate" | "suspend" | "revoke" | "retry") {
    if (!policy || busy) return;
    if (action === "revoke" && !window.confirm("Revogar a finalidade facial e eliminar índice e resultados temporários?")) return;
    setBusy(true);
    setError("");
    try {
      if (action === "prepare") await facialAdminApi.prepare(galleryId, policy);
      else if (action === "retry") await facialAdminApi.retry(galleryId, failures.map((failure) => failure.job_id));
      else await facialAdminApi.action(galleryId, action);
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Não foi possível atualizar a política facial.");
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <SystemState tone="loading" title="Consultando reconhecimento facial" detail="Verificando política, modelos e índice desta galeria." />;
  if (!policy) return <SystemState tone="error" title="Reconhecimento facial indisponível" detail={error || "A configuração segura não está disponível neste ambiente."} />;

  const missingRequirements = Array.isArray(policy.missing_requirements) ? policy.missing_requirements : ["policy"];
  const failures = Array.isArray(index?.failures) ? index.failures : [];
  const progress = index?.progress ?? { ready: 0, total: 0 };
  const canPrepare = [policy.legal_notice_version, policy.legal_basis_reference, policy.retention_policy_version, policy.minor_policy_version, policy.model_version, policy.quality_version, policy.calibration_version].every(Boolean);
  const statusLabel = policy.status === "active" ? "Ativo" : policy.status === "pending" ? "Preparado" : policy.status === "suspended" ? "Suspenso" : "Desligado";
  return (
    <section className="facial-admin-panel" aria-labelledby="facial-admin-title">
      <header>
        <div><p className="eyebrow">Filtro opcional</p><h3 id="facial-admin-title">Reconhecimento facial</h3></div>
        <StatusBadge tone={policy.status === "active" ? "success" : policy.status === "suspended" ? "warning" : "neutral"}>{statusLabel}</StatusBadge>
      </header>
      <p>As prévias são indexadas uma única vez em segundo plano. O recurso não publica fotos, não identifica pessoas como verdade e não interfere na seleção manual.</p>
      {error ? <p className="form-message form-message--error" role="alert">{error}</p> : null}
      {missingRequirements.length ? <div className="facial-admin-gates" role="status"><strong>Ativação ainda bloqueada</strong><ul>{missingRequirements.map((item) => <li key={item}>{requirementLabels[item] ?? item}</li>)}</ul></div> : null}
      <div className="facial-index-progress" aria-live="polite">
        <div><span>Índice da galeria</span><strong>{progress.ready} de {progress.total} fotos prontas</strong></div>
        <progress value={progress.ready} max={Math.max(progress.total, 1)} />
        <small>{index?.processing ?? 0} processando · {index?.queued ?? 0} na fila · {index?.failed ?? 0} falhas</small>
      </div>
      {failures.length ? <div className="facial-index-failures"><strong>Falhas técnicas</strong><ul>{failures.map((failure) => <li key={failure.job_id}>Foto {failure.photo_id.slice(0, 8)} · {failure.category}</li>)}</ul></div> : null}
      <div className="gallery-access-actions">
        {policy.status === "disabled" ? <MarkinaButton type="button" disabled={!canPrepare || busy} onClick={() => mutate("prepare")}>Preparar política</MarkinaButton> : null}
        {policy.status !== "active" && policy.status !== "disabled" ? <MarkinaButton type="button" disabled={!policy.ready_for_activation || busy} onClick={() => mutate("activate")}>Ativar filtro</MarkinaButton> : null}
        {policy.status === "active" ? <MarkinaButton type="button" variant="secondary" disabled={busy} onClick={() => mutate("suspend")}>Suspender</MarkinaButton> : null}
        {policy.status !== "disabled" ? <MarkinaButton type="button" variant="quiet" disabled={busy} onClick={() => mutate("revoke")}>Revogar e limpar</MarkinaButton> : null}
        {failures.length ? <MarkinaButton type="button" variant="secondary" disabled={busy} onClick={() => mutate("retry")}>Tentar falhas novamente</MarkinaButton> : null}
      </div>
      <small>Busca de menores permanece indisponível até haver fluxo jurídico e representação legal aprovados.</small>
    </section>
  );
}
