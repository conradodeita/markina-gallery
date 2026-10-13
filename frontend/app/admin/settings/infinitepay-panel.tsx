"use client";

import { type FormEvent, useEffect, useRef, useState } from "react";
import { MarkinaButton, StatusBadge, SystemState } from "../../ui-kit";

type Configuration = { status: string; version: number; handle: string | null; checkout_available: boolean; ownership_verified?: boolean; message?: string };
type Challenge = { challenge_id: string; expires_at: string; proposal: { handle: string | null; version: number; checkout_ready?: boolean } };

class ConfigurationError extends Error {
  constructor(message: string, public status: number) { super(message); }
}

async function requestConfiguration(path = "", body?: unknown) {
  const response = await fetch(`/api/admin/settings/infinitepay${path}`, {
    credentials: "same-origin", cache: "no-store",
    ...(body !== undefined ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {}),
  });
  const result = await response.json().catch(() => null);
  if (!response.ok) throw new ConfigurationError(typeof result?.detail === "string" ? result.detail : "Não foi possível concluir a configuração. Tente novamente.", response.status);
  return result;
}

export default function InfinitePayPanel() {
  const [configuration, setConfiguration] = useState<Configuration | null>(null);
  const [editing, setEditing] = useState(false);
  const [removing, setRemoving] = useState(false);
  const [handle, setHandle] = useState("");
  const [checkoutReady, setCheckoutReady] = useState(false);
  const [challenge, setChallenge] = useState<Challenge | null>(null);
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const otpInput = useRef<HTMLInputElement>(null);
  const editButton = useRef<HTMLButtonElement>(null);
  const handleInput = useRef<HTMLInputElement>(null);
  const passwordInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let active = true;
    requestConfiguration().then((value) => { if (active) setConfiguration(value); })
      .catch((failure) => { if (active) setError(failure.message); });
    return () => { active = false; };
  }, []);
  useEffect(() => {
    if (challenge) otpInput.current?.focus();
    else if (editing) (removing ? passwordInput : handleInput).current?.focus();
    else if (message) editButton.current?.focus();
  }, [challenge, editing, removing, message]);

  function begin(remove = false) {
    setHandle(configuration?.handle ?? ""); setCheckoutReady(false); setRemoving(remove); setEditing(true);
    setError(""); setMessage(""); setCode(""); setChallenge(null);
  }

  function cancel() {
    setEditing(false); setChallenge(null); setCode(""); setError("");
    setMessage("Alteração cancelada. A configuração atual foi mantida.");
  }

  async function showFailure(failure: unknown) {
    setError((failure as Error).message);
    if (failure instanceof ConfigurationError && failure.status === 409) {
      // Recarrega a versão autoritativa sem reaplicar automaticamente a proposta.
      setChallenge(null); setCode("");
      try { setConfiguration(await requestConfiguration()); } catch { /* Mantém o erro original. */ }
    }
  }

  async function start(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy || !configuration || !passwordInput.current) return;
    const password = passwordInput.current;
    const currentPassword = password.value;
    password.value = "";
    setBusy(true); setError(""); setMessage("");
    try {
      setChallenge(await requestConfiguration("/challenge", { current_password: currentPassword,
        expected_version: configuration.version, configuration: removing ? null : { handle },
        checkout_ready: !removing && checkoutReady }));
    } catch (failure) { await showFailure(failure); }
    finally { setBusy(false); }
  }

  async function confirm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy || !challenge) return;
    if (Date.parse(challenge.expires_at) <= Date.now()) {
      setChallenge(null); setCode(""); setError("O código expirou. Solicite outro usando sua senha do Pick-your-Pic.");
      return;
    }
    setBusy(true); setError("");
    try {
      setConfiguration(await requestConfiguration("/confirm", { challenge_id: challenge.challenge_id, code }));
      setEditing(false); setChallenge(null); setCode("");
      setMessage(removing ? "Configuração InfinitePay removida." : checkoutReady
        ? "InfinitePay habilitada conforme sua declaração. A configuração requer que você já tenha conferido o recebedor e confirmado no link de teste que só há cartão."
        : "InfiniteTag salva como pendente. Cartão permanece indisponível até confirmar as opções da sua conta.");
    } catch (failure) { await showFailure(failure); }
    finally { setBusy(false); }
  }

  async function resend() {
    if (busy || !challenge) return;
    setBusy(true); setError("");
    try {
      const result = await requestConfiguration("/resend", { challenge_id: challenge.challenge_id });
      setChallenge({ ...challenge, ...result }); setCode("");
      setMessage("Novo código enviado ao WhatsApp administrativo.");
    } catch (failure) { await showFailure(failure); }
    finally { setBusy(false); }
  }

  return <section id="infinitepay" className="admin-card global-pix-settings" aria-labelledby="infinitepay-title">
    <p className="eyebrow">Pagamentos · Sua conta</p>
    <h2 id="infinitepay-title">Cartão de crédito · InfinitePay</h2>
    <p>{configuration?.checkout_available ? "InfinitePay está disponível como opção de cartão de crédito para os clientes desta conta." : "Prepare sua conta para receber diretamente pela InfinitePay. O cartão ainda não está disponível aos clientes."}</p>
    <p>Na sua conta InfinitePay, habilite o Checkout Integrado, deixe cartão de crédito ligado e PIX desligado, pois o Pick-your-Pic já oferece PIX separadamente. Essa preferência também se aplica aos links de checkout criados pela API. Informe a InfiniteTag da mesma conta. Antes de habilitar, crie um link de teste sem concluir a compra e confira o recebedor e que somente cartão é oferecido. A confirmação registra sua declaração; não comprova a titularidade remotamente.</p>
    <a href="https://app.infinitepay.io/external-checkout#documentacao" target="_blank" rel="noopener noreferrer">Abrir Checkout Integrado na InfinitePay</a>
    {!configuration ? <SystemState tone={error ? "error" : "loading"} title={error ? "Configuração indisponível" : "Carregando InfinitePay"} detail={error || "Consultando sua configuração."} /> : <>
      <StatusBadge tone={configuration.checkout_available ? "success" : "warning"}>{configuration.checkout_available ? "Cartão habilitado · configuração confirmada" : configuration.status === "pending" ? "Pendente de configuração" : "Cartão indisponível"}</StatusBadge>
      {configuration.handle ? <p>InfiniteTag declarada: <strong style={{ overflowWrap: "anywhere" }}>{configuration.handle}</strong></p> : null}
      {!editing ? <div className="action-grid">
        <button ref={editButton} className="mk-button mk-button--primary" type="button" onClick={() => begin()}>{configuration.handle ? "Alterar InfiniteTag" : "Preparar InfinitePay"}</button>
        {configuration.handle ? <MarkinaButton variant="secondary" type="button" onClick={() => begin(true)}>Remover configuração InfinitePay</MarkinaButton> : null}
      </div> : challenge ? <form className="gallery-settings-form" onSubmit={confirm}>
        <h3>{challenge.proposal.handle ? "Confira a InfiniteTag proposta" : "Confirme a remoção da InfinitePay"}</h3>
        {challenge.proposal.handle ? <p style={{ overflowWrap: "anywhere" }}>{challenge.proposal.handle}</p> : null}
        {challenge.proposal.checkout_ready ? <p>Esta confirmação declara que você conferiu o recebedor, ativou Checkout Integrado e cartão, desligou PIX e conferiu um link de teste sem finalizar a compra, verificando que só oferece cartão.</p> : null}
        <p>Use o código enviado ao WhatsApp administrativo do Pick-your-Pic. Ele confirma somente esta alteração e é válido por 10 minutos.</p>
        <label>Código de confirmação InfinitePay<input ref={otpInput} value={code} onChange={(event) => setCode(event.target.value.replace(/\D/g, "").slice(0, 6))} inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} required /></label>
        <div className="action-grid">
          <MarkinaButton disabled={busy}>{busy ? "Aguarde…" : "Confirmar configuração InfinitePay"}</MarkinaButton>
          <MarkinaButton type="button" variant="secondary" disabled={busy} onClick={cancel}>Cancelar alteração InfinitePay</MarkinaButton>
          <MarkinaButton type="button" variant="quiet" disabled={busy} onClick={resend}>Reenviar código InfinitePay</MarkinaButton>
          <MarkinaButton type="button" variant="quiet" disabled={busy} onClick={() => { setChallenge(null); setCode(""); setError(""); }}>Recomeçar confirmação</MarkinaButton>
        </div>
      </form> : <form className="gallery-settings-form" onSubmit={start}>
        {removing ? <p>A remoção exige confirmação de segurança.</p> : <label>InfiniteTag<input ref={handleInput} value={handle} onChange={(event) => setHandle(event.target.value)} maxLength={100} required autoCapitalize="none" spellCheck={false} /></label>}
        {!removing ? <label className="checkbox-label"><input type="checkbox" checked={checkoutReady} onChange={(event) => setCheckoutReady(event.target.checked)} />Conferi que esta InfiniteTag é da minha conta, habilitei o Checkout Integrado e cartão, desliguei o PIX e testei um link sem pagar para confirmar que ele oferece somente cartão.</label> : null}
        <label>Senha atual do Pick-your-Pic<input ref={passwordInput} name="infinitepay_current_password" type="password" autoComplete="current-password" maxLength={128} required /></label>
        <div className="action-grid">
          <MarkinaButton disabled={busy}>{busy ? "Enviando…" : "Enviar código InfinitePay"}</MarkinaButton>
          <MarkinaButton type="button" variant="secondary" disabled={busy} onClick={cancel}>Cancelar alteração InfinitePay</MarkinaButton>
        </div>
      </form>}
    </>}
    {configuration && error ? <p className="form-message form-message--error" role="alert">{error}</p> : null}
    {message ? <p className="form-message" role="status">{message}</p> : null}
  </section>;
}
