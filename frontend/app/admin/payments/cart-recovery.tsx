"use client";

import { type FormEvent, useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { MarkinaButton } from "../../ui-kit";
import styles from "./cart-recovery.module.css";

export type CartRecoveryStatus = { can_reopen: boolean; revision: number; reopened_at: string | null };
type Preview = { payment_id: string; revision: number; fingerprint: string; restored_quantity: number;
  quantity: number; total_cents: number; previous_total_cents: number; card_available: boolean; pix_available: boolean };
type Decision = { plan: Preview; key: string; reason: string };
const money = (cents: number) => (cents / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

function RecoveryDialog({ clientName, paymentId, status, onClose, onSuccess, onConflict }: {
  clientName: string; paymentId: string; status: CartRecoveryStatus; onClose: () => void;
  onSuccess: () => Promise<void>; onConflict: () => Promise<void>;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const cancel = useRef<HTMLButtonElement>(null);
  const locked = useRef(false);
  const decision = useRef<Decision | null>(null);
  const [plan, setPlan] = useState<Preview | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [reason, setReason] = useState("Sem retorno ou falha inconclusiva");
  const [acknowledged, setAcknowledged] = useState(false);
  const title = useId(), detail = useId(), reasonId = useId();
  const endpoint = `/api/admin/provider-payments/${encodeURIComponent(paymentId)}/cart-recovery`;

  useEffect(() => {
    const trigger = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const modal = dialog.current;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    modal?.showModal(); cancel.current?.focus();
    return () => {
      modal?.close(); document.body.style.overflow = overflow;
      if (trigger?.isConnected) trigger.focus({ preventScroll: true });
    };
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    async function preview() {
      try {
        const response = await fetch(`${endpoint}/preview`, {
          method: "POST", credentials: "same-origin", signal: controller.signal,
          headers: { "Content-Type": "application/json" }, body: JSON.stringify({ expected_revision: status.revision }),
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail ?? "Não foi possível conferir o carrinho.");
        if (!controller.signal.aborted) setPlan(result);
      } catch (failure) {
        if (!controller.signal.aborted) setError(failure instanceof Error ? failure.message : "Não foi possível conferir o carrinho.");
      } finally { if (!controller.signal.aborted) setLoading(false); }
    }
    void preview();
    return () => controller.abort();
  }, [endpoint, status.revision]);

  async function confirm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (locked.current || !plan || !acknowledged || reason.trim().length < 3) return;
    decision.current ??= { plan, key: crypto.randomUUID(), reason: reason.trim() };
    const submitted = decision.current;
    locked.current = true; setBusy(true); setError("");
    try {
      const response = await fetch(endpoint, { method: "POST", credentials: "same-origin",
        headers: { "Content-Type": "application/json" }, body: JSON.stringify({
          expected_revision: submitted.plan.revision, expected_fingerprint: submitted.plan.fingerprint,
          idempotency_key: submitted.key, reason: submitted.reason, acknowledge_remote_checkout: true,
        }) });
      const result = await response.json();
      if (!response.ok) {
        if ([403, 404, 409, 422].includes(response.status)) setPlan(null);
        if (response.status === 409) await onConflict();
        throw new Error(result.detail ?? "Não foi possível confirmar a reabertura. Tente novamente.");
      }
      await onSuccess();
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Não foi possível confirmar o resultado. Tente novamente para consultar a mesma decisão.");
    } finally { locked.current = false; setBusy(false); }
  }

  return createPortal(<dialog ref={dialog} className={styles.dialog} aria-labelledby={title} aria-describedby={detail}
    onCancel={(event) => { event.preventDefault(); if (!locked.current) onClose(); }}>
    <form onSubmit={(event) => void confirm(event)}>
      <h2 id={title}>Reabrir carrinho</h2>
      <p id={detail}>{clientName} · compra {paymentId.slice(0, 8)}</p>
      {loading ? <p role="status">Conferindo fotos e valor…</p> : null}
      {plan ? <>
        <p><strong>{plan.restored_quantity} foto(s) da compra voltarão selecionadas.</strong> A cliente não precisará escolher essas fotos novamente.</p>
        <p>O carrinho ficará com {plan.quantity} foto(s), incluindo as novas seleções, por <strong>{money(plan.total_cents)}</strong>, conforme os preços atuais.</p>
        <p>Meios disponíveis: {[plan.card_available ? "Cartão de crédito" : null, plan.pix_available ? "PIX" : null].filter(Boolean).join(" e ")}.</p>
        <label htmlFor={reasonId}>Motivo da reabertura</label>
        <input id={reasonId} required minLength={3} maxLength={100} value={reason}
          disabled={busy || Boolean(decision.current)} onChange={(event) => setReason(event.target.value)} />
        <label className={styles.acknowledgement}><input type="checkbox" checked={acknowledged} disabled={busy}
          onChange={(event) => setAcknowledged(event.target.checked)} />
          Autorizo devolver as fotos ao carrinho. Entendo que isso não encerra o checkout anterior na InfinitePay nem confirma pagamento.
        </label>
      </> : null}
      {error ? <p role="alert">{error}</p> : null}
      <div className={styles.actions}>
        <button ref={cancel} className="mk-button mk-button--secondary" type="button" disabled={busy} onClick={onClose}>Cancelar</button>
        {plan ? <MarkinaButton type="submit" disabled={loading || busy || !acknowledged || reason.trim().length < 3}>
          {busy ? "Reabrindo…" : "Confirmar e reabrir carrinho"}
        </MarkinaButton> : null}
      </div>
    </form>
  </dialog>, document.body);
}

export function CartRecoveryActions({ paymentId, state, status, clientName, onRefresh }: {
  paymentId: string; state?: string; status: CartRecoveryStatus; clientName: string; onRefresh: () => Promise<void>;
}) {
  const [open, setOpen] = useState(false);
  const [reopened, setReopened] = useState(false);
  const [message, setMessage] = useState("");
  if (status.reopened_at || reopened) return <p role="status">{message || "Carrinho reaberto. As fotos foram devolvidas à seleção da cliente; o histórico da compra foi preservado."}</p>;
  if (!status.can_reopen || !["awaiting_payment", "verification_required"].includes(state ?? "")) return null;
  return <div>
    <MarkinaButton type="button" variant="secondary" onClick={() => setOpen(true)}>Reabrir carrinho</MarkinaButton>
    {message ? <p role="status">{message}</p> : null}
    {open ? <RecoveryDialog clientName={clientName} paymentId={paymentId} status={status} onClose={() => setOpen(false)} onConflict={onRefresh}
      onSuccess={async () => {
        setOpen(false); setReopened(true);
        try { await onRefresh(); }
        catch { setMessage("Carrinho reaberto. Atualize a lista para consultar o estado atual."); }
      }} /> : null}
  </div>;
}
