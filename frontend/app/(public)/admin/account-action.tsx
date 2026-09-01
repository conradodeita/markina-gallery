"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

type ActionKind = "password" | "email";

function takeTokenFromFragment() {
  const fragment = new URLSearchParams(window.location.hash.replace(/^#/, ""));
  const token = fragment.get("token") ?? "";
  window.history.replaceState(window.history.state, "", `${window.location.pathname}${window.location.search}`);
  return token;
}

async function responseDetail(response: Response, fallback: string) {
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

export function AdminAccountAction({ kind }: { kind: ActionKind }) {
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [complete, setComplete] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    const fragmentToken = takeTokenFromFragment();
    queueMicrotask(() => setToken(fragmentToken));
  }, []);

  async function resetPassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    const data = new FormData(event.currentTarget);
    const password = String(data.get("newPassword") ?? "");
    const confirmation = String(data.get("confirmation") ?? "");
    if (password !== confirmation) {
      setMessage("As senhas não coincidem.");
      return;
    }
    setLoading(true);
    setMessage("");
    const response = await fetch("/api/auth/admin/recovery/reset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({ token, new_password: password }),
    });
    const detail = await responseDetail(response, "Não foi possível redefinir a senha.");
    setLoading(false);
    setMessage(detail);
    if (response.ok) {
      setToken("");
      setComplete(true);
    }
  }

  async function confirmEmail() {
    if (!token) return;
    setLoading(true);
    setMessage("");
    const response = await fetch("/api/auth/admin/email/confirm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({ token }),
    });
    const detail = await responseDetail(response, "Não foi possível confirmar o novo e-mail.");
    setLoading(false);
    setMessage(detail);
    setToken("");
    setComplete(response.ok);
  }

  const tokenReady = token === null ? "loading" : token ? "ready" : "missing";
  return (
    <main className="auth-shell">
      <section className="auth-card" aria-labelledby="account-action-title">
        <p className="eyebrow">Markina Gallery · Fotógrafo</p>
        <h1 id="account-action-title">
          {kind === "password" ? "Crie uma nova senha" : "Confirme o novo e-mail"}
        </h1>
        {tokenReady === "loading" ? (
          <p className="intro" role="status">Preparando confirmação segura…</p>
        ) : complete ? (
          <div className="auth-form">
            <p className="intro" role="status">{message}</p>
            <p>Suas sessões anteriores foram encerradas. Entre novamente para continuar.</p>
            <Link className="primary account-action-link" href="/">Ir para o login</Link>
          </div>
        ) : tokenReady === "missing" ? (
          <div className="auth-form">
            <p className="intro" role="alert">Este link está incompleto, expirou ou já foi utilizado.</p>
            <Link className="secondary account-action-link" href="/">Voltar ao login</Link>
          </div>
        ) : kind === "password" ? (
          <form className="auth-form" onSubmit={resetPassword}>
            <p className="auth-helper">Use pelo menos 12 caracteres. Evite senhas comuns, seu e-mail e a senha atual.</p>
            <label>
              Nova senha
              <input name="newPassword" type="password" minLength={12} maxLength={128} autoComplete="new-password" required autoFocus />
            </label>
            <label>
              Confirme a nova senha
              <input name="confirmation" type="password" minLength={12} maxLength={128} autoComplete="new-password" required />
            </label>
            <button className="primary" disabled={loading}>{loading ? "Salvando…" : "Redefinir senha"}</button>
          </form>
        ) : (
          <div className="auth-form">
            <p className="intro">A alteração só será efetivada depois desta confirmação. Nenhum endereço é exibido nesta página.</p>
            <button type="button" className="primary" disabled={loading} onClick={confirmEmail}>{loading ? "Confirmando…" : "Confirmar novo e-mail"}</button>
            <Link className="secondary account-action-link" href="/">Cancelar e voltar ao login</Link>
          </div>
        )}
        {message && !complete ? <p className="form-message" role="status">{message}</p> : null}
      </section>
    </main>
  );
}
