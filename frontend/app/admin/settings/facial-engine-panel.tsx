"use client";

import { useEffect, useState } from "react";

type Experiment = {
  enabled: boolean;
  mode: "shadow";
  model_id: string;
  model_revision: string;
  worker_ready: boolean;
  worker_last_seen_at: string | null;
  indexed_faces: number;
  jobs: Record<string, number>;
  serving_engine: string;
  backfill_enabled: false;
};

export default function FacialEnginePanel() {
  const [state, setState] = useState<Experiment | null>(null);
  const [available, setAvailable] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    fetch("/api/admin/facial-engine-experiment", { credentials: "same-origin", cache: "no-store" })
      .then(async (response) => {
        if (response.status === 403 || response.status === 404) return;
        if (!response.ok) throw new Error();
        setState(await response.json());
        setAvailable(true);
      })
      .catch(() => setMessage("Não foi possível consultar o experimento facial."));
  }, []);

  if (!available && !message) return null;
  if (!available && message) return <section className="admin-card" role="status">{message}</section>;
  if (!state) return null;

  async function toggleExperiment() {
    if (!state) return;
    setSaving(true);
    setMessage("");
    try {
      const response = await fetch("/api/admin/facial-engine-experiment", {
        method: "PATCH",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: !state.enabled }),
      });
      if (!response.ok) {
        setMessage(response.status === 409
          ? "O experimento exige processamento facial habilitado e worker Gemma pronto."
          : "Não foi possível atualizar o experimento.");
        return;
      }
      setState(await response.json());
      setMessage("Configuração global atualizada.");
    } catch {
      setMessage("Não foi possível atualizar o experimento.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="admin-card" aria-labelledby="facial-engine-title">
      <p className="eyebrow">Experimento global · somente proprietário da instalação</p>
      <h2 id="facial-engine-title">Motor de reconhecimento facial</h2>
      <p>A escolha vale globalmente na homologação. Galerias anteriores à ativação e galerias novas sem índice Gemma completo usam SFace. O limiar de busca Gemma ainda não foi calibrado; não ative em produção.</p>
      <dl>
        <div><dt>Worker</dt><dd>{state.worker_ready ? "Pronto" : "Indisponível"}</dd></div>
        <div><dt>Faces Gemma indexadas</dt><dd>{state.indexed_faces.toLocaleString("pt-BR")}</dd></div>
        <div><dt>Jobs Gemma aguardando</dt><dd>{state.jobs.queued ?? 0}</dd></div>
        <div><dt>Escolha global</dt><dd>{state.enabled ? "Gemma" : "SFace"}</dd></div>
      </dl>
      <button className="primary" type="button" onClick={toggleExperiment} disabled={saving || (!state.enabled && !state.worker_ready)}>
        {saving ? "Salvando…" : state.enabled ? "Usar SFace" : "Usar Gemma"}
      </button>
      {message ? <p role="status">{message}</p> : null}
    </section>
  );
}
