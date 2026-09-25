"use client";

import { FormEvent, useEffect, useState } from "react";
import { MarkinaButton, PageHeading, SystemState } from "../../ui-kit";
import styles from "./notifications.module.css";

export type NotificationSetting = {
  event_type: string; label: string; recipient: "admin" | "client"; allowed_variables: string[];
  whatsapp_enabled: boolean; push_enabled: boolean; whatsapp_body: string;
  push_title: string; push_body: string; version: number;
};

function preview(text: string) {
  const values: Record<string, string> = { cliente: "Cliente", galeria: "Galeria", pedido: "1234abcd" };
  return text.replace(/\{\{(\w+)\}\}/g, (match, key) => values[key] ?? match);
}

function EventCard({ initial }: { initial: NotificationSetting }) {
  const [item, setItem] = useState(initial);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState(false);
  async function save(event: FormEvent) {
    event.preventDefault(); setBusy(true); setMessage(""); setError(false);
    try {
      const response = await fetch(`/api/admin/notification-settings/${item.event_type}`, {
        method: "PUT", credentials: "same-origin", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ version: item.version, whatsapp_enabled: item.whatsapp_enabled,
          push_enabled: item.push_enabled, whatsapp_body: item.whatsapp_body, push_title: item.push_title, push_body: item.push_body }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Revise o texto e as variáveis permitidas.");
      setItem(data); setMessage("Configuração global salva.");
    } catch (cause) {
      setError(true); setMessage(cause instanceof Error && cause.message !== "Failed to fetch" ? cause.message : "Não foi possível salvar. Tente novamente.");
    } finally { setBusy(false); }
  }
  return <details className={styles.card} id={item.event_type}>
    <summary className={styles.heading}><span className={styles.recipient}>{item.recipient === "admin" ? "Para o fotógrafo" : "Para o cliente"}</span><h2 id={`event-${item.event_type}`}>{item.label}</h2><span className={styles.arrow} aria-hidden="true">▼</span></summary>
    <form className={styles.content} onSubmit={save} aria-labelledby={`event-${item.event_type}`}>
    <p className={styles.variables}>Variáveis: {item.allowed_variables.map((variable) => <code key={variable}>{`{{${variable}}}`}</code>)}</p>
    <fieldset disabled={busy}><legend>Canais e mensagens</legend>
      <label className={styles.toggle}><input type="checkbox" checked={item.push_enabled} onChange={(event) => setItem({ ...item, push_enabled: event.target.checked })} />Enviar notificação Push</label>
      <div className={styles.fields}>
        <label>Título do push <span>{item.push_title.length}/60</span><input required maxLength={60} value={item.push_title} onChange={(event) => setItem({ ...item, push_title: event.target.value })} /></label>
        <label>Mensagem do push <span>{item.push_body.length}/140</span><textarea required maxLength={140} rows={3} value={item.push_body} onChange={(event) => setItem({ ...item, push_body: event.target.value.replace(/[\r\n]/g, " ") })} /></label>
      </div>
      <aside className={styles.preview} aria-label="Prévia do push"><small>PRÉVIA · PUSH</small><strong>{preview(item.push_title)}</strong><p>{preview(item.push_body)}</p></aside>
      <label className={styles.toggle}><input type="checkbox" checked={item.whatsapp_enabled} onChange={(event) => setItem({ ...item, whatsapp_enabled: event.target.checked })} />Enviar WhatsApp</label>
      <label>Mensagem do WhatsApp <span>{item.whatsapp_body.length}/500</span><textarea required maxLength={500} rows={4} value={item.whatsapp_body} onChange={(event) => setItem({ ...item, whatsapp_body: event.target.value })} /></label>
      <aside className={styles.preview} aria-label="Prévia do WhatsApp"><small>PRÉVIA · WHATSAPP</small><p>{preview(item.whatsapp_body)}</p></aside>
    </fieldset>
    <footer><MarkinaButton type="submit" disabled={busy}>{busy ? "Salvando…" : "Salvar evento"}</MarkinaButton>{message && <p role={error ? "alert" : "status"}>{message}</p>}</footer>
    </form>
  </details>;
}

export default function NotificationsPage() {
  const [settings, setSettings] = useState<NotificationSetting[] | null>(null);
  const [error, setError] = useState(false);
  const [reload, setReload] = useState(0);
  useEffect(() => {
    let current = true;
    fetch("/api/admin/notification-settings", { credentials: "same-origin", cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) throw new Error();
        const data = await response.json();
        if (!Array.isArray(data.settings) || !data.settings.length) throw new Error();
        if (current) { setSettings(data.settings); setError(false); }
      }).catch(() => { if (current) setError(true); });
    return () => { current = false; };
  }, [reload]);
  return <div className="admin-shell">
    <PageHeading eyebrow="Comunicação" title="Notificações" detail="Escolha os canais e personalize os avisos automáticos." />
    <div className={styles.notice}><strong>As alterações são globais e afetam todos os clientes.</strong><p>Os textos podem aparecer na tela bloqueada. Evite dados sensíveis. Ligar um canal vale para novos eventos, sem reenviar o histórico. O push depende da ativação no dispositivo e da configuração do servidor.</p></div>
    {error ? <><SystemState tone="error" title="Não foi possível carregar as mensagens" detail="Tente novamente sem alterar suas configurações." /><MarkinaButton type="button" onClick={() => { setError(false); setReload((value) => value + 1); }}>Tentar novamente</MarkinaButton></> : settings ? <section className={styles.grid} aria-label="Configuração dos eventos">{settings.map((item) => <EventCard key={`${reload}-${item.event_type}`} initial={item} />)}</section> : <SystemState tone="loading" title="Carregando mensagens" detail="Consultando configurações dos canais." />}
  </div>;
}
