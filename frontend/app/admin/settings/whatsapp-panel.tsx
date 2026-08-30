"use client";

import Image from "next/image";
import { FormEvent, useEffect, useMemo, useState } from "react";

type ChannelStatus = "sandbox" | "pending_pairing" | "connecting" | "ready" | "mismatch" | "disconnected" | "error";

type Pairing = {
  state: string;
  pairing_code: string | null;
  qr_base64: string | null;
};

type Channel = {
  provider: string;
  environment: string;
  expected_phone: string | null;
  connected_phone: string | null;
  status: ChannelStatus;
  last_error: string | null;
  last_checked_at: string | null;
  deliveries: Record<string, number>;
  pairing?: Pairing;
};

const statusCopy: Record<ChannelStatus, { label: string; detail: string }> = {
  sandbox: {
    label: "Modo seguro",
    detail: "O provedor está em sandbox. Nenhuma mensagem sai para a rede.",
  },
  pending_pairing: {
    label: "Aguardando pareamento",
    detail: "Configure o número próprio de homologação e conecte o WhatsApp antes de enviar mensagens.",
  },
  connecting: {
    label: "Conectando",
    detail: "O pareamento começou, mas a identidade remetente ainda não foi confirmada.",
  },
  ready: {
    label: "Canal pronto",
    detail: "A conexão está ativa e o número conectado coincide com o número esperado.",
  },
  mismatch: {
    label: "Número divergente",
    detail: "O número conectado não é o configurado. Os envios permanecem bloqueados.",
  },
  disconnected: {
    label: "Canal desconectado",
    detail: "A sessão não está aberta. Reconecte o número antes de tentar novos envios.",
  },
  error: {
    label: "Verificação indisponível",
    detail: "Não foi possível confirmar a conexão. Os envios não são considerados prontos.",
  },
};

function isChannel(value: unknown): value is Channel {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<Channel>;
  return typeof candidate.provider === "string" && typeof candidate.environment === "string" &&
    typeof candidate.status === "string" && candidate.status in statusCopy;
}

function pairingImage(value: string): string {
  return value.startsWith("data:image/") ? value : `data:image/png;base64,${value}`;
}

function checkedAt(value: string | null): string {
  if (!value) return "Ainda não verificado";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? "Horário indisponível" : parsed.toLocaleString("pt-BR");
}

