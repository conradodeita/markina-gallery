"use client";

import { type FormEvent, useEffect, useState } from "react";
import { RemovedMovements, type RemovedMovement } from "../../removed-movements";
import { MarkinaButton, SystemState } from "../../ui-kit";

type Movement = RemovedMovement & { client_id: string; parent_gallery_id: string };
type Result = {
  items: Movement[];
  galleries: Array<{ id: string; name: string }>;
  page: { offset: number; limit: number; has_more: boolean };
};
type Filters = { query: string; parent_gallery_id: string; created_from: string; created_to: string };
const emptyFilters: Filters = { query: "", parent_gallery_id: "", created_from: "", created_to: "" };
const pageSize = 25;

export default function RemovedHistory() {
  const [draft, setDraft] = useState<Filters>(emptyFilters);
  const [filters, setFilters] = useState<Filters>(emptyFilters);
  const [offset, setOffset] = useState(0);
  const [result, setResult] = useState<Result | null>(null);
  const [galleries, setGalleries] = useState<Result["galleries"]>([]);
  const [failed, setFailed] = useState(false);
  const [revision, setRevision] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    const params = new URLSearchParams({ limit: String(pageSize), offset: String(offset) });
    if (filters.query.trim()) params.set("query", filters.query.trim());
    if (filters.parent_gallery_id) params.set("parent_gallery_id", filters.parent_gallery_id);
    if (filters.created_from) params.set("created_from", new Date(`${filters.created_from}T00:00:00`).toISOString());
    if (filters.created_to) params.set("created_to", new Date(`${filters.created_to}T23:59:59.999`).toISOString());
    fetch(`/api/admin/removed-photo-movements?${params}`, { credentials: "same-origin", signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error();
        const payload: Result = await response.json();
        if (controller.signal.aborted) return;
        setResult(payload);
        setGalleries(payload.galleries);
        setFailed(false);
      }).catch(() => { if (!controller.signal.aborted) setFailed(true); });
    return () => controller.abort();
  }, [filters, offset, revision]);

  function apply(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setResult(null); setFailed(false); setOffset(0); setFilters({ ...draft });
  }
  function changePage(next: number) {
    setResult(null); setFailed(false); setOffset(next);
  }
  const groups = new Map<string, Movement[]>();
  for (const item of result?.items ?? []) {
    const key = `${item.client_id}:${item.parent_gallery_id}`;
    groups.set(key, [...(groups.get(key) ?? []), item]);
  }
  return <section aria-label="Consulta de histórico excluído">
    <h2>Histórico de acervo excluído</h2>
    <p>Consulte os movimentos por cliente, galeria e período. Pedidos e estados financeiros continuam em Pedidos e pagamentos.</p>
    <form className="admin-card filter-grid" onSubmit={apply}>
      <label>Cliente<input value={draft.query} maxLength={200} placeholder="Nome do cliente" onChange={(event) => setDraft({ ...draft, query: event.target.value })} /></label>
      <label>Galeria do histórico<select value={draft.parent_gallery_id} onChange={(event) => setDraft({ ...draft, parent_gallery_id: event.target.value })}><option value="">Todas</option>{galleries.map((gallery) => <option key={gallery.id} value={gallery.id}>{gallery.name}</option>)}</select></label>
      <label>De<input type="date" value={draft.created_from} max={draft.created_to || undefined} onChange={(event) => setDraft({ ...draft, created_from: event.target.value })} /></label>
      <label>Até<input type="date" value={draft.created_to} min={draft.created_from || undefined} onChange={(event) => setDraft({ ...draft, created_to: event.target.value })} /></label>
      <div className="payment-filter-actions"><MarkinaButton type="submit">Consultar histórico</MarkinaButton><MarkinaButton type="button" variant="secondary" onClick={() => { setDraft(emptyFilters); setFilters({ ...emptyFilters }); setOffset(0); setResult(null); setFailed(false); }}>Limpar filtros</MarkinaButton></div>
    </form>
    {failed ? <><SystemState tone="error" title="Não foi possível consultar o histórico" detail="Confira o período e tente novamente." /><MarkinaButton onClick={() => { setFailed(false); setResult(null); setRevision((value) => value + 1); }}>Tentar novamente</MarkinaButton></> : !result ? <SystemState tone="loading" title="Carregando histórico" detail="Consultando a página de movimentos." /> : <>
      {!result.items.length ? <SystemState title="Nenhum movimento neste filtro" detail="Ajuste cliente, galeria ou período para consultar outros registros." /> : <p role="status">Página {Math.floor(result.page.offset / result.page.limit) + 1} · {result.items.length} movimento(s)</p>}
      {[...groups].map(([key, items]) => <details className="admin-card" key={`${offset}:${revision}:${JSON.stringify(filters)}:${key}`}>
        <summary>{items[0].client_name} · {items[0].parent_gallery_name} · {items.length} movimento(s) nesta página</summary>
        <RemovedMovements items={items} />
      </details>)}
      <nav className="payment-pagination" aria-label="Páginas do histórico">
        <MarkinaButton variant="secondary" disabled={offset === 0} onClick={() => changePage(Math.max(0, offset - pageSize))}>Página anterior</MarkinaButton>
        <MarkinaButton variant="secondary" disabled={!result.page.has_more} onClick={() => changePage(offset + pageSize)}>Próxima página</MarkinaButton>
      </nav>
    </>}
  </section>;
}
