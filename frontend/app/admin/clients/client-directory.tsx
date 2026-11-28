"use client";

import { useEffect, useState } from "react";

import { MarkinaButton, MarkinaLink, MetricCard, PageHeading, StatusBadge, SystemState } from "../../ui-kit";
import { OverviewIcon } from "../overview-icon";
import styles from "../catalog.module.css";
import {
  ClientCreateForm,
  type ClientDirectoryItem,
  ClientEditorDialog,
  clientJsonRequest,
} from "./client-controls";

type DirectoryResponse = {
  clients: ClientDirectoryItem[];
  page: { has_more: boolean; next_cursor: string | null };
};

function hasGallery(person: ClientDirectoryItem) {
  return Boolean(person.aggregates?.public_galleries || person.aggregates?.private_galleries);
}

export function ClientDirectory() {
  const [clients, setClients] = useState<ClientDirectoryItem[]>([]);
  const [query, setQuery] = useState("");
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [editing, setEditing] = useState<ClientDirectoryItem | null>(null);
  const [refresh, setRefresh] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      setLoading(true);
      setError("");
      try {
        const parameters = new URLSearchParams({ limit: "24" });
        if (query.trim()) parameters.set("query", query.trim());
        const data = (await clientJsonRequest(
          `/api/admin/clients?${parameters.toString()}`,
          { signal: controller.signal },
        )) as DirectoryResponse;
        setClients(data.clients ?? []);
        setNextCursor(data.page?.next_cursor ?? null);
      } catch (caught) {
        if (!controller.signal.aborted) {
          setError(
            caught instanceof Error ? caught.message : "Não foi possível carregar as clientes.",
          );
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }, query ? 180 : 0);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [query, refresh]);

  async function loadMore() {
    if (!nextCursor || loadingMore) return;
    setLoadingMore(true);
    setError("");
    try {
      const parameters = new URLSearchParams({ limit: "24", cursor: nextCursor });
      if (query.trim()) parameters.set("query", query.trim());
      const data = (await clientJsonRequest(
        `/api/admin/clients?${parameters.toString()}`,
      )) as DirectoryResponse;
      setClients((current) => [...current, ...(data.clients ?? [])]);
      setNextCursor(data.page?.next_cursor ?? null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Não foi possível carregar mais clientes.");
    } finally {
      setLoadingMore(false);
    }
  }

  return (
    <div className={styles.catalog}>
      <PageHeading
        title="Clientes"
        detail="Cadastre, encontre e mantenha uma única identidade por WhatsApp, mesmo antes de criar uma galeria."
        actions={<MarkinaLink href="#cadastro-cliente"><OverviewIcon name="add" /> Cadastrar cliente</MarkinaLink>}
      />
      {message ? (
        <p className="notice" role="status">
          {message}
        </p>
      ) : null}
      {!loading && !error && clients.length > 0 && (
        <section className={styles.metrics} aria-label="Resumo das clientes exibidas">
          <MetricCard icon={<OverviewIcon name="group" />} label="Clientes exibidas" value={clients.length} detail={query ? "correspondentes à busca" : "carregadas no diretório"} />
          <MetricCard icon={<OverviewIcon name="folder_shared" />} label="Com galerias" value={clients.filter(hasGallery).length} detail="entre as clientes exibidas" />
          <MetricCard icon={<OverviewIcon name="payments" />} label="Com pedidos" value={clients.filter((person) => (person.aggregates?.orders ?? 0) > 0).length} detail="entre as clientes exibidas" />
        </section>
      )}
      <section className={styles.catalogPanel} aria-labelledby="client-directory-title">
        <div className={styles.panelHeading}>
          <h2 id="client-directory-title"><OverviewIcon name="group" /> Pessoas cadastradas</h2>
        </div>
        <div className={styles.directory}>
          <label className={styles.search}>
            <span id="client-directory-search-label">Buscar por nome ou WhatsApp</span>
            <span className={styles.searchField}>
              <OverviewIcon name="search" />
              <input
                aria-labelledby="client-directory-search-label"
                type="search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Ex.: Ana ou 11999999999"
              />
            </span>
          </label>
          {loading ? (
            <SystemState
              tone="loading"
              title="Carregando clientes"
              detail="Consultando vínculos e histórico."
            />
          ) : error ? (
            <SystemState tone="error" title="Diretório indisponível" detail={error} />
          ) : clients.length ? (
            <>
              <table className={styles.directoryTable} aria-label="Pessoas cadastradas" role="table">
                <thead role="rowgroup">
                  <tr role="row">
                    <th scope="col" role="columnheader">Cliente</th>
                    <th scope="col" role="columnheader">Contato</th>
                    <th scope="col" role="columnheader">Galerias e pedidos</th>
                    <th scope="col" role="columnheader">Histórico</th>
                    <th scope="col" role="columnheader">Ações</th>
                  </tr>
                </thead>
                <tbody role="rowgroup">
                  {clients.map((person) => {
                    const linked = hasGallery(person);
                    const initials = person.name.trim().split(/\s+/).slice(0, 2).map((name) => name.charAt(0)).join("");
                    return (
                      <tr key={person.id} role="row">
                        <th scope="row" role="rowheader">
                          <span className={styles.clientName}>
                            <span className={styles.clientAvatar} aria-hidden="true">{initials}</span>
                            <span>{person.name}</span>
                          </span>
                        </th>
                        <td role="cell"><span className={styles.clientContact}>{person.phone}</span></td>
                        <td role="cell">
                          <StatusBadge tone={linked ? "success" : "neutral"}>
                            {linked ? "Já vinculada" : "Sem galeria"}
                          </StatusBadge>
                          <dl className={styles.clientTotals}>
                            <div><dt>Públicas</dt><dd>{person.aggregates?.public_galleries ?? 0}</dd></div>
                            <div><dt>Privadas</dt><dd>{person.aggregates?.private_galleries ?? 0}</dd></div>
                            <div><dt>Pedidos</dt><dd>{person.aggregates?.orders ?? 0}</dd></div>
                          </dl>
                        </td>
                        <td role="cell">{person.deletion_eligible ? "Sem histórico comercial protegido" : "Histórico comercial preservado"}</td>
                        <td role="cell">
                          <MarkinaButton type="button" variant="secondary" onClick={() => setEditing(person)}>
                            Editar
                          </MarkinaButton>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              {nextCursor ? (
                <MarkinaButton type="button" variant="secondary" disabled={loadingMore} onClick={loadMore}>
                  {loadingMore ? "Carregando…" : "Carregar mais"}
                </MarkinaButton>
              ) : null}
            </>
          ) : (
            <SystemState
              title={query ? "Nenhuma cliente encontrada" : "Ainda não há clientes"}
              detail={
                query
                  ? "Revise o nome ou o número informado."
                  : "Cadastre a primeira cliente. Nenhuma galeria é necessária para começar."
              }
            />
          )}
        </div>
      </section>
      <section className={styles.clientForm} id="cadastro-cliente" tabIndex={-1} aria-labelledby="create-client-title">
        <h2 id="create-client-title">Cadastrar cliente</h2>
        <p className="gallery-scope-note">
          O telefone normalizado identifica a cliente em todas as galerias e não pode ser duplicado.
        </p>
        <ClientCreateForm
          onCreated={() => {
            setMessage("Cliente cadastrada no diretório da sua conta.");
            setRefresh((value) => value + 1);
          }}
        />
      </section>
      {editing ? (
        <ClientEditorDialog
          key={editing.id}
          client={editing}
          onClose={() => setEditing(null)}
          onUpdated={(updated) => {
            setClients((current) =>
              current.map((item) => (item.id === updated.id ? updated : item)),
            );
            setEditing(null);
            setMessage("Cadastro atualizado sem alterar seus vínculos ou histórico.");
          }}
          onDeleted={(clientId, pendingCleanupRequestId) => {
            setClients((current) => current.filter((item) => item.id !== clientId));
            setEditing(null);
            setMessage(
              pendingCleanupRequestId
                ? `Cadastro excluído; uma etapa auxiliar precisa de reconciliação. Referência de diagnóstico: ${pendingCleanupRequestId}.`
                : "Cadastro e estado operacional excluídos. O histórico comercial permaneceu protegido.",
            );
          }}
        />
      ) : null}
    </div>
  );
}
