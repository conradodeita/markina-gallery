"use client";

import { type FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { MarkinaButton, PageHeading, StatusBadge, SystemState } from "../../ui-kit";
import { OverviewIcon } from "../overview-icon";
import { MediaArchiveNoticeCenter } from "./media-archive-notice-center";
import styles from "./notifications.module.css";

export type NotificationSetting = {
  event_type: string; label: string; recipient: "admin" | "client"; allowed_variables: string[]; whatsapp_variables: string[];
  whatsapp_enabled: boolean; push_enabled: boolean; whatsapp_body: string;
  push_title: string; push_body: string; version: number;
};

const recipientFilters = [
  { value: "all", label: "Todas as notificações" },
  { value: "admin", label: "Para o fotógrafo" },
  { value: "client", label: "Para o cliente" },
] as const;

function preview(text: string, contextoPagamento = "da compra 1234abcd", whatsapp = false) {
  const values: Record<string, string> = {
    cliente: "Cliente", galeria: "Galeria", pedido: "1234abcd", contexto_pagamento: contextoPagamento,
    link_compras: whatsapp ? "https://fotografo.exemplo/library/purchases#order-00000000-0000-4000-8000-000000000000" : "",
    link_galeria: whatsapp ? "https://fotografo.exemplo/public-galleries/00000000-0000-4000-8000-000000000000" : "",
  };
  return text.replace(/\{\{(\w+)\}\}/g, (match, key) => values[key] ?? match);
}

function EventCard({ initial, whatsappEditable, hidden, onWhatsAppUnavailable }: {
  initial: NotificationSetting; whatsappEditable: boolean; hidden: boolean; onWhatsAppUnavailable: () => void;
}) {
  const [item, setItem] = useState(initial);
  const [persisted, setPersisted] = useState(initial);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState(false);
  async function save(event: FormEvent) {
    event.preventDefault(); setBusy(true); setMessage(""); setError(false);
    try {
      const response = await fetch(`/api/admin/notification-settings/${item.event_type}`, {
        method: "PUT", credentials: "same-origin", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ version: item.version, whatsapp_enabled: whatsappEditable ? item.whatsapp_enabled : persisted.whatsapp_enabled,
          push_enabled: item.push_enabled, whatsapp_body: whatsappEditable ? item.whatsapp_body : persisted.whatsapp_body, push_title: item.push_title, push_body: item.push_body }),
      });
      const data = await response.json();
      if (!response.ok) {
        if (data.detail?.code === "whatsapp_channel_required") onWhatsAppUnavailable();
        throw new Error(typeof data.detail === "string" ? data.detail : data.detail?.message ?? "Revise o texto e as variáveis permitidas.");
      }
      setItem(data); setPersisted(data); setMessage("Configuração da sua conta salva.");
    } catch (cause) {
      setError(true); setMessage(cause instanceof Error && cause.message !== "Failed to fetch" ? cause.message : "Não foi possível salvar. Tente novamente.");
    } finally { setBusy(false); }
  }
  return <details className={styles.card} id={item.event_type} hidden={hidden}>
    <summary className={styles.heading}>
      <span className={styles.eventIcon}><OverviewIcon name="notifications" /></span>
      <div>
        <span className={styles.recipient}>{item.recipient === "admin" ? "Para o fotógrafo" : "Para o cliente"}</span>
        <h2 id={`event-${item.event_type}`}>{item.label}</h2>
      </div>
      <span className={styles.arrow} aria-hidden="true">⌄</span>
    </summary>
    <form className={styles.content} onSubmit={save} aria-labelledby={`event-${item.event_type}`}>
    <p className={styles.variables}>Variáveis do push: {item.allowed_variables.map((variable) => <code key={variable}>{`{{${variable}}}`}</code>)}</p>
    <fieldset disabled={busy}><legend>Canais e mensagens</legend>
      <label className={styles.toggle}><input type="checkbox" checked={item.push_enabled} onChange={(event) => setItem({ ...item, push_enabled: event.target.checked })} />Enviar notificação Push</label>
      <div className={styles.fields}>
        <label>Título do push <span>{item.push_title.length}/60</span><input required maxLength={60} value={item.push_title} onChange={(event) => setItem({ ...item, push_title: event.target.value })} /></label>
        <label>Mensagem do push <span>{item.push_body.length}/140</span><textarea required maxLength={140} rows={3} value={item.push_body} onChange={(event) => setItem({ ...item, push_body: event.target.value.replace(/[\r\n]/g, " ") })} /></label>
      </div>
      <aside className={styles.preview} aria-label="Prévia do push"><small>PRÉVIA · PUSH</small><strong>{preview(item.push_title)}</strong><p>{preview(item.push_body)}</p></aside>
      <fieldset disabled={!whatsappEditable} aria-describedby="whatsapp-status"><legend>Mensagens pelo WhatsApp</legend>
      <label className={styles.toggle}><input type="checkbox" checked={item.whatsapp_enabled} onChange={(event) => setItem({ ...item, whatsapp_enabled: event.target.checked })} />Enviar WhatsApp</label>
      <label>Mensagem do WhatsApp <span>{item.whatsapp_body.length}/500</span><textarea required maxLength={500} rows={4} value={item.whatsapp_body} onChange={(event) => setItem({ ...item, whatsapp_body: event.target.value })} /></label>
      <aside className={styles.preview} aria-label="Prévia do WhatsApp"><small>PRÉVIA · WHATSAPP</small>
        {item.event_type.startsWith("payment_") ? <>
          <p><strong>Compra agrupada:</strong> {preview(item.whatsapp_body, "da compra 1234abcd", true)}</p>
          <p><strong>Pedido individual:</strong> {preview(item.whatsapp_body, "do pedido 1234abcd da galeria Formatura", true)}</p>
        </> : <p>{preview(item.whatsapp_body, "da compra 1234abcd", true)}</p>}
      </aside>
      <p className={styles.variables}>Variáveis do WhatsApp: {item.whatsapp_variables.map((variable) => <code key={variable}>{`{{${variable}}}`}</code>)}</p>
      </fieldset>
    </fieldset>
    <footer><MarkinaButton type="submit" disabled={busy}>{busy ? "Salvando…" : "Salvar evento"}</MarkinaButton>{message && <p role={error ? "alert" : "status"}>{message}</p>}</footer>
    </form>
  </details>;
}

