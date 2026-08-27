"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

type Item = { id: string; name: string; parent_gallery_id?: string };
type Folder = Item & { status: string; photo_count: number };
type FolderPhoto = {
  id: string;
  name: string;
  preview_url: string | null;
  status: string;
  error: string | null;
};

export default function OperationsPage() {
  const [authorized, setAuthorized] = useState<boolean | null>(null);
  const [clients, setClients] = useState<Item[]>([]);
  const [galleries, setGalleries] = useState<Item[]>([]);
  const [folders, setFolders] = useState<Folder[]>([]);
  const [privateGalleries, setPrivateGalleries] = useState<Item[]>([]);
  const [folderPhotos, setFolderPhotos] = useState<FolderPhoto[]>([]);
  const [openFolderId, setOpenFolderId] = useState("");
  const [parentId, setParentId] = useState("");
  const [message, setMessage] = useState("");
  const [uploadStatus, setUploadStatus] = useState("");

  function refresh() {
    fetch("/api/admin/clients", { credentials: "same-origin" }).then(
      async (response) => setClients((await response.json()).clients ?? []),
    );
    fetch("/api/admin/parent-galleries", { credentials: "same-origin" }).then(
      async (response) =>
        setGalleries((await response.json()).parent_galleries ?? []),
    );
    fetch("/api/admin/derived-galleries?tab=active", {
      credentials: "same-origin",
    }).then(async (response) =>
      setPrivateGalleries((await response.json()).galleries ?? []),
    );
  }
  function refreshFolders(galleryId: string) {
    if (!galleryId) {
      setFolders([]);
      return;
    }
    fetch(`/api/admin/parent-galleries/${galleryId}/folders`, {
      credentials: "same-origin",
    }).then(async (response) =>
      setFolders((await response.json()).folders ?? []),
    );
  }
  function inspectFolder(folderId: string) {
    setOpenFolderId(folderId);
    fetch(`/api/admin/photo-folders/${folderId}/photos`, {
      credentials: "same-origin",
    }).then(async (response) =>
      setFolderPhotos((await response.json()).photos ?? []),
    );
  }
  useEffect(() => {
    fetch("/api/admin", { credentials: "same-origin" })
      .then((response) => {
        setAuthorized(response.ok);
        if (response.ok) refresh();
      })
      .catch(() => setAuthorized(false));
  }, []);

  async function submit(
    path: string,
    payload: object,
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();
    const response = await fetch(`/api${path}`, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    setMessage(
      response.ok
        ? "Salvo com sucesso."
        : "Não foi possível salvar. Confira os dados.",
    );
    if (response.ok) {
      refresh();
      if (path.includes("/folders")) refreshFolders(parentId);
    }
  }
  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const file = data.get("jpeg");
    const selectedFolderId = String(data.get("folder") || "");
    if (!(file instanceof File) || !file.size) {
      setMessage("Escolha um JPEG.");
      return;
    }
    const key = `uploads/${Date.now()}-${file.name.replace(/[^a-zA-Z0-9._-]/g, "-")}`;
    const registered = await fetch(
      `/api/admin/photo-folders/${selectedFolderId}/photos`,
      {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename: file.name, storage_key: key }),
      },
    );
    if (!registered.ok) {
      setMessage("Não foi possível registrar a foto.");
      return;
    }
    const { id } = await registered.json();
    const imported = await fetch(`/api/admin/photo-assets/${id}/source`, {
      method: "PUT",
      credentials: "same-origin",
      headers: { "Content-Type": "image/jpeg" },
      body: file,
    });
    if (!imported.ok) {
      setMessage("O JPEG não pôde ser importado.");
      return;
    }
    form.reset();
    refreshFolders(parentId);
    setMessage("JPEG recebido. As prévias estão sendo processadas.");
    setUploadStatus("queued");
    const timer = window.setInterval(async () => {
      const status = await fetch(`/api/admin/photo-assets/${id}/media-status`, {
        credentials: "same-origin",
      });
      if (!status.ok) return;
      const result = await status.json();
      setUploadStatus(result.status);
      if (result.status === "completed" || result.status === "failed")
        window.clearInterval(timer);
    }, 1500);
  }
  async function releaseFolder(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const folderId = String(data.get("release-folder") || "");
    const galleryIds = Array.from(
      event.currentTarget.querySelectorAll<HTMLInputElement>(
        'input[name="release-gallery"]:checked',
      ),
    ).map((input) => input.value);
    if (!folderId || !galleryIds.length) {
      setMessage("Escolha uma pasta e pelo menos uma galeria privada.");
      return;
    }
    if (
      !confirm(
        "Liberar esta pasta para as galerias selecionadas? Depois disso ela não aceitará novas fotos.",
      )
    )
      return;
    const response = await fetch(
      `/api/admin/photo-folders/${folderId}/release`,
      {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ gallery_ids: galleryIds }),
      },
    );
    setMessage(
      response.ok
        ? "Pasta liberada somente para as galerias selecionadas."
        : "Não foi possível liberar esta pasta.",
    );
    if (response.ok) refreshFolders(parentId);
  }
  async function removeFolder(folder: Folder) {
    if (
      !confirm(
        `Excluir a pasta vazia “${folder.name}”? Esta ação não pode ser desfeita.`,
      )
    )
      return;
    const response = await fetch(`/api/admin/photo-folders/${folder.id}`, {
      method: "DELETE",
      credentials: "same-origin",
    });
    setMessage(
      response.ok
        ? "Pasta excluída."
        : "A pasta possui fotos ou já foi liberada e não pode ser excluída.",
    );
    if (response.ok) refreshFolders(parentId);
  }
  async function renameFolder(folder: Folder) {
    const name = prompt("Novo nome da pasta", folder.name)?.trim();
    if (!name || name === folder.name) return;
    const response = await fetch(`/api/admin/photo-folders/${folder.id}`, {
      method: "PATCH",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
    setMessage(
      response.ok
        ? "Pasta renomeada."
        : "Apenas pastas em preparação podem ser renomeadas.",
    );
    if (response.ok) refreshFolders(parentId);
  }

  if (authorized === null)
    return <main className="admin-shell">Carregando operação…</main>;
  if (!authorized)
    return (
      <main className="admin-shell">
        <h1>Acesso restrito</h1>
        <Link href="/">Voltar para entrada</Link>
      </main>
    );
  return (
    <main className="admin-shell">
      <p className="eyebrow">Markina Gallery · Fotógrafo</p>
      <h1>Nova galeria privada</h1>
      <p className="intro">
        Cada etapa consulta e grava apenas no backend autorizado.
      </p>
      <section className="admin-card">
        <h2>1. Cliente</h2>
        <form
          className="auth-form"
          onSubmit={(event) => {
            const data = new FormData(event.currentTarget);
            submit(
              "/admin/clients",
              { full_name: data.get("name"), phone_e164: data.get("phone") },
              event,
            );
          }}
        >
          <label>
            Nome completo
            <input name="name" required />
          </label>
          <label>
            WhatsApp internacional
            <input name="phone" placeholder="+55 11 99999-9999" required />
          </label>
          <button className="primary">Cadastrar cliente</button>
        </form>
      </section>
      <section className="admin-card">
        <h2>2. Acervo-mãe</h2>
        <form
          className="auth-form"
          onSubmit={(event) => {
            const data = new FormData(event.currentTarget);
            submit(
              "/admin/parent-galleries",
              { name: data.get("name"), event_name: data.get("event") },
              event,
            );
          }}
        >
          <label>
            Nome do acervo
            <input name="name" required />
          </label>
          <label>
            Evento
            <input name="event" />
          </label>
          <button className="primary">Criar acervo</button>
        </form>
      </section>
      <section className="admin-card">
        <h2>3. Pasta e JPEGs</h2>
        <label>
          Acervo para preparar
          <select
            value={parentId}
            onChange={(event) => {
              setParentId(event.target.value);
              refreshFolders(event.target.value);
            }}
          >
            <option value="">Selecione</option>
            {galleries.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
        <form
          className="auth-form"
          onSubmit={(event) => {
            const data = new FormData(event.currentTarget);
            submit(
              `/admin/parent-galleries/${parentId}/folders`,
              { name: data.get("name") },
              event,
            );
          }}
        >
          <label>
            Nome da nova pasta
            <input name="name" placeholder="Ex.: Entrega inicial" required />
          </label>
          <button className="secondary" disabled={!parentId}>
            Criar pasta
          </button>
        </form>
        <ul className="photo-list">
          {folders.map((folder) => (
            <li key={folder.id}>
              {folder.name} · {folder.photo_count} foto(s) · {folder.status}
              {folder.status === "preparing" && folder.photo_count === 0 ? (
                <button
                  className="link-button"
                  onClick={() => removeFolder(folder)}
                >
                  Excluir pasta vazia
                </button>
              ) : null}
            </li>
          ))}
        </ul>
        <div className="folder-inspector">
          <label>
            Inspecionar pasta
            <select value={openFolderId} onChange={(event) => inspectFolder(event.target.value)}>
              <option value="">Selecione</option>
              {folders.map((folder) => <option key={folder.id} value={folder.id}>{folder.name}</option>)}
            </select>
          </label>
          {openFolderId && folders.find((folder) => folder.id === openFolderId)?.status === "preparing" ? (
            <button className="link-button" onClick={() => renameFolder(folders.find((folder) => folder.id === openFolderId)!)}>Renomear pasta</button>
          ) : null}
          <div className="folder-photo-grid">
            {folderPhotos.map((photo) => (
              <article key={photo.id}>
                {photo.preview_url ? (
                  // A prévia depende da sessão administrativa e não deve passar por otimizador externo.
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={`/api${photo.preview_url}`} alt={`Prévia administrativa de ${photo.name}`} />
                ) : <div className="gallery-cover">Sem prévia</div>}
                <strong>{photo.name}</strong>
                <small>{photo.status === "completed" ? "Pronta" : photo.status === "failed" ? `Falha: ${photo.error ?? "processe novamente"}` : "Processando"}</small>
              </article>
            ))}
          </div>
        </div>
        <form className="auth-form" onSubmit={upload}>
          <label>
            Pasta em preparação
            <select name="folder" required>
              <option value="">Selecione</option>
              {folders
                .filter((folder) => folder.status === "preparing")
                .map((folder) => (
                  <option key={folder.id} value={folder.id}>
                    {folder.name} · {folder.photo_count} foto(s)
                  </option>
                ))}
            </select>
          </label>
          <label>
            Arquivo JPEG
            <input name="jpeg" type="file" accept="image/jpeg" required />
          </label>
          <button className="primary">Enviar para processamento</button>
        </form>
        {uploadStatus && (
          <p className="form-message" role="status">
            Processamento: {uploadStatus}
          </p>
        )}
      </section>
      <section className="admin-card">
        <h2>4. Galeria do cliente</h2>
        <form
          className="auth-form"
          onSubmit={(event) => {
            const data = new FormData(event.currentTarget);
            submit(
              "/admin/derived-galleries",
              {
                parent_gallery_id: parentId,
                client_id: data.get("client"),
                name: data.get("name"),
                photo_ids: [],
                custom_message: data.get("message") || null,
                favorites_enabled: data.get("favorites") === "on",
                comments_enabled: data.get("comments") === "on",
              },
              event,
            );
          }}
        >
          <label>
            Cliente
            <select name="client" required>
              <option value="">Selecione</option>
              {clients.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Nome da galeria
            <input name="name" required />
          </label>
          <label>
            Mensagem ao cliente
            <input name="message" />
          </label>
          <p className="form-message">
            A galeria nasce privada e vazia. As fotos entram somente quando uma
            pasta concluída for liberada.
          </p>
          <label>
            <input type="checkbox" name="favorites" /> Permitir favoritos
          </label>
          <label>
            <input type="checkbox" name="comments" /> Permitir comentários
          </label>
          <button className="primary" disabled={!parentId}>
            Criar galeria privada
          </button>
        </form>
      </section>
      <section className="admin-card">
        <h2>5. Liberar pasta concluída</h2>
        <form className="auth-form" onSubmit={releaseFolder}>
          <label>
            Pasta
            <select name="release-folder" required>
              <option value="">Selecione</option>
              {folders
                .filter((folder) => folder.status === "preparing")
                .map((folder) => (
                  <option key={folder.id} value={folder.id}>
                    {folder.name} · {folder.photo_count} foto(s)
                  </option>
                ))}
            </select>
          </label>
          <fieldset>
            <legend>Galerias privadas que receberão esta rodada</legend>
            {privateGalleries
              .filter((gallery) => gallery.parent_gallery_id === parentId)
              .map((gallery) => (
                <label key={gallery.id}>
                  <input
                    type="checkbox"
                    name="release-gallery"
                    value={gallery.id}
                  />{" "}
                  {gallery.name}
                </label>
              ))}
          </fieldset>
          <button className="primary">
            Liberar para as galerias selecionadas
          </button>
        </form>
      </section>
      {message && (
        <p className="form-message" role="status">
          {message}
        </p>
      )}
    </main>
  );
}
