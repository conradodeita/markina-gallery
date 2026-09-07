"use client";

import { useEffect, useState } from "react";

import { MarkinaButton, PageHeading, StatusBadge, SurfaceCard, SystemState } from "../../ui-kit";
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
    <div className="admin-shell client-directory-shell">
      <PageHeading
        eyebrow="Relacionamento"
        title="Clientes"
        detail="Cadastre, encontre e mantenha uma única identidade por WhatsApp, mesmo antes de criar uma galeria."
      />
      {message ? (
        <p className="notice" role="status">
          {message}
        </p>
      ) : null}
      <section className="client-directory-layout">
        <SurfaceCard className="client-directory-create">
          <p className="eyebrow">Novo cadastro</p>
          <h2>Cadastrar cliente</h2>
          <p className="gallery-scope-note">
            O telefone normalizado identifica a cliente em todas as galerias e não pode ser
            duplicado.
          </p>
          <ClientCreateForm
            onCreated={() => {
              setMessage("Cliente cadastrada no diretório global.");
              setRefresh((value) => value + 1);
            }}
          />
        </SurfaceCard>
        <section className="client-directory-results" aria-labelledby="client-directory-title">
          <div className="client-directory-toolbar">
            <div>
              <p className="eyebrow">Cadastro global</p>
              <h2 id="client-directory-title">Pessoas cadastradas</h2>
            </div>
            <label>
              Buscar por nome ou WhatsApp
              <input
                type="search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Ex.: Ana ou 11999999999"
              />
            </label>
          </div>
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
              <div className="client-directory-grid">
                {clients.map((person) => {
                  const aggregates = person.aggregates ?? {
                    public_galleries: 0,
                    private_galleries: 0,
                    orders: 0,
                  };
                  const linked = aggregates.public_galleries + aggregates.private_galleries > 0;
                  return (
                    <article className="client-directory-card" key={person.id}>
                      <header>
                        <div>
                          <strong>{person.name}</strong>
                          <small>{person.phone}</small>
                        </div>
                        <StatusBadge tone={linked ? "success" : "neutral"}>
                          {linked ? "Já vinculada" : "Sem galeria"}
                        </StatusBadge>
                      </header>
                      <dl>
                        <div>
                          <dt>Públicas</dt>
                          <dd>{aggregates.public_galleries}</dd>
                        </div>
                        <div>
                          <dt>Privadas</dt>
                          <dd>{aggregates.private_galleries}</dd>
                        </div>
                        <div>
                          <dt>Pedidos</dt>
                          <dd>{aggregates.orders}</dd>
                        </div>
                      </dl>
                      <div className="client-directory-card-footer">
                        <span>
                          {person.deletion_eligible
                            ? "Sem histórico comercial protegido"
                            : "Histórico comercial preservado"}
                        </span>
                        <MarkinaButton type="button" variant="secondary" onClick={() => setEditing(person)}>
                          Editar
                        </MarkinaButton>
                      </div>
                    </article>
                  );
                })}
              </div>
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
                  : "Use o cadastro ao lado; nenhuma galeria é necessária para começar."
              }
            />
          )}
        </section>
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
          onDeleted={(clientId) => {
            setClients((current) => current.filter((item) => item.id !== clientId));
            setEditing(null);
            setMessage("Cadastro e estado operacional excluídos. O histórico comercial permaneceu protegido.");
          }}
        />
      ) : null}
    </div>
  );
}
