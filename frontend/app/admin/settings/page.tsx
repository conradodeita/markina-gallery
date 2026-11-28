"use client";

import { DEFAULT_WATERMARK_TEXT } from "../../product-brand";


import { ChangeEvent, CSSProperties, FormEvent, MouseEvent, ReactNode, useEffect, useRef, useState } from "react";
import { MarkinaButton, PageHeading, SystemState } from "../../ui-kit";
import { OverviewIcon } from "../overview-icon";
import PixPanel from "./pix-panel";
import PaymentProvidersPanel from "./payment-providers-panel";
import WhatsAppPanel from "./whatsapp-panel";
import SecurityPanel from "./security-panel";
import { OnboardingPanel } from "./onboarding-panel";
import { TenantAddressPanel } from "./tenant-address-panel";
import { PhotographerClosurePanel } from "./tenant-closure-panel";
import styles from "./settings-page.module.css";

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
  watermark_opacity: number;
  watermark_position: string;
  watermark_shadow: boolean;
  watermark_security_lines: boolean;
};

type Asset = "logo" | "app-icon" | "favicon";

const fallback: Branding = {
  login_title: "Sua galeria, do seu jeito.",
  login_intro: "Entre para acessar fotos, seleções e entregas — ou gerenciar sua operação.",
  login_helper: "Escolha seu tipo de acesso para continuar.",
  logo_url: null,
  app_icon_url: null,
  favicon_url: null,
  watermark_text: DEFAULT_WATERMARK_TEXT,
  watermark_font: "sans-serif",
  watermark_color: "#FFFFFF",
  watermark_size: 24,
  watermark_direction: "diagonal",
  watermark_opacity: 42,
  watermark_position: "middle-center",
  watermark_shadow: true,
  watermark_security_lines: false,
};

const watermarkPositions = [
  ["top-left", "Superior esquerda"], ["top-center", "Superior centro"], ["top-right", "Superior direita"],
  ["middle-left", "Centro esquerda"], ["middle-center", "Centro"], ["middle-right", "Centro direita"],
  ["bottom-left", "Inferior esquerda"], ["bottom-center", "Inferior centro"], ["bottom-right", "Inferior direita"],
] as const;

const assetDetails: Record<Asset, { label: string; accept: string; help: string; url: keyof Branding }> = {
  logo: { label: "Logo principal", accept: "image/png,image/jpeg,image/webp", help: "PNG, JPEG ou WebP; até 2 MB.", url: "logo_url" },
  "app-icon": { label: "Ícone do aplicativo", accept: "image/png,image/jpeg,image/webp,image/x-icon", help: "PNG, JPEG, WebP ou ICO; até 1 MB.", url: "app_icon_url" },
  favicon: { label: "Favicon", accept: "image/png,image/x-icon", help: "PNG ou ICO; até 512 KB.", url: "favicon_url" },
};

type WatermarkPreviewCalculation = {
  width: number;
  height: number;
  textWidthAt100: number;
  textHeightAt100: number;
  direction: string;
  coverage: number;
  shadow: boolean;
};

