"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { MarkinaButton, StatusBadge, SystemState } from "../../../ui-kit";
import { formatBrazilianCurrency } from "../pricing-rules";

type Detail = {
  id: string;
  parent_gallery_id: string;
  name: string;
  custom_message: string;
  favorites_enabled: boolean;
  comments_enabled: boolean;
  selection_expires_at: string | null;
  cover_preview_url: string | null;
  frozen: boolean;
  blocked: boolean;
};
type PrivatePhoto = { id: string; name: string; folder_id: string; folder_name: string; preview_url: string; origins: Array<"admin" | "client" | "facial"> };
type AvailablePhoto = { id: string; name: string; folder_name: string; preview_url: string | null };
type Member = { membership_id: string; client_id: string; client_name: string; phone_e164: string | null; status: "active" | "blocked" | "unlinked"; selected_count: number; purchased_count: number; order_count: number; confirmed_total_cents: number; payment_status: "none" | "pending" | "confirmed" };

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
  const [availablePhotos, setAvailablePhotos] = useState<AvailablePhoto[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const [selectedPhotoIds, setSelectedPhotoIds] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [deleteError, setDeleteError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const detailData = await requestJson(`/api/admin/derived-galleries/${galleryId}`) as Detail;
      const [photoData, memberData, availableData] = await Promise.all([
        requestJson(`/api/admin/derived-galleries/${galleryId}/photos`),
        requestJson(`/api/admin/derived-galleries/${galleryId}/members`),
        requestJson(`/api/admin/parent-galleries/${detailData.parent_gallery_id}/available-photos`),
      ]);
      setDetail(detailData);
      setPhotos(photoData.photos ?? []);
      setMembers(memberData.members ?? []);
      setAvailablePhotos(availableData.photos ?? []);
      setFailed(false);
    } catch {
      setDetail(null);
      setFailed(true);
    } finally {
      setLoading(false);
    }
  }, [galleryId]);

  useEffect(() => { queueMicrotask(load); }, [load]);

  const folders = useMemo(() => Object.values(photos.reduce<Record<string, { id: string; name: string; photos: PrivatePhoto[] }>>((grouped, photo) => {
    grouped[photo.folder_id] ??= { id: photo.folder_id, name: photo.folder_name, photos: [] };
    grouped[photo.folder_id].photos.push(photo);
    return grouped;
  }, {})), [photos]);
  const addablePhotos = availablePhotos.filter((photo) => !photos.some((privatePhoto) => privatePhoto.id === photo.id));

  async function toggle() {
    if (!detail || !window.confirm(detail.blocked ? "Liberar o acesso desta galeria privada?" : "Bloquear o acesso desta galeria privada para todos os membros?")) return;
    setBusy(true);
    try {
      await requestJson(`/api/admin/derived-galleries/${galleryId}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ access_enabled: detail.blocked }) });
      setMessage("Acesso geral atualizado.");
      await load();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível atualizar o acesso.");
    } finally { setBusy(false); }
  }

  async function removeGallery() {
    if (busy) return;
    setBusy(true);
    setDeleteError("");
    try {
      await requestJson(`/api/admin/derived-galleries/${galleryId}`, { method: "DELETE" });
      router.push("/admin/galleries");
    } catch (error) {
      setDeleteError(error instanceof Error ? error.message : "Não foi possível excluir a galeria privada.");
    } finally { setBusy(false); }
  }

  async function saveName(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setBusy(true);
    try {
      await requestJson(`/api/admin/derived-galleries/${galleryId}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: data.get("name") }) });
      setMessage("Nome salvo.");
      await load();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível salvar o nome.");
    } finally { setBusy(false); }
  }

  async function addPhotos(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedPhotoIds.length || busy) return;
    setBusy(true);
    try {
      await requestJson(`/api/admin/derived-galleries/${galleryId}/photos`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ photo_ids: selectedPhotoIds }) });
      setSelectedPhotoIds([]);
      setMessage("Fotos adicionadas ao acervo privado sem criar seleção para nenhuma cliente.");
      await load();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível adicionar as fotos.");
    } finally { setBusy(false); }
  }

  async function removePhoto(photo: PrivatePhoto) {
    if (!window.confirm(`Remover ${photo.name} da inclusão administrativa desta privada?`)) return;
    setBusy(true);
    try {
      const result = await requestJson(`/api/admin/derived-galleries/${galleryId}/photos/${photo.id}`, { method: "DELETE" });
      setMessage(result.reference_removed ? "Foto removida da privada; o arquivo original permanece na Galeria pública." : "Inclusão administrativa removida, mas a foto permanece porque existe seleção de cliente ou outra origem autorizada.");
      await load();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível remover a foto.");
    } finally { setBusy(false); }
  }

  if (loading) return <SystemState tone="loading" title="Carregando galeria privada" detail="Consultando acervo comum e dados individuais das clientes." />;
  if (failed || !detail) return <SystemState tone="error" title="Galeria indisponível" detail="Não foi possível carregar os dados desta galeria." />;

  return <main className="admin-shell private-gallery-detail">
    <Link href="/admin/galleries">← Galerias</Link>
    <div className="gallery-editor-heading"><div><p className="eyebrow">Galeria privada · acervo compartilhado</p><h1>{detail.name}</h1><p className="intro">Todos os membros veem as mesmas fotos disponíveis; seleções, pedidos e pagamentos continuam individuais.</p></div><StatusBadge tone={detail.blocked ? "dark" : detail.frozen ? "warning" : "success"}>{detail.blocked ? "Acesso bloqueado" : detail.frozen ? "Prazo expirado" : "Ativa"}</StatusBadge></div>
    <div className="action-grid"><MarkinaButton variant="secondary" disabled={busy} onClick={toggle}>{detail.blocked ? "Liberar acesso geral" : "Bloquear acesso geral"}</MarkinaButton><Link className="mk-button mk-button--secondary" href={`/admin/galleries/sources/${detail.parent_gallery_id}/edit/vendas`}>Preço, PIX e regras herdadas</Link><Link className="mk-button mk-button--secondary" href={`/admin/galleries/${galleryId}/orders`}>Pedidos</Link><MarkinaButton className="mk-button--danger" disabled={busy} onClick={() => { setDeleteConfirmOpen(true); setDeleteError(""); }}>Excluir galeria privada</MarkinaButton></div>

    <section className="admin-card private-gallery-members"><div className="section-heading"><div><h2>Clientes desta galeria</h2><p className="gallery-scope-note">Os números abaixo nunca são somados entre membros.</p></div><StatusBadge>{members.length} cliente(s)</StatusBadge></div>{members.length ? <div className="private-member-cards">{members.map((member) => <article key={member.membership_id}><header><div><strong>{member.client_name}</strong><small>{member.phone_e164 ?? "Telefone indisponível"}</small></div><StatusBadge tone={member.status === "active" ? "success" : member.status === "blocked" ? "dark" : "neutral"}>{member.status === "active" ? "Ativa" : member.status === "blocked" ? "Bloqueada" : "Desvinculada"}</StatusBadge></header><dl><div><dt>Selecionadas</dt><dd>{member.selected_count}</dd></div><div><dt>Compradas</dt><dd>{member.purchased_count}</dd></div><div><dt>Pedidos</dt><dd>{member.order_count}</dd></div><div><dt>Total confirmado</dt><dd>{formatBrazilianCurrency(member.confirmed_total_cents)}</dd></div></dl><Link className="mk-button mk-button--secondary" href={`/admin/galleries/${galleryId}/selection?client=${member.client_id}`}>Abrir seleção individual</Link></article>)}</div> : <SystemState title="Nenhuma cliente vinculada" detail="Adicione membros pela etapa Clientes da Galeria pública." />}</section>

    <section className="admin-card"><div className="section-heading"><div><h2>Pastas e fotos disponíveis</h2><p className="gallery-scope-note">Remover daqui nunca apaga o JPEG original da Galeria pública e respeita outras justificativas ativas.</p></div><Link className="mk-button mk-button--secondary" href={`/admin/galleries/sources/${detail.parent_gallery_id}/edit/imagens`}>Carregar novos JPEGs na pública</Link></div>{folders.length ? <div className="private-folder-list">{folders.map((folder) => <article key={folder.id}><header><strong>{folder.name}</strong><StatusBadge>{folder.photos.length} foto(s)</StatusBadge></header><div className="private-photo-grid">{folder.photos.map((photo) => <figure key={photo.id}><img src={`/api${photo.preview_url}`} alt={`Prévia protegida de ${photo.name}`} /><figcaption><strong>{photo.name}</strong><small>{photo.origins.includes("client") ? "Mantida por seleção" : "Incluída pelo fotógrafo"}</small><MarkinaButton type="button" variant="quiet" disabled={busy || !photo.origins.includes("admin")} onClick={() => removePhoto(photo)}>{photo.origins.includes("admin") ? "Remover inclusão" : "Seleção de cliente"}</MarkinaButton></figcaption></figure>)}</div></article>)}</div> : <SystemState title="Galeria privada sem fotos" detail="Adicione fotos publicadas da origem no bloco abaixo." />}</section>

    <section className="admin-card"><div className="section-heading"><div><h2>Adicionar fotos da Galeria pública</h2><p className="gallery-scope-note">A ação cria apenas referências no acervo comum e não marca fotos como selecionadas.</p></div></div>{addablePhotos.length ? <form className="private-photo-add" onSubmit={addPhotos}><div>{addablePhotos.map((photo) => <label key={photo.id}><input type="checkbox" checked={selectedPhotoIds.includes(photo.id)} onChange={(event) => setSelectedPhotoIds((current) => event.target.checked ? [...current, photo.id] : current.filter((id) => id !== photo.id))} />{photo.preview_url ? <img src={`/api${photo.preview_url}`} alt="" /> : <span>Sem prévia</span>}<strong>{photo.name}</strong><small>{photo.folder_name}</small></label>)}</div><MarkinaButton disabled={busy || !selectedPhotoIds.length}>{busy ? "Adicionando…" : "Adicionar ao acervo privado"}</MarkinaButton></form> : <SystemState title="Todas as fotos já estão disponíveis" detail="Carregue e publique novos JPEGs na Galeria pública para ampliar este acervo." />}</section>

    <section className="admin-card"><h2>Ajustes da galeria privada</h2><form className="auth-form" onSubmit={saveName}><label>Nome<input name="name" defaultValue={detail.name} required /></label><MarkinaButton disabled={busy}>Salvar nome</MarkinaButton></form><p>Mensagem, prazo, favoritos, comentários, preço e PIX são herdados da Galeria pública.</p>{detail.custom_message ? <p><strong>Mensagem vigente:</strong> {detail.custom_message}</p> : null}</section>
    {deleteConfirmOpen ? <div className="mk-dialog-backdrop" role="presentation"><section aria-labelledby="delete-private-gallery-title" aria-modal="true" className="mk-dialog" role="dialog"><p className="eyebrow">Exclusão da galeria privada</p><h2 id="delete-private-gallery-title">Excluir “{detail.name}”?</h2><p>O acesso operacional, o link e as referências removíveis serão encerrados. Clientes, pedidos, pagamentos, entregas e histórico comercial serão preservados.</p><p>Se existir pagamento informado em análise, conclua primeiro a decisão administrativa indicada pelo backend.</p>{deleteError ? <p className="form-message form-message--error" role="alert">{deleteError}</p> : null}<div className="mk-dialog__actions"><MarkinaButton type="button" variant="secondary" disabled={busy} onClick={() => { setDeleteConfirmOpen(false); setDeleteError(""); }}>Cancelar</MarkinaButton><MarkinaButton type="button" className="mk-button--danger" disabled={busy} onClick={removeGallery}>{busy ? "Excluindo…" : "Confirmar exclusão"}</MarkinaButton></div></section></div> : null}
    {message ? <p className="form-message" role="status">{message}</p> : null}
  </main>;
}
