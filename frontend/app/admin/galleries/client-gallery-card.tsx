import { type FormEvent, type ReactNode, useState } from "react";

import { StatusBadge } from "../../ui-kit";
import { jpegStorageKey, uploadJpeg } from "../../upload-jpeg";
import { FinancialOrderShortcuts, type FinancialOrder } from "../payments/payment-actions";
import { OrderDeliveryForm, type OrderDelivery } from "../payments/order-delivery";
import { SelectionDeadline } from "../../selection-deadline";

export type ClientGalleryRow = {
  client_id: string;
  name: string;
  phone: string;
  phone_verified?: boolean;
  registration_status: string | null;
  membership_status?: "active" | "blocked" | "unlinked" | null;
  access_status?: "active" | "blocked";
  derived_gallery_id: string | null;
  available_count: number;
  selected_count: number;
  purchased_count: number;
  gallery_status: "pending_registration" | "no_selection" | "blocked" | "expired" | "active";
  commercial_status?: "selection_finalized" | "pending_review" | "awaiting_payment" | "paid" | "overdue" | "cancelled" | "no_order";
  reopening_status?: "pending" | "approved" | "refused" | null;
  finalized_orders?: Array<{ id: string; frozen_at: string; delivery: OrderDelivery; items: Array<{ name: string; preview_url: string | null }> }>;
  financial_orders?: FinancialOrder[];
  selection_expires_at?: string | null;
};

const galleryStatus = {
  pending_registration: { label: "Aguardando primeiro acesso", tone: "warning" },
  no_selection: { label: "Sem seleção", tone: "warning" },
  blocked: { label: "Galeria bloqueada", tone: "dark" },
  expired: { label: "Galeria expirada", tone: "warning" },
  active: { label: "Galeria ativa", tone: "success" },
} as const;

const commercialStatus = {
  selection_finalized: { label: "Seleção finalizada", tone: "success" },
  pending_review: { label: "Pagamento comunicado", tone: "warning" },
  awaiting_payment: { label: "Aguardando pagamento", tone: "neutral" },
  paid: { label: "Pago", tone: "success" },
  overdue: { label: "Prazo expirado", tone: "danger" },
  cancelled: { label: "Pedido cancelado", tone: "dark" },
  no_order: { label: "Sem pedido", tone: "neutral" },
} as const;

type CollectionFolder = { id: string; name: string; status: string; photo_count: number; assigned_client_ids: string[] };
type CollectionPhoto = { id: string; name: string; preview_url: string | null; publication_state: string; can_delete: boolean };

async function collectionRequest(path: string, init?: RequestInit) {
  const response = await fetch(path, { credentials: "same-origin", ...init });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(payload?.detail ?? "Não foi possível concluir a operação.");
  }
  return response.status === 204 ? null : response.json();
}

