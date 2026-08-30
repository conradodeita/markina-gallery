"use client";

import { ChangeEvent, FormEvent, useEffect, useState } from "react";
import { SystemState } from "../../ui-kit";

type Branding = {
  login_title: string;
  login_intro: string;
  login_helper: string;
  logo_url: string | null;
  app_icon_url: string | null;
  favicon_url: string | null;
  watermark_text: string;
  watermark_font: string;
  watermark_color: string;
  watermark_size: number;
  watermark_direction: string;
};

type Asset = "logo" | "app-icon" | "favicon";
type PaymentTemplates = { confirmed: string; refused: string };

const fallback: Branding = {
  login_title: "Sua galeria, do seu jeito.",
  login_intro: "Entre para acessar fotos, seleções e entregas — ou gerenciar sua operação.",
  login_helper: "Escolha seu tipo de acesso para continuar.",
  logo_url: null,
  app_icon_url: null,
  favicon_url: null,
  watermark_text: "MARKINA • PRÉVIA",
  watermark_font: "sans-serif",
  watermark_color: "#FFFFFF",
  watermark_size: 24,
  watermark_direction: "diagonal",
};

const assetDetails: Record<Asset, { label: string; accept: string; help: string; url: keyof Branding }> = {
  logo: { label: "Logo principal", accept: "image/png,image/jpeg,image/webp", help: "PNG, JPEG ou WebP; até 2 MB.", url: "logo_url" },
  "app-icon": { label: "Ícone do aplicativo", accept: "image/png,image/jpeg,image/webp,image/x-icon", help: "PNG, JPEG, WebP ou ICO; até 1 MB.", url: "app_icon_url" },
  favicon: { label: "Favicon", accept: "image/png,image/x-icon", help: "PNG ou ICO; até 512 KB.", url: "favicon_url" },
};

