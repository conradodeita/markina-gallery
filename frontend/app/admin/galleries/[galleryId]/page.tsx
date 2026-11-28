"use client";
import { confirmDuplicateJpegs, jpegFingerprint, jpegFingerprintFromStorageKey, jpegStorageKey, uploadJpeg } from "../../../upload-jpeg";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { MarkinaButton, MarkinaLink, MetricCard, PageHeading, StatusBadge, SystemState } from "../../../ui-kit";
import { OverviewIcon } from "../../overview-icon";
import catalogStyles from "../../catalog.module.css";
import styles from "./private-gallery.module.css";
import { formatBrazilianCurrency } from "../pricing-rules";
import { FinancialOrderShortcuts, type FinancialOrder } from "../../payments/payment-actions";
import { CreditUploadFeedback, isDefinitiveUploadRejection, useCreditUploadStatus } from "../../credits/credit-upload-status";
import { FolderDeadlineFields } from "../folder-deadline-fields";
import { applyPurchasedPhotoExportTheme } from "../../purchased-photo-export";

type Detail = { id: string; parent_gallery_id: string; name: string; custom_message: string; origin_active?: boolean; frozen: boolean; blocked: boolean; inherited_folder_display_mode?: "individual" | "sequential" };
type PhotoClient = { client_id: string; client_name: string };
type PhotoComment = PhotoClient & { id: string; body: string };
type PhotoCommercialState = PhotoClient & { state: "selected" | "awaiting_payment" | "payment_reported" | "purchased" };
type PrivatePhoto = { id: string; name: string; folder_id: string; folder_name: string; preview_url: string; ownership: "private" | "public_reference"; favorited_by?: PhotoClient[]; comments?: PhotoComment[]; commercial_states?: PhotoCommercialState[] };
type Folder = { id: string; name: string; status: string; photo_count: number; released_at?: string | null; access_duration_days?: number | null; access_expires_at?: string | null };
type Member = { financial_orders?: FinancialOrder[]; membership_id: string; client_id: string; client_name: string; phone_e164: string | null; status: "active" | "blocked" | "unlinked"; available_count?: number; selected_count: number; purchased_count: number; order_count: number; confirmed_total_cents: number; commercial_status?: string; payment_status?: string; reopening_status: string | null };
type Facial = { state: string; progress: { ready: number; total: number }; queued: number; processing: number; failed: number; coverage: { photos_with_faces: number; total: number; percent: number; detected_faces: number } };
type UploadState = { phase: "idle" | "uploading" | "success" | "error"; current: number; total: number; filename?: string };
type UploadBatch = { id: string; status: string; count: number; assets: { id: string; storage_key: string; upload_key?: string; status: string }[] };

async function requestJson(path: string, init?: RequestInit) {
  const response = await fetch(path, { credentials: "same-origin", ...init });
  const payload = response.status === 204 ? { cleanup_pending: response.headers.get("X-Asset-Cleanup") === "failed" } : await response.json().catch(() => null);
  if (!response.ok) throw new Error(payload?.detail ?? "Não foi possível concluir a operação.");
  return payload;
}

const photoStatePresentation = {
  selected: { label: "Selecionada", tone: "neutral" },
  awaiting_payment: { label: "Aguardando pagamento", tone: "warning" },
  payment_reported: { label: "Pagamento informado", tone: "warning" },
  purchased: { label: "Comprada", tone: "success" },
} as const;

