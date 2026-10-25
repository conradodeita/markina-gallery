"use client";

import { type FormEvent, useEffect, useState } from "react";
import { paymentRequest } from "../../library/mercadopago";
import { StatusBadge } from "../../ui-kit";
import styles from "./payment-providers.module.css";

type Settings = {
  version: number; pix_enabled: boolean; mercadopago_enabled: boolean; mercadopago_available: boolean;
  account: { seller_id: string; status: string; test_account: boolean; webhook_path: string } | null;
};
type Challenge = { challenge_id: string; expires_at: string };

export default function PaymentProvidersPanel() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [flags, setFlags] = useState({ pix: true, mp: false });
  const [challenge, setChallenge] = useState<Challenge | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [siteOrigin, setSiteOrigin] = useState("");

  useEffect(() => {
    let disposed = false;
    void paymentRequest<Settings>("/admin/settings/payment-providers").then((result) => {
      if (!disposed) { setSiteOrigin(window.location.origin); setSettings(result); setFlags({ pix: result.pix_enabled, mp: result.mercadopago_enabled }); }
    }).catch(() => { if (!disposed) setError("Não foi possível consultar os meios de pagamento."); });
    return () => { disposed = true; };
  }, []);

  async function start(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy || !settings) return;
    const form = event.currentTarget;
    const data = new FormData(form);
    setBusy(true); setError(""); setNotice("");
    const body = {
      expected_version: settings.version, pix_enabled: flags.pix, mercadopago_enabled: flags.mp,
      current_password: String(data.get("password") ?? ""),
      ...(data.get("access_token") || data.get("public_key") || data.get("webhook_secret") ? {
        access_token: String(data.get("access_token") ?? ""),
        public_key: String(data.get("public_key") ?? ""),
        webhook_secret: String(data.get("webhook_secret") ?? ""),
      } : {}),
    };
    try {
      setChallenge(await paymentRequest<Challenge>("/admin/settings/payment-providers/challenge", body));
    } catch (failure) { setError((failure as Error).message); }
    finally {
      for (const name of ["password", "access_token", "webhook_secret"]) {
        const input = form.elements.namedItem(name);
        if (input instanceof HTMLInputElement) input.value = "";
      }
      setBusy(false);
    }
  }

  async function confirm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!challenge || busy) return;
    const data = new FormData(event.currentTarget);
    setBusy(true); setError("");
    try {
      const result = await paymentRequest<Settings>("/admin/settings/payment-providers/confirm", {
        challenge_id: challenge.challenge_id, code: String(data.get("code") ?? ""),
      });
      setSettings(result); setChallenge(null);
      setNotice("Meios de pagamento salvos. As próximas compras usarão esta configuração.");
    } catch (failure) { setError((failure as Error).message); }
    finally { setBusy(false); }
  }

  async function resend() {
    if (!challenge || busy) return;
    setBusy(true); setError("");
    try {
      await paymentRequest("/admin/settings/payment-providers/resend", { challenge_id: challenge.challenge_id });
      setNotice("Código reenviado ao WhatsApp administrativo.");
    } catch (failure) { setError((failure as Error).message); }
    finally { setBusy(false); }
  }

  const webhookUrl = settings?.account ? `${siteOrigin}${settings.account.webhook_path}` : "";
  async function copyWebhook() {
    setError(""); setNotice("");
    try {
      await navigator.clipboard.writeText(webhookUrl);
      setNotice("Endereço do webhook copiado.");
    } catch { setError("Não foi possível copiar. Selecione o endereço e copie manualmente."); }
  }

  return <section className={`admin-card ${styles.panel}`} id="payment-providers" aria-labelledby="payment-providers-title">
    <header className={styles.header}>
      <span className={styles.icon} aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6"><rect x="3" y="5" width="18" height="14" rx="3" /><path d="M3 10h18M7 15h4" /></svg></span>
      <div><span className={styles.eyebrow}>Recebimentos</span><h2 id="payment-providers-title">Meios de pagamento</h2>
        <p>Escolha como seus clientes pagam. A configuração vale somente para a sua conta de fotógrafo.</p></div>
    </header>
    <div className={styles.status}>
      {settings ? <StatusBadge tone={settings.mercadopago_available ? "success" : "neutral"}>
        {settings.account?.status === "unauthorized" ? "Mercado Pago · reconexão necessária"
          : settings.account?.test_account && settings.mercadopago_enabled ? "Mercado Pago em teste"
          : settings.mercadopago_available ? "Mercado Pago disponível" : "Mercado Pago desabilitado ou indisponível"}
      </StatusBadge> : <p role="status">Carregando meios de pagamento…</p>}
      {settings?.account ? <span>Conta verificada · {settings.account.seller_id}{settings.account.test_account ? " · teste" : ""}</span> : <span>Conecte a sua própria conta Mercado Pago</span>}
    </div>
    {settings?.account ? <div className={styles.webhook}>
      <label htmlFor="payment-webhook-url">Endereço do webhook da aplicação</label>
      <div className={styles.copyRow}><input id="payment-webhook-url" readOnly value={webhookUrl} aria-describedby="payment-webhook-help" />
        <button type="button" className="secondary" onClick={() => void copyWebhook()}>Copiar URL</button></div>
      <p id="payment-webhook-help" className={styles.hint}>No Mercado Pago, abra Webhooks, cole este endereço HTTPS e selecione o evento <strong>Order</strong>. Isso permite atualizar seus pagamentos automaticamente.</p>
    </div> : null}
    {error ? <p className={styles.error} role="alert">{error}</p> : null}
    {notice ? <p className={styles.notice} role="status">{notice}</p> : null}
    {!challenge ? <form onSubmit={start} autoComplete="off" className={styles.form}>
      <fieldset disabled={busy || !settings} className={styles.fields}>
        <legend className={styles.legend}>Disponibilidade para novas compras</legend>
        <div className={styles.methods}>
          <label className={styles.method} data-enabled={flags.pix}>
            <input type="checkbox" checked={flags.pix} aria-labelledby="payment-pix-label" aria-describedby="payment-pix-help"
              onChange={(event) => setFlags({ ...flags, pix: event.target.checked })} />
            <span><strong id="payment-pix-label">PIX do sistema</strong><span id="payment-pix-help">Mantenha o PIX atual, com conferência manual pelo fotógrafo.</span></span>
          </label>
          <label className={styles.method} data-enabled={flags.mp}>
            <input type="checkbox" checked={flags.mp} aria-labelledby="payment-mp-label" aria-describedby="payment-mp-help"
              onChange={(event) => setFlags({ ...flags, mp: event.target.checked })} />
            <span><strong id="payment-mp-label">Mercado Pago · Checkout Transparente</strong><span id="payment-mp-help">Cartão e PIX dentro da compra, com confirmação automática.</span></span>
          </label>
        </div>
        <p className={styles.hint}>Você pode usar os dois. Alterar a disponibilidade não cancela pagamentos já iniciados.</p>
        <details className={styles.credentials} open={settings?.account ? undefined : true}>
          <summary>{settings?.account ? "Substituir credenciais Mercado Pago" : "Configurar conta Mercado Pago"}</summary>
          <div className={styles.credentialsBody}>
            <p>Use a aplicação brasileira da sua própria conta, configurada para <strong>Checkout Transparente via Orders API</strong>.</p>
            <a className={styles.docsLink} href="https://www.mercadopago.com.br/developers/panel/app" target="_blank" rel="noopener noreferrer">Abrir minhas integrações no Mercado Pago ↗</a>
            <div className={styles.inputGrid}>
              <div className={styles.field}><label htmlFor="payment-public-key">Public Key</label>
                <input id="payment-public-key" name="public_key" autoComplete="off" spellCheck={false} maxLength={200} placeholder="APP_USR-…" aria-describedby="payment-public-key-help" />
                <p id="payment-public-key-help" className={styles.hint}>Em Sua aplicação → Credenciais. Identifica sua aplicação no formulário seguro de pagamento.</p></div>
              <div className={styles.field}><label htmlFor="payment-access-token">Access Token</label>
                <input id="payment-access-token" name="access_token" type="password" autoComplete="off" maxLength={512} placeholder="Cole seu Access Token" aria-describedby="payment-access-token-help" />
                <p id="payment-access-token-help" className={styles.hint}>Na mesma seção da Public Key e no mesmo ambiente. Autoriza o servidor a processar seus pagamentos; fica protegido após salvar.</p></div>
              <div className={`${styles.field} ${styles.wide}`}><label htmlFor="payment-webhook-secret">Assinatura secreta dos webhooks</label>
                <input id="payment-webhook-secret" name="webhook_secret" type="password" autoComplete="off" maxLength={512} placeholder="Cole a assinatura secreta" aria-describedby="payment-webhook-secret-help" />
                <p id="payment-webhook-secret-help" className={styles.hint}>Em Sua aplicação → Webhooks → Assinatura secreta. Confirma que as notificações vieram do Mercado Pago.</p></div>
            </div>
            <aside className={styles.tip}><strong>Confira o ambiente das três credenciais</strong>
              <p>Use dados de Teste para validar a integração. Credenciais de Produção movimentam dinheiro e exigem liberação operacional.</p>
              <p>Para trocar a conexão, preencha os três campos. Para manter a atual, deixe os três vazios. Os segredos salvos nunca são exibidos.</p></aside>
          </div>
        </details>
        <div className={styles.security}><div><strong>Confirmação em duas etapas</strong><p className={styles.hint}>Informe sua senha. Depois, confirme o código enviado ao seu WhatsApp administrativo.</p></div>
          <div className={styles.field}><label htmlFor="payment-current-password">Sua senha atual</label>
            <input id="payment-current-password" name="password" type="password" autoComplete="current-password" required /></div>
          <button className="primary" disabled={busy || !settings}>{busy ? "Conferindo…" : "Confirmar alteração por código"}</button>
        </div>
      </fieldset>
    </form> : <form onSubmit={confirm} className={styles.confirmation}>
      <span className={styles.eyebrow}>Última etapa</span><h3>Confirme a alteração</h3>
      <p>Digite os seis números enviados ao seu WhatsApp administrativo. A configuração só será salva após esta confirmação.</p>
      <div className={styles.field}><label htmlFor="payment-confirmation-code">Código de confirmação</label>
        <input id="payment-confirmation-code" name="code" inputMode="numeric" autoComplete="one-time-code"
          required pattern="[0-9]{6}" minLength={6} maxLength={6} /></div>
      <div className={styles.actions}>
        <button className="primary" disabled={busy}>{busy ? "Salvando…" : "Salvar meios de pagamento"}</button>
        <button className="secondary" type="button" disabled={busy} onClick={() => void resend()}>Reenviar código</button>
        <button className="secondary" type="button" disabled={busy} onClick={() => setChallenge(null)}>Cancelar alteração</button>
      </div>
    </form>}
  </section>;
}
