"use client";

import { useEffect, useState } from "react";

import styles from "./facial-engine-panel.module.css";

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
    <section className={`admin-card ${styles.panel}`} aria-labelledby="facial-engine-title">
      <div className={styles.heading}>
        <div>
          <p className="eyebrow">Configuração global</p>
          <h2 id="facial-engine-title">Motor de reconhecimento facial</h2>
        </div>
        <span className={styles.badge}>Homologação</span>
      </div>
      <p className={styles.description}>Para todos os fotógrafos e clientes. Galerias antigas ou sem indexação Gemma completa continuam em SFace.</p>
      <div className={styles.selection}>
        <div className={styles.current}>
          <span>Motor selecionado</span>
          <strong>{state.enabled ? "Gemma" : "SFace"}</strong>
        </div>
        <button className={`primary ${styles.toggle}`} type="button" onClick={toggleExperiment} disabled={saving || (!state.enabled && !state.worker_ready)}>
          {saving ? "Salvando…" : state.enabled ? "Usar SFace" : "Usar Gemma"}
        </button>
      </div>
      {!state.worker_ready ? <p className={styles.description}>O processamento Gemma está indisponível. {state.enabled ? "Você pode voltar ao SFace." : "A ativação ficará disponível quando estiver pronto."}</p> : null}
      <details className={styles.details}>
        <summary>Detalhes do processamento</summary>
        <dl className={styles.metrics}>
          <div><dt>Processamento Gemma</dt><dd>{state.worker_ready ? "Pronto" : "Indisponível"}</dd></div>
          <div><dt>Faces Gemma indexadas</dt><dd>{state.indexed_faces.toLocaleString("pt-BR")}</dd></div>
          <div><dt>Jobs Gemma aguardando</dt><dd>{state.jobs.queued ?? 0}</dd></div>
        </dl>
        <p>Somente galerias criadas após a primeira ativação podem usar Gemma. O limiar de busca Gemma ainda não foi calibrado; não ative em produção.</p>
      </details>
      {message ? <p className={styles.feedback} role="status">{message}</p> : null}
    </section>
  );
}