export default function AdminSettingsPage() {
  const [settings, setSettings] = useState<Branding | null>(null);
  const [protectionPreview, setProtectionPreview] = useState(fallback);
  const [message, setMessage] = useState("");
  const [paymentTemplates, setPaymentTemplates] = useState<PaymentTemplates | null>(null);

  useEffect(() => {
    fetch("/api/admin/branding", { credentials: "same-origin" })
      .then(async (response) => {
        if (!response.ok) throw new Error();
        const loaded = { ...fallback, ...(await response.json()) };
        setSettings(loaded);
        setProtectionPreview(loaded);
      })
      .catch(() => setMessage("Não foi possível carregar as configurações."));
  }, []);

  useEffect(() => {
    fetch("/api/admin/payment-message-templates", { credentials: "same-origin" })
      .then(async (response) => {
        if (!response.ok) throw new Error();
        const result = await response.json();
        if (result.templates?.confirmed && result.templates?.refused) setPaymentTemplates(result.templates);
      })
      .catch(() => setPaymentTemplates(null));
  }, []);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!settings) return;
    const data = new FormData(event.currentTarget);
    const response = await fetch("/api/admin/branding", {
      method: "PATCH",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        login_title: data.get("login_title"),
        login_intro: data.get("login_intro"),
        login_helper: data.get("login_helper"),
      }),
    });
    setMessage(response.ok ? "Textos da entrada salvos." : "Não foi possível salvar os textos.");
    if (response.ok) {
      const updated = { ...settings, ...(await response.json()) };
      setSettings(updated);
      setProtectionPreview(updated);
    }
  }

  function updateProtectionPreview(event: FormEvent<HTMLFormElement>) {
    const data = new FormData(event.currentTarget);
    setProtectionPreview((current) => ({
      ...current,
      watermark_text: String(data.get("watermark_text") ?? ""),
      watermark_font: String(data.get("watermark_font") ?? "sans-serif"),
      watermark_color: String(data.get("watermark_color") ?? "#FFFFFF"),
      watermark_size: Number(data.get("watermark_size") ?? 24),
      watermark_direction: String(data.get("watermark_direction") ?? "diagonal"),
    }));
  }

  async function upload(asset: Asset, event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file || !settings) return;
    setMessage("");
    const response = await fetch(`/api/admin/branding/${asset}`, {
      method: "PUT",
      credentials: "same-origin",
      headers: { "Content-Type": file.type },
      body: file,
    });
    if (!response.ok) {
      setMessage(`Não foi possível enviar ${assetDetails[asset].label.toLowerCase()}.`);
      return;
    }
    setSettings({ ...settings, ...(await response.json()) });
    setMessage(`${assetDetails[asset].label} atualizado.`);
    event.target.value = "";
  }

  async function saveProtection(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!settings) return;
    const data = new FormData(event.currentTarget);
    const response = await fetch("/api/admin/branding/protection", {
      method: "PATCH",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        watermark_text: data.get("watermark_text"),
        watermark_font: data.get("watermark_font"),
        watermark_color: data.get("watermark_color"),
        watermark_size: Number(data.get("watermark_size")),
        watermark_direction: data.get("watermark_direction"),
      }),
    });
    setMessage(response.ok ? "Proteção visual global salva. As prévias serão atualizadas com segurança." : "Não foi possível salvar a proteção visual.");
    if (response.ok) {
      const updated = { ...settings, ...(await response.json()) };
      setSettings(updated);
      setProtectionPreview(updated);
    }
  }

  async function savePaymentTemplate(kind: keyof PaymentTemplates, event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const body = String(new FormData(event.currentTarget).get("body") ?? "");
    const response = await fetch(`/api/admin/payment-message-templates/${kind}`, {
      method: "PUT",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ body }),
    });
    setMessage(response.ok ? "Mensagem transacional salva." : "Não foi possível salvar: use apenas texto e variáveis permitidas.");
    if (response.ok && paymentTemplates) setPaymentTemplates({ ...paymentTemplates, [kind]: (await response.json()).body });
  }

  if (!settings) {
    return <SystemState tone={message ? "error" : "loading"} title={message ? "Configurações indisponíveis" : "Carregando configurações"} detail={message || "Consultando a identidade da sua entrada."} />;
  }

  return (
    <main className="admin-shell">
      <p className="eyebrow">Markina Gallery · Fotógrafo</p>
      <h1>Configurações</h1>
      <p className="intro">Personalize a mensagem que clientes e fotógrafos encontram antes de entrar. Os textos são simples, sem HTML ou scripts.</p>
      <form className="gallery-editor-panel gallery-settings-form" onSubmit={save}>
        <label>Título da entrada<input name="login_title" defaultValue={settings.login_title} maxLength={120} required /></label>
        <label>Texto introdutório<textarea name="login_intro" defaultValue={settings.login_intro} maxLength={300} rows={3} required /></label>
        <label>Orientação auxiliar<input name="login_helper" defaultValue={settings.login_helper} maxLength={240} required /></label>
        <div className="auth-preview" aria-live="polite">
          <p className="eyebrow">Prévia</p>
          {settings.logo_url ? <img className="auth-brand-logo" src={`/api${settings.logo_url}`} alt="Logo configurado" /> : null}
          <h2>{settings.login_title}</h2>
          <p>{settings.login_intro}</p>
          <small>{settings.login_helper}</small>
        </div>
        <button className="primary">Salvar textos</button>
      </form>
      <section className="admin-card" aria-labelledby="branding-assets-title">
        <h2 id="branding-assets-title">Identidade visual</h2>
        <p className="intro">Envie somente os ativos oficiais. O servidor confere formato, MIME, dimensões e tamanho antes de substituir a configuração.</p>
        <div className="gallery-settings-assets">
          {(Object.keys(assetDetails) as Asset[]).map((asset) => {
            const detail = assetDetails[asset];
            const configuredUrl = settings[detail.url] as string | null;
            return <label key={asset} className="gallery-settings-asset">
              <span>{detail.label}</span>
              <small>{detail.help}</small>
              <input aria-label={`Enviar ${detail.label}`} type="file" accept={detail.accept} onChange={(event) => upload(asset, event)} />
              {configuredUrl ? <span className="asset-status">Configurado</span> : <span className="asset-status">Usando fallback Markina</span>}
            </label>;
          })}
        </div>
      </section>
      <section className="admin-card protection-settings" aria-labelledby="visual-protection-title">
        <div className="protection-settings-heading">
          <div>
            <p className="eyebrow">Padrão global</p>
            <h2 id="visual-protection-title">Proteção visual das galerias</h2>
          </div>
          <span className="protection-settings-status">Aplicada pelo servidor</span>
        </div>
        <p className="intro">Defina a identificação que será gravada nas prévias protegidas. Os arquivos originais permanecem fora do navegador; esta camada desestimula cópias, mas não promete bloquear capturas de tela.</p>
        <form className="protection-settings-form" onSubmit={saveProtection} onChange={updateProtectionPreview}>
          <div className="protection-settings-controls">
            <fieldset className="protection-settings-group">
              <legend>Conteúdo</legend>
              <p>Use uma identificação curta e reconhecível em todas as galerias.</p>
              <label>Texto da marca-d’água<input name="watermark_text" defaultValue={settings.watermark_text} maxLength={120} required /></label>
              <label>Tipografia da marca-d’água<select name="watermark_font" defaultValue={settings.watermark_font}><option value="sans-serif">Sans-serif</option><option value="serif">Serifada</option><option value="monospace">Monoespaçada</option><option value="DejaVuSans">DejaVu Sans</option><option value="DejaVuSerif">DejaVu Serif</option></select></label>
            </fieldset>
            <fieldset className="protection-settings-group protection-settings-appearance">
              <legend>Aparência</legend>
              <p>A prova ao lado ajuda a conferir legibilidade em fundos opostos.</p>
              <label>Cor da marca-d’água<span className="protection-color-control"><input name="watermark_color" type="color" defaultValue={settings.watermark_color} /><code>{protectionPreview.watermark_color.toUpperCase()}</code></span></label>
              <label>Tamanho da marca-d’água<input name="watermark_size" type="number" min={10} max={96} defaultValue={settings.watermark_size} /></label>
              <label>Direção<select name="watermark_direction" defaultValue={settings.watermark_direction}><option value="horizontal">Horizontal</option><option value="vertical">Vertical</option><option value="diagonal">Diagonal</option></select></label>
            </fieldset>
            <button className="primary protection-settings-save">Salvar proteção global</button>
          </div>
          <aside className="protection-settings-preview" aria-labelledby="protection-preview-title" aria-live="polite">
            <div>
              <p className="eyebrow">Prova de contraste</p>
              <h3 id="protection-preview-title">Como a identificação se comporta</h3>
              <p>Superfícies neutras para avaliar leitura. Elas não simulam uma fotografia.</p>
            </div>
            <div className="protection-preview-surfaces">
              {(["dark", "light"] as const).map((surface) => <div className={`protection-preview-surface is-${surface}`} key={surface}><span className={`protection-preview-mark watermark-preview--${protectionPreview.watermark_direction}`} style={{ color: protectionPreview.watermark_color, fontFamily: protectionPreview.watermark_font, fontSize: `${Math.min(protectionPreview.watermark_size, 32)}px` }}>{protectionPreview.watermark_text || "MARKINA • PRÉVIA"}</span><small>{surface === "dark" ? "Fundo escuro" : "Fundo claro"}</small></div>)}
            </div>
            <p className="protection-settings-note">A marca será repetida sobre cada prévia protegida depois do salvamento e do processamento seguro.</p>
          </aside>
        </form>
      </section>
      <section className="admin-card" aria-labelledby="payment-messages-title">
        <h2 id="payment-messages-title">Mensagens de pagamento</h2>
        <p className="intro">Use somente texto simples e as variáveis controladas <code>{"{{cliente}}"}</code>, <code>{"{{pedido}}"}</code> e <code>{"{{galeria}}"}</code>. URLs, HTML e dados bancários não são aceitos.</p>
        {paymentTemplates ? <div className="dashboard-columns">
          <form className="gallery-settings-form" onSubmit={(event) => savePaymentTemplate("confirmed", event)}>
            <label>Confirmação<textarea name="body" defaultValue={paymentTemplates.confirmed} maxLength={500} rows={5} required /></label>
            <button className="primary">Salvar confirmação</button>
          </form>
          <form className="gallery-settings-form" onSubmit={(event) => savePaymentTemplate("refused", event)}>
            <label>Pagamento não localizado<textarea name="body" defaultValue={paymentTemplates.refused} maxLength={500} rows={5} required /></label>
            <button className="primary">Salvar recusa</button>
          </form>
        </div> : <SystemState title="Mensagens indisponíveis" detail="A configuração transacional não pôde ser carregada." />}
      </section>
      {message ? <p className="form-message" role="status">{message}</p> : null}
    </main>
  );
}