export default function NotificationsPage() {
  const [settings, setSettings] = useState<NotificationSetting[] | null>(null);
  const [error, setError] = useState(false);
  const [reload, setReload] = useState(0);
  const [whatsappEditable, setWhatsappEditable] = useState(false);
  const [recipient, setRecipient] = useState<(typeof recipientFilters)[number]["value"]>("all");
  useEffect(() => {
    let current = true;
    fetch("/api/admin/notification-settings", { credentials: "same-origin", cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) throw new Error();
        const data = await response.json();
        if (!Array.isArray(data.settings) || !data.settings.length) throw new Error();
        if (current) { setSettings(data.settings); setWhatsappEditable(data.whatsapp_editable === true); setError(false); }
      }).catch(() => { if (current) setError(true); });
    return () => { current = false; };
  }, [reload]);
  useEffect(() => {
    if (!settings || error) return;
    let frame = 0;
    function openLinkedEvent() {
      const target = document.getElementById(window.location.hash.slice(1));
      if (!(target instanceof HTMLDetailsElement) || !settings?.some((item) => item.event_type === target.id)) return;
      setRecipient("all");
      window.cancelAnimationFrame(frame);
      frame = window.requestAnimationFrame(() => {
        target.open = true;
        target.scrollIntoView?.({ block: "start" });
        target.querySelector("summary")?.focus({ preventScroll: true });
      });
    }
    openLinkedEvent();
    window.addEventListener("hashchange", openLinkedEvent);
    return () => {
      window.cancelAnimationFrame(frame);
      window.removeEventListener("hashchange", openLinkedEvent);
    };
  }, [settings, error]);

  return <div className={styles.page}>
    <PageHeading title="Notificações" detail="Escolha os canais e personalize os avisos automáticos." />
    <aside className={styles.notice}>
      <span className={styles.eventIcon}><OverviewIcon name="notifications" /></span>
      <div><strong>As alterações afetam os clientes da sua conta.</strong><p>Os textos podem aparecer na tela bloqueada. Evite dados sensíveis. Ligar um canal vale para novos eventos, sem reenviar o histórico. O push depende da ativação no dispositivo e da configuração do servidor.</p></div>
    </aside>
    <MediaArchiveNoticeCenter />
    {settings && !error ? <div id="whatsapp-status" className={styles.channel} role="status">
      <div>
        <StatusBadge tone={whatsappEditable ? "success" : "warning"}>{whatsappEditable ? "WhatsApp conectado" : "WhatsApp desconectado"}</StatusBadge>
        <p>{whatsappEditable ? "Seu canal está pronto para personalizar os avisos aos clientes." : "Conecte seu WhatsApp em Configurações para personalizar as mensagens."} As mensagens push são independentes do WhatsApp e continuam editáveis.</p>
      </div>
      <Link href="/admin/settings#whatsapp">Configurar WhatsApp</Link>
    </div> : null}
    {error ? <><SystemState tone="error" title="Não foi possível carregar as mensagens" detail="Tente novamente sem alterar suas configurações." /><MarkinaButton type="button" onClick={() => { setError(false); setReload((value) => value + 1); }}>Tentar novamente</MarkinaButton></> : settings ? (
      <section className={styles.grid} aria-label="Configuração dos eventos">
        <div className={styles.filters} role="group" aria-label="Filtrar notificações por destinatário">
          {recipientFilters.map(({ value, label }) => (
            <button key={value} type="button" aria-pressed={recipient === value} onClick={() => setRecipient(value)}>{label}</button>
          ))}
        </div>
        {recipient !== "all" && !settings.some((item) => item.recipient === recipient) && <SystemState title="Nenhum evento para este destinatário" detail="Escolha outro filtro para consultar os eventos." />}
        {settings.map((item) => <EventCard key={`${reload}-${item.event_type}`} initial={item} whatsappEditable={whatsappEditable} hidden={recipient !== "all" && item.recipient !== recipient} onWhatsAppUnavailable={() => setWhatsappEditable(false)} />)}
      </section>
    ) : <SystemState tone="loading" title="Carregando mensagens" detail="Consultando configurações dos canais." />}
  </div>;
}
