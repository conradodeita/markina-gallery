"use client";

import { type FormEvent, useEffect, useRef, useState } from "react";
import { MarkinaButton, StatusBadge, SystemState } from "../../ui-kit";

type Configuration = { status: string; version: number; handle: string | null; card_enabled: boolean; api_key_configured: boolean; checkout_available: boolean; ownership_verified?: boolean; message?: string; credential_status?: "stored" | "absent" | "unavailable"; credential_validation?: "unavailable" | "validated" | "rejected"; credential_storage_available?: boolean };
type Challenge = { challenge_id: string; expires_at: string; proposal: { handle: string | null; version: number; checkout_ready?: boolean; card_enabled?: boolean } };

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
  const [replacingKey, setReplacingKey] = useState(false);
  const [showKey, setShowKey] = useState(false);
  const [handle, setHandle] = useState("");
  const [checkoutReady, setCheckoutReady] = useState(false);
  const [cardEnabled, setCardEnabled] = useState(false);
  const [challenge, setChallenge] = useState<Challenge | null>(null);
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const otpInput = useRef<HTMLInputElement>(null);
  const editButton = useRef<HTMLButtonElement>(null);
  const handleInput = useRef<HTMLInputElement>(null);
  const passwordInput = useRef<HTMLInputElement>(null);
  const apiKeyInput = useRef<HTMLInputElement>(null);
  const storageAvailable = configuration?.credential_storage_available === true;

  useEffect(() => {
    let active = true;
    requestConfiguration().then((value) => { if (active) setConfiguration(value); })
      .catch((failure) => { if (active) setError(failure.message); });
    return () => { active = false; };
  }, []);
  useEffect(() => {
    if (challenge) otpInput.current?.focus();
    else if (editing) (removing ? passwordInput : replacingKey ? apiKeyInput : handleInput).current?.focus();
    else if (message) editButton.current?.focus();
  }, [challenge, editing, removing, replacingKey, message]);

  useEffect(() => {
    if (!editing) return;
    function warn(event: BeforeUnloadEvent) { event.preventDefault(); event.returnValue = ""; }
    function navigate(event: MouseEvent) {
      const link = event.target instanceof Element ? event.target.closest<HTMLAnchorElement>("a[href]") : null;
      if (link && (!link.target || link.target === "_self") && link.href !== window.location.href
          && !window.confirm("Há uma alteração InfinitePay não concluída. Deseja sair e descartá-la?")) {
        event.preventDefault(); event.stopPropagation();
      }
    }
    window.addEventListener("beforeunload", warn);
    document.addEventListener("click", navigate, true);
    return () => { window.removeEventListener("beforeunload", warn); document.removeEventListener("click", navigate, true); };
  }, [editing]);

  function begin(remove = false, replace = false) {
    if (apiKeyInput.current) apiKeyInput.current.value = "";
    setShowKey(false); setReplacingKey(replace);
    setHandle(remove ? "" : configuration?.handle ?? "");
    setCheckoutReady(!remove && configuration?.status === "active");
    setCardEnabled(!remove && !!configuration?.card_enabled);
    setRemoving(remove); setEditing(true);
    setError(""); setMessage(""); setCode(""); setChallenge(null);
  }

  function cancel() {
    if (!window.confirm("Descartar a alteração InfinitePay ainda não concluída?")) return;
    if (apiKeyInput.current) apiKeyInput.current.value = "";
    setShowKey(false);
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
    const apiKey = apiKeyInput.current?.value.trim() || "";
    password.value = "";
    if (apiKeyInput.current) apiKeyInput.current.value = "";
    setShowKey(false);
    if (!removing && !storageAvailable && (apiKey || replacingKey || !configuration.api_key_configured)) {
      setError("Cadastro seguro temporariamente indisponível. Tente novamente mais tarde.");
      return;
    }
    if (replacingKey && !apiKey) {
      setError("Informe a nova API Key para substituí-la.");
      return;
    }
    setBusy(true); setError(""); setMessage("");
    try {
      setChallenge(await requestConfiguration("/challenge", { current_password: currentPassword,
        expected_version: configuration.version, configuration: removing ? null : { handle },
        checkout_ready: !removing && checkoutReady, card_enabled: !removing && cardEnabled,
        ...(!removing && apiKey ? { api_key: apiKey } : {}) }));
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
      setMessage(removing ? "Integração InfinitePay desconectada. Novos cartões estão indisponíveis; o PIX manual mantém sua configuração." : challenge.proposal.card_enabled
        ? "Cartão habilitado para novas compras. Compras já emitidas mantêm seus links até confirmação ou conciliação."
        : challenge.proposal.checkout_ready
          ? "InfinitePay continua configurada, mas cartão está desabilitado para novas compras. Links já emitidos permanecem disponíveis."
          : "Configuração salva como pendente. Cartão permanece indisponível até confirmar as opções da sua conta.");
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
    <p>{configuration?.checkout_available ? "Cartão de crédito está habilitado para novas compras dos clientes desta conta." : configuration?.status === "active" && configuration.card_enabled && !configuration.api_key_configured ? "Cadastre a API Key da sua conta para disponibilizar cartão aos clientes." : configuration?.status === "active" ? "InfinitePay está configurada, mas cartão está desabilitado para novas compras." : "Prepare sua conta para receber diretamente pela InfinitePay. O cartão ainda não está disponível aos clientes."}</p>
    <p>Na sua conta InfinitePay, habilite o Checkout Integrado, deixe cartão de crédito ligado e PIX desligado, pois o Pick-your-Pic já oferece PIX separadamente. Essa preferência também se aplica aos links de checkout criados pela API. Informe a InfiniteTag da mesma conta. Antes de habilitar, crie um link de teste sem concluir a compra e confira o recebedor e que somente cartão é oferecido. A confirmação registra sua declaração; não comprova a titularidade remotamente.</p>
    <a href="https://app.infinitepay.io/external-checkout#documentacao" target="_blank" rel="noopener noreferrer">Abrir Checkout Integrado na InfinitePay</a>
    {!configuration ? <SystemState tone={error ? "error" : "loading"} title={error ? "Configuração indisponível" : "Carregando InfinitePay"} detail={error || "Consultando sua configuração."} /> : <>
      <StatusBadge tone={configuration.checkout_available ? "success" : "warning"}>{configuration.checkout_available ? "Cartão habilitado para novos pedidos" : configuration.status === "active" && configuration.card_enabled && !configuration.api_key_configured ? "Aguardando cadastro da API Key" : configuration.status === "active" ? "Cartão desabilitado para novos pedidos" : configuration.status === "pending" ? "Pendente de configuração" : "Cartão indisponível"}</StatusBadge>
      {configuration.handle ? <p>InfiniteTag declarada: <strong style={{ overflowWrap: "anywhere" }}>{configuration.handle}</strong></p> : null}
      <p>{configuration.credential_status === "unavailable" ? "API Key exige atenção: a credencial está temporariamente indisponível." : configuration.api_key_configured ? "API Key cadastrada. Seu valor não é exibido." : "API Key não cadastrada."}</p>
      {configuration.credential_validation === "validated" ? <p>Credencial validada pela InfinitePay.</p> : configuration.credential_validation === "rejected" ? <p role="alert">Credencial rejeitada pela InfinitePay. Substitua a API Key antes de novos cartões.</p> : <p>Validação remota indisponível neste fluxo. O cadastro não comprova a aceitação da chave pela InfinitePay.</p>}
      {!storageAvailable ? <p role="status">Cadastro seguro temporariamente indisponível. Tente novamente mais tarde.</p> : null}
      {!editing ? <div className="action-grid">
        <button ref={editButton} className="mk-button mk-button--primary" type="button" onClick={() => begin()}>{configuration.handle ? "Alterar InfiniteTag ou disponibilidade do cartão" : "Preparar InfinitePay"}</button>
        {configuration.api_key_configured ? <MarkinaButton variant="secondary" type="button" disabled={!storageAvailable} onClick={() => begin(false, true)}>Substituir API Key</MarkinaButton> : null}
        {configuration.handle ? <MarkinaButton variant="secondary" type="button" onClick={() => begin(true)}>Desconectar InfinitePay</MarkinaButton> : null}
      </div> : challenge ? <form className="gallery-settings-form" onSubmit={confirm}>
        <h3>{challenge.proposal.handle ? "Confira a InfiniteTag proposta" : "Confirme a remoção da InfinitePay"}</h3>
        {challenge.proposal.handle ? <p style={{ overflowWrap: "anywhere" }}>{challenge.proposal.handle}</p> : null}
        {challenge.proposal.checkout_ready ? <p>A configuração da conta está confirmada. {challenge.proposal.card_enabled ? "Esta alteração habilitará cartão para novos pedidos." : "Esta alteração manterá cartão desabilitado para novos pedidos."} Links de compras já emitidas continuam disponíveis até confirmação ou conciliação.</p> : null}
        <p>Use o código enviado ao WhatsApp administrativo do Pick-your-Pic. Ele confirma somente esta alteração e é válido por 10 minutos.</p>
        <label>Código de confirmação InfinitePay<input ref={otpInput} value={code} onChange={(event) => setCode(event.target.value.replace(/\D/g, "").slice(0, 6))} inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} required /></label>
        <div className="action-grid">
          <MarkinaButton disabled={busy}>{busy ? "Aguarde…" : "Confirmar configuração InfinitePay"}</MarkinaButton>
          <MarkinaButton type="button" variant="secondary" disabled={busy} onClick={cancel}>Cancelar alteração InfinitePay</MarkinaButton>
          <MarkinaButton type="button" variant="quiet" disabled={busy} onClick={resend}>Reenviar código InfinitePay</MarkinaButton>
          <MarkinaButton type="button" variant="quiet" disabled={busy} onClick={() => { setChallenge(null); setCode(""); setError(""); }}>Recomeçar confirmação</MarkinaButton>
        </div>
      </form> : <form className="gallery-settings-form" onSubmit={start}>
        {removing ? <p>A desconexão exige confirmação de segurança e nenhuma compra de cartão pendente. O PIX manual permanece disponível conforme sua configuração.</p> : <label>InfiniteTag<input ref={handleInput} value={handle} onChange={(event) => {
          setHandle(event.target.value);
          if (event.target.value.trim().replace(/^\$/, "") !== configuration.handle) {
            setCheckoutReady(false); setCardEnabled(false);
          }
        }} maxLength={100} required autoCapitalize="none" spellCheck={false} /></label>}
        {!removing ? <>
          <label>{configuration.api_key_configured ? "Nova API Key InfinitePay" : "API Key InfinitePay"}<input
            ref={apiKeyInput} name="infinitepay_api_key" type={showKey ? "text" : "password"}
            autoComplete="new-password" autoCapitalize="none" spellCheck={false} maxLength={512}
            data-private="true" data-sentry-mask data-dd-privacy="mask"
            disabled={busy || !storageAvailable}
            required={replacingKey || !configuration.api_key_configured || handle.trim().replace(/^\$/, "") !== configuration.handle} /></label>
          <MarkinaButton type="button" variant="quiet" disabled={busy || !storageAvailable}
            aria-pressed={showKey} onClick={() => setShowKey(!showKey)}>{showKey ? "Ocultar API Key" : "Mostrar API Key"}</MarkinaButton>
          <p>Obtenha a API Key no Checkout Integrado da sua conta InfinitePay. Use a credencial da mesma conta da InfiniteTag. A chave é enviada somente para cadastro seguro e não volta a ser exibida.</p>
          {configuration.api_key_configured ? <p>Deixe o campo vazio para manter a chave atual. Ao alterar a InfiniteTag, informe a chave correspondente. Antes de revogar uma chave antiga na InfinitePay, concilie as compras pendentes.</p> : null}
          <label className="checkbox-label"><input type="checkbox" checked={checkoutReady} onChange={(event) => {
            setCheckoutReady(event.target.checked);
            if (!event.target.checked) setCardEnabled(false);
          }} />Conferi que esta InfiniteTag é da minha conta, habilitei o Checkout Integrado e cartão, desliguei o PIX e testei um link sem pagar para confirmar que ele oferece somente cartão.</label>
          <label className="checkbox-label"><input type="checkbox" checked={cardEnabled} disabled={!checkoutReady || !handle.trim()} onChange={(event) => setCardEnabled(event.target.checked)} />Habilitar pagamento por cartão de crédito para novos pedidos de clientes</label>
          <p>Desabilitar esta opção impede novos checkouts de cartão. Links já emitidos continuam disponíveis nas compras pendentes.</p>
        </> : null}
        <label>Senha atual do Pick-your-Pic<input ref={passwordInput} name="infinitepay_current_password" type="password" autoComplete="current-password" maxLength={128} required /></label>
        <div className="action-grid">
          <MarkinaButton disabled={busy || (!removing && (replacingKey || !configuration.api_key_configured) && !storageAvailable)}>{busy ? "Enviando…" : "Enviar código InfinitePay"}</MarkinaButton>
          <MarkinaButton type="button" variant="secondary" disabled={busy} onClick={cancel}>Cancelar alteração InfinitePay</MarkinaButton>
        </div>
      </form>}
    </>}
    {configuration && error ? <p className="form-message form-message--error" role="alert">{error}</p> : null}
    {message ? <p className="form-message" role="status">{message}</p> : null}
  </section>;
}
