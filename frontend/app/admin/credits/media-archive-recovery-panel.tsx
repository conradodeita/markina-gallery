"use client";

import { type FormEvent, useCallback, useEffect, useRef, useState } from "react";

import { MarkinaButton, StatusBadge, SurfaceCard, SystemState } from "../../ui-kit";
import styles from "./media-archive-recovery-panel.module.css";

type Pricing = {
  recovery_fee_credits: number | null;
  configured: boolean;
  owner_exempt: boolean;
  available_credits: number | null;
  can_manage: boolean;
};

type Candidate = {
  cycle_id: string;
  folder_id: string;
  folder_name: string;
  cycle_number: number;
  archived_at: string | null;
};

type Recovery = {
  operation_id: string;
  cycle_id: string;
  folder_id: string;
  folder_name: string;
  status: string;
  duration_days: number;
  fee_credits: number | null;
  owner_exempt: boolean;
  created_at: string;
  completed_at: string | null;
  progress?: {
    stage: "queued" | "preparing" | "downloading" | "finishing";
    verified_objects: number;
    total_objects: number;
  };
};

const RECOVERY_DAYS = 30;

type JsonPayload = { detail?: unknown };

async function readJson<T>(response: Response): Promise<T> {
  const payload = await response.json().catch(() => null) as JsonPayload | null;
  if (!response.ok) {
    throw new Error(typeof payload?.detail === "string" ? payload.detail : "Não foi possível concluir a solicitação.");
  }
  return payload as T;
}

function dateLabel(value: string | null): string {
  if (!value) return "Data indisponível";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Data indisponível" : date.toLocaleString("pt-BR");
}

function statusLabel(status: string): string {
  return ({
    queued: "Na fila",
    processing: "Em recuperação",
    reconciliation_required: "Aguardando revisão",
    failed: "Falhou",
    completed: "Concluída",
  } as Record<string, string>)[status] ?? "Em processamento";
}

function statusTone(status: string): "success" | "warning" | "neutral" {
  if (status === "completed") return "success";
  if (status === "failed" || status === "reconciliation_required") return "warning";
  return "neutral";
}

function RecoveryProgress({ item }: { item: Recovery }) {
  const progress = item.progress;
  if (!progress || !["queued", "processing"].includes(item.status)) return null;
  const { stage, verified_objects: verified, total_objects: total } = progress;
  const downloading = stage === "downloading" && total > 0 && verified < total;
  const description = ({
    queued: "Aguardando na fila",
    preparing: "Preparando a recuperação",
    downloading: `${verified} de ${total} arquivos verificados`,
    finishing: "Finalizando a liberação da pasta",
  })[stage];
  return <div className={styles.recoveryProgress}>
    <progress max={downloading ? total : 1} value={downloading ? verified : undefined}
      aria-label={`Recuperação de ${item.folder_name}. ${description}`} />
    <small>{description}</small>
  </div>;
}

function RecoveryHistory({ items }: { items: Recovery[] }) {
  if (!items.length) {
    return <SystemState title="Nenhuma recuperação solicitada" detail="Os pedidos e os débitos concluídos aparecerão aqui." />;
  }

  return <ol className={styles.history} aria-label="Histórico de recuperação de pastas">
    {items.map((item) => (
      <li key={item.operation_id} className={styles.historyItem}>
        <div>
          <strong>{item.folder_name}</strong>
          <span>{item.duration_days} dias de acesso · {dateLabel(item.created_at)}</span>
          <small>{item.owner_exempt ? "Conta do proprietário · sem débito" : `Taxa: ${item.fee_credits ?? "indisponível"} créditos`}</small>
          <RecoveryProgress item={item} />
          {item.status === "completed" ? <small>Recuperação concluída em {dateLabel(item.completed_at)}.</small> : null}
          {item.status === "failed" ? <small>A pasta continua indisponível. O proprietário pode consultar o erro e tentar novamente.</small> : null}
          {item.status === "reconciliation_required" ? <small>O resultado está sendo conferido. Os créditos permanecem reservados enquanto isso.</small> : null}
        </div>
        <StatusBadge tone={statusTone(item.status)}>{statusLabel(item.status)}</StatusBadge>
      </li>
    ))}
  </ol>;
}

