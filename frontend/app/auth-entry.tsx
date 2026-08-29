"use client";

import { FormEvent, useEffect, useState } from "react";

type Context = "client" | "admin";
type Step = "details" | "code";
const genericError =
  "Não foi possível concluir a autenticação. Confira os dados e tente novamente.";
const defaultBranding = { login_title: "Sua galeria, do seu jeito.", login_intro: "Entre para acessar fotos, seleções e entregas — ou gerenciar sua operação.", login_helper: "Escolha seu tipo de acesso para continuar.", logo_url: null as string | null, app_icon_url: null as string | null, favicon_url: null as string | null };

export function AuthEntry() {
  const [context, setContext] = useState<Context>("client");
  const [step, setStep] = useState<Step>("details");
  const [challengeId, setChallengeId] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [branding, setBranding] = useState(defaultBranding);
  const [galleryId] = useState(() =>
    typeof window === "undefined"
      ? ""
      : (new URLSearchParams(window.location.search).get("parent_gallery_id") ??
        ""),
  );
  useEffect(() => {
    fetch("/api/branding")
      .then(async (response) => {
        if (!response.ok) throw new Error();
        const result = await response.json();
        setBranding({ ...defaultBranding, ...result, login_title: result.login_title || defaultBranding.login_title, login_intro: result.login_intro || defaultBranding.login_intro, login_helper: result.login_helper || defaultBranding.login_helper });
      })
      .catch(() => undefined);
  }, []);
  useEffect(() => {
    if (!branding.favicon_url) return;
    let icon = document.querySelector<HTMLLinkElement>('link[rel="icon"]');
    if (!icon) { icon = document.createElement("link"); icon.rel = "icon"; document.head.appendChild(icon); }
    icon.href = `/api${branding.favicon_url}`;
  }, [branding.favicon_url]);
  useEffect(() => {
    if (!branding.app_icon_url) return;
    let icon = document.querySelector<HTMLLinkElement>('link[rel="apple-touch-icon"]');
    if (!icon) { icon = document.createElement("link"); icon.rel = "apple-touch-icon"; document.head.appendChild(icon); }
    icon.href = `/api${branding.app_icon_url}`;
  }, [branding.app_icon_url]);
  async function requestCode(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setLoading(true);
    setMessage("");
    try {
      const response = await fetch(
        context === "client"
          ? "/api/auth/client/challenge"
          : "/api/auth/admin/password",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(
            context === "client"
              ? {
                  full_name: data.get("fullName"),
                  phone: data.get("phone"),
                  ...(galleryId ? { parent_gallery_id: galleryId } : {}),
                }
              : { email: data.get("email"), password: data.get("password") },
          ),
        },
      );
      const result = await response.json();
      if (!response.ok) throw new Error();
      setChallengeId(result.challenge_id);
      setMessage(result.message);
      setStep("code");
    } catch {
      setMessage(genericError);
    } finally {
      setLoading(false);
    }
  }
  async function verifyCode(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const code = new FormData(event.currentTarget).get("code");
    setLoading(true);
    setMessage("");
    try {
      const response = await fetch(
        context === "client"
          ? "/api/auth/client/verify"
          : "/api/auth/admin/totp",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "same-origin",
          body: JSON.stringify({ challenge_id: challengeId, code }),
        },
      );
      const result = await response.json();
      if (!response.ok) throw new Error();
      window.location.assign(result.destination);
    } catch {
      setMessage(
        context === "client"
          ? "O código expirou ou não pôde ser validado. Solicite outro e tente novamente."
          : genericError,
      );
    } finally {
      setLoading(false);
    }
  }
  async function resendCode() {
    setLoading(true);
    setMessage("");
    try {
      const response = await fetch("/api/auth/client/resend", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ challenge_id: challengeId }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error();
      setMessage(result.message);
    } catch {
      setMessage(
        "Não foi possível reenviar o código agora. Tente novamente mais tarde.",
      );
    } finally {
      setLoading(false);
    }
  }
  function choose(next: Context) {
    setContext(next);
    setStep("details");
    setMessage("");
    setChallengeId("");
  }
  return (
    <main className="auth-shell">
      <section className="auth-card" aria-labelledby="entry-title">
        {branding.logo_url ? <img className="auth-brand-logo" src={`/api${branding.logo_url}`} alt="Marca Markina Gallery" /> : null}
        <p className="eyebrow">Markina Gallery</p>
        <h1 id="entry-title">{branding.login_title}</h1>
        <p className="intro">{branding.login_intro}</p>
        <p className="auth-helper">{branding.login_helper}</p>
        <div
          className="context-tabs"
          role="tablist"
          aria-label="Tipo de acesso"
        >
          <button
            role="tab"
            aria-selected={context === "client"}
            className={context === "client" ? "selected" : ""}
            onClick={() => choose("client")}
          >
            Cliente
          </button>
          <button
            role="tab"
            aria-selected={context === "admin"}
            className={context === "admin" ? "selected" : ""}
            onClick={() => choose("admin")}
          >
            Fotógrafo
          </button>
        </div>
        {step === "details" ? (
          <form onSubmit={requestCode} className="auth-form">
            {context === "client" ? (
              <>
                <label>
                  Nome completo
                  <input name="fullName" autoComplete="name" required />
                </label>
                <label>
                  WhatsApp com código do país
                  <input
                    name="phone"
                    inputMode="tel"
                    autoComplete="tel"
                    placeholder="+55 11 99999-9999"
                    required
                  />
                </label>
              </>
            ) : (
              <>
                <label>
                  E-mail
                  <input
                    name="email"
                    type="email"
                    autoComplete="email"
                    required
                  />
                </label>
                <label>
                  Senha
                  <input
                    name="password"
                    type="password"
                    autoComplete="current-password"
                    required
                  />
                </label>
              </>
            )}
            <button className="primary" disabled={loading}>
              {loading
                ? "Aguarde…"
                : context === "client"
                  ? "Receber código"
                  : "Continuar"}
            </button>
          </form>
        ) : (
          <form onSubmit={verifyCode} className="auth-form">
            <label>
              {context === "client"
                ? "Código enviado por WhatsApp"
                : "Código do autenticador"}
              <input
                name="code"
                inputMode="numeric"
                autoComplete="one-time-code"
                pattern="[0-9]{6}"
                maxLength={6}
                required
                autoFocus
              />
            </label>
            <button className="primary" disabled={loading}>
              {loading ? "Validando…" : "Entrar"}
            </button>
            {context === "client" && (
              <button
                type="button"
                className="link-button"
                disabled={loading}
                onClick={resendCode}
              >
                Reenviar código
              </button>
            )}
            <button
              type="button"
              className="secondary"
              onClick={() => setStep("details")}
            >
              Voltar
            </button>
          </form>
        )}
        {message && (
          <p className="form-message" role="status">
            {message}
          </p>
        )}
      </section>
    </main>
  );
}
