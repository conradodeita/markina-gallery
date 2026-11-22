"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { createPortal } from "react-dom";
import { PhotographerTotpSetup } from "./photographer-totp-setup";
import { safePhotographerReturnPath } from "../../photographer-onboarding-gate";
import styles from "./onboarding-panel.module.css";

type Address = {
  zip_code: string;
  street_name: string;
  street_number: string;
  neighborhood: string;
  city: string;
  state: string;
  complement: string;
};

const emptyAddress: Address = {
  zip_code: "", street_name: "", street_number: "", neighborhood: "", city: "", state: "", complement: "",
};

type Status = {
  profile_complete: boolean;
  terms_accepted: boolean;
  terms_available: boolean;
  pix_configured: boolean;
  whatsapp_configured: boolean;
  credits_available: boolean;
  mercado_pago_optional: boolean;
  steps?: { id: string; complete: boolean }[];
};
type TermsAcceptance = { id: string; version: string; accepted_at: string };

const states = [
  ["AC", "Acre"], ["AL", "Alagoas"], ["AP", "Amapá"], ["AM", "Amazonas"], ["BA", "Bahia"],
  ["CE", "Ceará"], ["DF", "Distrito Federal"], ["ES", "Espírito Santo"], ["GO", "Goiás"],
  ["MA", "Maranhão"], ["MT", "Mato Grosso"], ["MS", "Mato Grosso do Sul"], ["MG", "Minas Gerais"],
  ["PA", "Pará"], ["PB", "Paraíba"], ["PR", "Paraná"], ["PE", "Pernambuco"], ["PI", "Piauí"],
  ["RJ", "Rio de Janeiro"], ["RN", "Rio Grande do Norte"], ["RS", "Rio Grande do Sul"],
  ["RO", "Rondônia"], ["RR", "Roraima"], ["SC", "Santa Catarina"], ["SP", "São Paulo"],
  ["SE", "Sergipe"], ["TO", "Tocantins"],
] as const;

type OnboardingPanelProps = {
  termsPortalTarget?: HTMLDivElement | null;
};

