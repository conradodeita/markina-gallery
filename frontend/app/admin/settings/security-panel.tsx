"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

type SecuritySummary = {
  email_masked: string;
  whatsapp_status: string;
  email_channel: { status: string; mode?: string };
};

type Flow = "idle" | "password-code" | "email-code" | "email-sent" | "session-ended";

async function detail(response: Response, fallback: string) {
  try {
    const payload = await response.json();
    return typeof payload.detail === "string"
      ? payload.detail
      : typeof payload.message === "string"
        ? payload.message
        : fallback;
  } catch {
    return fallback;
  }
}

function channelLabel(status: string | undefined) {
  if (status === "ready") return "Pronto";
  if (status === "sandbox") return "Sandbox (sem envio externo)";
  if (status === "connected") return "Conectado";
  return "Indisponível";
}

export default function SecurityPanel() {
  const [summary, setSummary] = useState<SecuritySummary | null>(null);
  const [loadError, setLoadError] = useState(false);
  const [flow, setFlow] = useState<Flow>("idle");
  const [challengeId, setChallengeId] = useState("");
  const [pendingPassword, setPendingPassword] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetch("/api/admin/security/summary", { credentials: "same-origin" })
      .then(async (response) => {
        if (!response.ok) throw new Error();
        const payload = await response.json();
        if (typeof payload.email_masked !== "string" || typeof payload.email_channel?.status !== "string") throw new Error();
        setSummary(payload);
      })
      .catch(() => setLoadError(true));
  }, []);

  function cancel() {
    setFlow("idle");
    setChallengeId("");
    setPendingPassword("");
    setMessage("");
  }

  async function startPasswordChange(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const newPassword = String(data.get("newPassword") ?? "");
    if (newPassword !== String(data.get("confirmation") ?? "")) {
      setMessage("As senhas não coincidem.");
      return;
    }
    setLoading(true);
    setMessage("");
    const response = await fetch("/api/admin/security/password/challenge", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ current_password: data.get("currentPassword") }),
    });
    const payloadResponse = response.clone();
    const responseMessage = await detail(response, "Não foi possível iniciar a troca de senha.");
    setLoading(false);
    setMessage(responseMessage);
    if (response.ok) {
      const payload = await payloadResponse.json().catch(() => ({}));
      setChallengeId(payload.challenge_id ?? "");
      setPendingPassword(newPassword);
      setFlow("password-code");
    }
  }

  async function confirmPassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setMessage("");
    const response = await fetch("/api/admin/security/password/confirm", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ challenge_id: challengeId, code: new FormData(event.currentTarget).get("code"), new_password: pendingPassword }),
    });
    const responseMessage = await detail(response, "Não foi possível alterar a senha.");
    setLoading(false);
    setMessage(responseMessage);
    if (response.ok) {
      setPendingPassword("");
      setChallengeId("");
      setFlow("session-ended");
    }
  }

  async function startEmailChange(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setLoading(true);
    setMessage("");
    const response = await fetch("/api/admin/security/email/challenge", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ current_password: data.get("currentPassword"), new_email: data.get("newEmail") }),
    });
    const payloadResponse = response.clone();
    const responseMessage = await detail(response, "Não foi possível iniciar a troca de e-mail.");
    setLoading(false);
    setMessage(responseMessage);
    if (response.ok) {
      const payload = await payloadResponse.json().catch(() => ({}));
      setChallengeId(payload.challenge_id ?? "");
      setFlow("email-code");
    }
  }

  async function confirmEmailOtp(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setMessage("");
    const response = await fetch("/api/admin/security/email/verify-otp", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ challenge_id: challengeId, code: new FormData(event.currentTarget).get("code") }),
    });
    const responseMessage = await detail(response, "Não foi possível validar o código.");
    setLoading(false);
    setMessage(responseMessage);
    if (response.ok) {
      setChallengeId("");
      setFlow("email-sent");
    }
  }

  return (
    <section className="admin-card security-settings" aria-labelledby="account-security-title">
      <p className="eyebrow">Acesso administrativo</p>
      <h2 id="account-security-title">Segurança da conta</h2>
      {loadError ? (
        <p className="form-message" role="alert">Não foi possível carregar o estado de segurança da conta.</p>
      ) : !summary ? (
        <p role="status">Carregando segurança da conta…</p>
      ) : (
        <>
          <div className="security-summary" aria-label="Resumo dos canais de segurança">
            <div><span>E-mail atual</span><strong>{summary.email_masked}</strong></div>
            <div><span>WhatsApp administrativo</span><strong>{channelLabel(summary.whatsapp_status)}</strong></div>
            <div><span>E-mail transacional</span><strong>{channelLabel(summary.email_channel.status)}</strong></div>
          </div>
          {summary.whatsapp_status !== "ready" ? <p className="security-warning">Conecte o WhatsApp administrativo antes de alterar senha ou e-mail.</p> : null}
          {summary.email_channel.status !== "ready" ? <p className="security-warning">O e-mail transacional ainda não está pronto para entregas externas.</p> : null}
        </>
      )}

      {flow === "session-ended" ? (
        <div className="security-result" role="status"><strong>{message}</strong><p>Todas as sessões foram encerradas por segurança.</p><Link className="primary account-action-link" href="/">Entrar novamente</Link></div>
      ) : flow === "email-sent" ? (
        <div className="security-result" role="status"><strong>{message}</strong><p>O e-mail atual continuará válido até o uso do link de confirmação.</p><button type="button" className="secondary" onClick={cancel}>Fechar</button></div>
      ) : (
        <div className="security-forms">
          <section aria-labelledby="password-security-title">
            <h3 id="password-security-title">Trocar senha</h3>
            {flow === "password-code" ? (
              <form className="gallery-settings-form" onSubmit={confirmPassword}>
                <label>Código enviado ao WhatsApp<input name="code" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} required autoFocus /></label>
                <button className="primary" disabled={loading}>{loading ? "Confirmando…" : "Confirmar nova senha"}</button>
                <button type="button" className="secondary" onClick={cancel}>Cancelar</button>
              </form>
            ) : (
              <form className="gallery-settings-form" onSubmit={startPasswordChange}>
                <label>Senha atual<input name="currentPassword" type="password" autoComplete="current-password" required /></label>
                <label>Nova senha<input name="newPassword" type="password" autoComplete="new-password" minLength={12} maxLength={128} required /></label>
                <label>Confirme a nova senha<input name="confirmation" type="password" autoComplete="new-password" minLength={12} maxLength={128} required /></label>
                <small>Use ao menos 12 caracteres; não reutilize a senha atual.</small>
                <button className="primary" disabled={loading || flow !== "idle"}>Enviar código de confirmação</button>
              </form>
            )}
          </section>
          <section aria-labelledby="email-security-title">
            <h3 id="email-security-title">Trocar e-mail</h3>
            {flow === "email-code" ? (
              <form className="gallery-settings-form" onSubmit={confirmEmailOtp}>
                <label>Código enviado ao WhatsApp<input name="code" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} required autoFocus /></label>
                <button className="primary" disabled={loading}>{loading ? "Validando…" : "Enviar confirmação por e-mail"}</button>
                <button type="button" className="secondary" onClick={cancel}>Cancelar</button>
              </form>
            ) : (
              <form className="gallery-settings-form" onSubmit={startEmailChange}>
                <label>Novo e-mail<input name="newEmail" type="email" autoComplete="email" required /></label>
                <label>Senha atual<input name="currentPassword" type="password" autoComplete="current-password" required /></label>
                <small>O endereço atual só será substituído depois da confirmação no novo e-mail.</small>
                <button className="primary" disabled={loading || flow !== "idle"}>Validar alteração pelo WhatsApp</button>
              </form>
            )}
          </section>
        </div>
      )}
      {message && flow !== "session-ended" && flow !== "email-sent" ? <p className="form-message" role="status">{message}</p> : null}
    </section>
  );
}