function ClientCollection({ person, parentGalleryId, linkedClients, onRefresh }: {
  person: ClientGalleryRow; parentGalleryId: string; linkedClients: ClientGalleryRow[];
  onRefresh: () => void | Promise<void>;
}) {
  const [open, setOpen] = useState(false);
  const [folders, setFolders] = useState<CollectionFolder[]>([]);
  const [activeFolder, setActiveFolder] = useState<string | null>(null);
  const [photos, setPhotos] = useState<CollectionPhoto[]>([]);
  const [busy, setBusy] = useState(false);
  const [candidateByFolder, setCandidateByFolder] = useState<Record<string, string>>({});
  const [message, setMessage] = useState("");
  const folderPath = `/api/admin/parent-galleries/${parentGalleryId}/clients/${person.client_id}/folders`;

  async function loadFolders() {
    const payload = await collectionRequest(folderPath) as { folders: CollectionFolder[] };
    setFolders(payload.folders);
  }

  async function toggle() {
    if (open) { setOpen(false); return; }
    setOpen(true);
    try { await loadFolders(); } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível carregar o acervo.");
    }
  }

  async function openFolder(folderId: string) {
    if (activeFolder === folderId) { setActiveFolder(null); setPhotos([]); return; }
    setActiveFolder(folderId);
    try {
      const payload = await collectionRequest(`/api/admin/photo-folders/${folderId}/photos`) as { photos: CollectionPhoto[] };
      setPhotos(payload.photos);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível abrir a pasta.");
    }
  }

  async function createFolder(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    const form = event.currentTarget;
    const name = String(new FormData(form).get("name") ?? "").trim();
    if (!name) return;
    setBusy(true);
    try {
      await collectionRequest(folderPath, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      form.reset();
      await loadFolders();
      setMessage("Pasta criada para esta cliente. Carregue os JPEGs para preparar as prévias.");
      await onRefresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível criar a pasta.");
    } finally { setBusy(false); }
  }

  async function uploadPhotos(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!activeFolder || busy) return;
    const input = event.currentTarget.elements.namedItem("jpeg") as HTMLInputElement;
    const files = Array.from(input.files ?? []);
    if (!files.length) return;
    setBusy(true);
    try {
      for (const file of files) {
        const storageKey = await jpegStorageKey(parentGalleryId, activeFolder, file);
        const photo = await collectionRequest(`/api/admin/photo-folders/${activeFolder}/photos`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ filename: file.name, storage_key: storageKey }),
        }) as { id: string };
        await uploadJpeg(`/api/admin/photo-assets/${photo.id}/source`, file);
      }
      input.value = "";
      await loadFolders();
      const payload = await collectionRequest(`/api/admin/photo-folders/${activeFolder}/photos`) as { photos: CollectionPhoto[] };
      setPhotos(payload.photos);
      setMessage(`${files.length} foto(s) enviada(s). As prévias serão preparadas pelo processamento normal.`);
      await onRefresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível enviar as fotos.");
    } finally { setBusy(false); }
  }

  async function assignClient(folder: CollectionFolder) {
    const clientId = candidateByFolder[folder.id];
    if (!clientId || busy) return;
    setBusy(true);
    try {
      await collectionRequest(`/api/admin/parent-galleries/${parentGalleryId}/folders/${folder.id}/clients/${clientId}`, { method: "POST" });
      await loadFolders();
      setCandidateByFolder((current) => ({ ...current, [folder.id]: "" }));
      setMessage("Cliente incluída na mesma pasta, sem copiar as fotos.");
      await onRefresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível atribuir a cliente.");
    } finally { setBusy(false); }
  }

  async function publishFolder(folder: CollectionFolder) {
    if (busy) return;
    setBusy(true);
    try {
      const result = await collectionRequest(`/api/admin/photo-folders/${folder.id}/publish`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: "{}",
      }) as { published_count: number; pending_count: number; failed_count: number };
      await loadFolders();
      setMessage(`${result.published_count} foto(s) disponibilizada(s); ${result.pending_count} em processamento; ${result.failed_count} com falha.`);
      await onRefresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível disponibilizar as fotos.");
    } finally { setBusy(false); }
  }

  async function revokeClient(folder: CollectionFolder, clientId: string) {
    if (busy) return;
    const name = linkedClients.find((client) => client.client_id === clientId)?.name ?? "esta cliente";
    if (!window.confirm(`Remover o acesso de ${name} à pasta “${folder.name}”? A pasta compartilhada continua disponível às outras clientes; compras confirmadas permanecem no histórico.`)) return;
    setBusy(true);
    try {
      await collectionRequest(`/api/admin/parent-galleries/${parentGalleryId}/folders/${folder.id}/clients/${clientId}`, { method: "DELETE" });
      await loadFolders();
      setMessage(`Acesso de ${name} removido desta pasta.`);
      await onRefresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível remover a atribuição.");
    } finally { setBusy(false); }
  }

  async function changeAccess() {
    if (busy) return;
    const nextStatus = person.access_status === "blocked" ? "active" : "blocked";
    if (nextStatus === "blocked" && !window.confirm(`Bloquear o acesso de ${person.name} a esta galeria? O histórico de compras será preservado.`)) return;
    setBusy(true);
    try {
      await collectionRequest(`/api/admin/parent-galleries/${parentGalleryId}/clients/${person.client_id}/access`, {
        method: "PATCH", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: nextStatus }),
      });
      setMessage(nextStatus === "blocked" ? "Acesso individual bloqueado." : "Acesso individual liberado.");
      await onRefresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível alterar o acesso.");
    } finally { setBusy(false); }
  }

  async function removeFolder(folder: CollectionFolder) {
    if (busy || !window.confirm(`Excluir a pasta “${folder.name}” e suas ${folder.photo_count} foto(s) para todas as clientes atribuídas? Compras confirmadas permanecem no histórico. Esta ação não pode ser desfeita.`)) return;
    setBusy(true);
    try {
      await collectionRequest(`/api/admin/photo-folders/${folder.id}`, { method: "DELETE" });
      setActiveFolder(null);
      setPhotos([]);
      await loadFolders();
      setMessage("Pasta removida. O histórico de compras foi preservado.");
      await onRefresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível excluir a pasta.");
    } finally { setBusy(false); }
  }

  async function removePhoto(folder: CollectionFolder, photo: CollectionPhoto) {
    if (busy || !window.confirm(`Excluir a foto “${photo.name}” da pasta “${folder.name}” para todas as clientes atribuídas? Compras confirmadas permanecem no histórico.`)) return;
    setBusy(true);
    try {
      await collectionRequest(`/api/admin/photo-folders/${folder.id}/photos/${photo.id}`, { method: "DELETE" });
      const payload = await collectionRequest(`/api/admin/photo-folders/${folder.id}/photos`) as { photos: CollectionPhoto[] };
      setPhotos(payload.photos);
      await loadFolders();
      setMessage("Foto removida. O histórico de compras foi preservado.");
      await onRefresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível excluir a foto.");
    } finally { setBusy(false); }
  }

  return <section className="client-collection" aria-label={`Acervo de ${person.name}`}>
    <button type="button" className="client-collection-toggle" aria-expanded={open} onClick={() => { void toggle(); }}>
      <span>Acervo da cliente</span><span aria-hidden="true">{open ? "▲" : "▼"}</span>
    </button>
    {open ? <div className="client-collection-body">
      <dl className="gallery-client-counts">
        <div><dt>Fotos disponíveis</dt><dd>{person.available_count}</dd></div>
        <div><dt>Fotos selecionadas</dt><dd>{person.selected_count}</dd></div>
        <div><dt>Fotos compradas</dt><dd>{person.purchased_count}</dd></div>
      </dl>
      {person.finalized_orders?.map((order) => <section key={order.id} aria-label="Seleção finalizada">
        <h3>Seleção finalizada · {order.items.length} foto(s)</h3>
        <p>Negociação externa · sem cobrança no sistema</p>
        <div className="folder-photo-grid">{order.items.map((item, index) => <article key={index}>
          {item.preview_url ? <a href={`/api${item.preview_url}`} target="_blank" rel="noopener noreferrer"><img src={`/api${item.preview_url}`} alt={`Prévia de ${item.name}`} /></a> : null}
          <strong>{item.name}</strong>
        </article>)}</div>
        <a href={`/api/admin/orders/${order.id}/selection/export.csv`}>Baixar seleção finalizada (CSV)</a>{" · "}
        <a href={`/api/admin/orders/${order.id}/selection/export.txt`}>Baixar seleção finalizada (TXT)</a>
        <OrderDeliveryForm orderId={order.id} delivery={order.delivery} onRefresh={async () => { await onRefresh(); }} />
      </section>)}
      <SelectionDeadline expiresAt={person.selection_expires_at} />
      <button type="button" className="secondary" disabled={busy} onClick={() => { void changeAccess(); }}>
        {person.access_status === "blocked" ? "Liberar acesso" : "Bloquear acesso"}
      </button>
      {person.selected_count > 0 ? <a className="mk-button mk-button--secondary" href={`/api/admin/parent-galleries/${parentGalleryId}/clients/${person.client_id}/selection/export.csv`}>Baixar seleção atual (CSV)</a> : null}
      {person.purchased_count > 0 ? <a className="mk-button mk-button--secondary" href={`/api/admin/parent-galleries/${parentGalleryId}/clients/${person.client_id}/selection/export.html`}>Baixar fotos compradas</a> : null}
      {person.reopening_status === "pending" ? <p className="gallery-client-pending">A cliente solicitou reabertura. Decida em Vendas e pagamentos.</p> : null}
      {message ? <p className="form-message" role="status">{message}</p> : null}
      <form className="gallery-inline-form" onSubmit={(event) => { void createFolder(event); }}>
        <label>Nova pasta restrita<input name="name" maxLength={200} required /></label>
        <button type="submit" className="primary" disabled={busy}>Criar pasta</button>
      </form>
      {folders.map((folder) => <section key={folder.id} className="client-collection-folder">
        <button type="button" aria-expanded={activeFolder === folder.id} onClick={() => { void openFolder(folder.id); }}>
          {folder.name} · {folder.photo_count} foto(s) · {folder.status === "released" ? "Disponível" : "Preparando"}
        </button>
        {activeFolder === folder.id ? <div>
          <button type="button" className="secondary" disabled={busy} onClick={() => { void publishFolder(folder); }}>Disponibilizar fotos prontas</button>
          <button type="button" className="link-button" disabled={busy} onClick={() => { void removeFolder(folder); }}>Excluir pasta</button>
          <div className="client-collection-recipients">
            <strong>Clientes atribuídas</strong>
            <ul>{folder.assigned_client_ids.map((clientId) => <li key={clientId}>
              {linkedClients.find((client) => client.client_id === clientId)?.name ?? "Cliente vinculada"}
              {folder.assigned_client_ids.length > 1 ? <button type="button" className="link-button" disabled={busy} onClick={() => { void revokeClient(folder, clientId); }}>Remover acesso</button> : null}
            </li>)}</ul>
            <label>Adicionar cliente<select value={candidateByFolder[folder.id] ?? ""} onChange={(event) => setCandidateByFolder((current) => ({ ...current, [folder.id]: event.target.value }))}>
              <option value="">Selecione</option>
              {linkedClients.filter((client) => !folder.assigned_client_ids.includes(client.client_id)).map((client) => <option key={client.client_id} value={client.client_id}>{client.name}</option>)}
            </select></label>
            <button type="button" className="secondary" disabled={busy || !candidateByFolder[folder.id]} onClick={() => { void assignClient(folder); }}>Adicionar à pasta</button>
          </div>
          <div className="folder-photo-grid">{photos.map((photo) => <article key={photo.id}>
            {photo.preview_url ? <img src={`/api${photo.preview_url}`} alt={`Prévia de ${photo.name}`} /> : <div className="gallery-cover">Preparando prévia</div>}
            <strong>{photo.name}</strong><small>{photo.publication_state}</small>
            {photo.can_delete ? <button type="button" className="link-button" disabled={busy} onClick={() => { void removePhoto(folder, photo); }}>Excluir foto</button> : null}
          </article>)}</div>
          <form className="gallery-inline-form" onSubmit={(event) => { void uploadPhotos(event); }}>
            <label>Adicionar JPEGs<input name="jpeg" type="file" accept="image/jpeg" multiple required /></label>
            <button type="submit" className="primary" disabled={busy}>Enviar fotos</button>
          </form>
        </div> : null}
      </section>)}
      <FinancialOrderShortcuts orders={person.financial_orders} clientName={person.name} onRefresh={onRefresh} />
    </div> : null}
  </section>;
}