export function MediaArchiveRecoveryPanel({ onWalletChange }: { onWalletChange?: () => void } = {}) {
  const [pricing, setPricing] = useState<Pricing | null>(null);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [recoveries, setRecoveries] = useState<Recovery[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [message, setMessage] = useState("");
  const [requestingCycle, setRequestingCycle] = useState<string | null>(null);
  const [feeDraft, setFeeDraft] = useState("");
  const [password, setPassword] = useState("");
  const [totp, setTotp] = useState("");
  const [pricingRequestId, setPricingRequestId] = useState("");
  const [savingPricing, setSavingPricing] = useState(false);
  const requestKeys = useRef(new Map<string, string>());
  const feeDirty = useRef(false);
  const lastRecoveryState = useRef<string | null>(null);

  const load = useCallback(async (signal?: AbortSignal) => {
    try {
      const [pricingResponse, candidatesResponse, recoveriesResponse] = await Promise.all([
        fetch("/api/admin/media-archive/recovery-pricing", {
          credentials: "same-origin", cache: "no-store", signal,
        }),
        fetch("/api/admin/media-archive/recovery-candidates", {
          credentials: "same-origin", cache: "no-store", signal,
        }),
        fetch("/api/admin/media-archive/recoveries?limit=50", {
          credentials: "same-origin", cache: "no-store", signal,
        }),
      ]);
      const [pricingResult, candidatesResult, recoveriesResult] = await Promise.all([
        readJson<Pricing>(pricingResponse),
        readJson<{ items: Candidate[] }>(candidatesResponse),
        readJson<{ items: Recovery[] }>(recoveriesResponse),
      ]);
      if (signal?.aborted) return;
      setLoadError("");
      setPricing(pricingResult);
      if (!feeDirty.current) setFeeDraft(pricingResult.recovery_fee_credits?.toString() ?? "");
      setCandidates(candidatesResult.items);
      setRecoveries(recoveriesResult.items);
      const recoveryState = JSON.stringify(recoveriesResult.items.map((item) => [item.operation_id, item.status]));
      if (lastRecoveryState.current !== null && lastRecoveryState.current !== recoveryState) {
        onWalletChange?.();
        if (recoveriesResult.items[0]?.status === "completed") setMessage("Pasta recuperada e verificada. O saldo e o histórico foram atualizados.");
        if (recoveriesResult.items[0]?.status === "failed") setMessage("A recuperação não foi concluída. Nenhum crédito foi debitado.");
      }
      lastRecoveryState.current = recoveryState;
    } catch (error) {
      if (signal?.aborted || (error instanceof DOMException && error.name === "AbortError")) return;
      setLoadError(error instanceof Error ? error.message : "Não foi possível carregar as recuperações.");
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [onWalletChange]);

  useEffect(() => {
    const controller = new AbortController();
    void Promise.resolve().then(() => load(controller.signal));
    return () => controller.abort();
  }, [load]);

  const recoveryInProgress = recoveries.some((item) => ["queued", "processing"].includes(item.status));
  useEffect(() => {
    if (!recoveryInProgress) return;
    const controller = new AbortController();
    let timer: number;
    function schedulePoll() {
      timer = window.setTimeout(async () => {
        await load(controller.signal);
        if (!controller.signal.aborted) schedulePoll();
      }, 2000);
    }
    schedulePoll();
    return () => { window.clearTimeout(timer); controller.abort(); };
  }, [recoveryInProgress, load]);

  async function requestRecovery(candidate: Candidate) {
    if (!pricing || requestingCycle) return;
    const intentKey = candidate.cycle_id;
    let key = requestKeys.current.get(intentKey);
    if (!key) {
      key = crypto.randomUUID();
      requestKeys.current.set(intentKey, key);
    }
    setRequestingCycle(candidate.cycle_id);
    setMessage("");
    setLoadError("");
    try {
      const recovery = await readJson<Recovery>(await fetch(
        `/api/admin/media-archive/cycles/${encodeURIComponent(candidate.cycle_id)}/recovery`,
        {
          method: "POST",
          credentials: "same-origin",
          cache: "no-store",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ duration_days: RECOVERY_DAYS, idempotency_key: key }),
        },
      ));
      requestKeys.current.delete(intentKey);
      setRecoveries((previous) => [
        recovery, ...previous.filter((item) => item.operation_id !== recovery.operation_id),
      ]);
      setMessage("Recuperação solicitada. Acompanhe o andamento abaixo.");
      await load();
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Não foi possível solicitar a recuperação.");
    } finally {
      setRequestingCycle(null);
    }
  }

  async function savePricing(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (savingPricing) return;
    const normalized = feeDraft.trim();
    const fee = normalized ? Number(normalized) : null;
    if (fee !== null && (!Number.isSafeInteger(fee) || fee <= 0)) {
      setLoadError("Informe uma taxa em créditos como número inteiro positivo ou deixe em branco para suspender novos pedidos.");
      return;
    }
    setSavingPricing(true);
    setLoadError("");
    setMessage("");
    const requestId = pricingRequestId || crypto.randomUUID();
    setPricingRequestId(requestId);
    try {
      const result = await readJson<Pricing>(await fetch(
        "/api/admin/platform/console/media-archive/recovery-pricing",
        {
          method: "PUT",
          credentials: "same-origin",
          cache: "no-store",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            request_id: requestId,
            recovery_fee_credits: fee,
            current_password: password,
            totp_code: totp,
          }),
        },
      ));
      setPricing(result);
      setFeeDraft(result.recovery_fee_credits?.toString() ?? "");
      feeDirty.current = false;
      setPricingRequestId("");
      setMessage(result.configured ? "Taxa global de recuperação atualizada." : "Novos pedidos pagos foram suspensos até definir uma taxa.");
      await load();
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Não foi possível salvar a taxa.");
    } finally {
      setPassword("");
      setTotp("");
      setSavingPricing(false);
    }
  }

  const activeCycles = new Set(recoveries.filter((item) =>
    ["queued", "processing", "reconciliation_required"].includes(item.status),
  ).map((item) => item.cycle_id));

  return <SurfaceCard className={styles.card}>
    <div className={styles.heading}>
      <div>
        <p className="eyebrow">Acesso às pastas arquivadas</p>
        <h2>Recuperação de arquivos frios</h2>
        <p>A pasta fica disponível por {RECOVERY_DAYS} dias a partir da conclusão da recuperação.</p>
      </div>
      {pricing?.owner_exempt ? <StatusBadge tone="success">Conta do proprietário</StatusBadge> : null}
    </div>

    {loading ? <SystemState tone="loading" title="Consultando arquivos arquivados" detail="Buscando os pedidos e a taxa atual da conta." /> : null}
    {loadError ? <p role="alert" className={styles.message}>{loadError}</p> : null}
    {message ? <p role="status" className={styles.message}>{message}</p> : null}

    {pricing?.can_manage ? (
      <section className={styles.pricing} aria-label="Configuração global da taxa de recuperação">
        <div>
          <p className="eyebrow">Configuração do proprietário</p>
          <h3>Taxa por pasta e ciclo</h3>
          <p>A taxa por pasta e ciclo só é debitada após a recuperação completa e verificada.</p>
          <p>Valor atual: <strong>{pricing.configured ? `${pricing.recovery_fee_credits} créditos` : "não configurado"}</strong></p>
        </div>
        <form className={styles.pricingForm} onSubmit={(event) => void savePricing(event)}>
          <label>Nova taxa em créditos
            <input type="number" min="1" step="1" disabled={savingPricing} value={feeDraft} onChange={(event) => {
              setFeeDraft(event.target.value);
              feeDirty.current = true;
              setPricingRequestId("");
            }} />
          </label>
          <small>Deixe em branco para suspender novos pedidos pagos.</small>
          <label>Senha atual do proprietário
            <input type="password" autoComplete="current-password" maxLength={128} required disabled={savingPricing} value={password} onChange={(event) => setPassword(event.target.value)} />
          </label>
          <label>Código do autenticador
            <input inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} required disabled={savingPricing} value={totp} onChange={(event) => setTotp(event.target.value)} />
          </label>
          <MarkinaButton disabled={savingPricing}>{savingPricing ? "Salvando…" : "Salvar taxa"}</MarkinaButton>
        </form>
      </section>
    ) : null}

    {!pricing?.owner_exempt ? (
      <p className={styles.feeNotice}>
        {pricing?.configured
          ? <>Taxa atual: <strong>{pricing.recovery_fee_credits} créditos por pasta e ciclo</strong>. O valor fica reservado durante a recuperação e só será debitado se ela terminar com sucesso. Uma nova recuperação em outro ciclo poderá gerar nova taxa.</>
          : "O proprietário ainda não configurou a taxa. Novas recuperações pagas estão indisponíveis."}
      </p>
    ) : <p className={styles.feeNotice}>A conta do proprietário segue o mesmo fluxo e prazo, sem reserva nem débito de créditos.</p>}

    <div className={styles.candidatesHeading}>
      <h3>Pastas disponíveis</h3>
      {pricing && !pricing.owner_exempt ? <span>Saldo disponível: {pricing.available_credits ?? "indisponível"} créditos</span> : null}
    </div>
    {candidates.length ? (
      <ul className={styles.candidates}>
        {candidates.map((candidate) => {
          const feeReady = Boolean(pricing?.owner_exempt || pricing?.configured);
          const recoveryFee = pricing?.recovery_fee_credits;
          const availableCredits = pricing?.available_credits;
          const hasBalance = Boolean(pricing?.owner_exempt || (
            typeof recoveryFee === "number"
            && typeof availableCredits === "number"
            && availableCredits >= recoveryFee
          ));
          const active = activeCycles.has(candidate.cycle_id);
          return <li className={styles.candidate} key={candidate.cycle_id}>
            <div>
              <strong>{candidate.folder_name}</strong>
              <span>Arquivada em {dateLabel(candidate.archived_at)}</span>
              <small>Ciclo {candidate.cycle_number}</small>
            </div>
            <div className={styles.requestControls}>
              <MarkinaButton type="button" variant="secondary"
                disabled={!feeReady || !hasBalance || active || requestingCycle !== null}
                onClick={() => void requestRecovery(candidate)}>
                {requestingCycle === candidate.cycle_id ? "Solicitando…" : active ? "Recuperação em andamento" : "Solicitar recuperação"}
              </MarkinaButton>
            </div>
            {!feeReady ? <small>Indisponível até o proprietário definir a taxa.</small> : null}
            {feeReady && !hasBalance ? <small>Saldo insuficiente. <a href="#credit-packages">Adquira um pacote de créditos</a> e tente novamente.</small> : null}
          </li>;
        })}
      </ul>
    ) : !loading && !loadError ? (
      <SystemState title="Nenhuma pasta arquivada disponível" detail="Uma pasta aparecerá aqui quando entrar em arquivo frio." />
    ) : null}

    <section className={styles.historySection}>
      <div className={styles.candidatesHeading}><h3>Pedidos de recuperação</h3><StatusBadge>{recoveries.length} registro(s)</StatusBadge></div>
      <RecoveryHistory items={recoveries} />
    </section>
  </SurfaceCard>;
}
