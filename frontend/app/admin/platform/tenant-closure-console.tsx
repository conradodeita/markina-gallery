"use client";

import { type FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { MarkinaButton } from "../../ui-kit";
import styles from "./tenant-closure-console.module.css";

type Operation = { status: string };
type RecoveryBatch = {
  batch_id: string;
  state: string;
  duration_days: number;
  created_at: string;
  operations: Operation[];
};
type DeletionOperation = { status: string; error_code: string | null };
type DeletionBatch = {
  batch_id: string;
  state: string;
  object_count: number;
  verified_deleted_object_count: number;
  cycle_count: number;
  operations: DeletionOperation[];
  retry_available: boolean;
};
type MediaDeletionStatus = {
  eligible: boolean;
  blocker: string | null;
  confirmation_phrase: string;
  review_due: boolean;
  batch: DeletionBatch | null;
  observed_at: string;
};
type ProfileRetention = {
  state: "retained" | "reduced" | "unavailable";
  eligible: boolean;
  blocker: string | null;
  confirmation_phrase: string;
  reduced_at: string | null;
};
type ClosureStatus = {
  tenant_id: string;
  lifecycle: string;
  availability: string;
  history_state: string;
  closed_at: string | null;
  days_closed: number | null;
  review_at: string | null;
  review_due: boolean | null;
  reopen_blocker: string | null;
  previous_cycle: { closed_at: string | null; reopened_at: string | null } | null;
  batches: RecoveryBatch[];
  media_deletion: MediaDeletionStatus;
  profile_retention?: ProfileRetention;
  observed_at: string;
};

function utcDate(value: string | null) {
  if (!value) return "não disponível";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "não disponível";
  return `${new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "medium", timeStyle: "short", timeZone: "UTC",
  }).format(parsed)} UTC`;
}

function batchLabel(state: string) {
  if (state === "completed") return "Concluída";
  if (state === "processing") return "Em andamento";
  if (state === "attention_required") return "Precisa de atenção";
  return "Estado indisponível";
}

function deletionBatchLabel(state: string) {
  if (state === "queued") return "Na fila";
  if (state === "processing") return "Em andamento";
  if (state === "attention_required") return "Precisa de revisão do proprietário";
  if (state === "reconciliation_required") return "Aguardando reconciliação";
  if (state === "completed") return "Concluída";
  return "Estado indisponível";
}

function deletionBlockerLabel(value: string | null) {
  const labels: Record<string, string> = {
    tenant_unavailable: "A conta não está disponível para revisão.",
    account_not_closed: "A conta precisa estar encerrada.",
    closure_history_unavailable: "O histórico atual de encerramento não pôde ser confirmado.",
    review_not_due: "O prazo de dez anos ainda não foi atingido.",
    media_operation_pending: "Há uma operação de mídia pendente ou em reconciliação.",
    deletion_already_requested: "Já existe um pedido de exclusão para este encerramento.",
    media_already_deleted: "A mídia já foi excluída após verificação.",
    cycle_not_archived: "Ainda há pastas que não concluíram o arquivamento.",
    archive_proof_unavailable: "Não foi possível comprovar o arquivamento completo de todas as pastas.",
    catalog_incomplete: "O inventário de mídia precisa de revisão.",
    manifest_catalog_mismatch: "O inventário não confere com o comprovante de arquivamento.",
    remote_identity_unavailable: "A identidade de um arquivo não pôde ser confirmada.",
    duplicate_remote_identity: "O inventário contém referências duplicadas e precisa de revisão.",
  };
  return value ? labels[value] ?? "A exclusão está bloqueada até a revisão das condições." : "A revisão está disponível.";
}

function deletionErrorLabel(value: string | null) {
  if (!value) return null;
  const labels: Record<string, string> = {
    remote_delete_not_verified: "Um arquivo ainda apareceu após a tentativa de remoção.",
    remote_content_unverified: "O conteúdo de um arquivo não pôde ser confirmado; ele não foi removido.",
    inventory_changed: "O inventário mudou durante a operação; a exclusão foi interrompida.",
    remote_object_reappeared: "Um arquivo reapareceu durante a conferência final.",
    media_objects_pending: "A conferência da mídia não terminou antes da etapa final.",
    manifest_catalog_mismatch: "O comprovante de arquivamento não confere com o inventário.",
    catalog_incomplete: "O inventário da pasta está incompleto.",
    remote_identity_unavailable: "A identidade remota de um arquivo não pôde ser confirmada.",
  };
  return labels[value] ?? "Falha técnica registrada; consulte os detalhes operacionais restritos.";
}

function operationLabel(state: string) {
  if (state === "queued") return "Na fila";
  if (state === "processing") return "Em andamento";
  if (state === "completed") return "Concluída";
  if (state === "failed" || state === "cancelled" || state === "reconciliation_required") return "Precisa de atenção";
  return "Estado indisponível";
}

function lifecycleLabel(value: string) {
  if (value === "open") return "Aberta";
  if (value === "closing") return "Encerrando";
  if (value === "closed") return "Encerrada";
  return "Estado indisponível";
}

function reopenBlockerLabel(value: string | null) {
  if (value === "restoration_pending") return "A recuperação ainda não concluiu todas as operações.";
  if (value === "identity_confirmation_required") return "Conclua o atendimento em Recuperar acesso do fotógrafo, após conferir a identidade fora do sistema e confirmar o novo contato. Depois, solicite a reabertura separadamente.";
  if (value === "closure_history_unavailable") return "O histórico atual de encerramento não pôde ser confirmado. A reabertura está bloqueada.";
  if (value === "media_deletion_pending") return "A exclusão permanente da mídia ainda está pendente; a reabertura permanece bloqueada.";
  if (value === "media_permanently_deleted") return "A mídia fria já foi excluída. A conta não pode ser reaberta por este fluxo.";
  return "A reabertura não está disponível para este estado.";
}

function requestError(status: number) {
  if (status === 401 || status === 403) return "Não foi possível confirmar a ação. Confira sua senha e o código do autenticador.";
  if (status === 409) return "O estado mudou ou existe uma condição pendente. Atualize o acompanhamento e confira os requisitos.";
  if (status === 503) return "O serviço de autenticação está indisponível no momento. Tente novamente.";
  return "Não foi possível concluir a consulta ou ação. Tente novamente.";
}

class ClosureStatusError extends Error {}

function profileReductionBlocker(value: string | null) {
  const labels: Record<string, string> = {
    account_not_closed: "A conta precisa estar encerrada.",
    closure_history_unavailable: "O histórico de encerramento precisa ser conferido.",
    review_not_due: "Esta revisão fica disponível após dez anos do encerramento.",
    profile_unavailable: "Não há perfil cadastral disponível para esta revisão.",
    already_reduced: "CPF e endereço já não estão armazenados no perfil.",
    obligations_pending: "Há obrigações ou operações em andamento que precisam ser resolvidas antes da revisão.",
    identity_protection_unavailable: "Não foi possível confirmar a proteção da identidade para uma recuperação futura. A redução está bloqueada.",
  };
  return value ? labels[value] ?? "A revisão do cadastro está indisponível." : "";
}

function closureStatusErrorMessage(failure: unknown) {
  return failure instanceof ClosureStatusError ? failure.message
    : "Não foi possível consultar o encerramento agora. Confira sua conexão e tente novamente.";
}

function checkedClosureStatus(value: unknown, tenantId: string): ClosureStatus {
  const result = value as ClosureStatus | null;
  const validOperations = (operations: unknown) => Array.isArray(operations)
    && operations.every((operation) => operation && typeof operation.status === "string");
  if (!result || result.tenant_id !== tenantId
    || !["open", "closing", "closed"].includes(result.lifecycle)
    || !Array.isArray(result.batches)
    || !result.batches.every((batch) => batch && typeof batch.batch_id === "string" && validOperations(batch.operations))
    || !result.media_deletion || typeof result.media_deletion.eligible !== "boolean"
    || typeof result.media_deletion.confirmation_phrase !== "string"
    || (result.profile_retention !== undefined && (!result.profile_retention
      || !["retained", "reduced", "unavailable"].includes(result.profile_retention.state)
      || typeof result.profile_retention.eligible !== "boolean"
      || typeof result.profile_retention.confirmation_phrase !== "string"))
    || (result.media_deletion.batch !== null && (!result.media_deletion.batch
      || !validOperations(result.media_deletion.batch.operations)))) {
    throw new ClosureStatusError("O estado de encerramento não pôde ser confirmado. Atualize a consulta antes de realizar uma ação.");
  }
  return result;
}

export function TenantClosureConsole({ tenantId, onUpdated }: { tenantId: string; onUpdated: () => void }) {
  const [data, setData] = useState<ClosureStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [duration, setDuration] = useState<7 | 14 | 30>(14);
  const [acknowledgeRecovery, setAcknowledgeRecovery] = useState(false);
  const [acknowledgeReopen, setAcknowledgeReopen] = useState(false);
  const [acknowledgeDeletion, setAcknowledgeDeletion] = useState(false);
  const [deletionPhrase, setDeletionPhrase] = useState("");
  const [deletionPassword, setDeletionPassword] = useState("");
  const [deletionTotp, setDeletionTotp] = useState("");
  const [confirmProfileReview, setConfirmProfileReview] = useState(false);
  const [profilePhrase, setProfilePhrase] = useState("");
  const [profilePassword, setProfilePassword] = useState("");
  const [profileTotp, setProfileTotp] = useState("");
  const [password, setPassword] = useState("");
  const [totp, setTotp] = useState("");
  const batchIntent = useRef<{ requestId: string; duration: number } | null>(null);
  const deletionIntent = useRef<string | null>(null);
  const deletionRetryIntent = useRef<string | null>(null);
  const profileReductionIntent = useRef<string | null>(null);
  const reopenIntent = useRef<string | null>(null);
  const controller = useRef<AbortController | null>(null);

  const refresh = useCallback(async () => {
    controller.current?.abort();
    const current = new AbortController();
    controller.current = current;
    setLoading(true);
    setError("");
    setNotice("");
    try {
      const response = await fetch(`/api/admin/platform/console/tenants/${tenantId}/closure`, {
        credentials: "same-origin", cache: "no-store", signal: current.signal,
      });
      if (!response.ok) throw new ClosureStatusError(requestError(response.status));
      const result = checkedClosureStatus(await response.json(), tenantId);
      if (!current.signal.aborted) setData(result);
    } catch (failure) {
      if (!current.signal.aborted) {
        setData(null);
        setError(closureStatusErrorMessage(failure));
      }
    } finally {
      if (!current.signal.aborted) setLoading(false);
    }
  }, [tenantId]);

  useEffect(() => {
    const current = new AbortController();
    controller.current = current;
    void fetch(`/api/admin/platform/console/tenants/${tenantId}/closure`, {
      credentials: "same-origin", cache: "no-store", signal: current.signal,
    }).then(async (response) => {
      if (!response.ok) throw new ClosureStatusError(requestError(response.status));
      return checkedClosureStatus(await response.json(), tenantId);
    }).then((result) => {
      if (!current.signal.aborted) setData(result);
    }).catch((failure: unknown) => {
      if (!current.signal.aborted) {
        setData(null);
        setError(closureStatusErrorMessage(failure));
      }
    }).finally(() => {
      if (!current.signal.aborted) setLoading(false);
    });
    return () => current.abort();
  }, [tenantId]);

  async function send(path: string, body: object) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const response = await fetch(`/api/admin/platform/console/tenants/${tenantId}/closure/${path}`, {
        method: "POST", credentials: "same-origin", cache: "no-store",
        headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
      });
      if (!response.ok) throw new Error(requestError(response.status));
      await refresh();
      return true;
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Não foi possível concluir a ação.");
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function requestRecovery(event: FormEvent) {
    event.preventDefault();
    if (!data || data.lifecycle !== "closed" || !acknowledgeRecovery) return;
    const intent = batchIntent.current?.duration === duration ? batchIntent.current : {
      requestId: crypto.randomUUID(), duration,
    };
    batchIntent.current = intent;
    const body = { request_id: intent.requestId, duration_days: duration, current_password: password, totp_code: totp };
    setPassword(""); setTotp("");
    const succeeded = await send("recovery-batches", body);
    if (succeeded) {
      batchIntent.current = null;
      setAcknowledgeRecovery(false);
      setNotice("Solicitação de recuperação registrada. Ela não reabre a conta automaticamente.");
    }
  }

  async function reopen(event: FormEvent) {
    event.preventDefault();
    if (!data || data.lifecycle !== "closed" || data.reopen_blocker !== null || !acknowledgeReopen) return;
    const requestId = reopenIntent.current || crypto.randomUUID();
    reopenIntent.current = requestId;
    const body = { request_id: requestId, current_password: password, totp_code: totp };
    setPassword(""); setTotp("");
    const succeeded = await send("reopen", body);
    if (succeeded) {
      reopenIntent.current = null;
      setAcknowledgeReopen(false);
      setNotice("Conta reaberta. A suspensão, se existente, permanece ativa; o fotógrafo precisará entrar novamente.");
      onUpdated();
    }
  }

  async function requestMediaDeletion(event: FormEvent) {
    event.preventDefault();
    const deletion = data?.media_deletion;
    if (!data || data.lifecycle !== "closed" || !deletion?.eligible || !acknowledgeDeletion
      || deletionPhrase !== deletion.confirmation_phrase) return;
    const requestId = deletionIntent.current || crypto.randomUUID();
    deletionIntent.current = requestId;
    const body = {
      request_id: requestId,
      confirm_phrase: deletionPhrase,
      current_password: deletionPassword,
      totp_code: deletionTotp,
    };
    setDeletionPassword(""); setDeletionTotp("");
    const succeeded = await send("media-deletion", body);
    if (succeeded) {
      deletionIntent.current = null;
      setAcknowledgeDeletion(false);
      setDeletionPhrase("");
      setNotice("Pedido registrado. A mídia só será considerada excluída após a conferência remota de todos os arquivos.");
    }
  }

  async function retryMediaDeletion(event: FormEvent) {
    event.preventDefault();
    const deletion = data?.media_deletion;
    if (!data || data.lifecycle !== "closed" || !deletion?.batch?.retry_available
      || !acknowledgeDeletion || deletionPhrase !== deletion.confirmation_phrase) return;
    const requestId = deletionRetryIntent.current || crypto.randomUUID();
    deletionRetryIntent.current = requestId;
    const body = {
      request_id: requestId,
      confirm_phrase: deletionPhrase,
      current_password: deletionPassword,
      totp_code: deletionTotp,
    };
    setDeletionPassword(""); setDeletionTotp("");
    const succeeded = await send("media-deletion/retry", body);
    if (succeeded) {
      deletionRetryIntent.current = null;
      setAcknowledgeDeletion(false);
      setDeletionPhrase("");
      setNotice("Nova tentativa registrada. O CPF protegido será mantido até a verificação completa de todos os arquivos.");
    }
  }

  async function reduceProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!data?.profile_retention?.eligible || !confirmProfileReview
      || profilePhrase !== data.profile_retention.confirmation_phrase || busy) return;
    profileReductionIntent.current ??= crypto.randomUUID();
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const response = await fetch(`/api/admin/platform/console/tenants/${tenantId}/closure/profile-reduction`, {
        method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ request_id: profileReductionIntent.current, confirm_review: confirmProfileReview,
          confirm_phrase: profilePhrase, current_password: profilePassword, totp_code: profileTotp }),
      });
      if (!response.ok) { setError(requestError(response.status)); return; }
      await refresh();
      profileReductionIntent.current = null;
      setConfirmProfileReview(false);
      setProfilePhrase("");
      setNotice("CPF e endereço foram removidos do perfil. A identidade mínima, o histórico e a referência protegida para recuperação foram preservados.");
      onUpdated();
    } catch {
      setError("Não foi possível confirmar a revisão do cadastro. Atualize a consulta antes de tentar novamente.");
    } finally {
      setProfilePassword("");
      setProfileTotp("");
      setBusy(false);
    }
  }

  const deletionOperations = data?.media_deletion.batch?.operations ?? [];
  const deletionCompleted = deletionOperations.filter((item) => item.status === "completed").length;
  const deletionInProgress = deletionOperations.filter((item) => ["queued", "processing"].includes(item.status)).length;
  const deletionNeedsAttention = deletionOperations.filter((item) => ["failed", "cancelled", "reconciliation_required"].includes(item.status)).length;

  return <section className={styles.panel} aria-labelledby="tenant-closure-heading">
      <div className={styles.headingRow}>
        <div>
          <p className={styles.eyebrow}>Situação da conta</p>
          <h3 id="tenant-closure-heading">Encerramento e recuperação</h3>
        </div>
        <MarkinaButton variant="secondary" disabled={loading || busy} onClick={() => void refresh()}>Atualizar estado</MarkinaButton>
      </div>
      {loading && !data ? <p role="status">Consultando encerramento…</p> : null}
      {error ? <p className={styles.error} role="alert">{error}</p> : null}
      {notice ? <p className={styles.notice} role="status">{notice}</p> : null}
      {data ? <>
        <div className={styles.summary}>
          <p><span>Encerramento</span><strong>{lifecycleLabel(data.lifecycle)}</strong></p>
          <p><span>Disponibilidade</span><strong>{data.availability === "suspended" ? "Suspensa" : "Ativa"}</strong></p>
          {data.lifecycle === "closed" ? <>
            <p><span>Encerrada em</span><strong>{utcDate(data.closed_at)}</strong></p>
            <p><span>Tempo encerrada</span><strong>{data.days_closed === null ? "Não calculado" : `Há ${data.days_closed} dias completos`}</strong></p>
            <p><span>Revisão manual de dez anos</span><strong>{utcDate(data.review_at)}</strong></p>
          </> : null}
          {data.previous_cycle ? <p><span>Último ciclo</span><strong>Encerrado em {utcDate(data.previous_cycle.closed_at)}; reaberto em {utcDate(data.previous_cycle.reopened_at)}</strong></p> : null}
        </div>
        {data.history_state === "unavailable" ? <p className={styles.error} role="alert">O histórico deste encerramento não pôde ser confirmado. Recuperação e reabertura permanecem bloqueadas.</p> : null}
        {data.lifecycle === "closing" ? <p>O encerramento ainda está aguardando a conclusão das obrigações e do arquivamento.</p> : null}
        {data.lifecycle === "closed" && data.review_due ? <p className={styles.review} role="status">A revisão manual de dez anos está pendente. Este marco não inicia exclusão automática.</p> : null}
        {data.lifecycle === "closed" && data.review_due === false ? <p>A revisão manual começará na data indicada acima. A mídia pode ser recuperada antes desse marco.</p> : null}

        {data.lifecycle === "closed" && data.history_state === "available" ? <>
          <div className={styles.batches}>
            <h4>Recuperações desta conta</h4>
            {data.batches.length === 0 ? <p>Nenhuma solicitação de recuperação registrada neste ciclo.</p> : <ul>
              {data.batches.map((batch) => {
                const completed = batch.operations.filter((item) => item.status === "completed").length;
                const needsAttention = batch.operations.filter((item) => ["failed", "cancelled", "reconciliation_required"].includes(item.status)).length;
                return <li key={batch.batch_id}>
                  <strong>{batch.operations.length ? batchLabel(batch.state) : "Nenhuma pasta para recuperar"}</strong>
                  <span> · Prazo escolhido: {batch.duration_days} dias{batch.operations.length ? ` · ${completed}/${batch.operations.length} operações concluídas` : " · Nenhuma transferência foi necessária neste pedido."}</span>
                  {needsAttention ? <span> · {needsAttention} operação(ões) precisam de atenção</span> : null}
                  <ul>{batch.operations.map((operation, index) => <li key={`${batch.batch_id}-${index}`}>{operationLabel(operation.status)}</li>)}</ul>
                </li>;
              })}
            </ul>}
          </div>

          {data.profile_retention ? <div className={styles.deletion}>
            <h4>Revisão dos dados cadastrais</h4>
            <p>Após dez anos do encerramento, você pode remover o CPF e o endereço cifrados do perfil. Nome, e-mail, referência protegida de CPF, histórico financeiro e aceites seguem suas regras de preservação.</p>
            <p>Se a conta for reaberta depois dessa redução, o fotógrafo deverá preencher novamente CPF e endereço antes de comprar créditos.</p>
            {data.profile_retention.state === "reduced" ? <p role="status">CPF e endereço não estão armazenados no perfil.{data.profile_retention.reduced_at ? ` Revisão registrada em ${utcDate(data.profile_retention.reduced_at)}.` : ""}</p>
              : !data.profile_retention.eligible ? <p className={styles.blocker}>{profileReductionBlocker(data.profile_retention.blocker)}</p>
                : <form className={styles.actionForm} onSubmit={reduceProfile}>
                  <label className={styles.confirm}><input type="checkbox" required checked={confirmProfileReview} onChange={(event) => setConfirmProfileReview(event.target.checked)} />Confirmei que não há disputa ou obrigação de retenção que impeça esta redução.</label>
                  <label>Digite {data.profile_retention.confirmation_phrase}<input required autoComplete="off" value={profilePhrase} onChange={(event) => setProfilePhrase(event.target.value)} /></label>
                  <label>Senha para reduzir o cadastro<input type="password" autoComplete="current-password" required maxLength={128} value={profilePassword} onChange={(event) => setProfilePassword(event.target.value)} /></label>
                  <label>Código do autenticador para reduzir o cadastro<input inputMode="numeric" autoComplete="one-time-code" required pattern="[0-9]{6}" maxLength={6} value={profileTotp} onChange={(event) => setProfileTotp(event.target.value)} /></label>
                  <MarkinaButton variant="secondary" className="mk-button--danger" disabled={busy || loading || !confirmProfileReview || profilePhrase !== data.profile_retention.confirmation_phrase}>Remover CPF e endereço do perfil</MarkinaButton>
                </form>}
          </div> : null}

          <div className={styles.deletion}>
            <h4>Revisão da mídia arquivada</h4>
            <p>Esta ação é manual e permanente. Se iniciada, remove a mídia fria de todas as pastas desta conta e só conclui após conferir a ausência de cada arquivo. Pedidos, pagamentos e histórico financeiro permanecem registrados.</p>
            {data.media_deletion.batch ? <>
              <div className={styles.deletionSummary}>
                <p><span>Estado</span><strong>{deletionBatchLabel(data.media_deletion.batch.state)}</strong></p>
                <p><span>Pastas</span><strong>{data.media_deletion.batch.cycle_count}</strong></p>
                <p><span>Arquivos confirmados ausentes</span><strong>{data.media_deletion.batch.verified_deleted_object_count} de {data.media_deletion.batch.object_count}</strong></p>
              </div>
              <p role="status">{deletionCompleted} pasta(s) concluída(s), {deletionInProgress} na fila ou em andamento e {deletionNeedsAttention} com falha que requer atenção.</p>
              {deletionNeedsAttention > 0 && deletionInProgress > 0 ? <p>As demais pastas já autorizadas continuam na fila; operações com falha não são repetidas automaticamente.</p> : null}
              {data.media_deletion.batch.operations.some((item) => item.error_code) ? <ul className={styles.deletionErrors} aria-label="Falhas resumidas">
                {data.media_deletion.batch.operations.filter((item) => item.error_code).map((item, index) => <li key={`${item.status}-${index}`}>{deletionErrorLabel(item.error_code)}</li>)}
              </ul> : null}
              {data.media_deletion.batch.state === "completed" ? <p role="status">Todos os arquivos foram conferidos como ausentes. O identificador protegido de CPF foi removido do perfil. Os dados cadastrais seguem a revisão separada acima; os registros operacionais permanecem.</p> : null}
              {data.media_deletion.batch.retry_available ? <form className={styles.actionForm} onSubmit={retryMediaDeletion}>
                <h5>Retomar exclusão após revisão</h5>
                <label className={styles.confirm}><input type="checkbox" required checked={acknowledgeDeletion} onChange={(event) => setAcknowledgeDeletion(event.target.checked)} />Revisei o estado parcial e autorizo uma nova tentativa de exclusão.</label>
                <label>Digite exatamente: <strong>{data.media_deletion.confirmation_phrase}</strong><input required autoComplete="off" value={deletionPhrase} onChange={(event) => setDeletionPhrase(event.target.value)} /></label>
                <label>Senha do proprietário<input type="password" autoComplete="current-password" required maxLength={128} value={deletionPassword} onChange={(event) => setDeletionPassword(event.target.value)} /></label>
                <label>Código do autenticador<input inputMode="numeric" autoComplete="one-time-code" required pattern="[0-9]{6}" maxLength={6} value={deletionTotp} onChange={(event) => setDeletionTotp(event.target.value)} /></label>
                <MarkinaButton disabled={busy || loading || !acknowledgeDeletion || deletionPhrase !== data.media_deletion.confirmation_phrase}>Retomar exclusão</MarkinaButton>
              </form> : null}
            </> : data.media_deletion.eligible ? <form className={styles.actionForm} onSubmit={requestMediaDeletion}>
              <p role="status">Elegível para revisão manual. Nenhuma exclusão acontecerá sem esta confirmação do proprietário.</p>
              <label className={styles.confirm}><input type="checkbox" required checked={acknowledgeDeletion} onChange={(event) => setAcknowledgeDeletion(event.target.checked)} />Confirmo que entendo que a exclusão é permanente e se aplica a todas as pastas arquivadas desta conta.</label>
              <label>Digite exatamente: <strong>{data.media_deletion.confirmation_phrase}</strong><input required autoComplete="off" value={deletionPhrase} onChange={(event) => setDeletionPhrase(event.target.value)} /></label>
              <label>Senha do proprietário<input type="password" autoComplete="current-password" required maxLength={128} value={deletionPassword} onChange={(event) => setDeletionPassword(event.target.value)} /></label>
              <label>Código do autenticador<input inputMode="numeric" autoComplete="one-time-code" required pattern="[0-9]{6}" maxLength={6} value={deletionTotp} onChange={(event) => setDeletionTotp(event.target.value)} /></label>
              <MarkinaButton disabled={busy || loading || !acknowledgeDeletion || deletionPhrase !== data.media_deletion.confirmation_phrase}>Excluir mídia fria</MarkinaButton>
            </form> : <p className={styles.blocker}>{deletionBlockerLabel(data.media_deletion.blocker)}</p>}
          </div>

          <form className={styles.actionForm} onSubmit={requestRecovery}>
            <h4>Solicitar recuperação do conteúdo arquivado</h4>
            <p>A taxa configurada é fixa por pasta e ciclo; o saldo só é debitado após a recuperação verificada. Sem saldo suficiente, a operação não conclui. A capa isolada não tem cobrança adicional.</p>
            <label>Prazo de acesso após a recuperação
              <select value={duration} onChange={(event) => {
                const next = Number(event.target.value) as 7 | 14 | 30;
                setDuration(next);
                if (batchIntent.current?.duration !== next) batchIntent.current = null;
              }}>
                <option value={7}>7 dias</option><option value={14}>14 dias</option><option value={30}>30 dias</option>
              </select>
            </label>
            <label className={styles.confirm}><input type="checkbox" required checked={acknowledgeRecovery} onChange={(event) => setAcknowledgeRecovery(event.target.checked)} />Entendo que a recuperação é por pasta, depende de espaço e saldo e não reabre a conta.</label>
            <label>Senha para solicitar recuperação<input type="password" autoComplete="current-password" required maxLength={128} value={password} onChange={(event) => setPassword(event.target.value)} /></label>
            <label>Código do autenticador para solicitar recuperação<input inputMode="numeric" autoComplete="one-time-code" required pattern="[0-9]{6}" maxLength={6} value={totp} onChange={(event) => setTotp(event.target.value)} /></label>
            <MarkinaButton disabled={busy || loading || !acknowledgeRecovery}>Solicitar recuperação</MarkinaButton>
          </form>

          {data.reopen_blocker === null ? <form className={styles.actionForm} onSubmit={reopen}>
            <h4>Reabrir a conta</h4>
            <p>A conta volta a ficar aberta. Se estiver suspensa, a suspensão será mantida. Os acessos anteriores não serão restaurados.</p>
            <label className={styles.confirm}><input type="checkbox" required checked={acknowledgeReopen} onChange={(event) => setAcknowledgeReopen(event.target.checked)} />Confirmo que a mídia foi recuperada e verificada e quero reabrir esta conta.</label>
            <label>Senha para reabrir a conta<input type="password" autoComplete="current-password" required maxLength={128} value={password} onChange={(event) => setPassword(event.target.value)} /></label>
            <label>Código do autenticador para reabrir a conta<input inputMode="numeric" autoComplete="one-time-code" required pattern="[0-9]{6}" maxLength={6} value={totp} onChange={(event) => setTotp(event.target.value)} /></label>
            <MarkinaButton disabled={busy || loading || !acknowledgeReopen}>Confirmar reabertura</MarkinaButton>
          </form> : <p className={styles.blocker}>{reopenBlockerLabel(data.reopen_blocker)}</p>}
        </> : null}
        <small>Consulta UTC: {utcDate(data.observed_at)}</small>
      </> : null}
  </section>;
}