export function ClientGalleryCard({ person, parentGalleryId, linkedClients = [], actions, onRefresh = () => {} }: { person: ClientGalleryRow; parentGalleryId?: string; linkedClients?: ClientGalleryRow[]; actions?: ReactNode; onRefresh?: () => void | Promise<void> }) {
  const access = galleryStatus[person.gallery_status];
  const commercial = commercialStatus[person.commercial_status ?? "no_order"];
  return <article aria-label={`Cliente ${person.name}`} className={`gallery-linked-client gallery-linked-client--${person.gallery_status}`}>
    <header>
      <div>
        <strong>{person.name}</strong>
        <small>{person.phone}</small>
      </div>
      <span className="gallery-client-badges" aria-label="Estados da cliente">
        <StatusBadge tone={access.tone}>{access.label}</StatusBadge>
        <StatusBadge tone={commercial.tone}>{commercial.label}</StatusBadge>
      </span>
    </header>
    {person.gallery_status === "pending_registration" ? <p className="gallery-client-pending">O vínculo já existe. No primeiro acesso pelo link, a cliente ainda precisa validar este WhatsApp com o código OTP.</p> : null}
    {parentGalleryId ? <ClientCollection person={person} parentGalleryId={parentGalleryId} linkedClients={linkedClients} onRefresh={onRefresh} /> : null}
    {actions ? <div className="gallery-client-card-actions">{actions}</div> : null}
  </article>;
}
