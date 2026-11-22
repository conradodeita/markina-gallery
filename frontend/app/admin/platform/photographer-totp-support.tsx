"use client";

import { type FormEvent, useEffect, useRef, useState } from "react";
import { MarkinaButton } from "../../ui-kit";
import styles from "./photographer-access-recovery.module.css";

type Reason = "lost_device" | "authenticator_unavailable" | "assisted_recovery";
type Target = { available: false } | { available: true; admin_id: string; email_masked: string; totp_enabled: boolean; version: string | null };
type Intent = { requestId: string; adminId: string; version: string; reason: Reason };

export function supportReasonLabel(reason: string) {
  if (reason === "lost_device") return "Perda de aparelho";
  if (reason === "authenticator_unavailable") return "Autenticador indisponível";
  if (reason === "assisted_recovery") return "Recuperação assistida de acesso";
  return "Motivo indisponível";
}

export function PhotographerTotpSupport({ tenantId }: { tenantId: string }) {
  const [target, setTarget] = useState<Target | null>(null);
  const [reason, setReason] = useState<Reason | "">("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const controller = useRef<AbortController | null>(null);
  const pending = useRef<Intent | null>(null);
  useEffect(() => () => controller.current?.abort(), []);

  async function lookup() {
    controller.current?.abort();
    const active = new AbortController(); controller.current = active;
    setBusy(true); setTarget(null);
    try {
      const response = await fetch(`/api/admin/platform/console/tenants/${tenantId}/totp-support`, {
        cache: "no-store", credentials: "same-origin", signal: active.signal,
      });
      if (!response.ok) throw new Error();
      const data = await response.json();
      if (active.signal.aborted) return;
      if (data.available === false) { setTarget({ available: false }); return; }
      if (data.available !== true || typeof data.admin_id !== "string" || typeof data.email_masked !== "string"
        || typeof data.totp_enabled !== "boolean" || (data.version !== null && (typeof data.version !== "string" || !/^[0-9a-f]{64}$/.test(data.version)))) throw new Error();
      setTarget(data);
    } catch { if (!active.signal.aborted) setMessage("Não foi possível consultar a recuperação desta conta. Verifique seu acesso e tente novamente."); }
    finally { if (!active.signal.aborted) setBusy(false); }
  }

  async function revoke(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!target?.available || !target.totp_enabled || !target.version || !reason) return;
    const form = event.currentTarget;
    const fields = new FormData(form);
    const previous = pending.current;
    if (!previous || previous.adminId !== target.admin_id || previous.version !== target.version || previous.reason !== reason) {
      pending.current = { requestId: crypto.randomUUID(), adminId: target.admin_id, version: target.version, reason };
    }
    const intent = pending.current!;
    const body = JSON.stringify({ request_id: intent.requestId, reason_code: intent.reason, expected_version: intent.version,
      current_password: fields.get("supportPassword"), totp_code: fields.get("supportTotp") });
    form.reset(); setBusy(true); setMessage("");
    const active = new AbortController(); controller.current = active;
    try {
      const response = await fetch(`/api/admin/platform/console/tenants/${tenantId}/photographers/${target.admin_id}/revoke-totp`, {
        method: "POST", credentials: "same-origin", cache: "no-store", signal: active.signal,
        headers: { "Content-Type": "application/json" }, body,
      });
      if (active.signal.aborted) return;
      if (!response.ok) {
        if (response.status === 401 || response.status === 403) setTarget(null);
        throw new Error();
      }
      const result = await response.json();
      if (!result.completed) throw new Error();
      pending.current = null;
      setMessage("Autenticador revogado. Sessões encerradas e aviso ao e-mail enfileirado.");
      await lookup();
    } catch { if (!active.signal.aborted) setMessage("Não foi possível confirmar a operação. Consulte novamente o estado antes de tentar."); }
    finally { if (!active.signal.aborted) setBusy(false); }
  }

  return <section className={`${styles.panel} ${styles.factorPanel}`} aria-labelledby="totp-assistance-title">
    <h3 id="totp-assistance-title">Recuperação assistida do autenticador</h3>
    <p>Consulte o acesso do fotógrafo selecionado para atender uma perda de aparelho ou dificuldade com o autenticador.</p>
    <MarkinaButton type="button" disabled={busy} onClick={() => { setMessage(""); void lookup(); }}>Consultar recuperação de acesso</MarkinaButton>
    {target?.available === false ? <p>Esta conta não está disponível para recuperação assistida do autenticador.</p> : null}
    {target?.available ? <>
      <p>Conta: {target.email_masked}</p>
      {target.totp_enabled && target.version ? <form onSubmit={revoke}>
        <p>Confirme com sua senha e seu autenticador de proprietário. A revogação encerra as sessões do fotógrafo e permite voltar ao login por senha.</p>
        <label>Motivo do atendimento<select required value={reason} onChange={(event) => setReason(event.target.value as Reason | "")}>
          <option value="">Selecione o motivo</option>
          {(["lost_device", "authenticator_unavailable", "assisted_recovery"] as Reason[]).map((value) => <option key={value} value={value}>{supportReasonLabel(value)}</option>)}
        </select></label>
        <label>Sua senha para este atendimento<input name="supportPassword" type="password" autoComplete="current-password" maxLength={128} required /></label>
        <label>Seu código do autenticador para este atendimento<input name="supportTotp" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} required /></label>
        <MarkinaButton disabled={busy || !reason}>{busy ? "Confirmando…" : "Revogar autenticador do fotógrafo"}</MarkinaButton>
      </form> : <p>{target.totp_enabled ? "O estado do fator não pôde ser confirmado para revogação." : "O autenticador está desativado. O acesso continua sujeito ao estado da conta."}</p>}
    </> : null}
    {message ? <p role="status">{message}</p> : null}
  </section>;
}
