"use client";

import { type FormEvent, useEffect, useRef, useState } from "react";

import { MarkinaButton } from "../../ui-kit";
import styles from "./photographer-access-recovery.module.css";

type Recovery = { request_id: string; state: "email_pending" | "email_verified" | "completed" | "expired";
  created_at: string; expires_at: string; reset_totp: boolean; reason_code: string };
type Target = { available: true; version: string; email_masked: string; totp_enabled: boolean; requests: Recovery[] };
const labels: Record<Recovery["state"], string> = {
  email_pending: "Aguardando confirmação do novo e-mail",
  email_verified: "E-mail confirmado — aguardando conclusão",
  completed: "Recuperação concluída",
  expired: "Atendimento expirado",
};

export function PhotographerAccessRecovery({ tenantId }: { tenantId: string }) {
  const [target, setTarget] = useState<Target | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const controller = useRef<AbortController | null>(null);
  const intent = useRef<{ key: string; request_id: string } | null>(null);
  const base = `/api/admin/platform/console/tenants/${tenantId}/access-recovery`;
  useEffect(() => () => controller.current?.abort(), []);

  async function lookup() {
    controller.current?.abort();
    const active = new AbortController(); controller.current = active;
    setBusy(true); setTarget(null); setUnavailable(false);
    try {
      const response = await fetch(base, { credentials: "same-origin", cache: "no-store", signal: active.signal });
      if (!response.ok) throw new Error();
      const data = await response.json();
      if (active.signal.aborted) return;
      if (data.available === false) { setUnavailable(true); return; }
      if (data.available !== true || typeof data.version !== "string" || !/^[0-9a-f]{64}$/.test(data.version)
        || typeof data.email_masked !== "string" || typeof data.totp_enabled !== "boolean" || !Array.isArray(data.requests)
        || data.requests.length > 10 || data.requests.some((row: Recovery) => typeof row.request_id !== "string"
          || !Object.hasOwn(labels, row.state) || typeof row.created_at !== "string" || typeof row.expires_at !== "string")) throw new Error();
      setTarget(data);
    } catch { if (!active.signal.aborted) setMessage("Não foi possível consultar os atendimentos. Confira seu acesso e tente novamente."); }
    finally { if (!active.signal.aborted) setBusy(false); }
  }

  async function send(path: string, body: object) {
    const active = new AbortController(); controller.current = active;
    setBusy(true); setMessage("");
    try {
      const response = await fetch(path, { method: "POST", credentials: "same-origin", cache: "no-store",
        headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), signal: active.signal });
      if (active.signal.aborted) return false;
      if (!response.ok) {
        if ([401, 403].includes(response.status)) setTarget(null);
        throw new Error();
      }
      return true;
    } catch { if (!active.signal.aborted) setMessage("Não foi possível confirmar o resultado. Consulte o atendimento antes de repetir a operação."); return false; }
    finally { if (!active.signal.aborted) setBusy(false); }
  }

  async function start(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!target) return;
    const fields = new FormData(event.currentTarget);
    const body = { expected_version: target.version, new_email: String(fields.get("recoveryEmail") || ""),
      identity_confirmed: fields.get("externalIdentity") === "on", reason_code: String(fields.get("recoveryReason")),
      reset_totp: fields.get("resetLostTotp") === "on" };
    const key = JSON.stringify(body);
    if (intent.current?.key !== key) intent.current = { key, request_id: crypto.randomUUID() };
    if (await send(base, { ...body, request_id: intent.current!.request_id })) {
      intent.current = null;
      await lookup();
      setMessage("Atendimento registrado. O fotógrafo precisa confirmar o novo e-mail e definir a senha antes da sua conclusão.");
    }
  }

  async function commit(event: FormEvent<HTMLFormElement>, requestId: string) {
    event.preventDefault();
    const form = event.currentTarget;
    const fields = new FormData(form);
    const body = { current_password: fields.get("recoveryOwnerPassword"), totp_code: fields.get("recoveryOwnerTotp") };
    form.reset();
    if (await send(`${base}/${requestId}/commit`, body)) {
      await lookup();
      setMessage("Credenciais atualizadas. Encerramento e suspensão continuam conforme o estado da conta.");
    }
  }

  return <section className={styles.panel} aria-labelledby="access-recovery-title" aria-busy={busy}>
    <header className={styles.heading}>
      <span className={styles.eyebrow}>Atendimento do proprietário</span>
      <h3 id="access-recovery-title">Recuperar acesso do fotógrafo</h3>
      <p>Um caminho seguro quando o fotógrafo perde os meios de acesso à conta.</p>
    </header>
    <ol className={styles.steps} aria-label="Etapas da recuperação assistida">
      <li><span aria-hidden="true">1</span><div><strong>Você confere</strong><small>Verifique a identidade fora do sistema.</small></div></li>
      <li><span aria-hidden="true">2</span><div><strong>O fotógrafo confirma</strong><small>Valida o e-mail e escolhe a própria senha.</small></div></li>
      <li><span aria-hidden="true">3</span><div><strong>Você conclui</strong><small>Autoriza a troca com sua senha e autenticador.</small></div></li>
    </ol>
    <details className={styles.guidance}><summary>Quando usar este atendimento?</summary>
      <p>Priorize o e-mail verificado e os meios de recuperação já disponíveis. Use este atendimento quando precisar verificar a identidade pessoalmente, fora do sistema.</p>
      <p>Nome, CPF, telefone cadastrado e número conectado ao WhatsApp não comprovam identidade por si só. Não envie documentos ou fotos por este painel.</p>
    </details>
    <MarkinaButton type="button" variant="secondary" disabled={busy} onClick={() => { setMessage(""); void lookup(); }}>Consultar atendimentos de recuperação</MarkinaButton>
    {unavailable ? <p>Esta conta não está disponível para este atendimento. A identidade do proprietário e contas legadas possuem caminhos próprios.</p> : null}
    {target ? <>
      <p>Contato atual: {target.email_masked}</p>
      <details open={target.requests.length === 0}>
      <summary>Iniciar novo atendimento de recuperação</summary>
      <form onSubmit={start}>
        <label>Novo e-mail do fotógrafo<input name="recoveryEmail" type="email" autoComplete="off" maxLength={320} required /></label>
        <label>Motivo<select name="recoveryReason" required><option value="lost_email">Perda do e-mail anterior</option><option value="lost_all_access">Perda de todos os meios de acesso</option></select></label>
        <label><input name="externalIdentity" type="checkbox" required />Confirmei fora do sistema a identidade deste fotógrafo e autorizo iniciar o atendimento.</label>
        {target.totp_enabled ? <label><input name="resetLostTotp" type="checkbox" />O fotógrafo também perdeu o autenticador. Revogar esse fator somente ao concluir.</label> : null}
        <p>O link tem validade de 15 minutos. O fotógrafo define sua própria senha; você não a recebe. E-mail e senha anteriores só serão substituídos na confirmação final.</p>
        <MarkinaButton disabled={busy}>Solicitar link para o novo e-mail</MarkinaButton>
      </form>
      </details>
      <h4>Atendimentos recentes</h4>
      {target.requests.length ? <ul>{target.requests.map((row) => <li key={row.request_id} data-state={row.state}>
        <span className={styles.badge}>{labels[row.state]}</span>
        <small>Iniciado em {new Date(row.created_at).toLocaleString("pt-BR")}</small>
        {row.state === "email_pending" || row.state === "email_verified" ? <>
          <p>{row.state === "email_pending" ? "Próximo passo: o fotógrafo confirma o link recebido e escolhe a senha." : "Próximo passo: confira o atendimento e autorize a troca abaixo."}</p>
          <small>Válido até {new Date(row.expires_at).toLocaleString("pt-BR")}. Consulte novamente para atualizar.</small>
          <p className={styles.factor}>{row.reset_totp ? "O autenticador perdido será desativado na conclusão." : "O autenticador atual será preservado."}</p>
        </> : null}
        {row.state === "email_verified" ? <form onSubmit={(event) => void commit(event, row.request_id)}>
          <p>Concluir troca o e-mail e a senha, encerra sessões anteriores e registra sua decisão. Não reabre uma conta encerrada nem retira suspensão.</p>
          <label>Sua senha de proprietário<input name="recoveryOwnerPassword" type="password" autoComplete="current-password" maxLength={128} required /></label>
          <label>Seu código do autenticador<input name="recoveryOwnerTotp" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} required /></label>
          <MarkinaButton disabled={busy}>Concluir recuperação de acesso</MarkinaButton>
        </form> : null}
      </li>)}</ul> : <p>Nenhum atendimento registrado.</p>}
    </> : null}
    {message ? <p role="status">{message}</p> : null}
  </section>;
}
