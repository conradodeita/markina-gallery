"use client";

import { type FormEvent, useRef, useState } from "react";

import { MarkinaButton, StatusBadge, SystemState } from "../../ui-kit";
import styles from "./owner-media-archive-recoveries.module.css";

export type OwnerRecovery = {
  operation_id: string;
  cycle_id: string;
  folder_id: string;
  folder_name: string;
  status: string;
  stage: string | null;
  duration_days: number;
  fee_credits: number | null;
  owner_exempt: boolean;
  requester_type: "tenant" | "owner";
  retry_of_operation_id: string | null;
  last_error_code: string | null;
  last_error: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
};

type JsonPayload = { detail?: unknown };

async function readJson(response: Response) {
  const payload = await response.json().catch(() => null) as JsonPayload | null;
  if (!response.ok) {
    throw new Error(typeof payload?.detail === "string" ? payload.detail : "Não foi possível iniciar a nova tentativa.");
  }
  return payload;
}

function dateLabel(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Data indisponível" : date.toLocaleString("pt-BR");
}

function statusLabel(status: string) {
  return ({
    queued: "Na fila", processing: "Em andamento", reconciliation_required: "Reconciliação necessária",
    failed: "Falhou", completed: "Concluída",
  } as Record<string, string>)[status] ?? status;
}

export function OwnerMediaArchiveRecoveries({
  tenantId,
  items,
  onUpdated,
}: {
  tenantId: string;
  items: OwnerRecovery[];
  onUpdated: () => void;
}) {
  const failedItems = items.filter((item) => item.status === "failed");
  const [operationId, setOperationId] = useState("");
  const [durationDays, setDurationDays] = useState(14);
  const [password, setPassword] = useState("");
  const [totp, setTotp] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const idempotencyKeys = useRef(new Map<string, string>());

  async function retry(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!operationId || saving) return;
    const keyName = `${operationId}:${durationDays}`;
    let idempotencyKey = idempotencyKeys.current.get(keyName);
    if (!idempotencyKey) {
      idempotencyKey = `archive-retry-${crypto.randomUUID()}`;
      idempotencyKeys.current.set(keyName, idempotencyKey);
    }
    setSaving(true);
    setError("");
    setMessage("");
    try {
      await readJson(await fetch(
        `/api/admin/platform/credit-tenants/${encodeURIComponent(tenantId)}/media-archive/recoveries/${encodeURIComponent(operationId)}/retry`,
        {
          method: "POST",
          credentials: "same-origin",
          cache: "no-store",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            duration_days: durationDays,
            idempotency_key: idempotencyKey,
            current_password: password,
            totp_code: totp,
          }),
        },
      ));
      idempotencyKeys.current.delete(keyName);
      setOperationId("");
      setMessage("Nova tentativa registrada. O débito só ocorrerá se a recuperação terminar completa e verificada.");
      onUpdated();
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Não foi possível iniciar a nova tentativa.");
    } finally {
      setPassword("");
      setTotp("");
      setSaving(false);
    }
  }

  return <section className={styles.section} aria-label="Recuperações de arquivo frio do tenant">
    <div className={styles.heading}>
      <div><p className="eyebrow">Arquivo frio</p><h3>Recuperações deste tenant</h3></div>
      <StatusBadge>{items.length} registro(s)</StatusBadge>
    </div>
    {items.length ? <ol className={styles.list}>
      {items.map((item) => (
        <li key={item.operation_id}>
          <div>
            <strong>{item.folder_name}</strong>
            <span>{statusLabel(item.status)} · {item.duration_days} dias · {dateLabel(item.created_at)}</span>
            <small>{item.owner_exempt ? "Isento" : `${item.fee_credits ?? "—"} créditos reservados/consumidos conforme o resultado`}</small>
            {item.last_error_code ? <small>Código: {item.last_error_code}</small> : null}
            {item.last_error ? <small>{item.last_error}</small> : null}
            {item.retry_of_operation_id ? <small>Retry da operação {item.retry_of_operation_id}</small> : null}
          </div>
          {item.status === "failed" ? <MarkinaButton type="button" variant="secondary" disabled={saving}
            onClick={() => { setOperationId(item.operation_id); setError(""); setMessage(""); }}>
            Tentar novamente
          </MarkinaButton> : null}
        </li>
      ))}
    </ol> : <SystemState title="Nenhuma recuperação registrada" detail="Pedidos, falhas e débitos desse tenant aparecerão aqui." />}

    {failedItems.length && operationId ? (
      <form className={styles.retryForm} onSubmit={(event) => void retry(event)}>
        <h4>Retry manual após falha comprovada</h4>
        <p>A mesma taxa do pedido que falhou será reservada novamente. Ela só será debitada após uma recuperação íntegra.</p>
        <label>Operação com falha
          <select required value={operationId} onChange={(event) => setOperationId(event.target.value)}>
            {failedItems.map((item) => <option key={item.operation_id} value={item.operation_id}>{item.folder_name} · {item.operation_id.slice(0, 8)}</option>)}
          </select>
        </label>
        <label>Novo prazo de acesso
          <select value={durationDays} onChange={(event) => setDurationDays(Number(event.target.value))}>
            {[7, 14, 30].map((days) => <option key={days} value={days}>{days} dias</option>)}
          </select>
        </label>
        <label>Senha atual do proprietário
          <input type="password" autoComplete="current-password" maxLength={128} required value={password} onChange={(event) => setPassword(event.target.value)} />
        </label>
        <label>Código do autenticador
          <input inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} required value={totp} onChange={(event) => setTotp(event.target.value)} />
        </label>
        <div className={styles.actions}>
          <MarkinaButton disabled={saving}>{saving ? "Registrando…" : "Confirmar retry"}</MarkinaButton>
          <MarkinaButton type="button" variant="secondary" disabled={saving} onClick={() => setOperationId("")}>Cancelar</MarkinaButton>
        </div>
      </form>
    ) : null}
    {error ? <p role="alert" className={styles.message}>{error}</p> : null}
    {message ? <p role="status" className={styles.message}>{message}</p> : null}
  </section>;
}
