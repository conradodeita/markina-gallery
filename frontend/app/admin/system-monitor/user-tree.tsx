"use client";
import { FormEvent, useEffect, useState } from "react";
import { date, numeric, states } from "./types";
import styles from "./monitor.module.css";
import { monitorFetch } from "./request";

type Item = { id: string; label: string; sessions: number; state: string; last_activity: string | null; clients?: number; account_state?: string; operational_issues?: Record<string, number> };
type Page = { items: Item[]; next_cursor: string | null; collected_at: string; totals?: { photographers: number; clients: number; active_photographers: number | null; active_clients: number | null } };

export function UserTree({ tenant, denied }: { tenant?: string; denied: () => void }) {
  const [data, setData] = useState<Page | null>(null);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("all");
  const [request, setRequest] = useState({ query: "", state: "all", cursor: "", revision: 0 });
  const [expanded, setExpanded] = useState<string | null>(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    let current = true;
    const params = new URLSearchParams({ limit: "25", q: request.query, state: request.state });
    if (tenant) params.set("tenant_id", tenant);
    if (request.cursor) params.set("cursor", request.cursor);
    void monitorFetch(`/api/admin/system-monitor/tree?${params}`, { credentials: "same-origin", cache: "no-store", signal: controller.signal })
      .then(async (response) => {
        if ([401, 403].includes(response.status)) { if (current) { setData(null); denied(); } return; }
        if (!response.ok) throw new Error("unavailable");
        const result = await response.json() as Page;
        if (current) setData((previous) => ({ ...result, items: request.cursor ? [...(previous?.items ?? []), ...result.items] : result.items }));
      }).catch(() => { if (current) setError(true); }).finally(() => { if (current) setBusy(false); });
    return () => { current = false; controller.abort(); };
  }, [tenant, request, denied]);
  function search(event: FormEvent) { event.preventDefault(); setBusy(true); setError(false); setData(null); setExpanded(null); setRequest({ query, state: filter, cursor: "", revision: request.revision + 1 }); }
  return <div className={styles.tree}>
    {data?.totals && <p>{numeric(data.totals.photographers)} fotógrafos · {numeric(data.totals.clients)} clientes · Ativos agora: {numeric(data.totals.active_photographers)} fotógrafos e {numeric(data.totals.active_clients)} clientes.</p>}
    <form onSubmit={search} className={styles.controls}>
      <label>{tenant ? "Pesquisar cliente" : "Pesquisar conta ou cliente"}<input value={query} maxLength={80} onChange={(event) => setQuery(event.target.value)} /></label>
      <label>Atividade<select value={filter} onChange={(event) => setFilter(event.target.value)}><option value="all">Todas</option>{["active", "recent", "valid_session", "inactive", "unknown"].map((key) => <option key={key} value={key}>{states[key]}</option>)}</select></label>
      <button disabled={busy} type="submit">Pesquisar / atualizar</button>
    </form>
    {error && <p role="alert">Não foi possível consultar a árvore. Tente atualizar.</p>}
    {busy && <p role="status">Consultando…</p>}
    {data && <small>Consulta: {date(data.collected_at)}. A árvore é atualizada sob demanda.</small>}
    {data && !data.items.length && <p>Nenhum resultado para esta consulta.</p>}
    <ul>{data?.items.map((item) => <li key={item.id}>
      <div className={styles.treeRow}>{tenant ? <strong>{item.label}</strong> : <button aria-expanded={expanded === item.id} onClick={() => setExpanded(expanded === item.id ? null : item.id)}>{expanded === item.id ? "−" : "+"} {item.label}</button>}
        <span>{states[item.state] ?? "Desconhecido"}</span>{item.clients !== undefined && <span>{item.clients} clientes</span>}<span>{item.sessions} sessões válidas</span>
      </div>
      <small>Última interação: {date(item.last_activity)}{item.account_state === "suspended" ? " · Conta suspensa" : ""}</small>
      {!!item.operational_issues && Object.values(item.operational_issues).some(Boolean) && <p>Falhas registradas de processamento: {Object.values(item.operational_issues).reduce((a, b) => a + b, 0)}. Consulte as filas.</p>}
      {expanded === item.id && <UserTree tenant={item.id} denied={denied} />}
    </li>)}</ul>
    {data?.next_cursor && <button disabled={busy} onClick={() => { setBusy(true); setError(false); setRequest({ ...request, cursor: data.next_cursor! }); }}>Carregar mais</button>}
  </div>;
}
