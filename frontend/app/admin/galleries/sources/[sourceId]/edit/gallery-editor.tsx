"use client";

import Link from "next/link";
import { type FormEvent, useEffect, useMemo, useRef, useState } from "react";

import { MarkinaButton, StatusBadge, SystemState } from "../../../../../ui-kit";

type StepId = "ajustes" | "vendas" | "detalhes" | "imagens" | "clientes";
type EditorStep = { id: StepId; label: string; status: "complete" | "pending" | "unavailable"; available: boolean };
type Editor = { gallery: { id: string; name: string; event_name: string; description: string; active: boolean; unlisted_link: string; cover_photo_id: string | null; cover_preview_url: string | null; watermark_text: string; watermark_font: string; watermark_color: string; watermark_size: number; watermark_direction: string; folder_display_mode: string; cover_title_font: string; cover_title_color: string; cover_title_size: number; cover_title_position: string }; steps: EditorStep[]; counts: { folders: number; registrations: number; derived_galleries: number }; capabilities: Record<string, boolean>; actions: { can_create_folder: boolean; can_upload: boolean } };
type Folder = { id: string; name: string; status: string; position: number; photo_count: number; preview_url: string | null; released_at: string | null };
type Photo = { id: string; name: string; preview_url: string | null; status: string; error: string | null; can_delete: boolean; is_cover: boolean };
type ClientRow = { client_id: string; name: string; phone: string; registration_status: string | null; derived_gallery_id: string | null };
type ClientOption = { id: string; name: string; phone: string };
type Availability = { available: false; reason: string; capabilities: string[] };

const stepOrder: StepId[] = ["ajustes", "vendas", "detalhes", "imagens", "clientes"];

async function jsonRequest(path: string, init?: RequestInit) {
  const response = await fetch(path, { credentials: "same-origin", ...init });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(payload?.detail ?? "Não foi possível concluir a operação.");
  }
  return response.status === 204 ? null : response.json();
}

