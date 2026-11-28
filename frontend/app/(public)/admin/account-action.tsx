"use client";

import Link from "next/link";
import { type FormEvent, useEffect, useRef, useState } from "react";
import { BrandLogo } from "../../brand-logo";
import styles from "../../auth-entry.module.css";

type ActionKind = "password" | "email" | "assisted";
const actionTitles = {
  assisted: "Confirme seu e-mail e escolha uma senha",
  password: "Crie uma nova senha",
  email: "Confirme o novo e-mail",
} as const;

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
  const tokenRead = useRef(false);

  useEffect(() => {
    if (tokenRead.current) return;
    tokenRead.current = true;
    const fragmentToken = takeTokenFromFragment();
    queueMicrotask(() => setToken(fragmentToken));
  }, []);

  async function resetPassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    const data = new FormData(event.currentTarget);
    const password = String(data.get("newPassword") ?? "");
    const confirmation = String(data.get("confirmation") ?? "");
    const secondFactor = String(data.get("secondFactor") ?? "").trim();
    if (password !== confirmation) {
      setMessage("As senhas não coincidem.");
      return;
    }
    setLoading(true);
    setMessage("");
    try {
      const response = await fetch(kind === "assisted" ? "/api/auth/photographer-access-recovery/confirm" : "/api/auth/admin/recovery/reset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({ token, new_password: password, ...(kind === "password" && secondFactor ? { second_factor_code: secondFactor } : {}) }),
      });
      const detail = await responseDetail(response, "Não foi possível redefinir a senha.");
      setMessage(detail);
      if (response.ok) {
        setToken("");
        setComplete(true);
      }
    } catch {
      setMessage("Não foi possível confirmar o resultado. Verifique sua conexão antes de tentar novamente.");
    } finally {
      setLoading(false);
    }
  }

  async function confirmEmail() {
    if (!token) return;
    setLoading(true);
    setMessage("");
    try {
      const response = await fetch("/api/auth/admin/email/confirm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({ token }),
      });
      const detail = await responseDetail(response, "Não foi possível confirmar o novo e-mail.");
      setMessage(detail);
      if (response.ok) {
        setToken("");
        setComplete(true);
      }
    } catch {
      setMessage("Não foi possível confirmar o resultado. Verifique sua conexão antes de tentar novamente.");
    } finally {
      setLoading(false);
    }
  }

  const tokenReady = token === null ? "loading" : token ? "ready" : "missing";
  return (
    <main className={styles.shell}>
      <header className={styles.brand}><BrandLogo src={null} className="product-logo--entry" /></header>
      <section className={`${styles.centered} ${styles.card} ${styles.confirmation} ${styles.accountAction}`} aria-labelledby="account-action-title">
        <header className={styles.heading}>
          <h1 id="account-action-title">{actionTitles[kind]}</h1>
        </header>
        {tokenReady === "loading" ? (
          <p className="intro" role="status">Preparando confirmação segura…</p>
        ) : complete ? (
          <div className="auth-form">
            <p className={styles.accountSuccess} role="status">{message}</p>
            <p>{kind === "assisted" ? "O novo e-mail e a nova senha só entrarão em vigor quando o proprietário concluir o atendimento. O status da conta continua sendo respeitado." : "Suas sessões anteriores foram encerradas. Entre novamente para continuar."}</p>
            <Link className="primary account-action-link" href="/">Ir para o login</Link>
          </div>
        ) : tokenReady === "missing" ? (
          <div className="auth-form">
            <p className={styles.accountProblem} role="alert">Este link está incompleto, expirou ou já foi utilizado.</p>
            <Link className="secondary account-action-link" href="/">Voltar ao login</Link>
          </div>
        ) : kind !== "email" ? (
          <form className="auth-form" onSubmit={resetPassword}>
            {kind === "assisted" ? <p className="intro">Esta confirmação prepara a recuperação. O proprietário concluirá a alteração depois; sua senha não será exibida a ele.</p> : null}
            <p className="auth-helper">Use pelo menos 12 caracteres. Evite senhas comuns, seu e-mail e a senha atual.</p>
            <label>
              Nova senha
              <input name="newPassword" type="password" minLength={12} maxLength={128} autoComplete="new-password" required autoFocus />
            </label>
            <label>
              Confirme a nova senha
              <input name="confirmation" type="password" minLength={12} maxLength={128} autoComplete="new-password" required />
            </label>
            {kind === "password" ? <><label>
              Código do autenticador ou de recuperação
              <input name="secondFactor" inputMode="text" autoComplete="one-time-code" pattern="[0-9]{6}|[A-Za-z0-9_-]{24}" maxLength={24} />
            </label>
            <p className="auth-helper">Se recebeu o link pelo fluxo de recuperação por e-mail do cadastro de fotógrafo no site e ativou o autenticador, informe o código do aplicativo ou um código de recuperação salvo. Se recebeu este link após validar o código do WhatsApp, deixe o campo vazio; o TOTP continua exigido no próximo login.</p></> : null}
            <button className="primary" disabled={loading}>{loading ? "Salvando…" : kind === "assisted" ? "Confirmar e aguardar proprietário" : "Redefinir senha"}</button>
          </form>
        ) : (
          <div className="auth-form">
            <p className="intro">A alteração só será efetivada depois desta confirmação. Nenhum endereço é exibido nesta página.</p>
            <button type="button" className="primary" disabled={loading} onClick={confirmEmail}>{loading ? "Confirmando…" : "Confirmar novo e-mail"}</button>
            <Link className="secondary account-action-link" href="/">Cancelar e voltar ao login</Link>
          </div>
        )}
        {message && !complete ? <p className={`form-message ${styles.accountProblem}`} role="status">{message}</p> : null}
      </section>
    </main>
  );
}