export function OnboardingPanel({ termsPortalTarget }: OnboardingPanelProps) {
  const [status, setStatus] = useState<Status | null>(null);
  const [message, setMessage] = useState("");
  const [cpf, setCpf] = useState("");
  const [address, setAddress] = useState<Address>(emptyAddress);
  const [terms, setTerms] = useState("");
  const [termsVersion, setTermsVersion] = useState("");
  const [termsTestOnly, setTermsTestOnly] = useState(false);
  const [termAcceptances, setTermAcceptances] = useState<TermsAcceptance[]>([]);
  const [accepted, setAccepted] = useState(false);
  const [returnTo, setReturnTo] = useState<string | null>(null);

  async function refresh() {
    const response = await fetch("/api/admin/onboarding", { credentials: "same-origin", cache: "no-store" });
    if (!response.ok) throw new Error("Não foi possível carregar seu progresso.");
    const data = await response.json() as Status;
    setStatus(data);
    if (data.terms_accepted) {
      const acceptanceResponse = await fetch("/api/admin/onboarding/terms/acceptances", { credentials: "same-origin", cache: "no-store" });
      if (acceptanceResponse.ok) {
        const result = await acceptanceResponse.json() as { items?: TermsAcceptance[] };
        setTermAcceptances(Array.isArray(result.items) ? result.items : []);
      }
    }
  }

  useEffect(() => {
    let cancelled = false;
    fetch("/api/admin/onboarding", { credentials: "same-origin", cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) throw new Error("Não foi possível carregar seu progresso.");
        const data = await response.json();
        if (!cancelled) setStatus(data);
        if (!cancelled && data.terms_accepted) {
          const acceptanceResponse = await fetch("/api/admin/onboarding/terms/acceptances", { credentials: "same-origin", cache: "no-store" });
          if (acceptanceResponse.ok) {
            const result = await acceptanceResponse.json() as { items?: TermsAcceptance[] };
            setTermAcceptances(Array.isArray(result.items) ? result.items : []);
          }
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) setMessage(error instanceof Error ? error.message : "Falha ao carregar.");
      });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    const requestedReturn = new URLSearchParams(window.location.search).get("return_to");
    // Sincroniza a origem externa da navegação sem variar a renderização inicial do SSR.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setReturnTo(safePhotographerReturnPath(requestedReturn));
  }, []);

  async function saveProfile() {
    if (!cpf.trim() || [address.zip_code, address.street_name, address.street_number,
      address.neighborhood, address.city, address.state].some((value) => !value.trim())) {
      setMessage("Preencha o CPF, CEP, endereço, bairro, cidade e estado.");
      return;
    }
    const response = await fetch("/api/admin/onboarding/profile", {
      method: "PUT", credentials: "same-origin", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cpf, address }),
    });
    setMessage(response.ok ? "Perfil salvo. Nome e e-mail vieram do cadastro verificado." : "Confira CPF e endereço e tente novamente.");
    if (response.ok) { setCpf(""); setAddress(emptyAddress); await refresh(); }
  }

  async function loadTerms() {
    const response = await fetch("/api/admin/onboarding/terms", { credentials: "same-origin", cache: "no-store" });
    if (!response.ok) { setMessage("Os termos ainda não estão disponíveis."); return; }
    const data = await response.json(); setTerms(data.text); setTermsVersion(data.version); setTermsTestOnly(data.test_only === true); setAccepted(false);
  }

  async function acceptTerms() {
    const response = await fetch(termsTestOnly ? "/api/admin/onboarding/terms/test-acceptance" : "/api/admin/onboarding/terms/accept", {
      method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(termsTestOnly ? { accepted } : { version: termsVersion, accepted }),
    });
    setMessage(response.ok ? (termsTestOnly ? "Aceite de teste registrado para esta demonstração local." : "Aceite registrado para a versão vigente.") : "Complete o perfil e confirme o aceite.");
    if (response.ok) await refresh();
  }

  async function runLocalDemo(path: string, success: string) {
    const response = await fetch(path, { method: "POST", credentials: "same-origin" });
    if (!response.ok) {
      setMessage("A etapa de demonstração não foi concluída.");
      return;
    }
    setMessage(success);
    await refresh();
  }

  const requiredSteps = status ? [
    { id: "profile", title: "Dados do titular", complete: status.profile_complete },
    { id: "terms", title: "Termos de uso", complete: status.terms_accepted },
    { id: "credits", title: "Créditos", complete: status.credits_available },
    { id: "pix", title: "PIX de recebimento", complete: status.pix_configured },
    { id: "whatsapp", title: "WhatsApp", complete: status.whatsapp_configured },
  ] : [];
  const completedRequired = requiredSteps.filter((step) => step.complete).length;
  const firstIncomplete = requiredSteps.find((step) => !step.complete)?.id;

  function stepHeading(title: string, complete: boolean, optional = false) {
    return <summary className={styles.summary}>
      <span className={`${styles.check} ${complete ? styles.checkComplete : ""}`} aria-hidden="true">{complete ? "✓" : "○"}</span>
      <span className={styles.summaryText}>
        <strong>{title}</strong>
        <span className={complete ? styles.completeText : styles.pendingText}>
          {optional ? (complete ? "Ativo · opcional" : "Opcional") : (complete ? "Concluído" : "Pendente")}
        </span>
      </span>
      <span className={styles.chevron} aria-hidden="true">⌄</span>
    </summary>;
  }

  const termsBody = status?.terms_accepted ? <><p>Aceite registrado para a versão vigente.</p>
    {termAcceptances.map((item) => <p key={item.id}><a href={`/api/admin/onboarding/terms/acceptances/${encodeURIComponent(item.id)}/copy`} download>Baixar cópia do aceite {item.version}</a> · {new Date(item.accepted_at).toLocaleString("pt-BR")}</p>)}</> : !status?.profile_complete ? <p>Complete primeiro os dados do titular.</p> : !status.terms_available ? <p>Os termos ainda não estão disponíveis nesta configuração.</p> : <>
    <p>Leia e aceite os termos para liberar novos uploads de fotos.</p>
    <button type="button" className="mk-button mk-button--secondary" onClick={loadTerms}>Ler termos</button>
    {terms ? <><div className={styles.termsText}>{terms}</div>
      <label className={styles.accept}><input type="checkbox" checked={accepted} onChange={(event) => setAccepted(event.target.checked)} />{termsTestOnly ? "Li e aceito os termos sintéticos para teste local" : `Li e aceito os Termos do Fotógrafo Tenant, versão ${termsVersion}`}</label>
      <button type="button" className="mk-button mk-button--primary" disabled={!accepted} onClick={acceptTerms}>{termsTestOnly ? "Aceitar termos de teste" : "Aceitar termos"}</button></> : null}
  </>;

  const termsPortal = termsPortalTarget ? createPortal(
    <details className={styles.step} open={status ? !status.terms_accepted : undefined}>
      {stepHeading("Aceite e histórico dos Termos", status?.terms_accepted ?? false)}
      <div className={styles.content}>{status ? termsBody : <p role="status">Carregando aceite e histórico…</p>}</div>
    </details>,
    termsPortalTarget,
  ) : null;

  return <>
  <section id="onboarding" className={`mk-card ${styles.panel}`} aria-labelledby="onboarding-title">
    <div className={styles.header}>
      <div>
        <p className="eyebrow">Checklist da conta</p>
        <h2 id="onboarding-title">Etapas para começar</h2>
        <p>Conclua as etapas abaixo. Seus dados de cadastro ficam salvos na sua conta.</p>
      </div>
      {status ? <div className={styles.progressBadge} aria-live="polite">
        <strong>{completedRequired} de {requiredSteps.length}</strong>
        <span>etapas concluídas</span>
      </div> : null}
    </div>
    {status ? <progress className={styles.progress} aria-label="Progresso das etapas obrigatórias"
      max={requiredSteps.length} value={completedRequired} /> : <p>Carregando progresso…</p>}
    {returnTo ? <p className={styles.returnLink}>Depois de concluir as etapas pendentes, <Link href={returnTo}>volte à ação que iniciou o cadastro</Link>.</p> : null}

    {status ? <div role="group" className={styles.steps} aria-label="Etapas para operar">
      <details className={styles.step} open={firstIncomplete === "profile"}>
        {stepHeading("Dados do titular", status.profile_complete)}
        <div className={styles.content}>
          {status.profile_complete ? <p>Identidade, CPF e endereço cadastrados. Nome e e-mail vieram do ingresso verificado.</p> : <>
            <p>Nome e e-mail já foram confirmados no cadastro. Informe CPF e endereço para preencher os dados do pagador na compra de créditos.</p>
            <label>CPF<input inputMode="numeric" autoComplete="off" value={cpf} onChange={(event) => setCpf(event.target.value)} required /></label>
            <div className={styles.addressGrid}>
              <label>CEP<input inputMode="numeric" autoComplete="postal-code" placeholder="00000-000" value={address.zip_code} onChange={(event) => setAddress({ ...address, zip_code: event.target.value })} required /></label>
              <label>Estado<select autoComplete="address-level1" value={address.state} onChange={(event) => setAddress({ ...address, state: event.target.value })} required>
                <option value="">Selecione</option>{states.map(([value, label]) => <option value={value} key={value}>{value} · {label}</option>)}
              </select></label>
              <label className={styles.wide}>Logradouro<input autoComplete="address-line1" maxLength={120} value={address.street_name} onChange={(event) => setAddress({ ...address, street_name: event.target.value })} required /></label>
              <label>Número<input autoComplete="address-line2" maxLength={20} placeholder="Número ou S/N" value={address.street_number} onChange={(event) => setAddress({ ...address, street_number: event.target.value })} required /></label>
              <label>Bairro<input maxLength={80} value={address.neighborhood} onChange={(event) => setAddress({ ...address, neighborhood: event.target.value })} required /></label>
              <label>Cidade<input autoComplete="address-level2" maxLength={80} value={address.city} onChange={(event) => setAddress({ ...address, city: event.target.value })} required /></label>
              <label className={styles.wide}>Complemento <span>opcional</span><input autoComplete="address-line3" maxLength={80} value={address.complement} onChange={(event) => setAddress({ ...address, complement: event.target.value })} /></label>
            </div>
            <small>Endereço conforme os dados de pagador aceitos pelo Mercado Pago. Os dados ficam cifrados e são usados para preencher o checkout.</small>
            <button type="button" className="mk-button mk-button--primary" onClick={saveProfile}>Salvar CPF e endereço</button>
          </>}
        </div>
      </details>

      <details className={styles.step} open={firstIncomplete === "terms"}>
        {stepHeading("Termos de uso", status.terms_accepted)}
        <div className={styles.content}>
          {termsPortalTarget === undefined ? termsBody : <>
            <p>{status.terms_accepted ? "A cópia vigente e o histórico de aceite ficam no fim desta página." : "Leia e aceite os Termos no fim desta página."}</p>
            <a className="mk-button mk-button--secondary" href="#settings-terms">{status.terms_accepted ? "Ver aceite e histórico" : "Ler e aceitar os Termos"}</a>
          </>}
        </div>
      </details>

      <details className={styles.step} open={firstIncomplete === "credits"}>
        {stepHeading("Créditos", status.credits_available)}
        <div className={styles.content}>
          {status.credits_available ? <p>Há créditos disponíveis para enviar fotos.</p> : <>
            <p>Após preencher o perfil, você pode comprar créditos. Para enviar fotos, aceite os Termos de uso e conclua as demais etapas.</p>
            <Link className="mk-button mk-button--primary" href="/admin/credits">Ver pacotes de créditos</Link>
          </>}
        </div>
      </details>

      <details className={styles.step} open={firstIncomplete === "pix"}>
        {stepHeading("PIX de recebimento", status.pix_configured)}
        <div className={styles.content}>
          <p>{status.pix_configured ? "PIX configurado para os pagamentos das suas galerias." : "Configure o PIX que seus clientes usarão para pagar pelas fotos."}</p>
          {!status.pix_configured ? <a className="mk-button mk-button--secondary" href="#pix">Configurar PIX</a> : null}
        </div>
      </details>

      <details className={styles.step} open={firstIncomplete === "whatsapp"}>
        {stepHeading("WhatsApp", status.whatsapp_configured)}
        <div className={styles.content}>
          <p>{status.whatsapp_configured ? "Seu canal está conectado e pronto para enviar notificações." : "Conecte seu número próprio para enviar notificações aos seus clientes."}</p>
          {!status.whatsapp_configured ? <a className="mk-button mk-button--secondary" href="#whatsapp">Configurar WhatsApp</a> : null}
        </div>
      </details>

      <div className={styles.optionalHeading}><h3>Segurança e integrações opcionais</h3><p>Estas opções não impedem o uso da conta nem a compra de créditos.</p></div>
      <details className={`${styles.step} ${styles.optionalStep}`}>
        {stepHeading("Autenticador TOTP", status.steps?.some((step) => step.id === "totp" && step.complete) ?? false, true)}
        <div className={styles.content}><PhotographerTotpSetup enabled={status.steps?.some((step) => step.id === "totp" && step.complete) ?? false} /></div>
      </details>
      <details className={`${styles.step} ${styles.optionalStep}`}>
        {stepHeading("Mercado Pago próprio", false, true)}
        <div className={styles.content}><p>Não é necessário para comprar créditos. Configure a integração somente se quiser oferecer pagamentos online diretamente aos seus clientes.</p></div>
      </details>
    </div> : null}

    {process.env.NEXT_PUBLIC_LOCAL_PHOTOGRAPHER_DEMO === "true" && status?.profile_complete ? <div aria-label="Demonstração local" className={styles.demo}>
      <p>Demonstração local: sem cobrança, conexão ou envio de mensagens externas.</p>
      <button type="button" className="mk-button mk-button--secondary" onClick={() => runLocalDemo(
        "/api/local-demo/simulate-credit-purchase",
        "Compra simulada registrada. Nenhum pagamento foi enviado.",
      )}>Simular compra de créditos</button>
      <button type="button" className="mk-button mk-button--secondary" disabled={!status.credits_available} onClick={() => runLocalDemo(
        "/api/local-demo/configure-upload-prerequisites",
        "PIX e WhatsApp sandbox preparados para o teste local.",
      )}>Preparar PIX e WhatsApp sandbox</button>
    </div> : null}
    {message ? <p role="status" className={styles.message}>{message}</p> : null}
  </section>
  {termsPortal}
  </>;
}