export default function GalleryEditor({ sourceId, step }: { sourceId: string; step: string }) {
  const currentStep = step as StepId;
  const [editor, setEditor] = useState<Editor | null>(null);
  const [folders, setFolders] = useState<Folder[]>([]);
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [selectedPhotoIds, setSelectedPhotoIds] = useState<string[]>([]);
  const [expandedPhoto, setExpandedPhoto] = useState<Photo | null>(null);
  const [openFolderId, setOpenFolderId] = useState("");
  const [linkedClients, setLinkedClients] = useState<ClientRow[]>([]);
  const [clientOptions, setClientOptions] = useState<ClientOption[]>([]);
  const [clientQuery, setClientQuery] = useState("");
  const [destinations, setDestinations] = useState<string[]>([]);
  const [availability, setAvailability] = useState<Availability | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [failed, setFailed] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const previewDialog = useRef<HTMLDivElement>(null);
  const uploadInput = useRef<HTMLInputElement>(null);
  const uploadForm = useRef<HTMLFormElement>(null);

  useEffect(() => {
    if (expandedPhoto) previewDialog.current?.focus();
  }, [expandedPhoto]);

  useEffect(() => {
    let active = true;
    queueMicrotask(() => {
      if (!active) return;
      setLoading(true);
      setFailed(false);
      setMessage("");
    });
    const editorRequest = jsonRequest(`/api/admin/parent-galleries/${sourceId}/editor`);
    let sectionRequest: Promise<unknown> = Promise.resolve(null);
    if (currentStep === "ajustes") sectionRequest = jsonRequest(`/api/admin/parent-galleries/${sourceId}/settings`);
    if (currentStep === "vendas") sectionRequest = jsonRequest(`/api/admin/parent-galleries/${sourceId}/sales`);
    if (currentStep === "detalhes") sectionRequest = jsonRequest(`/api/admin/parent-galleries/${sourceId}/details`);
    if (currentStep === "imagens") sectionRequest = Promise.all([
      jsonRequest(`/api/admin/parent-galleries/${sourceId}/folders`),
      jsonRequest(`/api/admin/parent-galleries/${sourceId}/clients`),
    ]);
    if (currentStep === "clientes") sectionRequest = Promise.all([
      jsonRequest(`/api/admin/parent-galleries/${sourceId}/clients`),
      jsonRequest(`/api/admin/clients${clientQuery ? `?query=${encodeURIComponent(clientQuery)}` : ""}`),
    ]);
    Promise.all([editorRequest, sectionRequest])
      .then(([editorData, sectionData]) => {
        if (!active) return;
        setEditor(editorData as Editor);
        if (currentStep === "vendas" || currentStep === "detalhes") setAvailability(sectionData as Availability);
        if (currentStep === "imagens") {
          const [folderData, clientData] = sectionData as [{ folders: Folder[] }, { clients: ClientRow[] }];
          setFolders(folderData.folders ?? []);
          setLinkedClients(clientData.clients ?? []);
        }
        if (currentStep === "clientes") {
          const [clientData, optionData] = sectionData as [{ clients: ClientRow[] }, { clients: ClientOption[] }];
          setLinkedClients(clientData.clients ?? []);
          setClientOptions(optionData.clients ?? []);
        }
      })
      .catch(() => { if (active) setFailed(true); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [clientQuery, currentStep, refresh, sourceId]);

  const currentIndex = stepOrder.indexOf(currentStep);
  const previous = currentIndex > 0 ? stepOrder[currentIndex - 1] : null;
  const next = currentIndex < stepOrder.length - 1 ? stepOrder[currentIndex + 1] : null;
  const selectedFolder = useMemo(
    () => folders.find((folder) => folder.id === openFolderId) ?? null,
    [folders, openFolderId],
  );

  async function mutate(path: string, method: string, body?: object) {
    try {
      const data = await jsonRequest(path, {
        method,
        headers: body ? { "content-type": "application/json" } : undefined,
        body: body ? JSON.stringify(body) : undefined,
      });
      setMessage("Alteração salva com sucesso.");
      setRefresh((value) => value + 1);
      return data;
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível concluir a operação.");
      return null;
    }
  }

  async function inspectFolder(folderId: string) {
    setOpenFolderId(folderId);
    setPhotos([]);
    setSelectedPhotoIds([]);
    if (!folderId) return;
    try {
      const data = await jsonRequest(`/api/admin/photo-folders/${folderId}/photos`);
      setPhotos(data.photos ?? []);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível abrir a pasta.");
    }
  }

  async function setCover(photo: Photo) {
    try {
      await jsonRequest(`/api/admin/parent-galleries/${sourceId}/cover`, {
        method: "PUT",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ photo_id: photo.id }),
      });
      setPhotos((current) => current.map((item) => ({ ...item, is_cover: item.id === photo.id })));
      setMessage("Foto definida como capa da galeria.");
      setRefresh((value) => value + 1);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível definir a capa.");
    }
  }

  async function deletePhoto(photo: Photo) {
    if (!window.confirm(`Excluir ${photo.name}? Esta ação não pode ser desfeita.`)) return;
    try {
      await jsonRequest(`/api/admin/photo-folders/${openFolderId}/photos/${photo.id}`, { method: "DELETE" });
      setMessage("Foto excluída da pasta.");
      setExpandedPhoto(null);
      await inspectFolder(openFolderId);
      setRefresh((value) => value + 1);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível excluir a foto.");
    }
  }

  async function deleteSelectedPhotos() {
    const eligible = photos.filter((photo) => selectedPhotoIds.includes(photo.id) && photo.can_delete);
    if (!eligible.length) return;
    if (!window.confirm(`Excluir ${eligible.length} foto(s) selecionada(s)? Esta ação não pode ser desfeita.`)) return;
    try {
      const result = await jsonRequest(`/api/admin/photo-folders/${openFolderId}/photos`, {
        method: "DELETE",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ photo_ids: selectedPhotoIds }),
      });
      const blockedCount = result.blocked_ids?.length ?? 0;
      setMessage(blockedCount ? `${result.deleted_ids.length} foto(s) excluída(s); ${blockedCount} protegida(s) por compra confirmada.` : `${result.deleted_ids.length} foto(s) excluída(s).`);
      setSelectedPhotoIds([]);
      await inspectFolder(openFolderId);
      setRefresh((value) => value + 1);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível excluir as fotos.");
    }
  }

  async function saveSettings(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await mutate(`/api/admin/parent-galleries/${sourceId}/settings`, "PATCH", {
      name: form.get("name"),
      event_name: form.get("event_name"),
      description: form.get("description"),
      active: form.get("active") === "on",
    });
  }

  async function saveVisualSettings(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await mutate(`/api/admin/parent-galleries/${sourceId}/settings`, "PATCH", {
      watermark_text: form.get("watermark_text"), watermark_font: form.get("watermark_font"),
      watermark_color: form.get("watermark_color"), watermark_size: Number(form.get("watermark_size")),
      watermark_direction: form.get("watermark_direction"), folder_display_mode: form.get("folder_display_mode"),
      cover_title_font: form.get("cover_title_font"), cover_title_color: form.get("cover_title_color"),
      cover_title_size: Number(form.get("cover_title_size")), cover_title_position: form.get("cover_title_position"),
    });
  }

  async function createFolder(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const created = await mutate(`/api/admin/parent-galleries/${sourceId}/folders`, "POST", { name: form.get("name") });
    if (created) formElement.reset();
  }

  async function uploadPhotos(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const folderId = String(form.get("folder") ?? "");
    const input = formElement.elements.namedItem("jpeg") as HTMLInputElement;
    const files = Array.from(input.files ?? []);
    if (!folderId || !files.length) return;
    for (const [index, file] of files.entries()) {
      const safeName = file.name.replace(/[^a-zA-Z0-9._-]/g, "-");
      try {
        const photo = await jsonRequest(`/api/admin/photo-folders/${folderId}/photos`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({
            filename: file.name,
            storage_key: `${sourceId}/${folderId}/${Date.now()}-${index}-${safeName}`,
          }),
        });
        await jsonRequest(`/api/admin/photo-assets/${photo.id}/source`, {
          method: "PUT",
          headers: { "content-type": "image/jpeg" },
          body: file,
        });
      } catch (error) {
        setMessage(error instanceof Error ? error.message : `Falha ao enviar ${file.name}.`);
        return;
      }
    }
    setMessage(`${files.length} foto(s) enviada(s) para processamento.`);
    setRefresh((value) => value + 1);
    await inspectFolder(folderId);
    formElement.reset();
  }

  async function createClientAndGallery(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const name = String(form.get("full_name") ?? "");
    const created = await mutate("/api/admin/clients", "POST", {
      full_name: name,
      phone_e164: form.get("phone_e164"),
    });
    if (!created) return;
    await bindClient(created.id, name);
    formElement.reset();
  }

  async function bindClient(clientId: string, name: string) {
    await mutate("/api/admin/derived-galleries", "POST", {
      parent_gallery_id: sourceId,
      client_id: clientId,
      name: `${editor?.gallery.name ?? "Galeria"} · ${name}`,
      photo_ids: [],
    });
  }

  if (failed) return <SystemState tone="error" title="Galeria indisponível" detail="Não foi possível carregar o editor. Atualize a página ou entre novamente." />;
  if (loading || !editor) return <SystemState tone="loading" title="Abrindo a galeria" detail="Consultando etapas, permissões e conteúdo." />;

  return (
    <main className="admin-shell gallery-editor-shell">
      <div className="gallery-editor-heading">
        <div>
          <Link href="/admin/galleries">← Galerias</Link>
          <p className="eyebrow">Galeria do evento · link não listado</p>
          <h1>{editor.gallery.name}</h1>
          <p className="intro">Organize as pastas, revise as fotos e vincule responsáveis sem sair desta galeria.</p>
        </div>
        <StatusBadge tone={editor.gallery.active ? "success" : "danger"}>{editor.gallery.active ? "Ativa" : "Bloqueada"}</StatusBadge>
      </div>
      <nav className="gallery-stepper" aria-label="Etapas da galeria">
        {editor.steps.map((item, index) => (
          <Link key={item.id} href={`/admin/galleries/sources/${sourceId}/edit/${item.id}`} aria-current={item.id === currentStep ? "step" : undefined} className={item.id === currentStep ? "is-current" : ""}>
            <span>{index + 1}</span><strong>{item.label}</strong><small>{item.status === "complete" ? "Concluída" : item.status === "unavailable" ? "Em breve" : "Pendente"}</small>
          </Link>
        ))}
      </nav>

      {currentStep === "ajustes" ? (
        <form className="gallery-editor-panel gallery-settings-form" onSubmit={saveSettings}>
          <div className="section-heading"><div><p className="eyebrow">Etapa 1</p><h2>Ajustes da galeria</h2></div></div>
          <label>Título da galeria<input name="name" defaultValue={editor.gallery.name} required /></label>
          <label>Evento<input name="event_name" defaultValue={editor.gallery.event_name} /></label>
          <label>Descrição administrativa<textarea name="description" defaultValue={editor.gallery.description} rows={4} /><small className="field-hint">Uso interno do fotógrafo para registrar contexto, observações e pendências desta galeria.</small></label>
          <label className="gallery-toggle"><input name="active" type="checkbox" defaultChecked={editor.gallery.active} /> Galeria ativa</label>
          <MarkinaButton>Salvar ajustes</MarkinaButton>
        </form>
      ) : null}

      {currentStep === "vendas" || currentStep === "detalhes" ? (
        <section className="gallery-editor-panel">
          <p className="eyebrow">Etapa {currentIndex + 1}</p>
          <h2>{currentStep === "vendas" ? "Vendas" : "Detalhes e aparência"}</h2>
          <SystemState title="Configuração ainda indisponível" detail={availability?.reason ?? "O backend ainda não habilitou esta capacidade."} />
          <p className="gallery-scope-note">Esta tela não cria valores ou opções locais. Ela será ativada quando o contrato correspondente estiver implementado e aprovado.</p>
        </section>
      ) : null}

      {currentStep === "imagens" ? (
        <section className="gallery-editor-panel">
          <div className="section-heading"><div><p className="eyebrow">Etapa 4</p><h2>Imagens e pastas</h2></div><StatusBadge>{folders.length} pasta(s)</StatusBadge></div>
          <p className="gallery-scope-note">Crie a pasta nesta galeria, carregue todos os JPEGs e libere a rodada somente quando estiver completa.</p>
          <form className="gallery-settings-form gallery-visual-settings" onSubmit={saveVisualSettings}><div className="section-heading"><div><p className="eyebrow">Personalização</p><h3>Marca-d’água, capa e exibição</h3></div></div><label>Texto da marca-d’água<input name="watermark_text" defaultValue={editor.gallery.watermark_text} /></label><label>Tipografia da marca-d’água<input name="watermark_font" defaultValue={editor.gallery.watermark_font} /></label><label>Cor da marca-d’água<input name="watermark_color" type="color" defaultValue={editor.gallery.watermark_color} /></label><label>Tamanho da marca-d’água<input name="watermark_size" type="number" min={10} max={96} defaultValue={editor.gallery.watermark_size} /></label><label>Direção<select name="watermark_direction" defaultValue={editor.gallery.watermark_direction}><option value="horizontal">Horizontal</option><option value="vertical">Vertical</option><option value="diagonal">Diagonal</option></select></label><label>Tipografia do título<input name="cover_title_font" defaultValue={editor.gallery.cover_title_font} /></label><label>Cor do título<input name="cover_title_color" type="color" defaultValue={editor.gallery.cover_title_color} /></label><label>Tamanho do título<input name="cover_title_size" type="number" min={12} max={96} defaultValue={editor.gallery.cover_title_size} /></label><label>Posição do título<select name="cover_title_position" defaultValue={editor.gallery.cover_title_position}><option value="top-left">Superior esquerdo</option><option value="top-center">Superior centro</option><option value="top-right">Superior direito</option><option value="middle-left">Centro esquerdo</option><option value="middle-center">Centro</option><option value="middle-right">Centro direito</option><option value="bottom-left">Inferior esquerdo</option><option value="bottom-center">Inferior centro</option><option value="bottom-right">Inferior direito</option></select></label><label>Exibição das pastas<select name="folder_display_mode" defaultValue={editor.gallery.folder_display_mode}><option value="individual">Pastas lado a lado</option><option value="sequential">Sequência cronológica</option></select></label><MarkinaButton>Salvar personalização</MarkinaButton></form>
          <form className="gallery-inline-form" onSubmit={createFolder}><label>Nome da nova pasta<input name="name" required placeholder="Ex.: Apresentação da manhã" /></label><MarkinaButton disabled={!editor.actions.can_create_folder}>Criar pasta</MarkinaButton></form>
          {folders.length ? <div className="gallery-folder-grid">{folders.map((folder) => <article key={folder.id} className={folder.id === openFolderId ? "is-open" : ""}><button type="button" onClick={() => inspectFolder(folder.id)}><span className="gallery-folder-cover">{folder.preview_url ? <img src={`/api${folder.preview_url}`} alt="" /> : null}<b>{folder.photo_count ? `${folder.photo_count} fotos` : "Pasta vazia"}</b></span><strong>{folder.name}</strong><small>{folder.status === "released" ? "Liberada para clientes" : "Em preparação"}</small></button>{folder.status === "preparing" ? <div className="gallery-folder-actions"><button type="button" className="link-button" onClick={() => { const name = window.prompt("Novo nome da pasta", folder.name); if (name) mutate(`/api/admin/photo-folders/${folder.id}`, "PATCH", { name }); }}>Renomear</button>{folder.photo_count === 0 ? <button type="button" className="link-button" onClick={() => { if (window.confirm("Excluir esta pasta vazia?")) mutate(`/api/admin/photo-folders/${folder.id}`, "DELETE"); }}>Excluir</button> : null}</div> : null}</article>)}</div> : <SystemState title="Nenhuma pasta nesta galeria" detail="Crie a primeira pasta para iniciar o carregamento das fotos." />}
          {selectedFolder ? <div className="gallery-folder-workspace"><div className="section-heading"><div><p className="eyebrow">Pasta selecionada</p><h3>{selectedFolder.name}</h3></div><StatusBadge tone={selectedFolder.status === "released" ? "success" : "warning"}>{selectedFolder.status === "released" ? "Liberada" : "Em preparação"}</StatusBadge></div>{photos.length ? <><div className="folder-photo-toolbar"><label><input type="checkbox" checked={photos.length > 0 && selectedPhotoIds.length === photos.length} onChange={(event) => setSelectedPhotoIds(event.target.checked ? photos.map((photo) => photo.id) : [])} /> Selecionar todas</label><MarkinaButton type="button" className="mk-button--danger" disabled={!selectedPhotoIds.some((id) => photos.some((photo) => photo.id === id && photo.can_delete))} onClick={deleteSelectedPhotos}>Excluir selecionadas</MarkinaButton></div><div className="folder-photo-grid">{photos.map((photo) => <article key={photo.id}><label className="photo-select"><input type="checkbox" checked={selectedPhotoIds.includes(photo.id)} disabled={!photo.can_delete} onChange={(event) => setSelectedPhotoIds((current) => event.target.checked ? [...current, photo.id] : current.filter((id) => id !== photo.id))} /> {photo.can_delete ? "Selecionar" : "Compra confirmada"}</label>{photo.preview_url ? <button type="button" className="photo-preview-button" onClick={() => setExpandedPhoto(photo)} aria-label={`Ampliar ${photo.name}`}><img src={`/api${photo.preview_url}`} alt={`Prévia com marca d’água de ${photo.name}`} /></button> : <div className="gallery-cover">Processando</div>}<strong>{photo.name}</strong><small>{photo.error ?? (photo.status === "completed" ? "Prévia pronta" : "Processando")}</small><div className="photo-card-actions"><button type="button" className="link-button" disabled={!photo.preview_url || photo.is_cover} onClick={() => setCover(photo)}>{photo.is_cover ? "Capa atual" : "Usar como capa"}</button><button type="button" className="link-button danger-action" disabled={!photo.can_delete} title={photo.can_delete ? "Excluir foto" : "Há uma compra confirmada para esta foto"} onClick={() => deletePhoto(photo)}>{photo.can_delete ? "Excluir" : "Compra confirmada"}</button></div></article>)}</div></> : <SystemState title="Pasta sem fotos" detail="Selecione os JPEGs abaixo para iniciar o processamento." />}{selectedFolder.status === "preparing" ? <><form ref={uploadForm} className="gallery-inline-form" onSubmit={uploadPhotos}><input name="folder" type="hidden" value={selectedFolder.id} /><input ref={uploadInput} name="jpeg" type="file" accept="image/jpeg" multiple required hidden onChange={() => uploadForm.current?.requestSubmit()} /><MarkinaButton type="button" disabled={!editor.actions.can_upload} onClick={() => uploadInput.current?.click()}>Carregar fotos</MarkinaButton></form><fieldset className="gallery-destinations"><legend>Liberar para galerias privadas</legend>{linkedClients.filter((person) => person.derived_gallery_id).map((person) => <label key={person.client_id}><input type="checkbox" checked={destinations.includes(person.derived_gallery_id!)} onChange={(event) => setDestinations((current) => event.target.checked ? [...current, person.derived_gallery_id!] : current.filter((id) => id !== person.derived_gallery_id))} />{person.name}</label>)}{!linkedClients.some((person) => person.derived_gallery_id) ? <p>Vincule uma cliente na etapa Clientes antes de liberar.</p> : null}<MarkinaButton type="button" disabled={!photos.length || !destinations.length} onClick={() => mutate(`/api/admin/photo-folders/${selectedFolder.id}/release`, "POST", { gallery_ids: destinations })}>Liberar pasta concluída</MarkinaButton></fieldset></> : null}</div> : null}
        </section>
      ) : null}

      {currentStep === "clientes" ? (
        <section className="gallery-editor-panel">
          <div className="section-heading"><div><p className="eyebrow">Etapa 5</p><h2>Clientes e acesso</h2></div><StatusBadge>{linkedClients.length} vínculo(s)</StatusBadge></div>
          <div className="unlisted-link"><span>Link único e não listado</span><code>{editor.gallery.unlisted_link}</code><small>A cliente ainda precisará concluir o login por nome, telefone e código.</small></div>
          <div className="gallery-client-columns"><div><h3>Responsáveis vinculados</h3>{linkedClients.length ? <div className="dashboard-recent">{linkedClients.map((person) => <div key={person.client_id}><div><strong>{person.name}</strong><small>{person.phone}</small></div>{person.derived_gallery_id ? <Link href={`/admin/galleries/${person.derived_gallery_id}`}>Abrir galeria privada</Link> : <StatusBadge tone="warning">Cadastro pendente</StatusBadge>}</div>)}</div> : <SystemState title="Nenhum responsável vinculado" detail="Busque um cadastro existente ou faça um novo cadastro." />}</div><div><h3>Vincular responsável existente</h3><label className="gallery-client-search">Buscar por nome ou WhatsApp<input value={clientQuery} onChange={(event) => setClientQuery(event.target.value)} placeholder="Ex.: Ana ou 11999999999" /></label>{clientOptions.filter((option) => !linkedClients.some((linked) => linked.client_id === option.id)).length ? <div className="client-option-list">{clientOptions.filter((option) => !linkedClients.some((linked) => linked.client_id === option.id)).map((option) => <button type="button" key={option.id} onClick={() => bindClient(option.id, option.name)}><span><strong>{option.name}</strong><small>{option.phone}</small></span>Vincular</button>)}</div> : <SystemState title="Nenhum cadastro encontrado" detail="Cadastre o responsável abaixo para vinculá-lo a esta galeria." />}<h3>Cadastrar e vincular</h3><form className="gallery-settings-form" onSubmit={createClientAndGallery}><label>Nome completo<input name="full_name" required minLength={3} /></label><label>Número do WhatsApp<input name="phone_e164" required placeholder="+55 11 99999-9999" /></label><MarkinaButton>Cadastrar responsável</MarkinaButton></form></div></div>
        </section>
      ) : null}

      {expandedPhoto ? <div className="photo-preview-dialog" role="presentation" onMouseDown={() => setExpandedPhoto(null)}><div ref={previewDialog} role="dialog" aria-modal="true" aria-label={`Prévia ampliada de ${expandedPhoto.name}`} tabIndex={-1} onKeyDown={(event) => { if (event.key === "Escape") setExpandedPhoto(null); }} onMouseDown={(event) => event.stopPropagation()}><button type="button" className="photo-preview-close" onClick={() => setExpandedPhoto(null)}>Fechar</button><img src={`/api${expandedPhoto.preview_url}`} alt={`Prévia com marca d’água ampliada de ${expandedPhoto.name}`} /><p>{expandedPhoto.name}</p></div></div> : null}
      {message ? <p className="notice" role="status">{message}</p> : null}
      <footer className="gallery-editor-footer">
        {previous ? <Link className="mk-button mk-button--secondary" href={`/admin/galleries/sources/${sourceId}/edit/${previous}`}>← Voltar</Link> : <span />}
        {next ? <Link className="mk-button mk-button--primary" href={`/admin/galleries/sources/${sourceId}/edit/${next}`}>Avançar →</Link> : <Link className="mk-button mk-button--primary" href={`/admin/galleries/sources/${sourceId}`}>Concluir</Link>}
      </footer>
    </main>
  );
}
