"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { MarkinaButton, StatusBadge, SystemState } from "../../../../ui-kit";

type ClientRow = {
  client_id: string;
  name: string;
  phone: string;
  registration_status: string | null;
  derived_gallery_id: string | null;
};
type Folder = { id: string; name: string; status: string; photo_count: number };
type Summary = {
  name: string;
  event_name: string;
  active: boolean;
  unlisted_link: string | null;
  public_link_status: "active" | "unavailable";
  cover_preview_url: string | null;
  counts: { folders: number; photos: number; clients: number };
  clients: ClientRow[];
};
type InventorySection = Record<string, number | Record<string, number>>;
type DeletionPreview = {
  operation_type: "delete_parent_gallery";
  target: { id: string; name: string };
  inventory: { remove: InventorySection; preserve: InventorySection };
  consequences: {
    private_galleries_preserved: boolean;
    private_referenced_photos_preserved: boolean;
    clients_preserved: boolean;
    commercial_history_preserved: boolean;
    restoration_available_after_start: boolean;
  };
};
type LifecycleOperation = {
  operation_id: string;
  status: string;
  status_url: string;
  last_error: string | null;
  progress: { label: string; percent: number; failed_step: string | null };
  actions: { can_cancel: boolean; can_retry: boolean; should_poll: boolean; poll_after_ms: number | null };
};

const inventoryLabels: Record<string, string> = {
  folders: "pastas",
  photos: "fotos sem uso privado",
  media_derivatives: "arquivos derivados sem uso privado",
  registrations: "vínculos públicos",
  access_capabilities: "links e convites públicos",
  clients: "clientes",
  private_galleries: "galerias privadas",
  photos_referenced_by_private: "fotos usadas por galerias privadas",
  folders_with_private_photos: "pastas necessárias às galerias privadas",
  available_references: "referências privadas de fotos",
  selections: "seleções",
  favorites: "favoritos",
  comments: "comentários",
  views: "registros de visualização",
  orders: "pedidos",
  order_items: "itens de pedidos",
  historical_media: "mídias históricas",
  pending: "pedidos pendentes",
  confirmed: "pedidos confirmados",
  cancelled: "pedidos cancelados",
};

function inventoryRows(section: InventorySection) {
  return Object.entries(section).flatMap(([key, value]) => {
    if (typeof value === "number") return [{ key, label: inventoryLabels[key] ?? key, value }];
    return Object.entries(value).map(([nestedKey, nestedValue]) => ({
      key: `${key}.${nestedKey}`,
      label: inventoryLabels[nestedKey] ?? nestedKey,
      value: nestedValue,
    }));
  });
}