export function calculateWatermarkPreviewFontSize({
  width,
  height,
  textWidthAt100,
  textHeightAt100,
  direction,
  coverage,
  shadow,
}: WatermarkPreviewCalculation) {
  const margin = Math.max(4, Math.round(Math.min(width, height) * 0.025));
  const innerWidth = Math.max(1, width - (margin * 2));
  const innerHeight = Math.max(1, height - (margin * 2));
  const axis = direction === "horizontal"
    ? innerWidth
    : direction === "vertical"
      ? innerHeight
      : Math.hypot(innerWidth, innerHeight);
  const naturalScale = (axis * Math.max(10, Math.min(96, coverage)) / 100) / Math.max(1, textWidthAt100);
  const naturalFontSize = Math.max(1, 100 * naturalScale);
  const shadowOffset = shadow ? Math.max(2, naturalFontSize * 0.025) : 0;
  const gutter = Math.max(5, shadowOffset + 3);
  const layerWidth = (textWidthAt100 * naturalScale) + (gutter * 2) + shadowOffset;
  const layerHeight = (textHeightAt100 * naturalScale) + (gutter * 2) + shadowOffset;
  const angle = direction === "vertical" ? 90 : direction === "diagonal" ? 35 : 0;
  const angleRadians = angle * Math.PI / 180;
  const rotatedWidth = (layerWidth * Math.abs(Math.cos(angleRadians))) + (layerHeight * Math.abs(Math.sin(angleRadians)));
  const rotatedHeight = (layerWidth * Math.abs(Math.sin(angleRadians))) + (layerHeight * Math.abs(Math.cos(angleRadians)));
  const containment = Math.min(1, innerWidth / Math.max(1, rotatedWidth), innerHeight / Math.max(1, rotatedHeight));
  return Math.max(1, naturalFontSize * containment);
}

function ProtectionPreviewSurface({ surface, settings }: { surface: "dark" | "light"; settings: Branding }) {
  const preview = useRef<HTMLDivElement>(null);
  const [layout, setLayout] = useState({ fontSize: 24, margin: 5 });
  const text = settings.watermark_text || DEFAULT_WATERMARK_TEXT;

  useEffect(() => {
    function updateLayout() {
      const element = preview.current;
      if (!element) return;
      const bounds = element.getBoundingClientRect();
      const width = bounds.width || element.clientWidth || 360;
      const height = bounds.height || element.clientHeight || 160;
      let textWidthAt100 = Math.max(1, text.length * 58);
      let textHeightAt100 = 100;
      try {
        const context = navigator.userAgent.includes("jsdom")
          ? null
          : document.createElement("canvas").getContext("2d");
        if (context) {
          context.font = `100px ${settings.watermark_font}`;
          const metrics = context.measureText(text);
          textWidthAt100 = Math.max(1, metrics.width);
          textHeightAt100 = Math.max(
            1,
            (metrics.actualBoundingBoxAscent || 80) + (metrics.actualBoundingBoxDescent || 20),
          );
        }
      } catch {
        // A aproximação por caracteres mantém a prova funcional sem Canvas.
      }
      setLayout({
        fontSize: calculateWatermarkPreviewFontSize({
          width,
          height,
          textWidthAt100,
          textHeightAt100,
          direction: settings.watermark_direction,
          coverage: settings.watermark_size,
          shadow: settings.watermark_shadow,
        }),
        margin: Math.max(4, Math.round(Math.min(width, height) * 0.025)),
      });
    }

    updateLayout();
    const observer = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(updateLayout);
    if (observer && preview.current) observer.observe(preview.current);
    window.addEventListener("resize", updateLayout);
    return () => {
      observer?.disconnect();
      window.removeEventListener("resize", updateLayout);
    };
  }, [settings.watermark_direction, settings.watermark_font, settings.watermark_shadow, settings.watermark_size, text]);

  const markStyle = {
    "--mark-margin": `${layout.margin}px`,
    color: settings.watermark_color,
    fontFamily: settings.watermark_font,
    fontSize: `${layout.fontSize}px`,
    opacity: settings.watermark_opacity / 100,
    textShadow: settings.watermark_shadow ? "0 2px 5px #000" : "none",
  } as CSSProperties;

  return <div ref={preview} className={`protection-preview-surface is-${surface}`} data-watermark-coverage={settings.watermark_size} data-watermark-direction={settings.watermark_direction}>
    {settings.watermark_security_lines ? <span className="protection-preview-security-lines" aria-hidden="true" style={{ opacity: settings.watermark_opacity / 200 }} /> : null}
    <span className={`protection-preview-mark watermark-preview--${settings.watermark_direction} is-${settings.watermark_position}`} style={markStyle}>{text}</span>
    <small>{surface === "dark" ? "Fundo escuro" : "Fundo claro"}</small>
  </div>;
}

