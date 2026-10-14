"use client";

import { useEffect, useState } from "react";

type Engine = { id: "lightcraft" | "rawtherapee"; installed_version: string | null; available: boolean; supported_formats: string[] };
type RawDevelopmentSettings = {
  enabled: boolean;
  selected_engine: "lightcraft" | "rawtherapee";
  engines: Engine[];
  installed_version: string | null;
  lightcraft_installed_version: string | null;
  lightcraft_latest_stable_version: string | null;
  lightcraft_update_available: boolean;
  lightcraft_latest_stable_url: string | null;
  lightcraft_latest_stable_published_at: string | null;
  last_release_check_at: string | null;
  release_check_status: "unknown" | "ok" | "unavailable";
  supported_formats: string[];
  compatibility_policy: string;
};

async function request(path: string, init?: RequestInit): Promise<RawDevelopmentSettings> {
  const response = await fetch(path, { credentials: "same-origin", ...init });
  const payload = await response.json().catch(() => null);
  if (!response.ok) throw new Error(payload?.detail ?? "Não foi possível atualizar o módulo RAW.");
  if (!payload || !Array.isArray(payload.engines)) throw new Error("Módulo RAW indisponível.");
  return payload;
}

export default function RawDevelopmentPanel() {
  const [settings, setSettings] = useState<RawDevelopmentSettings | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    let active = true;
    request("/api/admin/settings/raw-development")
      .then((value) => { if (active) setSettings(value); })
      .catch((error) => { if (active) setMessage(error instanceof Error ? error.message : "Módulo indisponível."); });
    return () => { active = false; };
  }, []);

  async function save(next: { enabled: boolean; selected_engine: "lightcraft" | "rawtherapee" }) {
    setBusy(true);
    setMessage("");
    try {
      setSettings(await request("/api/admin/settings/raw-development", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(next),
      }));
      setMessage("Configuração do módulo RAW salva.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível salvar a configuração.");
    } finally {
      setBusy(false);
    }
  }

  async function checkRelease() {
    setBusy(true);
    setMessage("");
    try {
      setSettings(await request("/api/admin/settings/raw-development/release-check", { method: "POST" }));
      setMessage("Consulta de versão do LightCraft atualizada.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível consultar a versão.");
    } finally {
      setBusy(false);
    }
  }

  const installed = settings?.engines.filter((engine) => engine.available) ?? [];
  const selected = settings?.selected_engine ?? "lightcraft";

  return <section className="admin-card" aria-labelledby="raw-development-title">
    <p className="eyebrow">Ingestão opcional</p>
    <h2 id="raw-development-title">Desenvolvimento de arquivos RAW</h2>
    <p className="intro">RAWs serão convertidos durante o processamento e descartados. O fluxo de JPEG de alta resolução continua igual.</p>
    {!settings ? <p role="status">{message || "Consultando os motores instalados…"}</p> : <>
      <label>Motor para novos arquivos RAW
        <select
          value={selected}
          disabled={busy || installed.length === 0}
          onChange={(event) => void save({ enabled: settings.enabled, selected_engine: event.currentTarget.value as "lightcraft" | "rawtherapee" })}
        >
          {settings.engines.map((engine) => <option key={engine.id} value={engine.id} disabled={!engine.available}>
            {engine.id === "lightcraft" ? "LightCraft" : "RawTherapee"}{engine.available ? ` · ${engine.installed_version}` : " · não instalado"}
          </option>)}
        </select>
      </label>
      <label className="protection-toggle">
        <input
          type="checkbox"
          checked={settings.enabled}
          disabled={busy || !settings.engines.find((engine) => engine.id === selected)?.available || settings.supported_formats.length === 0}
          onChange={(event) => void save({ enabled: event.currentTarget.checked, selected_engine: selected })}
        />
        Aceitar arquivos RAW compatíveis
      </label>
      <p>{settings.compatibility_policy}</p>
      <p>Formatos deste motor: {settings.supported_formats.length ? settings.supported_formats.map((format) => format.toUpperCase()).join(", ") : "nenhum disponível"}.</p>
      <div className="admin-card" aria-label="Versão do LightCraft">
        <h3>Versão do LightCraft</h3>
        <p>Instalada: <strong>{settings.lightcraft_installed_version ?? "não instalado"}</strong></p>
        <p>Última estável conhecida: <strong>{settings.lightcraft_latest_stable_version ?? "indisponível"}</strong></p>
        {settings.lightcraft_update_available ? <p>Há uma versão mais recente. Atualize pelo processo normal de publicação.</p> : null}
        {settings.lightcraft_latest_stable_url ? <p><a href={settings.lightcraft_latest_stable_url} target="_blank" rel="noreferrer">Notas do lançamento</a></p> : null}
        <small>
          {settings.release_check_status === "unavailable"
            ? "A consulta externa falhou; o processamento e os uploads continuam disponíveis."
            : settings.last_release_check_at
              ? `Consultada em ${new Date(settings.last_release_check_at).toLocaleString("pt-BR")}.`
              : "Aguardando primeira consulta."}
        </small>
        <button type="button" className="secondary" disabled={busy} onClick={() => void checkRelease()}>
          Consultar versão do LightCraft
        </button>
      </div>
    </>}
    {message ? <p role="status">{message}</p> : null}
  </section>;
}
