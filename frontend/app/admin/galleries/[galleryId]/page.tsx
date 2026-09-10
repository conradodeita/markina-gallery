"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { MarkinaButton, StatusBadge, SystemState } from "../../../ui-kit";
import { formatBrazilianCurrency } from "../pricing-rules";

type Detail = { id: string; parent_gallery_id: string; name: string; custom_message: string; selection_expires_at: string | null; origin_active?: boolean; frozen: boolean; blocked: boolean };
type PrivatePhoto = { id: string; name: string; folder_id: string; folder_name: string; preview_url: string; ownership: "private" | "public_reference" };
type Folder = { id: string; name: string; status: string; photo_count: number };
type Member = { membership_id: string; client_id: string; client_name: string; phone_e164: string | null; status: "active" | "blocked" | "unlinked"; available_count?: number; selected_count: number; purchased_count: number; order_count: number; confirmed_total_cents: number; commercial_status?: string; payment_status?: string; reopening_status: string | null };
type Facial = { state: string; progress: { ready: number; total: number }; queued: number; processing: number; failed: number; coverage: { photos_with_faces: number; total: number; percent: number; detected_faces: number } };
type UploadState = { phase: "idle" | "uploading" | "success" | "error"; current: number; total: number; filename?: string };

async function requestJson(path: string, init?: RequestInit) {
  const response = await fetch(path, { credentials: "same-origin", ...init });
  const payload = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) throw new Error(payload?.detail ?? "Não foi possível concluir a operação.");
  return payload;
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
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [deleteError, setDeleteError] = useState("");

  const load = useCallback(async (showLoading = true) => {
    if (showLoading) setLoading(true);
    try {
      const [detailData, photoData, folderData, memberData, facialData] = await Promise.all([
        requestJson(`/api/admin/derived-galleries/${galleryId}`), requestJson(`/api/admin/derived-galleries/${galleryId}/photos`),
        requestJson(`/api/admin/derived-galleries/${galleryId}/folders`), requestJson(`/api/admin/derived-galleries/${galleryId}/members`),
        requestJson(`/api/admin/derived-galleries/${galleryId}/facial-index`),
      ]);
      const loadedPhotos = photoData.photos ?? [];
      const inferredFolders = [...new Map(loadedPhotos.filter((photo: PrivatePhoto) => photo.ownership === "private").map((photo: PrivatePhoto) => [photo.folder_id, { id: photo.folder_id, name: photo.folder_name, status: "released", photo_count: loadedPhotos.filter((item: PrivatePhoto) => item.folder_id === photo.folder_id).length }])).values()];
      setDetail(detailData); setPhotos(loadedPhotos); setFolders(folderData.folders ?? inferredFolders); setMembers(memberData.members ?? []); setFacial(facialData?.progress ? facialData : null); setFailed(false);
    } catch { setFailed(true); } finally { if (showLoading) setLoading(false); }
  }, [galleryId]);

  useEffect(() => { queueMicrotask(() => load()); }, [load]);
  useEffect(() => { const refresh = () => void load(false); window.addEventListener("focus", refresh); return () => window.removeEventListener("focus", refresh); }, [load]);
  useEffect(() => { if (!facial || !["waiting", "processing"].includes(facial.state)) return; const timer = window.setTimeout(() => void load(false), 1800); return () => window.clearTimeout(timer); }, [facial, load]);
  const photosByFolder = useMemo(() => new Map(folders.map((folder) => [folder.id, photos.filter((photo) => photo.folder_id === folder.id)])), [folders, photos]);

  async function createFolder(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = event.currentTarget; const data = new FormData(form); setBusy(true);
    try { await requestJson(`/api/admin/derived-galleries/${galleryId}/folders`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: data.get("name") }) }); form.reset(); setMessage("Pasta privada criada."); await load(false); }
    catch (error) { setMessage(error instanceof Error ? error.message : "Não foi possível criar a pasta."); } finally { setBusy(false); }
  }

  async function uploadPhotos(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = event.currentTarget; const data = new FormData(form); const folderId = String(data.get("folder") ?? ""); const input = form.elements.namedItem("jpeg") as HTMLInputElement; const files = Array.from(input.files ?? []);
    if (!folderId || !files.length || busy) return;
    setBusy(true); setUpload({ phase: "uploading", current: 0, total: files.length });
    for (const [index, file] of files.entries()) {
      setUpload({ phase: "uploading", current: index + 1, total: files.length, filename: file.name });
      try {
        const safeName = file.name.replace(/[^a-zA-Z0-9._-]/g, "-");
        const photo = await requestJson(`/api/admin/photo-folders/${folderId}/photos`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ filename: file.name, storage_key: `private/${galleryId}/${folderId}/${Date.now()}-${index}-${safeName}` }) });
        await requestJson(`/api/admin/photo-assets/${photo.id}/source`, { method: "PUT", headers: { "Content-Type": "image/jpeg" }, body: file });
      } catch (error) { setUpload({ phase: "error", current: index, total: files.length, filename: file.name }); setMessage(error instanceof Error ? error.message : `Falha ao enviar ${file.name}.`); setBusy(false); return; }
    }
    await requestJson(`/api/admin/photo-folders/${folderId}/publish`, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
    setUpload({ phase: "success", current: files.length, total: files.length }); setMessage(`${files.length} foto(s) enviada(s). As prévias e o reconhecimento serão atualizados automaticamente.`); form.reset(); setBusy(false); await load(false);
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
  return <main className="admin-shell private-gallery-detail">
    <Link href="/admin/galleries">← Galerias</Link>
    <div className="gallery-editor-heading"><div><p className="eyebrow">Galeria privada · acervo da cliente</p><h1>{detail.name}</h1><p className="intro">O acervo combina as seleções feitas pela cliente na Galeria pública com novos uploads exclusivos feitos diretamente nesta privada. O admin não escolhe manualmente fotos já existentes na pública.</p></div><StatusBadge tone={detail.blocked ? "dark" : detail.frozen ? "warning" : "success"}>{detail.blocked ? "Acesso bloqueado" : detail.frozen ? "Prazo expirado" : "Ativa"}</StatusBadge></div>
    <div className="action-grid"><MarkinaButton variant="secondary" disabled={busy} onClick={toggle}>{detail.blocked ? "Liberar acesso geral" : "Bloquear acesso geral"}</MarkinaButton><Link className="mk-button mk-button--secondary" href="/admin/payments">Vendas e pagamentos</Link><MarkinaButton className="mk-button--danger" disabled={busy} onClick={() => setDeleteConfirmOpen(true)}>Excluir galeria privada</MarkinaButton></div>
    {detail.origin_active === false ? <SystemState title="Galeria pública de origem removida" detail="A privada, suas seleções e o histórico continuam preservados. Novos uploads exclusivos ainda podem ser gerenciados aqui." /> : null}

    <section className="admin-card"><div className="section-heading"><div><p className="eyebrow">Processamento automático</p><h2>Reconhecimento facial</h2></div><StatusBadge tone={facial?.state === "completed" ? "success" : facial?.failed ? "danger" : "warning"}>{facial?.state === "completed" ? "Concluído" : facial?.failed ? "Com falhas" : "Em andamento"}</StatusBadge></div><progress max={100} value={facialPercent}>{facialPercent}%</progress><p><strong>{facial?.progress?.ready ?? 0} de {facial?.progress?.total ?? 0} fotos prontas</strong> · {facialPercent}% processado</p><p>{facial?.coverage?.photos_with_faces ?? 0} fotos com rosto · {facial?.coverage?.percent ?? 0}% de cobertura · {facial?.coverage?.detected_faces ?? 0} rostos detectados.</p>{facial?.failed ? <p className="form-message form-message--error">{facial.failed} falha(s) aguardam retentativa operacional.</p> : null}</section>

    <section className="admin-card private-gallery-members"><div className="section-heading"><div><h2>Clientes desta galeria</h2><p>Os números são calculados pela mesma projeção usada na Galeria pública e em Vendas e pagamentos.</p></div><StatusBadge>{members.length} cliente(s)</StatusBadge></div>{members.length ? <div className="private-member-cards">{members.map((member) => <article key={member.membership_id}><header><div><strong>{member.client_name}</strong><small>{member.phone_e164 ?? "Telefone indisponível"}</small></div><StatusBadge tone={member.status === "active" ? "success" : "dark"}>{member.status}</StatusBadge></header><dl><div><dt>Fotos no acervo privado</dt><dd>{member.available_count ?? photos.length}</dd></div><div><dt>Fotos selecionadas</dt><dd>{member.selected_count}</dd></div><div><dt>Fotos compradas</dt><dd>{member.purchased_count}</dd></div><div><dt>Pedidos</dt><dd>{member.order_count}</dd></div><div><dt>Total confirmado</dt><dd>{formatBrazilianCurrency(member.confirmed_total_cents)}</dd></div></dl><p><strong>Situação:</strong> {member.commercial_status ?? member.payment_status}{member.reopening_status ? ` · reabertura ${member.reopening_status}` : ""}</p><Link className="mk-button mk-button--secondary" href={`/admin/galleries/${galleryId}/selection?client=${member.client_id}`}>Abrir seleção individual</Link></article>)}</div> : <SystemState title="Nenhuma cliente vinculada" detail="Adicione membros pela etapa Clientes da Galeria pública." />}</section>

    {photos.some((photo) => photo.ownership === "public_reference") ? <section className="admin-card"><div className="section-heading"><div><h2>Seleções vindas da Galeria pública</h2><p>Estas fotos entram automaticamente quando a cliente as seleciona. O fotógrafo não as adiciona manualmente por esta tela.</p></div><StatusBadge>{photos.filter((photo) => photo.ownership === "public_reference").length} foto(s)</StatusBadge></div><div className="private-photo-grid">{photos.filter((photo) => photo.ownership === "public_reference").map((photo) => <figure key={photo.id}><img src={`/api${photo.preview_url}`} alt={`Prévia protegida de ${photo.name}`} /><figcaption><strong>{photo.name}</strong><small>{photo.folder_name}</small></figcaption></figure>)}</div></section> : null}
    <section className="admin-card"><div className="section-heading"><div><h2>Uploads próprios da galeria privada</h2><p>Crie uma pasta e carregue novos JPEGs do dispositivo. Nenhuma foto pública pode ser adicionada manualmente aqui.</p></div></div><form className="auth-form" onSubmit={createFolder}><label>Nome da nova pasta<input name="name" maxLength={200} required /></label><MarkinaButton disabled={busy}>Criar pasta</MarkinaButton></form>{folders.length ? <><form className="auth-form" onSubmit={uploadPhotos}><label>Pasta<select name="folder" required defaultValue=""><option value="" disabled>Escolha a pasta</option>{folders.map((folder) => <option value={folder.id} key={folder.id}>{folder.name}</option>)}</select></label><label>JPEGs do dispositivo<input name="jpeg" type="file" accept="image/jpeg,.jpg,.jpeg" multiple required /></label><MarkinaButton disabled={busy}>{upload.phase === "uploading" ? `Enviando ${upload.current} de ${upload.total}…` : "Carregar fotos"}</MarkinaButton></form>{upload.phase !== "idle" ? <p className={upload.phase === "error" ? "form-message form-message--error" : "form-message"} role="status">{upload.phase === "uploading" ? `${Math.round(upload.current * 100 / upload.total)}% · ${upload.filename ?? ""}` : upload.phase === "success" ? "Upload concluído; processamento em segundo plano iniciado." : `Falha em ${upload.filename ?? "um arquivo"}.`}</p> : null}<div className="private-folder-list">{folders.map((folder) => <article key={folder.id}><header><strong>{folder.name}</strong><StatusBadge>{folder.photo_count} foto(s)</StatusBadge></header>{(photosByFolder.get(folder.id) ?? []).length ? <div className="private-photo-grid">{(photosByFolder.get(folder.id) ?? []).map((photo) => <figure key={photo.id}><img src={`/api${photo.preview_url}`} alt={`Prévia protegida de ${photo.name}`} /><figcaption><strong>{photo.name}</strong><small>Upload exclusivo</small><MarkinaButton type="button" variant="quiet" disabled={busy} onClick={() => removePhoto(photo)}>Remover</MarkinaButton></figcaption></figure>)}</div> : <p>Pasta vazia.</p>}</article>)}</div></> : <SystemState title="Crie a primeira pasta" detail="Depois, selecione-a para carregar JPEGs diretamente do dispositivo." />}</section>

    <section className="admin-card"><h2>Ajustes da galeria privada</h2><form className="auth-form" onSubmit={saveName}><label>Nome<input name="name" defaultValue={detail.name} required /></label><MarkinaButton disabled={busy}>Salvar nome</MarkinaButton></form><p>Preço, prazo e regras comerciais são herdados da Galeria pública. O PIX e a mensagem global ficam em Configurações e Vendas e pagamentos.</p></section>
    {deleteConfirmOpen ? <div className="mk-dialog-backdrop" role="presentation"><section aria-labelledby="delete-private-title" aria-modal="true" className="mk-dialog" role="dialog"><h2 id="delete-private-title">Excluir “{detail.name}”?</h2><p>O cadastro e o histórico comercial serão preservados. Mídia exclusiva exige as proteções de exclusão vigentes.</p>{deleteError ? <p className="form-message form-message--error" role="alert">{deleteError}</p> : null}<div className="mk-dialog__actions"><MarkinaButton variant="secondary" disabled={busy} onClick={() => { setDeleteConfirmOpen(false); setDeleteError(""); }}>Cancelar</MarkinaButton><MarkinaButton className="mk-button--danger" disabled={busy} onClick={removeGallery}>{busy ? "Excluindo…" : "Confirmar exclusão"}</MarkinaButton></div></section></div> : null}
    {message ? <p className="form-message" role="status">{message}</p> : null}
  </main>;
}
