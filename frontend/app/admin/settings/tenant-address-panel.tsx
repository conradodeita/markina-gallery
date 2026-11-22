"use client";

import { FormEvent, useState } from "react";
import { ADDRESS_CHANGED, ADDRESS_ENDPOINT, parseTenantAddress, useTenantAddress } from "../tenant-address";
import styles from "./tenant-address-panel.module.css";

export function TenantAddressPanel() {
  const { address, phase, retry, setAddress } = useTenantAddress();
  const [input, setInput] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const prefix = input ?? address?.suggested_prefix ?? "";

  async function reserve(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setMessage("");
    try {
      const response = await fetch(ADDRESS_ENDPOINT, {
        method: "PUT", credentials: "same-origin", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prefix: prefix.trim().toLowerCase() }),
      });
      if (!response.ok) {
        setMessage(response.status === 409 ? "Este nome de link não está disponível. Escolha outro nome."
          : response.status === 422 ? "Use letras sem acentos, números ou hífens, sem hífen nas pontas."
          : "Não foi possível reservar o link. Tente novamente.");
        return;
      }
      const selected = parseTenantAddress(await response.json());
      if (!selected.choice_complete) throw new Error("Reserva não confirmada.");
      setAddress(selected);
      setMessage("Link da marca reservado para sua conta.");
      window.dispatchEvent(new Event(ADDRESS_CHANGED));
    } catch {
      setMessage("Não foi possível confirmar a reserva do link. Tente novamente com o mesmo nome.");
    } finally { setBusy(false); }
  }

  if (phase === "hidden") return null;
  return <section id="tenant-address" className={`mk-card ${styles.panel}`} aria-labelledby="tenant-address-title">
    <p className="eyebrow">Primeiro passo</p>
    <h2 id="tenant-address-title">Link da sua marca no Pick-your-Pic</h2>
    {phase === "loading" ? <p>Consultando o link da sua marca…</p> : phase === "error" ? <>
      <p role="alert">Não foi possível consultar o link da sua marca. Nenhuma escolha foi confirmada nesta tela.</p>
      <button type="button" className="mk-button mk-button--secondary" onClick={retry}>Tentar novamente</button>
    </> : address ? <details className={styles.step} open={!address.choice_complete}>
      <summary>
        <span className={address.choice_complete ? styles.complete : styles.pending} aria-hidden="true">
          {address.choice_complete ? "✓" : "○"}
        </span>
        <span><strong>Link da sua marca</strong><small>
          {address.choice_complete ? "Escolha concluída" : "Escolha pendente"}
        </small></span>
        <span className={styles.chevron} aria-hidden="true">⌄</span>
      </summary>
      <div className={styles.content}>
        {address.choice_complete ? <>
          <p className={styles.hostname}>{address.hostname}</p>
          {address.state === "reserved" ? <p>O link da sua marca está reservado. Ele ainda está em preparação e será liberado para seus clientes depois dessa etapa.</p>
            : <><p>O link da sua marca está pronto para uso.</p><a className="mk-button mk-button--secondary" href={address.public_url ?? undefined}>Acessar meu espaço</a></>}
        </> : <form onSubmit={reserve} className={styles.form}>
          <p>Escolha o nome que aparecerá no link da sua marca e será usado pelos seus clientes para acessar seu espaço.</p>
          <label htmlFor="tenant-address-prefix">Nome para o link da marca</label>
          <input id="tenant-address-prefix" aria-describedby="tenant-address-help tenant-address-preview"
            value={prefix} onChange={(event) => setInput(event.target.value)} required minLength={1} maxLength={63}
            pattern="[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?" autoCapitalize="none" autoComplete="off"
            spellCheck={false} disabled={busy} />
          <small id="tenant-address-help">Use letras sem acentos, números e hífens. A disponibilidade será confirmada ao reservar.</small>
          <div className={styles.preview} id="tenant-address-preview" aria-live="polite">
            <small>Prévia do link da sua marca</small>
            <strong>{prefix.trim().toLowerCase() || "seu-nome"}.{address.base_domain}</strong>
          </div>
          <p>Confirme o nome com atenção. Depois da reserva, ele ficará vinculado à sua conta. A preparação do link para acesso dos clientes é uma etapa separada.</p>
          <button className="mk-button mk-button--primary" disabled={busy} type="submit">
            {busy ? "Reservando…" : "Reservar meu link"}
          </button>
        </form>}
      </div>
    </details> : null}
    {address?.state === "reserved" ? <p className={styles.preparation}>Preparação do link: pendente</p> : null}
    {message ? <p role="status">{message}</p> : null}
  </section>;
}
