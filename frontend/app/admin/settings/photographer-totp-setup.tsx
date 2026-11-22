"use client";

import Image from "next/image";
import Link from "next/link";
import { type FormEvent, useEffect, useState } from "react";

type Setup = { enrollment_id: string; secret: string; qr_data_url: string; expires_at: string };

export function PhotographerTotpSetup({ enabled }: { enabled: boolean }) {
  const [open, setOpen] = useState(false);
  const [setup, setSetup] = useState<Setup | null>(null);
  const [codes, setCodes] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [activated, setActivated] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!setup) return;
    const remaining = Date.parse(setup.expires_at) - Date.now();
    const timeout = setTimeout(() => {
      setSetup(null);
      setOpen(false);
      setMessage("A configuração expirou. Inicie novamente quando estiver com seu autenticador.");
    }, Math.max(0, remaining));
    return () => clearTimeout(timeout);
  }, [setup]);

  async function begin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const password = String(new FormData(form).get("currentPassword") ?? "");
    form.reset();
    setBusy(true); setMessage("");
    try {
      const response = await fetch("/api/admin/security/totp/enrollment", {
        method: "POST", credentials: "same-origin", cache: "no-store",
        headers: { "Content-Type": "application/json" }, body: JSON.stringify({ current_password: password }),
      });
      const result = await response.json();
      if (!response.ok || typeof result.enrollment_id !== "string" || typeof result.secret !== "string"
        || !/^[A-Z2-7]+$/.test(result.secret) || typeof result.qr_data_url !== "string"
        || !result.qr_data_url.startsWith("data:image/png;base64,") || !Number.isFinite(Date.parse(result.expires_at))) throw new Error();
      setSetup(result); setOpen(false);
    } catch { setMessage("Não foi possível iniciar. Confira a senha ou tente novamente mais tarde."); }
    finally { setBusy(false); }
  }

  async function confirm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!setup) return;
    const form = event.currentTarget;
    const code = String(new FormData(form).get("code") ?? "");
    form.reset(); setBusy(true); setMessage("");
    try {
      const response = await fetch("/api/admin/security/totp/enrollment/confirm", {
        method: "POST", credentials: "same-origin", cache: "no-store",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enrollment_id: setup.enrollment_id, code }),
      });
      const result = await response.json();
      if (!response.ok || !Array.isArray(result.codes) || result.codes.length !== 10
        || !result.codes.every((item: unknown) => typeof item === "string")) throw new Error();
      setSetup(null); setCodes(result.codes); setActivated(true);
      setMessage("Autenticador ativado. Suas sessões anteriores foram encerradas.");
    } catch { setMessage("Não foi possível confirmar. Confira o código ou reinicie se a configuração expirou."); }
    finally { setBusy(false); }
  }

  return <section aria-labelledby="photographer-totp-title">
    <h3 id="photographer-totp-title">Autenticador opcional</h3>
    {codes.length ? <>
      <p>Guarde estes códigos em um local privado. Cada um funciona uma vez se você perder o autenticador.</p>
      <ol aria-label="Novos códigos de recuperação">{codes.map((code) => <li key={code}><code>{code}</code></li>)}</ol>
      <button type="button" onClick={() => setCodes([])}>Já guardei: limpar códigos da tela</button>
      <Link href="/">Entrar novamente</Link>
    </> : enabled || activated ? <><p>Ativo: o código será exigido no login. Os códigos de recuperação podem ser regenerados em Segurança da conta.</p>{activated ? <Link href="/">Entrar novamente</Link> : null}</>
      : setup ? <>
        <p>1. Abra seu aplicativo autenticador e adicione uma conta pelo QR Code ou pela chave manual. A configuração expira em cinco minutos.</p>
        <Image src={setup.qr_data_url} alt="QR Code para adicionar o Pick-your-Pic ao autenticador" width={220} height={220} unoptimized />
        <p>Chave manual: <code>{setup.secret}</code></p>
        <form onSubmit={confirm}>
          <label>2. Código do aplicativo<input name="code" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} required /></label>
          <button disabled={busy}>{busy ? "Confirmando…" : "Ativar autenticador"}</button>
        </form>
        <button type="button" disabled={busy} onClick={() => { setSetup(null); setOpen(false); }}>Fechar configuração</button>
      </> : open ? <form onSubmit={begin}>
        <p>Confirme sua senha para preparar uma chave. O autenticador só será exigido depois de confirmar um código válido.</p>
        <label>Senha para ativar autenticador<input name="currentPassword" type="password" autoComplete="current-password" required /></label>
        <button disabled={busy}>{busy ? "Preparando…" : "Preparar autenticador"}</button>
        <button type="button" disabled={busy} onClick={() => setOpen(false)}>Cancelar ativação</button>
      </form> : <>
        <p>Adicione uma etapa de segurança ao login. Ao ativar, guarde os códigos de recuperação e entre novamente com senha e código.</p>
        <button type="button" onClick={() => setOpen(true)}>Configurar autenticador</button>
      </>}
    {message ? <p role="status">{message}</p> : null}
  </section>;
}