function revealSettingsAnchor(hash: string) {
  let id: string;
  try { id = decodeURIComponent(hash.replace(/^#/, "")); } catch { return; }
  if (!id) return;
  const target = document.getElementById(id);
  if (!target) return;
  let ancestor: HTMLElement | null = target;
  while (ancestor) {
    if (ancestor instanceof HTMLDetailsElement) ancestor.open = true;
    ancestor = ancestor.parentElement;
  }
  target.scrollIntoView?.({ block: "start" });
}

function handleSettingsAnchor(event: MouseEvent<HTMLElement>) {
  if (event.defaultPrevented || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
  const link = event.target instanceof Element ? event.target.closest('a[href^="#"]') : null;
  if (link instanceof HTMLAnchorElement) revealSettingsAnchor(link.hash);
}

function SettingsGroup({ id, title, description, icon, children, initiallyOpen = false }: {
  id: string; title: string; description: string; icon: string; children: ReactNode; initiallyOpen?: boolean;
}) {
  return <details id={id} className={styles.group} open={initiallyOpen}>
    <summary className={styles.groupSummary}>
      <span className={styles.groupIcon}><OverviewIcon name={icon} /></span>
      <div className={styles.groupHeading}>
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
      <span className={styles.chevron} aria-hidden="true">⌄</span>
    </summary>
    <div className={styles.groupContent}>{children}</div>
  </details>;
}

export default function AdminSettingsPage() {
  const [settings, setSettings] = useState<Branding | null>(null);
  const [termsPortalTarget, setTermsPortalTarget] = useState<HTMLDivElement | null>(null);
  const settingsLoaded = settings !== null;

  useEffect(() => {
    if (!settingsLoaded) return;
    const revealHash = () => revealSettingsAnchor(window.location.hash);
    revealHash();
    window.addEventListener("hashchange", revealHash);
    return () => window.removeEventListener("hashchange", revealHash);
  }, [settingsLoaded, termsPortalTarget]);
  const [protectionPreview, setProtectionPreview] = useState(fallback);
  const [message, setMessage] = useState("");
  const [assetVersion, setAssetVersion] = useState(0);
  const [uploading, setUploading] = useState<Asset | null>(null);

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
      watermark_opacity: Number(data.get("watermark_opacity") ?? 42),
      watermark_position: String(data.get("watermark_position") ?? "middle-center"),
      watermark_shadow: data.has("watermark_shadow"),
      watermark_security_lines: data.has("watermark_security_lines"),
    }));
  }

  async function upload(asset: Asset, event: ChangeEvent<HTMLInputElement>) {
    const input = event.currentTarget;
    const file = event.target.files?.[0];
    if (!file || !settings) return;
    setMessage("");
    setUploading(asset);
    try {
      const response = await fetch(`/api/admin/branding/${asset}`, {
        method: "PUT",
        credentials: "same-origin",
        headers: { "Content-Type": file.type },
        body: file,
      });
      if (!response.ok) throw new Error();
      const payload = await response.json();
      setSettings((current) => current ? { ...current, ...payload } : current);
      const version = assetVersion + 1;
      setAssetVersion(version);
      if (asset === "favicon") {
        document.querySelectorAll<HTMLLinkElement>('link[rel="icon"]').forEach((link) => {
          link.href = `/api/branding/favicon?v=${version}`;
        });
      }
      setMessage(`${assetDetails[asset].label} atualizado.`);
    } catch {
      setMessage(`Não foi possível enviar ${assetDetails[asset].label.toLowerCase()}.`);
    } finally {
      setUploading(null);
      input.value = "";
    }
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
        watermark_opacity: Number(data.get("watermark_opacity")),
        watermark_position: data.get("watermark_position"),
        watermark_shadow: data.has("watermark_shadow"),
        watermark_security_lines: data.has("watermark_security_lines"),
      }),
    });
    setMessage(response.ok ? "Proteção visual da sua conta salva. As prévias serão atualizadas com segurança." : "Não foi possível salvar a proteção visual.");
    if (response.ok) {
      const updated = { ...settings, ...(await response.json()) };
      setSettings(updated);
      setProtectionPreview(updated);
    }
  }


  if (!settings) {
    return <SystemState tone={message ? "error" : "loading"} title={message ? "Configurações indisponíveis" : "Carregando configurações"} detail={message || "Consultando a identidade da sua entrada."} />;
  }

  return (
    <div className={styles.page} data-settings-page onClick={handleSettingsAnchor}>
      <PageHeading title="Configurações" detail="Gerencie acesso, comunicação, recebimentos e identidade do seu estúdio." />
      <nav className={styles.navigation} aria-label="Seções de configurações">
        <a href="#settings-start">Primeiros passos</a>
        <a href="#settings-security">Acesso e segurança</a>
        <a href="#settings-whatsapp">WhatsApp</a>
        <a href="#settings-payments">Recebimentos</a>
        <a href="#settings-brand">Marca e aparência</a>
        <a href="#settings-closure">Encerrar conta</a>
        <a href="#settings-terms">Termos de uso</a>
      </nav>

      <SettingsGroup id="settings-start" icon="grid_view" title="Primeiros passos" description="Configure o link da sua marca e acompanhe o que falta para operar." initiallyOpen>
        <TenantAddressPanel />
        <OnboardingPanel termsPortalTarget={termsPortalTarget} />
      </SettingsGroup>

      <SettingsGroup id="settings-security" icon="settings" title="Acesso e segurança" description="Gerencie sua senha, autenticador e formas de recuperar o acesso à conta.">
        <SecurityPanel />
      </SettingsGroup>

      <SettingsGroup id="settings-whatsapp" icon="notifications" title="WhatsApp" description="Conecte seu número para enviar notificações aos clientes.">
        <WhatsAppPanel />
      </SettingsGroup>

      <SettingsGroup id="settings-payments" icon="payments" title="Recebimentos" description="Configure como os clientes pagam pelas fotos e onde você recebe.">
        <PixPanel />
        <PaymentProvidersPanel />
      </SettingsGroup>

      <SettingsGroup id="settings-brand" icon="photo_camera" title="Marca e aparência" description="Personalize a entrada da plataforma e a proteção visual aplicada às prévias.">
        <form className={`gallery-editor-panel gallery-settings-form ${styles.entryForm}`} onSubmit={save}>
          <div className={styles.entryFields}>
            <h3>Textos da página de entrada</h3>
            <p>Os textos são simples, sem HTML ou scripts.</p>
            <label>Título da entrada<input name="login_title" defaultValue={settings.login_title} maxLength={120} required /></label>
            <label>Texto introdutório<textarea name="login_intro" defaultValue={settings.login_intro} maxLength={300} rows={3} required /></label>
            <label>Orientação auxiliar<input name="login_helper" defaultValue={settings.login_helper} maxLength={240} required /></label>
            <MarkinaButton type="submit">Salvar textos</MarkinaButton>
          </div>
          <div className="auth-preview" aria-live="polite">
            <p className="eyebrow">Prévia</p>
            {settings.logo_url ? <img className="auth-brand-logo" src={`/api${settings.logo_url}?v=${assetVersion}`} alt="Logo configurado" /> : null}
            <h2>{settings.login_title}</h2>
            <p>{settings.login_intro}</p>
            <small>{settings.login_helper}</small>
          </div>
        </form>
        <section className="admin-card" aria-labelledby="branding-assets-title">
          <h3 id="branding-assets-title">Logo e ícones</h3>
          <p className="intro">Envie os ativos da sua marca. O servidor confere formato, dimensões e tamanho antes de substituir a configuração.</p>
          <div className="gallery-settings-assets">
            {(Object.keys(assetDetails) as Asset[]).map((asset) => {
              const detail = assetDetails[asset];
              const configuredUrl = settings[detail.url] as string | null;
              return <label key={asset} className="gallery-settings-asset">
                <span>{detail.label}</span>
                <small>{detail.help}</small>
                <input aria-label={`Enviar ${detail.label}`} type="file" accept={detail.accept} disabled={uploading !== null} onChange={(event) => upload(asset, event)} />
                {/* eslint-disable-next-line @next/next/no-img-element -- Ativo de marca validado no upload, atualizado sem cache de transformação. */}
                {configuredUrl ? <img className="branding-asset-preview" src={`/api${configuredUrl}?v=${assetVersion}`} alt={`${detail.label} configurado`} /> : null}
                {uploading === asset ? <span className="asset-status">Enviando…</span> : configuredUrl ? <span className="asset-status">Configurado</span> : <span className="asset-status">Ainda não configurado</span>}
              </label>;
            })}
          </div>
        </section>
        <section className="admin-card protection-settings" aria-labelledby="visual-protection-title">
          <div className="protection-settings-heading">
            <div>
              <p className="eyebrow">Padrão da sua conta</p>
              <h3 id="visual-protection-title">Proteção visual das galerias</h3>
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
                <label>Cobertura da marca-d’água (%)<input aria-label="Cobertura da marca-d’água (%)" name="watermark_size" type="number" min={10} max={96} defaultValue={settings.watermark_size} /><small>Percentual aproximado do eixo da foto; o texto é reduzido apenas se necessário para permanecer inteiro.</small></label>
                <label>Direção<select name="watermark_direction" defaultValue={settings.watermark_direction}><option value="horizontal">Horizontal</option><option value="vertical">Vertical</option><option value="diagonal">Diagonal</option></select></label>
                <label>Transparência — {protectionPreview.watermark_opacity}%<input name="watermark_opacity" type="range" min={10} max={100} step={1} defaultValue={settings.watermark_opacity} /></label>
                <label className="protection-toggle"><input name="watermark_shadow" type="checkbox" defaultChecked={settings.watermark_shadow} /> Aplicar sombra ao texto</label>
                <label className="protection-toggle"><input name="watermark_security_lines" type="checkbox" defaultChecked={settings.watermark_security_lines} /> Usar linhas transversais de segurança</label>
                <fieldset className="watermark-position-control">
                  <legend>Posição principal do padrão</legend>
                  {watermarkPositions.map(([value, label]) => <label key={value} title={label}><input aria-label={label} type="radio" name="watermark_position" value={value} defaultChecked={settings.watermark_position === value} /><span aria-hidden="true" /></label>)}
                </fieldset>
              </fieldset>
              <MarkinaButton type="submit" className="protection-settings-save">Salvar proteção da sua conta</MarkinaButton>
            </div>
            <aside className="protection-settings-preview" aria-labelledby="protection-preview-title" aria-live="polite">
              <div>
                <p className="eyebrow">Prova de contraste</p>
                <h4 id="protection-preview-title">Como a identificação se comporta</h4>
                <p>Superfícies neutras para avaliar leitura. Elas não simulam uma fotografia.</p>
              </div>
              <div className="protection-preview-surfaces">
                {(["dark", "light"] as const).map((surface) => <ProtectionPreviewSurface surface={surface} settings={protectionPreview} key={surface} />)}
              </div>
              <p className="protection-settings-note">A identificação aparecerá uma única vez em cada prévia protegida gerada pelo processamento seguro.</p>
            </aside>
          </form>
        </section>
        {message ? <p className="form-message" role="status">{message}</p> : null}
      </SettingsGroup>

      <SettingsGroup id="settings-closure" icon="folder_open" title="Encerramento da conta" description="Consulte prazos, pendências e consequências antes de solicitar o encerramento.">
        <PhotographerClosurePanel />
      </SettingsGroup>

      <SettingsGroup id="settings-terms" icon="folder_shared" title="Termos de uso" description="Leia os termos vigentes e consulte o histórico de aceites registrados para sua conta.">
        <div className={styles.termsSlot} ref={setTermsPortalTarget} />
      </SettingsGroup>
    </div>
  );
}
