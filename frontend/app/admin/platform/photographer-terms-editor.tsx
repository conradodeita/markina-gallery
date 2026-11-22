"use client";

import { type FormEvent, useEffect, useMemo, useState } from "react";
import { MarkinaButton, SurfaceCard } from "../../ui-kit";

type Draft = {
  revision: string | null;
  template_text: string;
  provider_legal_name: string;
  provider_contact_email: string;
  updated_at: string | null;
};
type Version = { version: string; template_sha256: string; published_at: string; provider_legal_name: string; provider_contact_email: string };

async function api(path: string, init?: RequestInit) {
  const response = await fetch(`/api/admin/platform/terms${path}`, {
    ...init, credentials: "same-origin", cache: "no-store",
    ...(init?.body ? { headers: { "Content-Type": "application/json", ...init.headers } } : {}),
  });
  if (!response.ok) throw new Error(response.status === 409 ? "O rascunho mudou ou a publicação não foi aceita. Atualize os dados e tente novamente." : "Não foi possível salvar os Termos. Tente novamente.");
  return response.json();
}

export function PhotographerTermsEditor() {
  const [draft, setDraft] = useState<Draft | null>(null);
  const [versions, setVersions] = useState<Version[]>([]);
  const [password, setPassword] = useState("");
  const [totp, setTotp] = useState("");
  const [confirmPublish, setConfirmPublish] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function refresh() {
    const [saved, published] = await Promise.all([api("/draft"), api("/versions")]);
    setDraft(saved as Draft);
    setVersions(published.items as Version[]);
  }

  useEffect(() => {
    let active = true;
    void Promise.all([api("/draft"), api("/versions")]).then(([saved, published]) => {
      if (active) { setDraft(saved as Draft); setVersions(published.items as Version[]); }
    }).catch(() => { if (active) setError("Não foi possível carregar os Termos."); });
    return () => { active = false; };
  }, []);

  const preview = useMemo(() => draft?.template_text
    .replaceAll("{{provider_legal_name}}", draft.provider_legal_name || "[Nome do provedor]")
    .replaceAll("{{provider_contact_email}}", draft.provider_contact_email || "[E-mail de contato]")
    .replaceAll("{{photographer_name}}", "[Nome do fotógrafo]")
    .replaceAll("{{photographer_verified_email}}", "[E-mail verificado do fotógrafo]") ?? "", [draft]);

  function changeDraft(update: Partial<Draft>) { setDraft((current) => current ? { ...current, ...update } : current); }

  async function save(event: FormEvent) {
    event.preventDefault(); if (!draft) return;
    setBusy(true); setError(""); setMessage("");
    try {
      const result = await api("/draft", { method: "PUT", body: JSON.stringify({
        revision: draft.revision,
        template_text: draft.template_text,
        provider_legal_name: draft.provider_legal_name,
        provider_contact_email: draft.provider_contact_email,
      }) });
      setDraft(result as Draft); setMessage("Rascunho salvo. A versão publicada continua inalterada.");
    } catch (failure) { setError(failure instanceof Error ? failure.message : "Não foi possível salvar o rascunho."); }
    finally { setBusy(false); }
  }

  async function publish(event: FormEvent) {
    event.preventDefault(); if (!draft?.revision || !confirmPublish) return;
    setBusy(true); setError(""); setMessage("");
    try {
      const result = await api("/publish", { method: "POST", body: JSON.stringify({
        expected_revision: draft.revision, confirm_publication: true,
        current_password: password, totp_code: totp,
      }) });
      setPassword(""); setTotp(""); setConfirmPublish(false);
      setMessage(result.already_current ? `${result.version} já é a versão vigente.` : `Versão ${result.version} publicada.`);
      await refresh();
    } catch (failure) { setError(failure instanceof Error ? failure.message : "Não foi possível publicar os Termos."); }
    finally { setBusy(false); }
  }

  return <SurfaceCard>
    <h2>Termos do fotógrafo</h2>
    <p>Edite e confira a prévia. Salvar cria apenas um rascunho; publicar exige confirmação e senha mais código do autenticador. Versões publicadas ficam preservadas.</p>
    {!draft ? <p role="status">Carregando rascunho…</p> : <>
      <form onSubmit={save}>
        <label>Nome legal do provedor<input maxLength={160} value={draft.provider_legal_name} onChange={(event) => changeDraft({ provider_legal_name: event.target.value })} required /></label>
        <label>E-mail público de suporte e privacidade<input type="email" maxLength={320} value={draft.provider_contact_email} onChange={(event) => changeDraft({ provider_contact_email: event.target.value })} required /></label>
        <label>Texto dos Termos<textarea rows={16} maxLength={50_000} value={draft.template_text} onChange={(event) => changeDraft({ template_text: event.target.value })} required /></label>
        <details><summary>Prévia do rascunho</summary><pre style={{ whiteSpace: "pre-wrap", maxHeight: "30rem", overflow: "auto" }}>{preview}</pre></details>
        <MarkinaButton disabled={busy}>Salvar rascunho</MarkinaButton>
      </form>
      <form onSubmit={publish}>
        <h3>Publicação explícita</h3>
        <label><input type="checkbox" required checked={confirmPublish} onChange={(event) => setConfirmPublish(event.target.checked)} />Confirmo que revisei este rascunho e quero publicá-lo para novos aceites.</label>
        <label>Senha atual do proprietário<input type="password" autoComplete="current-password" required maxLength={128} value={password} onChange={(event) => setPassword(event.target.value)} /></label>
        <label>Código do autenticador<input inputMode="numeric" autoComplete="one-time-code" required pattern="[0-9]{6}" maxLength={6} value={totp} onChange={(event) => setTotp(event.target.value)} /></label>
        <MarkinaButton disabled={busy || !draft.revision || !confirmPublish}>Publicar nova versão</MarkinaButton>
      </form>
    </>}
    {error ? <p role="alert">{error}</p> : null}{message ? <p role="status">{message}</p> : null}
    <h3>Versões publicadas</h3>
    {versions.length ? <ul>{versions.map((version) => <li key={version.version}>{version.version} · {new Date(version.published_at).toLocaleString("pt-BR")} · SHA-256 {version.template_sha256}</li>)}</ul> : <p>Nenhuma versão publicada.</p>}
  </SurfaceCard>;
}
