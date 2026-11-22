"use client";

import Link from "next/link";
import { type FormEvent, useEffect, useState } from "react";
import { MarkinaButton, PageHeading, SurfaceCard } from "../ui-kit";
import { TurnstileWidget } from "./turnstile-widget";

type Setup = { photographer_name: string; email: string };
type SignupConfig = { turnstile_enabled: boolean; turnstile_site_key: string | null };

async function signupRequest(path: string, body?: unknown) {
  const response = await fetch(`/api/auth/photographer-signup${path}`, {
    method: body ? "POST" : "GET", credentials: "same-origin", cache: "no-store",
    ...(body ? { headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {}),
  });
  if (!response.ok) throw new Error(response.status === 404 || response.status === 503 ? "Cadastro em preparação. Tente novamente mais tarde." : response.status === 429 ? "Aguarde antes de tentar novamente." : "Não foi possível concluir esta etapa. Confira os dados ou reinicie o cadastro.");
  return response.json();
}

export default function PhotographerSignupPage() {
  const [step, setStep] = useState<"start" | "email" | "setup" | "active">("start");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [adultAttested, setAdultAttested] = useState(false);
  const [requestId, setRequestId] = useState("");
  const [otp, setOtp] = useState("");
  const [setup, setSetup] = useState<Setup | null>(null);
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [signupConfig, setSignupConfig] = useState<SignupConfig | null>(null);
  const [turnstileToken, setTurnstileToken] = useState("");
  const [turnstileReset, setTurnstileReset] = useState(0);

  useEffect(() => {
    let current = true;
    signupRequest("/config")
      .then((result: SignupConfig) => {
        if (current) setSignupConfig(result);
      })
      .catch(() => {
        if (current) setSignupConfig({ turnstile_enabled: false, turnstile_site_key: null });
      });
    return () => { current = false; };
  }, []);

  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError("");
    try {
      if (step === "start") {
        if (signupConfig?.turnstile_enabled && !turnstileToken) {
          throw new Error("Conclua a verificação de segurança antes de continuar.");
        }
        const result = await signupRequest("", {
          photographer_name: name,
          email,
          adult_attested: adultAttested,
          anti_bot_proof: signupConfig?.turnstile_enabled ? turnstileToken : "",
        });
        setTurnstileToken("");
        setRequestId(result.request_id); setStep("email");
      } else if (step === "email") {
        await signupRequest("/verify-email", { request_id: requestId, code: otp });
        setOtp("");
        setSetup(await signupRequest("/setup")); setStep("setup");
      } else if (step === "setup") {
        await signupRequest("/complete", { password });
        setPassword(""); setSetup(null); setRequestId(""); setStep("active");
      }
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Não foi possível continuar.");
      if (step === "start" && signupConfig?.turnstile_enabled) {
        setTurnstileToken("");
        setTurnstileReset((current) => current + 1);
      }
    }
    finally { setBusy(false); }
  }

  function restart() {
    setStep("start"); setOtp(""); setPassword(""); setSetup(null); setRequestId(""); setError("");
  }

  return <main className="admin-content" style={{ maxWidth: "38rem", margin: "0 auto" }}>
    <PageHeading eyebrow="Pick-your-Pic" title="Sua conta de fotógrafo" detail="Crie sua conta com nome, e-mail e senha. Você completa os dados operacionais quando decidir começar." />
    <SurfaceCard>
      {step === "active" ? <><h2>Conta criada</h2><p>Seu acesso está pronto. Você pode explorar o painel e completar o cadastro quando quiser operar.</p><Link href="/admin">Entrar no painel</Link></> : <form className="photographer-signup-form" onSubmit={submit}>
        {step === "start" ? <><label>Nome do fotógrafo<input autoComplete="name" required maxLength={120} value={name} onChange={(event) => setName(event.target.value)} /></label>
          <label>E-mail<input type="email" autoComplete="email" required maxLength={320} value={email} onChange={(event) => setEmail(event.target.value)} /></label>
          <label className="photographer-signup-attestation"><input type="checkbox" required checked={adultAttested} onChange={(event) => setAdultAttested(event.target.checked)} />Declaro que sou maior de 18 anos e estou criando uma conta de fotógrafo.</label>
          {signupConfig?.turnstile_enabled && signupConfig.turnstile_site_key ? <TurnstileWidget
            key={signupConfig.turnstile_site_key}
            siteKey={signupConfig.turnstile_site_key}
            resetSignal={turnstileReset}
            onToken={setTurnstileToken}
          /> : null}</> : null}
        {step === "email" ? <><h2>Verifique seu e-mail</h2><p>Se o cadastro puder prosseguir, você receberá um código no endereço informado.</p>
          <label>Código recebido por e-mail<input required inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} value={otp} onChange={(event) => setOtp(event.target.value)} /></label></> : null}
        {step === "setup" && setup ? <><h2>Crie sua senha</h2><p>{setup.photographer_name} · {setup.email}</p>
          <p>Depois de verificar o e-mail e criar a senha, você poderá explorar o painel. O autenticador é opcional e pode ser ativado em Configurações.</p>
          <label>Senha<input type="password" autoComplete="new-password" required minLength={12} maxLength={128} value={password} onChange={(event) => setPassword(event.target.value)} /></label></> : null}
        {error ? <p role="alert">{error}</p> : null}
        <MarkinaButton disabled={busy || signupConfig === null || (step === "start" && signupConfig.turnstile_enabled && !turnstileToken)}>{busy ? "Aguarde…" : step === "start" ? "Receber código" : step === "email" ? "Verificar e-mail" : "Criar minha conta"}</MarkinaButton>
        {step !== "start" ? <MarkinaButton variant="quiet" type="button" disabled={busy} onClick={restart}>Reiniciar cadastro</MarkinaButton> : null}
      </form>}
      <p><Link href="/">Já tenho uma conta</Link></p>
    </SurfaceCard>
  </main>;
}
