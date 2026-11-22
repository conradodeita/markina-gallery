"use client";

import { type FormEvent, useState } from "react";
import { MarkinaButton } from "../../ui-kit";

const AUTH_ORIGIN = "https://accounts.google.com";
const AUTH_PATH = "/o/oauth2/v2/auth";
const DRIVE_FILE_SCOPE = "https://www.googleapis.com/auth/drive.file";
const DRIVE_CALLBACK = "https://markina.pickyourpic.com.br/api/admin/platform/drive/oauth/callback";

export function isAllowedGoogleAuthorizationUrl(value: unknown): value is string {
  if (typeof value !== "string" || value.length > 4096) return false;
  try {
    const url = new URL(value);
    const params = url.searchParams;
    const one = (name: string) => params.getAll(name).length === 1;
    return url.origin === AUTH_ORIGIN && url.pathname === AUTH_PATH && url.protocol === "https:" &&
      url.port === "" && !url.username && !url.password && !url.hash &&
      ["client_id", "redirect_uri", "response_type", "scope", "code_challenge_method", "state", "code_challenge"]
        .every(one) && params.get("scope") === DRIVE_FILE_SCOPE &&
      params.get("redirect_uri") === DRIVE_CALLBACK && params.get("response_type") === "code" &&
      params.get("code_challenge_method") === "S256" && Boolean(params.get("code_challenge")) &&
      Boolean(params.get("state")) && Boolean(params.get("client_id"));
  } catch {
    return false;
  }
}

export function GoogleDriveConnectForm({ navigate = (url: string) => window.location.assign(url) }: {
  navigate?: (url: string) => void;
}) {
  const [password, setPassword] = useState("");
  const [totp, setTotp] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    const body = JSON.stringify({ current_password: password, totp_code: totp });
    setPassword("");
    setTotp("");
    setBusy(true);
    setError("");
    try {
      const response = await fetch("/api/admin/platform/drive/connect/start", {
        method: "POST", credentials: "same-origin", cache: "no-store", redirect: "error",
        headers: { "Content-Type": "application/json" }, body,
      });
      if (!response.ok) throw new Error();
      const result = await response.json() as { authorization_url?: unknown };
      if (!isAllowedGoogleAuthorizationUrl(result.authorization_url)) throw new Error();
      navigate(result.authorization_url);
    } catch {
      setError("Não foi possível iniciar a conexão. Confira as credenciais e tente novamente.");
      setBusy(false);
    }
  }

  return <div className="mk-stack">
    <h4>Conectar Google Drive</h4>
    <p>Confirme sua senha e o código atual do autenticador para abrir o consentimento Google com o escopo <code>drive.file</code>.</p>
    <form onSubmit={(event) => void submit(event)} autoComplete="off">
      <label>Senha atual do proprietário<input type="password" autoComplete="off" required maxLength={128} value={password} onChange={(event) => setPassword(event.target.value)} /></label>
      <label>Código atual do autenticador<input inputMode="numeric" autoComplete="one-time-code" required pattern="[0-9]{6}" maxLength={6} value={totp} onChange={(event) => setTotp(event.target.value.replace(/\D/g, "").slice(0, 6))} /></label>
      <MarkinaButton disabled={busy || password.length === 0 || !/^[0-9]{6}$/.test(totp)}>{busy ? "Iniciando conexão…" : "Continuar para o Google"}</MarkinaButton>
    </form>
    {error ? <p role="alert">{error}</p> : null}
  </div>;
}