export default function WhatsAppPanel() {
  const [channel, setChannel] = useState<Channel | null>(null);
  const [pairing, setPairing] = useState<Pairing | null>(null);
  const [expectedPhone, setExpectedPhone] = useState("");
  const [busy, setBusy] = useState<"loading" | "saving" | "refreshing" | "pairing" | null>("loading");
  const [feedback, setFeedback] = useState("");

  useEffect(() => {
    let active = true;
    fetch("/api/admin/whatsapp/channel", { credentials: "same-origin" })
      .then(async (response) => {
        const data: unknown = response.ok ? await response.json() : null;
        if (!response.ok || !isChannel(data)) throw new Error();
        if (active) setChannel(data);
      })
      .catch(() => { if (active) setFeedback("Não foi possível carregar o estado do WhatsApp."); })
      .finally(() => { if (active) setBusy(null); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!pairing) return;
    const timer = window.setTimeout(() => {
      setPairing(null);
      setFeedback("O QR code/código expirou. Gere um novo material de pareamento se necessário.");
    }, 60_000);
    return () => window.clearTimeout(timer);
  }, [pairing]);

  const pending = useMemo(() => {
    if (!channel) return 0;
    return ["queued", "processing", "unknown", "failed"].reduce(
      (total, status) => total + (channel.deliveries?.[status] ?? 0),
      0,
    );
  }, [channel]);

  async function saveExpectedPhone(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy("saving");
    setFeedback("");
    try {
      const response = await fetch("/api/admin/whatsapp/channel", {
        method: "PATCH",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ expected_phone_e164: expectedPhone }),
      });
      const data: unknown = await response.json().catch(() => null);
      if (!response.ok || !isChannel(data)) throw new Error();
      setChannel(data);
      setPairing(null);
      setExpectedPhone("");
      setFeedback("Número esperado salvo. Agora faça o pareamento para confirmar a identidade.");
    } catch {
      setFeedback("Não foi possível salvar. Informe o número completo no formato +5511999999999.");
    } finally {
      setBusy(null);
    }
  }

  async function refresh() {
    setBusy("refreshing");
    setFeedback("");
    try {
      const response = await fetch("/api/admin/whatsapp/channel/refresh", {
        method: "POST",
        credentials: "same-origin",
      });
      const data: unknown = response.ok ? await response.json() : null;
      if (!response.ok || !isChannel(data)) throw new Error();
      setChannel(data);
      setFeedback(data.status === "ready" ? "Conexão e identidade confirmadas." : "Estado atualizado. O canal ainda não está pronto.");
    } catch {
      setFeedback("Não foi possível atualizar a conexão. Os envios continuam bloqueados.");
    } finally {
      setBusy(null);
    }
  }

  async function startPairing() {
    setBusy("pairing");
    setFeedback("");
    setPairing(null);
    try {
      const response = await fetch("/api/admin/whatsapp/channel/pairing", {
        method: "POST",
        credentials: "same-origin",
      });
      const data: unknown = response.ok ? await response.json() : null;
      if (!response.ok || !isChannel(data) || !data.pairing) throw new Error();
      setChannel(data);
      setPairing(data.pairing);
      setFeedback("Material gerado por 60 segundos. Faça a leitura somente no aparelho de homologação.");
    } catch {
      setFeedback("Não foi possível iniciar o pareamento. Confirme a infraestrutura e o número esperado.");
    } finally {
      setBusy(null);
    }
  }

  const state = channel ? statusCopy[channel.status] : null;
  const canPair = channel?.provider === "evolution" && Boolean(channel.expected_phone) && busy === null;

  return (
    <section className="admin-card whatsapp-settings" aria-labelledby="whatsapp-settings-title">
      <div className="whatsapp-settings-heading">
        <div>
          <p className="eyebrow">Canal transacional</p>
          <h2 id="whatsapp-settings-title">WhatsApp</h2>
        </div>
        <span className={`whatsapp-status whatsapp-status--${channel?.status ?? "loading"}`}>
          {busy === "loading" ? "Consultando" : state?.label ?? "Indisponível"}
        </span>
      </div>

      <p className="intro">O sistema envia OTP e avisos pelo número próprio pareado. API key, sessão e QR nunca ficam gravados nesta tela.</p>

      {channel ? <div className="whatsapp-overview" aria-live="polite">
        <div><span>Provedor</span><strong>{channel.provider === "evolution" ? "Evolution API" : "Sandbox"}</strong></div>
        <div><span>Ambiente</span><strong>{channel.environment}</strong></div>
        <div><span>Número esperado</span><strong>{channel.expected_phone ?? "Não configurado"}</strong></div>
        <div><span>Número conectado</span><strong>{channel.connected_phone ?? "Não confirmado"}</strong></div>
        <div><span>Última verificação</span><strong>{checkedAt(channel.last_checked_at)}</strong></div>
        <div><span>Pendências operacionais</span><strong>{pending}</strong></div>
      </div> : null}

      <div className={`whatsapp-readiness whatsapp-readiness--${channel?.status ?? "loading"}`} role="status">
        <strong>{state?.label ?? (busy === "loading" ? "Consultando o canal" : "Canal indisponível")}</strong>
        <span>{channel?.last_error || state?.detail || feedback || "Aguarde a consulta do estado operacional."}</span>
      </div>

      <div className="whatsapp-actions">
        <form className="whatsapp-phone-form" onSubmit={saveExpectedPhone}>
          <label htmlFor="whatsapp-expected-phone">Número próprio de homologação</label>
          <div>
            <input
              id="whatsapp-expected-phone"
              name="expected_phone_e164"
              type="tel"
              inputMode="tel"
              autoComplete="tel"
              placeholder={channel?.expected_phone ?? "+5511999999999"}
              pattern={"\\+[1-9][0-9]{7,14}"}
              value={expectedPhone}
              onChange={(event) => setExpectedPhone(event.target.value)}
              required
            />
            <button className="primary" disabled={busy !== null}>Salvar número</button>
          </div>
          <small>Use E.164: sinal de +, país, DDD e número, sem espaços.</small>
        </form>

        <div className="whatsapp-action-buttons">
          <button className="secondary" type="button" disabled={!channel || busy !== null} onClick={() => void refresh()}>
            {busy === "refreshing" ? "Atualizando…" : "Atualizar conexão"}
          </button>
          <button className="primary" type="button" disabled={!canPair} onClick={() => void startPairing()}>
            {busy === "pairing" ? "Gerando…" : "Parear aparelho"}
          </button>
        </div>
      </div>

      {pairing ? <aside className="whatsapp-pairing" aria-labelledby="whatsapp-pairing-title">
        <div>
          <p className="eyebrow">Uso único · expira em 60 segundos</p>
          <h3 id="whatsapp-pairing-title">Conecte o aparelho de homologação</h3>
          <p>Abra “Aparelhos conectados” no WhatsApp e leia o QR. Se o provedor oferecer código, use-o apenas no aparelho autorizado.</p>
        </div>
        {pairing.qr_base64 ? <Image
          className="whatsapp-pairing-qr"
          src={pairingImage(pairing.qr_base64)}
          alt="QR code efêmero para parear o WhatsApp de homologação"
          width={240}
          height={240}
          unoptimized
        /> : null}
        {pairing.pairing_code ? <p className="whatsapp-pairing-code"><span>Código de pareamento</span><strong>{pairing.pairing_code}</strong></p> : null}
        <button className="secondary" type="button" onClick={() => setPairing(null)}>Ocultar agora</button>
      </aside> : null}

      {feedback ? <p className="form-message" role="alert">{feedback}</p> : null}
    </section>
  );
}