export default function SourceGalleryDetailPage() {
  const { sourceId } = useParams<{ sourceId: string }>();
  const router = useRouter();
  const [folders, setFolders] = useState<Folder[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [failed, setFailed] = useState(false);
  const [message, setMessage] = useState("");
  const [deletionPreview, setDeletionPreview] = useState<DeletionPreview | null>(null);
  const [operation, setOperation] = useState<LifecycleOperation | null>(null);
  const [deletionBusy, setDeletionBusy] = useState(false);
  const idempotencyKey = useRef("");

  async function openDeletionConfirmation() {
    setDeletionBusy(true);
    setMessage("");
    try {
      const response = await fetch(`/api/admin/parent-galleries/${sourceId}/deletion-inventory`, { credentials: "same-origin" });
      const payload = await response.json().catch(() => null);
      if (!response.ok) throw new Error(payload?.detail ?? "Não foi possível preparar o inventário.");
      setDeletionPreview(payload);
      idempotencyKey.current = crypto.randomUUID();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível preparar o inventário.");
    } finally {
      setDeletionBusy(false);
    }
  }

  async function confirmDeletion() {
    if (!deletionPreview || deletionBusy) return;
    setDeletionBusy(true);
    try {
      const response = await fetch(`/api/admin/parent-galleries/${sourceId}`, {
        method: "DELETE",
        credentials: "same-origin",
        headers: { "Idempotency-Key": idempotencyKey.current },
      });
      const payload = await response.json().catch(() => null);
      if (!response.ok) throw new Error(payload?.detail ?? "Não foi possível iniciar a exclusão.");
      setOperation(payload);
      setDeletionPreview(null);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível iniciar a exclusão.");
    } finally {
      setDeletionBusy(false);
    }
  }

  async function operationAction(action: "cancel" | "retry") {
    if (!operation || deletionBusy) return;
    setDeletionBusy(true);
    try {
      const response = await fetch(`/api/admin/gallery-lifecycle-operations/${operation.operation_id}/${action}`, {
        method: "POST",
        credentials: "same-origin",
      });
      const payload = await response.json().catch(() => null);
      if (!response.ok) throw new Error(payload?.detail ?? "Não foi possível atualizar a operação.");
      setOperation(payload);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível atualizar a operação.");
    } finally {
      setDeletionBusy(false);
    }
  }

  useEffect(() => {
    Promise.all([
      fetch(`/api/admin/parent-galleries/${sourceId}/folders`, { credentials: "same-origin" }),
      fetch(`/api/admin/parent-galleries/${sourceId}/summary`, { credentials: "same-origin" }),
    ]).then(async ([folderResponse, summaryResponse]) => {
      if (!folderResponse.ok || !summaryResponse.ok) throw new Error();
      setFolders((await folderResponse.json()).folders ?? []);
      setSummary(await summaryResponse.json());
    }).catch(() => setFailed(true));
  }, [sourceId]);

  useEffect(() => {
    if (!operation?.actions.should_poll) return;
    const timer = window.setTimeout(async () => {
      try {
        const response = await fetch(`/api${operation.status_url}`, { credentials: "same-origin" });
        if (!response.ok) throw new Error();
        setOperation(await response.json());
      } catch {
        setMessage("Não foi possível atualizar o progresso. Tente novamente.");
      }
    }, operation.actions.poll_after_ms ?? 1000);
    return () => window.clearTimeout(timer);
  }, [operation]);

  if (failed) return <SystemState tone="error" title="Galeria indisponível" detail="Não foi possível consultar seus dados agora." />;
  if (!summary) return <SystemState tone="loading" title="Carregando galeria" detail="Consultando clientes e pastas vinculadas." />;

  return (
    <main className="admin-shell">
      <Link href="/admin/galleries">← Galerias</Link>
      <p className="eyebrow">Galeria pública · compartilhamento protegido</p>
      <h1>{summary.name}</h1>
      <p className="intro">{summary.event_name || "Evento sem nome"}. O acesso às fotos segue o modo configurado e sempre exige autenticação da cliente.</p>
      <div className="action-grid"><Link className="mk-button mk-button--primary" href={`/admin/galleries/sources/${sourceId}/preview`}>Visualizar galeria</Link><Link className="mk-button mk-button--secondary" href={`/admin/galleries/sources/${sourceId}/edit/ajustes`}>Editar galeria</Link><Link className="mk-button mk-button--secondary" href={`/admin/galleries/sources/${sourceId}/edit/imagens`}>Abrir imagens</Link><MarkinaButton className="mk-button--danger" disabled={deletionBusy || Boolean(operation)} onClick={openDeletionConfirmation}>{deletionBusy ? "Preparando…" : "Excluir Galeria pública"}</MarkinaButton></div>
      <section className="admin-card"><div className="source-summary"><Link className="source-summary-cover" href={`/admin/galleries/sources/${sourceId}/preview`}>{summary.cover_preview_url ? <img src={`/api${summary.cover_preview_url}`} alt="Capa protegida da galeria" /> : "Sem capa definida"}</Link><div><h2>Resumo da galeria</h2><p>{summary.counts.folders} pastas · {summary.counts.photos} fotos · {summary.counts.clients} clientes vinculadas</p><p><strong>Link seguro:</strong> {summary.public_link_status === "active" ? "ativo" : "indisponível"}</p><Link href={`/admin/galleries/sources/${sourceId}/edit/clientes`}>Gerenciar links e clientes</Link></div></div></section>
      <section className="admin-card"><h2>Pastas</h2>{folders.length ? <div className="dashboard-recent">{folders.map((folder) => <div key={folder.id}><div><strong>{folder.name}</strong><small>{folder.photo_count} foto(s)</small></div><StatusBadge tone={folder.status === "released" ? "success" : "warning"}>{folder.status === "released" ? "Liberada" : "Em preparação"}</StatusBadge></div>)}</div> : <SystemState title="Nenhuma pasta" detail="Abra a etapa Imagens para criar a primeira pasta desta galeria." />}</section>
      <section className="admin-card"><h2>Clientes vinculadas</h2>{summary.clients.length ? <div className="dashboard-recent">{summary.clients.map((person) => <div key={person.client_id}><div><strong>{person.name}</strong><small>{person.phone}</small></div>{person.derived_gallery_id ? <Link href={`/admin/galleries/${person.derived_gallery_id}`}>Abrir galeria privada</Link> : <StatusBadge tone="warning">Cadastro pendente</StatusBadge>}</div>)}</div> : <SystemState title="Nenhuma cliente vinculada" detail="O vínculo pode nascer pelo login no link ou pela etapa Clientes." />}</section>

      {deletionPreview ? <div className="mk-dialog-backdrop" role="presentation"><section aria-labelledby="delete-gallery-title" aria-modal="true" className="mk-dialog lifecycle-dialog" role="dialog"><p className="eyebrow">Confirmação única</p><h2 id="delete-gallery-title">Excluir “{deletionPreview.target.name}”?</h2><p>A Galeria pública e o acesso compartilhável serão removidos. Esta limpeza não poderá ser restaurada depois que a etapa física começar.</p><div className="lifecycle-inventory"><section><h3>Será removido</h3><ul>{inventoryRows(deletionPreview.inventory.remove).map((item) => <li key={item.key}><strong>{item.value}</strong> {item.label}</li>)}</ul></section><section><h3>Será preservado</h3><ul>{inventoryRows(deletionPreview.inventory.preserve).map((item) => <li key={item.key}><strong>{item.value}</strong> {item.label}</li>)}</ul></section></div><p>Clientes, galerias privadas, fotos ainda referenciadas e histórico comercial permanecem preservados.</p><div className="mk-dialog__actions"><MarkinaButton variant="secondary" disabled={deletionBusy} onClick={() => setDeletionPreview(null)}>Cancelar</MarkinaButton><MarkinaButton className="mk-button--danger" disabled={deletionBusy} onClick={confirmDeletion}>{deletionBusy ? "Iniciando…" : `Excluir ${deletionPreview.target.name}`}</MarkinaButton></div></section></div> : null}

      {operation ? <section className="admin-card lifecycle-progress" aria-live="polite"><div className="section-heading"><div><p className="eyebrow">Exclusão da Galeria pública</p><h2>{operation.progress.label}</h2></div><StatusBadge tone={operation.status === "completed" ? "success" : operation.status === "failed" ? "danger" : operation.status === "cancelled" ? "warning" : "neutral"}>{operation.progress.percent}%</StatusBadge></div><progress value={operation.progress.percent} max={100} /><p>{operation.last_error ?? (operation.actions.should_poll ? "A operação continua em segundo plano. Esta página atualiza o progresso automaticamente." : "A operação não exige novas etapas automáticas.")}</p><div className="lifecycle-actions">{operation.actions.can_cancel ? <MarkinaButton variant="secondary" disabled={deletionBusy} onClick={() => operationAction("cancel")}>Cancelar antes da remoção física</MarkinaButton> : null}{operation.actions.can_retry ? <MarkinaButton disabled={deletionBusy} onClick={() => operationAction("retry")}>Retomar operação</MarkinaButton> : null}{operation.status === "completed" ? <MarkinaButton onClick={() => router.push("/admin/galleries")}>Voltar para galerias</MarkinaButton> : null}{operation.status === "cancelled" ? <MarkinaButton variant="secondary" onClick={() => setOperation(null)}>Fechar acompanhamento</MarkinaButton> : null}</div></section> : null}
      {message ? <p className="notice" role="alert">{message}</p> : null}
    </main>
  );
}