function AdminPhotoInteractions({ photo }: { photo: PrivatePhoto }) {
  const favorites = photo.favorited_by ?? [];
  const comments = photo.comments ?? [];
  const commercialStates = photo.commercial_states ?? [];
  if (!favorites.length && !comments.length && !commercialStates.length) return null;
  return <div className="private-photo-interactions">
    {commercialStates.map((item) => {
      const presentation = photoStatePresentation[item.state];
      return <StatusBadge key={`${item.client_id}-${item.state}`} tone={presentation.tone}>{presentation.label} · {item.client_name}</StatusBadge>;
    })}
    {favorites.length ? <p className="private-photo-favorites"><span aria-hidden="true">♥</span> Favoritada por {favorites.map((item) => item.client_name).join(", ")}</p> : null}
    {comments.length ? <div className="private-photo-comments"><strong>Comentários</strong><ul>{comments.map((comment) => <li key={comment.id}><b>{comment.client_name}</b><span>{comment.body}</span></li>)}</ul></div> : null}
  </div>;
}

export default function GalleryDetailPage() {
  const { galleryId } = useParams<{ galleryId: string }>();
  const router = useRouter();
  const [detail, setDetail] = useState<Detail | null>(null);
  const [photos, setPhotos] = useState<PrivatePhoto[]>([]);
  const [folders, setFolders] = useState<Folder[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const [facial, setFacial] = useState<Facial | null>(null);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [upload, setUpload] = useState<UploadState>({ phase: "idle", current: 0, total: 0 });
  const [openBatches, setOpenBatches] = useState<UploadBatch[]>([]);
  const [resumeBatchId, setResumeBatchId] = useState("");
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [deleteError, setDeleteError] = useState("");
  const creditUpload = useCreditUploadStatus(upload.phase !== "idle");

  const load = useCallback(async (showLoading = true) => {
    if (showLoading) setLoading(true);
    try {
      const [detailData, photoData, folderData, memberData, facialData, batchData] = await Promise.all([
        requestJson(`/api/admin/derived-galleries/${galleryId}`), requestJson(`/api/admin/derived-galleries/${galleryId}/photos`),
        requestJson(`/api/admin/derived-galleries/${galleryId}/folders`), requestJson(`/api/admin/derived-galleries/${galleryId}/members`),
        requestJson(`/api/admin/derived-galleries/${galleryId}/facial-index`),
        requestJson(`/api/admin/derived-galleries/${galleryId}/upload-batches`),
      ]);
      const loadedPhotos = photoData.photos ?? [];
      const inferredFolders = [...new Map(loadedPhotos.filter((photo: PrivatePhoto) => photo.ownership === "private").map((photo: PrivatePhoto) => [photo.folder_id, { id: photo.folder_id, name: photo.folder_name, status: "released", photo_count: loadedPhotos.filter((item: PrivatePhoto) => item.folder_id === photo.folder_id).length }])).values()];
      setDetail(detailData); setPhotos(loadedPhotos); setFolders(folderData.folders ?? inferredFolders); setMembers(memberData.members ?? []); setFacial(facialData?.progress ? facialData : null); setFailed(false);
      setOpenBatches(batchData.batches ?? []);
    } catch { setFailed(true); } finally { if (showLoading) setLoading(false); }
  }, [galleryId]);

  useEffect(() => { queueMicrotask(() => load()); }, [load]);
  useEffect(() => { const refresh = () => void load(false); window.addEventListener("focus", refresh); return () => window.removeEventListener("focus", refresh); }, [load]);
  useEffect(() => { if (!facial || !["waiting", "processing"].includes(facial.state)) return; const timer = window.setTimeout(() => void load(false), 1800); return () => window.clearTimeout(timer); }, [facial, load]);
  const photosByFolder = useMemo(() => new Map(folders.map((folder) => [folder.id, photos.filter((photo) => photo.folder_id === folder.id)])), [folders, photos]);

  async function createFolder(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = event.currentTarget; const data = new FormData(form); setBusy(true);
    try { await requestJson(`/api/admin/derived-galleries/${galleryId}/folders`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: data.get("name"), access_duration_days: Number(data.get("access_duration_days")) }) }); form.reset(); setMessage("Pasta privada criada."); await load(false); }
    catch (error) { setMessage(error instanceof Error ? error.message : "Não foi possível criar a pasta."); } finally { setBusy(false); }
  }

  async function configureFolderDeadline(folder: Folder, event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    const accessDurationDays = Number(new FormData(event.currentTarget).get("access_duration_days"));
    setBusy(true);
    try {
      await requestJson(`/api/admin/photo-folders/${folder.id}/deadline`, {
        method: "PATCH", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ access_duration_days: accessDurationDays }),
      });
      setMessage(folder.released_at
        ? "Prazo configurado. A contagem começa agora."
        : "Prazo atualizado. A contagem começa quando você liberar a pasta.");
      await load(false);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível configurar o prazo da pasta.");
    } finally { setBusy(false); }
  }

  async function uploadPhotos(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = event.currentTarget; const data = new FormData(form); const folderId = String(data.get("folder") ?? ""); const input = form.elements.namedItem("jpeg") as HTMLInputElement; const files = Array.from(input.files ?? []);
    if (!folderId || !files.length || busy) return;
    setBusy(true); setUpload({ phase: "uploading", current: 0, total: files.length });
    let batch = openBatches.find((item) => item.id === resumeBatchId);
    let uploadFiles = files;
    let skippedDuplicates = 0;
    let duplicateIndexes = new Set<number>();
    try {
      const folderPhotos = await requestJson(`/api/admin/photo-folders/${folderId}/photos`) as {
        photos: Array<{ id: string; content_fingerprint?: string | null }>;
      };
      const resumedAssetIds = new Set((batch?.assets ?? []).map((asset) => asset.id));
      const existingFingerprints = folderPhotos.photos
        .filter((photo) => !resumedAssetIds.has(photo.id))
        .map((photo) => photo.content_fingerprint);
      const review = await confirmDuplicateJpegs(files, (file) => file, existingFingerprints);
      uploadFiles = review.items;
      skippedDuplicates = review.skippedCount;
      duplicateIndexes = new Set(review.confirmed ? review.duplicateIndexes : []);
      if (!uploadFiles.length) {
        setUpload({ phase: "success", current: files.length, total: files.length });
        setMessage(`${skippedDuplicates} foto(s) repetida(s) ignorada(s). Nenhuma foto nova para enviar.`);
        form.reset(); setBusy(false); return;
      }
      const activeBatch = batch ?? await requestJson(
        `/api/admin/derived-galleries/${galleryId}/upload-batches`, { method: "POST" },
      ) as UploadBatch;
      batch = activeBatch;
      setResumeBatchId(activeBatch.id);
      setOpenBatches((current) => current.some((item) => item.id === activeBatch.id)
        ? current : [...current, activeBatch]);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível iniciar o lote.");
      setBusy(false); setUpload({ phase: "error", current: 0, total: files.length }); return;
    }
    if (!batch) { setBusy(false); return; }
    const resumedAssetIds = new Set<string>();
    for (const [index, file] of uploadFiles.entries()) {
      setUpload({ phase: "uploading", current: index + 1, total: uploadFiles.length, filename: file.name });
      let photoId: string | null = null;
      try {
        const fingerprint = await jpegFingerprint(file);
        const storageKey = await jpegStorageKey(`private/${galleryId}`, folderId, file);
        const previous = resumeBatchId ? batch.assets.find((asset) =>
          !resumedAssetIds.has(asset.id) && asset.status === "not_imported" &&
          jpegFingerprintFromStorageKey(asset.upload_key ?? asset.storage_key) === fingerprint) : undefined;
        if (previous) resumedAssetIds.add(previous.id);
        if (previous && previous.status !== "not_imported") continue;
        const photo = previous ?? await requestJson(`/api/admin/photo-folders/${folderId}/photos`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ filename: file.name, storage_key: storageKey, upload_batch_id: batch.id, allow_duplicate_content: duplicateIndexes.has(index) }) });
        if ("duplicate" in photo && photo.duplicate === "true") continue;
        photoId = photo.id;
        creditUpload.startPhoto(photo.id, file.name);
        await uploadJpeg(`/api/admin/photo-assets/${photo.id}/source`, file, () => setMessage("Aguardando o processamento liberar espaço para continuar o envio."));
        await creditUpload.refreshPhoto(photo.id, file.name);
      } catch (error) {
        if (photoId) {
          void creditUpload.refreshPhoto(photoId, file.name, isDefinitiveUploadRejection(error));
        }
        setUpload({ phase: "error", current: index, total: files.length, filename: file.name }); setMessage(error instanceof Error ? error.message : `Falha ao enviar ${file.name}.`); setBusy(false); await load(false); return;
      }
    }
    try {
      await requestJson(`/api/admin/derived-galleries/${galleryId}/upload-batches/${batch.id}/close`, { method: "POST" });
      setResumeBatchId("");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível encerrar o lote. Retome abaixo.");
      setBusy(false); await load(false); return;
    }
    setUpload({ phase: "success", current: uploadFiles.length, total: uploadFiles.length }); setMessage(`${skippedDuplicates ? `${skippedDuplicates} repetida(s) ignorada(s). ` : ""}${uploadFiles.length} foto(s) enviada(s). As prévias e o reconhecimento serão atualizados automaticamente.`); form.reset(); setBusy(false); await load(false);
  }

  async function closePartialBatch(batch: UploadBatch) {
    setBusy(true);
    try {
      await requestJson(`/api/admin/derived-galleries/${galleryId}/upload-batches/${batch.id}/close`, { method: "POST" });
      if (resumeBatchId === batch.id) setResumeBatchId("");
      setMessage("Lote encerrado. O aviso considerará somente novas fotos disponíveis.");
      await load(false);
    } catch (error) { setMessage(error instanceof Error ? error.message : "Não foi possível encerrar o lote."); }
    finally { setBusy(false); }
  }

  async function publishFolder(folder: Folder) {
    if (busy || folder.status === "released") return;
    setBusy(true);
    try {
      await requestJson(`/api/admin/photo-folders/${folder.id}/publish`, { method: "POST" });
      setMessage(`Pasta “${folder.name}” liberada para a cliente.`);
      await load(false);
    } catch (error) { setMessage(error instanceof Error ? error.message : "Não foi possível liberar a pasta."); }
    finally { setBusy(false); }
  }

  async function renameFolder(folder: Folder) {
    if (busy) return;
    const proposedName = window.prompt("Novo nome da pasta", folder.name);
    if (proposedName === null) return;
    const name = proposedName.trim();
    if (!name) { setMessage("Informe um nome para a pasta."); return; }
    setBusy(true);
    try {
      await requestJson(`/api/admin/photo-folders/${folder.id}`, {
        method: "PATCH", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      setMessage("Nome da pasta atualizado.");
      await load(false);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível renomear a pasta.");
    } finally { setBusy(false); }
  }

  async function removeFolder(folder: Folder) {
    if (busy || !window.confirm(`Excluir a pasta “${folder.name}” e suas ${folder.photo_count} foto(s) desta galeria privada? Nomes das fotos, seleções e estados financeiros permanecem no histórico, sem imagens. Esta ação não pode ser desfeita.`)) return;
    setBusy(true);
    try {
      const result = await requestJson(`/api/admin/photo-folders/${folder.id}`, { method: "DELETE" });
      setFolders((current) => current.filter((item) => item.id !== folder.id));
      setPhotos((current) => current.filter((item) => item.folder_id !== folder.id));
      setMessage(result?.cleanup_pending ? "Pasta removida. A limpeza dos arquivos continuará em segundo plano." : "Pasta e fotos excluídas da galeria privada.");
      await load(false);
    } catch (error) { setMessage(error instanceof Error ? error.message : "Não foi possível excluir a pasta."); }
    finally { setBusy(false); }
  }

  async function removePhoto(photo: PrivatePhoto) {
    if (!window.confirm(`Excluir ${photo.name} desta galeria privada?`)) return; setBusy(true);
    try { await requestJson(photo.ownership === "private" ? `/api/admin/photo-folders/${photo.folder_id}/photos/${photo.id}` : `/api/admin/derived-galleries/${galleryId}/photos/${photo.id}`, { method: "DELETE" }); setMessage("Foto removida da galeria privada sem afetar outras galerias."); await load(false); }
    catch (error) { setMessage(error instanceof Error ? error.message : "Não foi possível remover a foto."); } finally { setBusy(false); }
  }

  async function toggle() { if (!detail || !window.confirm(detail.blocked ? "Liberar o acesso desta galeria privada?" : "Bloquear o acesso desta galeria privada para todos os membros?")) return; setBusy(true); try { await requestJson(`/api/admin/derived-galleries/${galleryId}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ access_enabled: detail.blocked }) }); await load(false); } finally { setBusy(false); } }
  async function saveName(event: FormEvent<HTMLFormElement>) { event.preventDefault(); const data = new FormData(event.currentTarget); setBusy(true); try { await requestJson(`/api/admin/derived-galleries/${galleryId}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: data.get("name") }) }); setMessage("Nome salvo."); await load(false); } finally { setBusy(false); } }
  async function removeGallery() { setBusy(true); setDeleteError(""); try { await requestJson(`/api/admin/derived-galleries/${galleryId}`, { method: "DELETE" }); router.push("/admin/galleries"); } catch (error) { setDeleteError(error instanceof Error ? error.message : "Não foi possível excluir a galeria."); setBusy(false); } }

  if (loading) return <SystemState tone="loading" title="Carregando galeria privada" detail="Consultando acervo, clientes e processamento." />;
  if (failed || !detail) return <SystemState tone="error" title="Galeria indisponível" detail="Não foi possível carregar os dados desta galeria." />;
  const facialPercent = facial?.progress?.total ? Math.round(facial.progress.ready * 100 / facial.progress.total) : 0;
  return <div className={`${catalogStyles.catalog} private-gallery-detail ${styles.detail}`}>
    <Link className={styles.back} href="/admin/galleries"><span aria-hidden="true">←</span> Galerias</Link>
    <PageHeading
      eyebrow="Galeria privada"
      title={detail.name}
      detail="Seleções feitas pela cliente na Galeria pública e JPEGs exclusivos enviados para esta galeria."
      actions={<>
        <MarkinaLink href={`/admin/galleries/${galleryId}/orders`} variant="secondary">Pedidos da galeria</MarkinaLink>
        <MarkinaLink href="#private-gallery-content">Revisar acervo</MarkinaLink>
      </>}
    />
    <div className={styles.access}>
      <div><strong>Acesso à galeria</strong><StatusBadge tone={detail.blocked ? "dark" : detail.frozen ? "warning" : "success"}>{detail.blocked ? "Acesso bloqueado" : detail.frozen ? "Prazo expirado" : "Ativa"}</StatusBadge></div>
      <div><MarkinaButton variant="secondary" disabled={busy} onClick={toggle}>{detail.blocked ? "Liberar acesso geral" : "Bloquear acesso geral"}</MarkinaButton><Link className="mk-button mk-button--secondary" href="/admin/payments">Vendas e pagamentos</Link></div>
    </div>
    <section className={catalogStyles.metrics} aria-label="Resumo do acervo privado">
      <MetricCard label="Membros vinculados" value={members.length} detail="com vínculo na galeria" icon={<OverviewIcon name="group" />} />
      <MetricCard label="Seleções de origem" value={photos.filter((photo) => photo.ownership === "public_reference").length} detail="vindas da Galeria pública" icon={<OverviewIcon name="public" />} />
      <MetricCard label="JPEGs exclusivos" value={photos.filter((photo) => photo.ownership === "private").length} detail="enviados a esta galeria" icon={<OverviewIcon name="photo_camera" />} />
    </section>
    <MarkinaLink className={styles.back} href={`/admin/galleries/${galleryId}/pricing`} variant="quiet">Consultar condições comerciais herdadas</MarkinaLink>
    {detail.origin_active === false ? <SystemState title="Galeria pública de origem removida" detail="A privada, suas seleções e o histórico continuam preservados. Novos uploads exclusivos ainda podem ser gerenciados aqui." /> : null}

    <section className="admin-card"><div className="section-heading"><div><p className="eyebrow">Processamento automático</p><h2>Reconhecimento facial</h2></div><StatusBadge tone={facial?.state === "completed" ? "success" : facial?.failed ? "danger" : "warning"}>{facial?.state === "completed" ? "Concluído" : facial?.failed ? "Com falhas" : "Em andamento"}</StatusBadge></div><progress max={100} value={facialPercent}>{facialPercent}%</progress><p><strong>{facial?.progress?.ready ?? 0} de {facial?.progress?.total ?? 0} fotos prontas</strong> · {facialPercent}% processado</p><p>{facial?.coverage?.photos_with_faces ?? 0} fotos com rosto · {facial?.coverage?.percent ?? 0}% de cobertura · {facial?.coverage?.detected_faces ?? 0} rostos detectados.</p>{facial?.failed ? <p className="form-message form-message--error">{facial.failed} falha(s) aguardam retentativa operacional.</p> : null}</section>

    <section className="admin-card private-gallery-members"><div className="section-heading"><div><h2>Clientes desta galeria</h2><p>Os números são calculados pela mesma projeção usada na Galeria pública e em Vendas e pagamentos.</p></div><StatusBadge>{members.length} cliente(s)</StatusBadge></div>{members.length ? <div className="private-member-cards">{members.map((member) => <article key={member.membership_id}><header><div><strong>{member.client_name}</strong><small>{member.phone_e164 ?? "Telefone indisponível"}</small></div><StatusBadge tone={member.status === "active" ? "success" : "dark"}>{member.status}</StatusBadge></header><dl><div><dt>Fotos no acervo privado</dt><dd>{member.available_count ?? photos.length}</dd></div><div><dt>Selecionadas e não compradas</dt><dd>{member.selected_count}</dd></div><div><dt>Fotos compradas</dt><dd>{member.purchased_count}</dd></div><div><dt>Pedidos</dt><dd>{member.order_count}</dd></div><div><dt>Total confirmado</dt><dd>{formatBrazilianCurrency(member.confirmed_total_cents)}</dd></div></dl><p><strong>Situação:</strong> {member.commercial_status ?? member.payment_status}{member.reopening_status ? ` · reabertura ${member.reopening_status}` : ""}</p>{member.purchased_count > 0 || member.financial_orders?.some((order) => order.status === "confirmed") ? <a className="mk-button mk-button--secondary" href={`/api/admin/derived-galleries/${galleryId}/selection/export.html?client_id=${encodeURIComponent(member.client_id)}`} onClick={applyPurchasedPhotoExportTheme}>Baixar seleção individual</a> : <span>Disponível após a primeira compra confirmada.</span>}<FinancialOrderShortcuts orders={member.financial_orders} clientName={member.client_name} onRefresh={() => load(false)} /></article>)}</div> : <SystemState title="Nenhuma cliente vinculada" detail="Adicione membros pela etapa Clientes da Galeria pública." />}</section>

    <div id="private-gallery-content" className={styles.content} tabIndex={-1}>
    {photos.some((photo) => photo.ownership === "public_reference") ? <section className="admin-card"><div className="section-heading"><div><h2>Seleções vindas da Galeria pública</h2><p>Estas fotos entram automaticamente quando a cliente as seleciona. O fotógrafo não as adiciona manualmente por esta tela.</p></div><StatusBadge>{photos.filter((photo) => photo.ownership === "public_reference").length} foto(s)</StatusBadge></div><div className="private-photo-grid">{photos.filter((photo) => photo.ownership === "public_reference").map((photo) => <figure key={photo.id}><img src={`/api${photo.preview_url}`} alt={`Prévia protegida de ${photo.name}`} loading="lazy" decoding="async" /><figcaption><strong>{photo.name}</strong><small>{photo.folder_name}</small><AdminPhotoInteractions photo={photo} /></figcaption></figure>)}</div></section> : null}
    <section className="admin-card"><div className="section-heading"><div><h2>Uploads próprios da galeria privada</h2><p>Crie uma pasta e carregue novos JPEGs do dispositivo. Nenhuma foto pública pode ser adicionada manualmente aqui.</p></div></div><form className="auth-form" onSubmit={createFolder}><label>Nome da nova pasta<input name="name" maxLength={200} required /></label><FolderDeadlineFields mode="creation" startsAt="release" /><MarkinaButton disabled={busy}>Criar pasta</MarkinaButton></form>{folders.length ? <><form className="auth-form" onSubmit={uploadPhotos}><label>Pasta<select name="folder" required defaultValue=""><option value="" disabled>Escolha a pasta</option>{folders.map((folder) => <option value={folder.id} key={folder.id}>{folder.name}</option>)}</select></label><label>JPEGs do dispositivo<input name="jpeg" type="file" accept="image/jpeg,.jpg,.jpeg" multiple required /></label><MarkinaButton disabled={busy}>{upload.phase === "uploading" ? `Enviando ${upload.current} de ${upload.total}…` : "Carregar fotos"}</MarkinaButton></form>{upload.phase !== "idle" ? <p className={upload.phase === "error" ? "form-message form-message--error" : "form-message"} role="status">{upload.phase === "uploading" ? `${Math.round(upload.current * 100 / upload.total)}% · ${upload.filename ?? ""}` : upload.phase === "success" ? "Upload concluído; processamento em segundo plano iniciado." : `Falha em ${upload.filename ?? "um arquivo"}.`}</p> : null}<CreditUploadFeedback wallet={creditUpload.wallet} walletState={creditUpload.walletState} items={creditUpload.items} visible={upload.phase === "uploading"} onVerifyPending={creditUpload.verifyPending} /><div className="private-folder-list">{folders.map((folder) => <article key={folder.id}><header><strong>{folder.name}</strong><StatusBadge>{folder.photo_count} foto(s)</StatusBadge><StatusBadge tone={folder.status === "released" ? "success" : "warning"}>{folder.status === "released" ? "Liberada" : "Em preparação"}</StatusBadge>{folder.status !== "released" ? <MarkinaButton type="button" variant="secondary" disabled={busy} onClick={() => publishFolder(folder)}>Liberar para cliente</MarkinaButton> : null}<MarkinaButton type="button" variant="quiet" disabled={busy} onClick={() => { void renameFolder(folder); }}>Renomear pasta</MarkinaButton><MarkinaButton type="button" variant="quiet" disabled={busy} onClick={() => removeFolder(folder)} aria-label={`Excluir pasta ${folder.name}`}>Excluir pasta</MarkinaButton></header><p>{folder.access_expires_at ? `Acesso até ${new Date(folder.access_expires_at).toLocaleString("pt-BR")}` : folder.access_duration_days ? `${folder.access_duration_days} dias após liberação` : "Prazo indeterminado"}</p>{folder.status !== "released" || (!folder.access_duration_days && !folder.access_expires_at) ? <form className="auth-form" onSubmit={(event) => { void configureFolderDeadline(folder, event); }}><FolderDeadlineFields mode="existing" startsAt={folder.released_at ? "save" : "release"} initialDays={folder.released_at ? null : folder.access_duration_days} /><MarkinaButton disabled={busy}>{folder.released_at ? "Definir prazo" : "Salvar prazo"}</MarkinaButton></form> : null}{(photosByFolder.get(folder.id) ?? []).length ? <div className="private-photo-grid">{(photosByFolder.get(folder.id) ?? []).map((photo) => <figure key={photo.id}><img src={`/api${photo.preview_url}`} alt={`Prévia protegida de ${photo.name}`} loading="lazy" decoding="async" /><figcaption><strong>{photo.name}</strong><small>Upload exclusivo</small><AdminPhotoInteractions photo={photo} /><MarkinaButton type="button" variant="quiet" disabled={busy} onClick={() => removePhoto(photo)}>Remover</MarkinaButton></figcaption></figure>)}</div> : <p>Pasta vazia.</p>}</article>)}</div></> : <SystemState title="Crie a primeira pasta" detail="Depois, selecione-a para carregar JPEGs diretamente do dispositivo." />}</section>

    </div>

    <section className="admin-card"><h2>Ajustes da galeria privada</h2><form className="auth-form" onSubmit={saveName}><label>Nome<input name="name" defaultValue={detail.name} required /></label><MarkinaButton disabled={busy}>Salvar nome</MarkinaButton></form><label>Exibição das pastas (herdada da Galeria pública)<select aria-label="Exibição das pastas herdada" value={detail.inherited_folder_display_mode ?? "individual"} disabled><option value="individual">Pastas lado a lado</option><option value="sequential">Sequência cronológica</option></select></label><p>Preços, regras comerciais e organização seguem a Galeria pública. O prazo de acesso é definido separadamente para cada pasta. O PIX fica em Configurações; as mensagens da sua conta, em Notificações.</p><MarkinaButton variant="quiet" className="mk-button--danger" disabled={busy} onClick={() => setDeleteConfirmOpen(true)}>Excluir galeria privada</MarkinaButton></section>
    {deleteConfirmOpen ? <div className="mk-dialog-backdrop" role="presentation"><section aria-labelledby="delete-private-title" aria-modal="true" className="mk-dialog" role="dialog"><h2 id="delete-private-title">Excluir “{detail.name}”?</h2><p>O cadastro e o histórico comercial serão preservados. Pastas, fotos e prévias próprias serão removidas. Fotos compartilhadas da origem permanecem; nomes, movimentos e estados financeiros ficam no histórico.</p>{deleteError ? <p className="form-message form-message--error" role="alert">{deleteError}</p> : null}<div className="mk-dialog__actions"><MarkinaButton variant="secondary" disabled={busy} onClick={() => { setDeleteConfirmOpen(false); setDeleteError(""); }}>Cancelar</MarkinaButton><MarkinaButton className="mk-button--danger" disabled={busy} onClick={removeGallery}>{busy ? "Excluindo…" : "Confirmar exclusão"}</MarkinaButton></div></section></div> : null}
    {openBatches.length ? <section className="admin-card" aria-label="Uploads interrompidos"><h2>Lotes ainda abertos</h2><p>Retome selecionando os mesmos arquivos ou encerre com as fotos já enviadas.</p>{openBatches.map((batch) => <article key={batch.id}><p>{batch.count} foto(s) registradas · lote {batch.id.slice(0, 8)}</p><MarkinaButton type="button" variant="secondary" disabled={busy} onClick={() => { setResumeBatchId(batch.id); setMessage("Lote selecionado. Escolha a pasta e os arquivos para retomar o upload."); }}>{resumeBatchId === batch.id ? "Selecionado para retomar" : "Retomar lote"}</MarkinaButton><MarkinaButton type="button" variant="quiet" disabled={busy} onClick={() => closePartialBatch(batch)}>Encerrar com as fotos enviadas</MarkinaButton></article>)}</section> : null}
    {message ? <p className="form-message" role="status">{message}</p> : null}
  </div>;
}
