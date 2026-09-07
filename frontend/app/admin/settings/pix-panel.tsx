"use client";

import { type FormEvent, useEffect, useRef, useState } from "react";

import { MarkinaButton, StatusBadge, SystemState } from "../../ui-kit";

export type GlobalPix = {
  status: "active" | "unconfigured" | "review_required";
  version: number;
  copy_paste?: string | null;
  receiver_name: string | null;
  receiver_city: string | null;
  instructions: string | null;
  qr_png_data_url: string | null;
  checkout_available: boolean;
};

async function requestPix(path = "", body?: unknown) {
  const response = await fetch(`/api/admin/settings/pix${path}`, {
    credentials: "same-origin",
    ...(body !== undefined ? {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    } : {}),
  });
  const result = await response.json().catch(() => null);
  if (!response.ok) throw new Error(typeof result?.detail === "string" ? result.detail : "Não foi possível concluir a configuração do PIX. Confira os campos e tente novamente.");
  return result;
}

export function GlobalPixSummary({ pix }: { pix: GlobalPix }) {
  return <div className="global-pix-summary">
    <StatusBadge tone={pix.status === "active" ? "success" : "warning"}>
      {pix.status === "active" ? "PIX configurado" : pix.status === "review_required" ? "PIX precisa de revisão" : "PIX não configurado"}
    </StatusBadge>
    {pix.status === "active" ? <>
      <p><strong>{pix.receiver_name}</strong>{pix.receiver_city ? ` · ${pix.receiver_city}` : ""}</p>
      {pix.qr_png_data_url ? <img className="gallery-pix-qr" src={pix.qr_png_data_url} alt="QR Code PIX global" /> : null}
      {pix.instructions ? <p>{pix.instructions}</p> : null}
      <small>Configuração compartilhada por todas as galerias · versão {pix.version}</small>
    </> : <p role="status">{pix.status === "review_required" ? "As configurações anteriores precisam ser conferidas. Defina o PIX em Configurações para receber novos pagamentos." : "Configure o PIX para habilitar novos pagamentos. Você pode continuar preparando a galeria e as seleções serão preservadas."}</p>}
  </div>;
}

