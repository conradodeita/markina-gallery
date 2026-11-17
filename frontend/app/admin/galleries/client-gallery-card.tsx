import { type FormEvent, type ReactNode, useRef, useState } from "react";

import { StatusBadge } from "../../ui-kit";
import { confirmDuplicateJpegs, jpegStorageKey, uploadJpeg } from "../../upload-jpeg";
import { CreditUploadFeedback, isDefinitiveUploadRejection, useCreditUploadStatus } from "../credits/credit-upload-status";
import { FinancialOrderShortcuts, type FinancialOrder } from "../payments/payment-actions";
import { OrderDeliveryForm, type OrderDelivery } from "../payments/order-delivery";
import { applyPurchasedPhotoExportTheme } from "../purchased-photo-export";
import { AdminPhotoPreviewDialog, type AdminPhotoPreview } from "./admin-photo-preview-dialog";
import { FolderDeadlineFields } from "./folder-deadline-fields";
import { folderAccessStatusLabel, mediaArchiveStatusLabel, type MediaArchiveStatus } from "../../media-archive-status";
import { useFolderAccessClock } from "../../use-folder-access-clock";

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
  commercial_status?: "selection_finalized" | "pending_review" | "awaiting_payment" | "paid" | "cancelled" | "no_order";
  reopening_status?: "pending" | "approved" | "refused" | null;
  finalized_orders?: Array<{ id: string; frozen_at: string; delivery: OrderDelivery; items: Array<{ name: string; preview_url: string | null }> }>;
  financial_orders?: FinancialOrder[];
  last_access_at?: string | null;
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
  cancelled: { label: "Pedido cancelado", tone: "dark" },
  no_order: { label: "Sem pedido", tone: "neutral" },
} as const;

type CollectionFolder = { id: string; name: string; status: string; photo_count: number;
  preview_url?: string | null; media_state?: MediaArchiveStatus; assigned_client_ids: string[]; released_at?: string | null;
  access_duration_days?: number | null; access_expires_at?: string | null };