export default function PixPanel() {
  const [pix, setPix] = useState<GlobalPix | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState(false);
  const [removing, setRemoving] = useState(false);
  const [challenge, setChallenge] = useState<{ challenge_id: string; expires_at: string; proposal?: GlobalPix } | null>(null);
  const [code, setCode] = useState("");
  const [draft, setDraft] = useState({ copy_paste: "", receiver_name: "", receiver_city: "", instructions: "" });
  const otpInput = useRef<HTMLInputElement>(null);
  const editButton = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    let active = true;
    requestPix().then((result) => { if (active) setPix(result); })
      .catch((failure) => { if (active) setError(failure.message); });
    return () => { active = false; };
  }, []);
  useEffect(() => { if (challenge) otpInput.current?.focus(); }, [challenge]);
  useEffect(() => { if (!editing && message) editButton.current?.focus(); }, [editing, message]);

  function begin(remove = false) {
    if (!pix) return;
    setDraft({ copy_paste: pix.copy_paste ?? "", receiver_name: pix.receiver_name ?? "", receiver_city: pix.receiver_city ?? "", instructions: pix.instructions ?? "" });
    setRemoving(remove);
    setEditing(true);
    setError("");
    setMessage("");
    setChallenge(null);
    setCode("");
  }

  function cancel() {
    setEditing(false);
    setChallenge(null);
    setCode("");
    setError("");
    setMessage("Alteração cancelada. A configuração atual foi mantida.");
    editButton.current?.focus();
  }

  async function start(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    const password = event.currentTarget.elements.namedItem("current_password") as HTMLInputElement;
    const currentPassword = password.value;
    setBusy(true); setError("");
    try {
      const result = await requestPix("/challenge", { current_password: currentPassword, configuration: removing ? null : draft });
      password.value = "";
      setChallenge(result);
    } catch (failure) { setError((failure as Error).message); }
    finally { setBusy(false); }
  }

  async function confirm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!challenge || busy) return;
    if (Date.parse(challenge.expires_at) <= Date.now()) {
      setChallenge(null); setCode("");
      setError("O código expirou. Informe a senha para solicitar um novo código.");
      return;
    }
    setBusy(true); setError("");
    try {
      const result = await requestPix("/confirm", { challenge_id: challenge.challenge_id, code });
      setPix(result); setEditing(false); setChallenge(null); setCode("");
      setMessage(removing ? "PIX removido. Novos pagamentos estão indisponíveis; os pedidos existentes foram preservados." : "PIX global salvo. Todas as galerias usarão esta configuração nos novos pedidos.");
      editButton.current?.focus();
    } catch (failure) { setError((failure as Error).message); }
    finally { setBusy(false); }
  }

  return <section id="pix" className="admin-card global-pix-settings" aria-labelledby="global-pix-title">
    <p className="eyebrow">Pagamentos · Padrão global</p>
    <h2 id="global-pix-title">PIX</h2>
    <p>Configure uma vez para todas as galerias. Pedidos já iniciados conservam o PIX informado na compra.</p>
    {!pix ? <SystemState tone={error ? "error" : "loading"} title={error ? "PIX indisponível" : "Carregando PIX"} detail={error || "Consultando a configuração de pagamento."} /> : <>
      <GlobalPixSummary pix={pix} />
      {!editing ? <div className="action-grid">
        <button className="mk-button mk-button--primary" ref={editButton} type="button" onClick={() => begin()}>{pix.status === "active" ? "Alterar PIX" : "Configurar PIX"}</button>
        {pix.status === "active" ? <MarkinaButton type="button" variant="secondary" onClick={() => begin(true)}>Remover PIX</MarkinaButton> : null}
      </div> : challenge ? <form className="gallery-settings-form" onSubmit={confirm}>
        <h3>{removing ? "Confirmar remoção do PIX" : "Confirmar configuração do PIX"}</h3>
        <p>Enviamos um código ao WhatsApp administrativo. Ele é válido por 10 minutos e confirma somente esta alteração.</p>
        {!removing && challenge.proposal ? <div><h4>Confira o PIX que será salvo</h4><GlobalPixSummary pix={challenge.proposal} /></div> : null}
        <label>Código de confirmação<input ref={otpInput} value={code} onChange={(event) => setCode(event.target.value.replace(/\D/g, "").slice(0, 6))} autoComplete="one-time-code" inputMode="numeric" pattern="[0-9]{6}" minLength={6} maxLength={6} required /></label>
        <div className="action-grid"><MarkinaButton disabled={busy}>{busy ? "Confirmando…" : removing ? "Confirmar remoção" : "Confirmar PIX"}</MarkinaButton><MarkinaButton type="button" variant="secondary" disabled={busy} onClick={cancel}>Cancelar</MarkinaButton><MarkinaButton type="button" variant="quiet" disabled={busy} onClick={() => { setChallenge(null); setCode(""); setError(""); }}>Solicitar novo código</MarkinaButton></div>
      </form> : <form className="gallery-settings-form" onSubmit={start}>
        <h3>{removing ? "Remover configuração PIX" : "Dados do pagamento"}</h3>
        {removing ? <p>Novos pagamentos ficarão indisponíveis até configurar o PIX novamente. Pedidos existentes continuam acessíveis.</p> : <>
          <label>Chave PIX ou copia e cola<textarea value={draft.copy_paste} maxLength={4000} required rows={3} onChange={(event) => setDraft({ ...draft, copy_paste: event.target.value })} /></label>
          <p className="field-hint">Aceita CPF, telefone brasileiro, e-mail ou PIX copia e cola. Para uma chave simples, informe também o nome e a cidade do recebedor.</p>
          {!draft.copy_paste.trim().startsWith("000201") ? <div className="gallery-form-grid">
            <label>Nome do recebedor<input value={draft.receiver_name} maxLength={25} required onChange={(event) => setDraft({ ...draft, receiver_name: event.target.value })} /></label>
            <label>Cidade do recebedor<input value={draft.receiver_city} maxLength={15} required onChange={(event) => setDraft({ ...draft, receiver_city: event.target.value })} /></label>
          </div> : null}
          <label>Instruções de pagamento<textarea value={draft.instructions} maxLength={500} rows={3} onChange={(event) => setDraft({ ...draft, instructions: event.target.value })} /></label>
        </>}
        <label>Senha atual<input name="current_password" type="password" autoComplete="current-password" required maxLength={128} /></label>
        <p className="field-hint">A alteração exige sua senha e o código enviado ao WhatsApp administrativo conectado.</p>
        <div className="action-grid"><MarkinaButton disabled={busy}>{busy ? "Enviando código…" : "Enviar código de confirmação"}</MarkinaButton><MarkinaButton type="button" variant="secondary" disabled={busy} onClick={cancel}>Cancelar</MarkinaButton></div>
      </form>}
    </>}
    {pix && error ? <p className="form-message form-message--error" role="alert">{error}</p> : null}
    {message ? <p className="form-message" role="status">{message}</p> : null}
  </section>;
}