type CollectionPhoto = { id: string; name: string; preview_url: string | null; publication_state: string; can_delete: boolean; content_fingerprint?: string | null };
type UploadIntent = { file: File; id: string; allowDuplicateContent?: boolean };
type UploadState = { phase: "preparing" | "uploading" | "waiting" | "success" | "error";
  current: number; total: number; completed: number; filename: string;
  fileBytes: number; fileTotal: number };

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
  const observedAt = useFolderAccessClock(folders, open);
  const [activeFolder, setActiveFolder] = useState<string | null>(null);
  const [photos, setPhotos] = useState<CollectionPhoto[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [expandedPhoto, setExpandedPhoto] = useState<AdminPhotoPreview | null>(null);
  const [uploadState, setUploadState] = useState<UploadState | null>(null);
  const [retryFiles, setRetryFiles] = useState<UploadIntent[]>([]);
  const uploading = useRef(false);
  const creditUpload = useCreditUploadStatus(uploadState !== null);
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
    setUploadState(null);
    setRetryFiles([]);
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
    const accessDurationDays = Number(new FormData(form).get("access_duration_days"));
    if (!name) return;
    setBusy(true);
    try {
      await collectionRequest(folderPath, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, access_duration_days: accessDurationDays }),
      });
      form.reset();
      await loadFolders();
      setMessage("Pasta criada para esta cliente. Carregue os JPEGs para preparar as prévias.");
      await onRefresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível criar a pasta.");
    } finally { setBusy(false); }
  }

  async function configureFolderDeadline(folder: CollectionFolder, event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    const accessDurationDays = Number(new FormData(event.currentTarget).get("access_duration_days"));
    setBusy(true);
    try {
      await collectionRequest(`/api/admin/photo-folders/${folder.id}/deadline`, {
        method: "PATCH", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ access_duration_days: accessDurationDays }),
      });
      await loadFolders();
      setMessage(folder.released_at
        ? "Prazo configurado. A contagem começa agora."
        : "Prazo atualizado. A contagem começa quando você liberar a pasta.");
      await onRefresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível configurar o prazo da pasta.");
    } finally { setBusy(false); }
  }

  async function renameFolder(folder: CollectionFolder) {
    if (busy) return;
    const proposedName = window.prompt("Novo nome da pasta", folder.name);
    if (proposedName === null) return;
    const name = proposedName.trim();
    if (!name) { setMessage("Informe um nome para a pasta."); return; }
    setBusy(true);
    try {
      await collectionRequest(`/api/admin/photo-folders/${folder.id}`, {
        method: "PATCH", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      await loadFolders();
      setMessage("Nome da pasta atualizado.");
      await onRefresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível renomear a pasta.");
    } finally { setBusy(false); }
  }

  async function uploadPhotos(intents: UploadIntent[], retrying = false) {
    if (!activeFolder || uploading.current || !intents.length) return;
    const folderId = activeFolder;
    const selectedCount = intents.length;
    uploading.current = true;
    setBusy(true);
    setRetryFiles([]);
    let completed = 0;
    let skippedDuplicates = 0;
    const failed: UploadIntent[] = [];
    const errors: string[] = [];
    try {
      if (!retrying) {
        const folderPhotos = await collectionRequest(`/api/admin/photo-folders/${folderId}/photos`) as { photos: CollectionPhoto[] };
        const review = await confirmDuplicateJpegs(
          intents,
          (intent) => intent.file,
          folderPhotos.photos.map((photo) => photo.content_fingerprint),
        );
        const duplicateIndexes = new Set(review.confirmed ? review.duplicateIndexes : []);
        intents = review.items.map((intent, index) => ({
          ...intent, allowDuplicateContent: duplicateIndexes.has(index),
        }));
        skippedDuplicates = review.skippedCount;
        if (!intents.length) {
          setUploadState({ phase: "success", current: selectedCount, total: selectedCount,
            completed: 0, filename: "", fileBytes: 0, fileTotal: 0 });
          setMessage(`${skippedDuplicates} foto(s) repetida(s) ignorada(s). Nenhuma foto nova para enviar.`);
          return;
        }
      }
      const openBatches = await collectionRequest(`/api/admin/photo-folders/${folderId}/upload-batches`) as { batches: Array<{ id: string }> };
      const batch = openBatches.batches[0] ?? await collectionRequest(`/api/admin/photo-folders/${folderId}/upload-batches`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: "{}",
      }) as { id: string };
      try {
        for (const [index, intent] of intents.entries()) {
          const { file, id: uploadIntentId } = intent;
          const state = { current: index + 1, total: intents.length, completed,
            filename: file.name, fileBytes: 0, fileTotal: file.size };
          setUploadState({ ...state, phase: "preparing" });
          let photoId: string | null = null;
          try {
            const storageKey = await jpegStorageKey(parentGalleryId, folderId, file, uploadIntentId);
            const photo = await collectionRequest(`/api/admin/photo-folders/${folderId}/photos`, {
              method: "POST", headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ filename: file.name, storage_key: storageKey,
                upload_batch_id: batch.id,
                  allow_duplicate_content: intent.allowDuplicateContent ?? false }),
            }) as { id: string };
            photoId = photo.id;
            creditUpload.startPhoto(photo.id, file.name);
            await uploadJpeg(`/api/admin/photo-assets/${photo.id}/source`, file,
              () => setUploadState({ ...state, phase: "waiting" }),
              (loaded, total) => setUploadState({ ...state, phase: "uploading",
                fileBytes: loaded, fileTotal: total }));
            await creditUpload.refreshPhoto(photo.id, file.name);
            completed++;
          } catch (error) {
            if (photoId) {
              void creditUpload.refreshPhoto(photoId, file.name, isDefinitiveUploadRejection(error));
            }
            failed.push(intent);
            errors.push(`${file.name}: ${error instanceof Error ? error.message : "falha no envio"}`);
          }
        }
      } finally {
        await collectionRequest(`/api/admin/photo-folders/${folderId}/upload-batches/${batch.id}/close`, {
          method: "POST", headers: { "Content-Type": "application/json" }, body: "{}",
        });
      }
      setRetryFiles(failed);
      setUploadState({ phase: failed.length ? "error" : "success", current: selectedCount,
        total: selectedCount, completed, filename: failed[0]?.file.name ?? intents.at(-1)?.file.name ?? "",
        fileBytes: 0, fileTotal: 0 });
      await loadFolders();
      const payload = await collectionRequest(`/api/admin/photo-folders/${folderId}/photos`) as { photos: CollectionPhoto[] };
      setPhotos(payload.photos);
      const skippedNote = skippedDuplicates ? `${skippedDuplicates} repetida(s) ignorada(s). ` : "";
      setMessage(failed.length ? `${skippedNote}${completed} foto(s) enviada(s). ${errors.join(" ")}`
        : `${skippedNote}${completed} foto(s) enviada(s). As prévias serão preparadas pelo processamento normal.`);
      await onRefresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Fotos enviadas, mas não foi possível atualizar a lista.");
    } finally { uploading.current = false; setBusy(false); }
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
    <button type="button" className="client-collection-toggle" aria-expanded={open} disabled={busy} onClick={() => { void toggle(); }}>
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
      <div className="client-collection__actions" role="group" aria-label={`Ações do acervo de ${person.name}`}>
        <button type="button" className="mk-button mk-button--secondary" disabled={busy} onClick={() => { void changeAccess(); }}>
          {person.access_status === "blocked" ? "Liberar acesso" : "Bloquear acesso"}
        </button>
        {person.selected_count > 0 ? <a className="mk-button mk-button--secondary" href={`/api/admin/parent-galleries/${parentGalleryId}/clients/${person.client_id}/selection/export.csv`}>Baixar seleção atual (CSV)</a> : null}
        {person.purchased_count > 0 ? <a className="mk-button mk-button--secondary" href={`/api/admin/parent-galleries/${parentGalleryId}/clients/${person.client_id}/selection/export.html`} onClick={applyPurchasedPhotoExportTheme}>Baixar fotos compradas</a> : null}
      </div>
      {person.reopening_status === "pending" ? <p className="gallery-client-pending">A cliente solicitou reabertura. Decida em Vendas e pagamentos.</p> : null}
      {message ? <p className="form-message" role="status">{message}</p> : null}
      <section className="client-collection-folder-create">
        <h3>Pastas restritas ao cliente</h3>
        <form className="gallery-inline-form gallery-folder-create-form" onSubmit={(event) => { void createFolder(event); }}>
          <label>Nova pasta restrita<input name="name" maxLength={200} required /></label>
          <FolderDeadlineFields mode="creation" startsAt="release" />
          <button type="submit" className="mk-button mk-button--primary" disabled={busy}>Criar pasta</button>
        </form>
      </section>
      <div className="client-collection-folder-list">{folders.map((folder) => <section key={folder.id}
        className={`client-collection-folder${activeFolder === folder.id ? " is-open" : ""}`}>
        <button type="button" aria-label={`${activeFolder === folder.id ? "Recolher" : "Abrir"} pasta ${folder.name}`}
          aria-expanded={activeFolder === folder.id} disabled={busy} onClick={() => { void openFolder(folder.id); }}>
          <span className="client-collection-folder__preview"><b>Sem prévia</b>
            {folder.preview_url ? <img src={`/api${folder.preview_url}`} alt="" loading="lazy" decoding="async"
              onError={(event) => { event.currentTarget.hidden = true; }} /> : null}
          </span>
          <span className="client-collection-folder__label"><strong>{folder.name}</strong>
            <span className="client-collection-folder__summary">
              <small>{folder.photo_count} foto(s)</small>
              <span className="mk-badge mk-badge--neutral">{folderAccessStatusLabel(folder, observedAt)}</span>
            </span>
            <small className="client-collection-folder__deadline-summary">
              {folder.access_expires_at ? `Acesso até ${new Date(folder.access_expires_at).toLocaleString("pt-BR")}` : folder.access_duration_days ? `${folder.access_duration_days} dias após liberação` : "Prazo indeterminado"}
            </small>
          </span>
          <span className="client-collection-folder__chevron" aria-hidden="true">{activeFolder === folder.id ? "▲" : "▼"}</span>
        </button>
        {activeFolder === folder.id ? <div className="client-collection-folder__body">
          {folder.media_state && folder.media_state !== "available" ? <p className="client-collection-folder__status" role="status">{mediaArchiveStatusLabel(folder.media_state)}{folder.media_state === "archived" ? <>. Consulte <a href="/admin/credits">Créditos</a> para solicitar a recuperação.</> : "."}</p> : null}
          {folder.media_state === "available" || !folder.media_state ? <>
            <section className="client-collection-folder__management" aria-label={`Gestão da pasta ${folder.name}`}>
              <h4>Ações da pasta</h4>
              <div className="client-collection-folder__actions" role="group" aria-label={`Ações para pasta ${folder.name}`}>
                <a className="mk-button mk-button--secondary" href={`/admin/galleries/sources/${parentGalleryId}/edit/imagens?folder=${folder.id}`}>Processamento da pasta</a>
                <button type="button" className="mk-button mk-button--primary" disabled={busy} onClick={() => { void publishFolder(folder); }}>Disponibilizar fotos prontas</button>
                <button type="button" className="mk-button mk-button--secondary" disabled={busy} onClick={() => { void renameFolder(folder); }}>Renomear pasta</button>
                <button type="button" className="mk-button mk-button--danger" disabled={busy} onClick={() => { void removeFolder(folder); }}>Excluir pasta</button>
              </div>
            </section>
          </> : null}
          {folder.status !== "released" || (!folder.access_duration_days && !folder.access_expires_at) ? <form className="gallery-inline-form client-collection-folder__deadline" onSubmit={(event) => { void configureFolderDeadline(folder, event); }}>
            <FolderDeadlineFields mode="existing" startsAt={folder.released_at ? "save" : "release"} initialDays={folder.released_at ? null : folder.access_duration_days} />
            <button type="submit" className="mk-button mk-button--primary" disabled={busy}>{folder.released_at ? "Definir prazo" : "Salvar prazo"}</button>
          </form> : null}
          {folder.assigned_client_ids.length > 1 ? <section className="client-collection-recipients" aria-label="Clientes com acesso">
            <h4>Pasta compartilhada anterior · clientes com acesso</h4>
            <ul>{folder.assigned_client_ids.map((clientId) => <li key={clientId}>
              {linkedClients.find((client) => client.client_id === clientId)?.name ?? "Cliente vinculada"}
              <button type="button" className="link-button" disabled={busy} onClick={() => { void revokeClient(folder, clientId); }}>Remover acesso</button>
            </li>)}</ul>
          </section> : null}
          <section className="client-collection-folder__photos" aria-label={`Fotos da pasta ${folder.name}`}>
            <h4>Fotos da pasta</h4>
            <div className="folder-photo-grid">{photos.map((photo) => <article key={photo.id}>
              {photo.preview_url ? <button type="button" className="photo-preview-button"
                aria-label={`Ampliar ${photo.name}`} onClick={(event) => setExpandedPhoto({
                  src: `/api${photo.preview_url}`, alt: `Prévia ampliada de ${photo.name}`,
                  name: photo.name, trigger: event.currentTarget,
                })}><img src={`/api${photo.preview_url}`} alt={`Prévia de ${photo.name}`} /></button> : <div className="gallery-cover">{folder.media_state && folder.media_state !== "available" ? mediaArchiveStatusLabel(folder.media_state) : "Preparando prévia"}</div>}
              <strong>{photo.name}</strong><small>{folder.media_state && folder.media_state !== "available" ? mediaArchiveStatusLabel(folder.media_state) : photo.publication_state}</small>
              {photo.can_delete ? <button type="button" className="link-button" disabled={busy} onClick={() => { void removePhoto(folder, photo); }}>Excluir foto</button> : null}
            </article>)}</div>
          </section>
          {folder.media_state === "available" || !folder.media_state ? <section className="client-collection-folder__upload" aria-label={`Upload para pasta ${folder.name}`}>
            <h4>Enviar fotos</h4>
            <label>Adicionar fotos (JPEG)<input type="file" accept="image/jpeg" multiple disabled={busy}
              onChange={(event) => { const files = Array.from(event.currentTarget.files ?? []);
                event.currentTarget.value = ""; void uploadPhotos(files.map((file) => ({ file, id: crypto.randomUUID() }))); }} /></label>
          </section> : null}
          {uploadState ? <div className={`upload-status upload-status--${uploadState.phase}`} role="status" aria-live="polite">
            <strong>{uploadState.phase === "preparing" ? "Preparando arquivo"
              : uploadState.phase === "uploading" ? `Enviando foto ${uploadState.current} de ${uploadState.total}`
              : uploadState.phase === "waiting" ? "Aguardando espaço para continuar"
              : uploadState.phase === "success" ? "Upload concluído" : "Algumas fotos não foram enviadas"}</strong>
            <span>{uploadState.filename} · {uploadState.completed} de {uploadState.total} concluída(s)</span>
            {uploadState.phase === "uploading" ? <><progress value={uploadState.fileTotal ? uploadState.fileBytes : undefined}
              max={uploadState.fileTotal || 1} />{uploadState.fileTotal ? <span>{Math.round(uploadState.fileBytes / uploadState.fileTotal * 100)}% desta foto</span> : null}</> : null}
            {retryFiles.length ? <button type="button" className="secondary" disabled={busy}
                onClick={() => { void uploadPhotos(retryFiles, true); }}>Tentar novamente {retryFiles.length} foto(s)</button> : null}
          </div> : null}
          <CreditUploadFeedback wallet={creditUpload.wallet} walletState={creditUpload.walletState}
            items={creditUpload.items} visible={uploadState !== null} onVerifyPending={creditUpload.verifyPending} />
        </div> : null}
      </section>)}</div>
      {expandedPhoto ? <AdminPhotoPreviewDialog preview={expandedPhoto} onClose={() => setExpandedPhoto(null)} /> : null}
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
