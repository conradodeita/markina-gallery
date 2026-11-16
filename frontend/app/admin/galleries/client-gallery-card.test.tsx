import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { ClientGalleryCard, type ClientGalleryRow } from "./client-gallery-card";

const person: ClientGalleryRow = {
  client_id: "ana", name: "Ana", phone: "+5511999999999", registration_status: "active",
  derived_gallery_id: null, available_count: 0, selected_count: 0, purchased_count: 0,
  gallery_status: "active", access_status: "active",
};

const uploads = vi.hoisted(() => ({
  key: vi.fn(),
  send: vi.fn(),
  confirmDuplicates: vi.fn(async (items: unknown[]) => ({
    items, duplicateCount: 0, duplicateIndexes: [], skippedCount: 0, confirmed: false,
  })),
}));
vi.mock("../../upload-jpeg", () => ({
  confirmDuplicateJpegs: uploads.confirmDuplicates,
  jpegStorageKey: uploads.key,
  uploadJpeg: uploads.send,
}));

afterEach(() => {
  vi.unstubAllGlobals(); vi.restoreAllMocks(); uploads.key.mockReset(); uploads.send.mockReset();
  uploads.confirmDuplicates.mockClear();
});

it("abre a pasta pela prévia protegida e mantém outra pasta sem prévia acessível", async () => {
  const fetcher = vi.fn((path: string, init?: RequestInit) => {
    if (init?.method && init.method !== "GET") throw new Error("Escrita inesperada.");
    return Promise.resolve(new Response(JSON.stringify(
    path.endsWith("/folders") ? { folders: [
      { id: "folder-1", name: "Pasta 01", status: "released", photo_count: 1,
        preview_url: "/admin/photo-assets/photo-1/watermarked-preview", assigned_client_ids: ["ana"] },
      { id: "folder-2", name: "Pasta 02", status: "preparing", photo_count: 0,
        preview_url: null, assigned_client_ids: ["ana"] },
    ] } : path.endsWith("/processing") ? {
      folder_id: "folder-1", folder_name: "Pasta 01", preview_mode: "custom", facial_mode: "on",
      preview_strength: 50, preview_exposure_tenths: 0,
      effective_preview: { mode: "custom", enabled: true, strength: 50, exposure_tenths: 0 },
      facial_available: false, facial_allowed: false, total_photos: 1,
      preview_counts: { queued: 0, processing: 0, ready: 0, failed: 0 },
      facial_counts: { queued: 0, processing: 0, completed: 0, failed: 0 }, comparison_photo_id: null,
    } : { photos: [] },
    ), { status: 200 }));
  });
  vi.stubGlobal("fetch", fetcher);
  render(<ClientGalleryCard person={person} parentGalleryId="gallery-1" />);
  fireEvent.click(screen.getByRole("button", { name: "Acervo da cliente" }));
  expect(screen.getByRole("heading", { name: "Pastas restritas ao cliente" })).toBeTruthy();
  const first = await screen.findByRole("button", { name: "Abrir pasta Pasta 01" });
  const second = screen.getByRole("button", { name: "Abrir pasta Pasta 02" });
  const preview = first.querySelector("img");
  expect(preview?.getAttribute("src")).toBe("/api/admin/photo-assets/photo-1/watermarked-preview");
  expect(second.textContent).toContain("Sem prévia");
  fireEvent.click(preview!);
  expect(first.getAttribute("aria-expanded")).toBe("true");
  expect(second.getAttribute("aria-expanded")).toBe("false");
  fireEvent.click(screen.getByRole("button", { name: "Recolher pasta Pasta 01" }));
  expect(first.getAttribute("aria-expanded")).toBe("false");
  fireEvent.click(second);
  expect(second.getAttribute("aria-expanded")).toBe("true");
  expect(fetcher.mock.calls.every(([, init]) => !init?.method || init.method === "GET")).toBe(true);
});

it("mostra pasta arquivada e impede ações de mídia até a recuperação", async () => {
  const fetcher = vi.fn((path: string, init?: RequestInit) => {
    if (init?.method && init.method !== "GET") throw new Error("Escrita inesperada.");
    if (path.endsWith("/media-archive/recovery-pricing")) return Promise.resolve(new Response(JSON.stringify({
      recovery_fee_credits: 10, configured: true, owner_exempt: false,
    }), { status: 200 }));
    const body = path.endsWith("/folders") ? { folders: [{ id: "folder-cold", name: "Retratos",
      status: "released", photo_count: 1, preview_url: null, media_state: "archived", assigned_client_ids: ["ana"] }] }
      : { photos: [{ id: "photo-cold", name: "retrato.jpg", preview_url: null,
        publication_state: "published", can_delete: false }] };
    return Promise.resolve(new Response(JSON.stringify(body), { status: 200 }));
  });
  vi.stubGlobal("fetch", fetcher);
  render(<ClientGalleryCard person={person} parentGalleryId="gallery-1" />);
  fireEvent.click(screen.getByRole("button", { name: "Acervo da cliente" }));
  const folder = await screen.findByRole("button", { name: "Abrir pasta Retratos" });
  expect(folder.textContent).toContain("Arquivada no arquivo frio");
  fireEvent.click(folder);

  expect(await screen.findByText("retrato.jpg")).toBeTruthy();
  expect(screen.getAllByText("Arquivada no arquivo frio").length).toBeGreaterThan(0);
  expect(screen.getByRole("link", { name: "Créditos" }).getAttribute("href")).toBe("/admin/credits");
  expect(screen.queryByRole("link", { name: "Processamento da pasta" })).toBeNull();
  expect(screen.queryByRole("button", { name: "Renomear pasta" })).toBeNull();
  expect(screen.queryByRole("button", { name: "Excluir pasta" })).toBeNull();
  expect(screen.queryByLabelText("Adicionar JPEGs")).toBeNull();
  expect(screen.queryByRole("img", { name: "Prévia de retrato.jpg" })).toBeNull();
});

it("mostra destinatárias legadas sem oferecer nova atribuição", async () => {
  const fetcher = vi.fn((path: string, init?: RequestInit) => {
    if (init?.method && init.method !== "GET") throw new Error("Escrita inesperada.");
    return Promise.resolve(new Response(JSON.stringify(
    path.endsWith("/folders") ? { folders: [{ id: "folder-1", name: "Retratos", status: "released",
      photo_count: 0, assigned_client_ids: ["ana", "bia"] }] }
      : { photos: [{ id: "photo-1", name: "retrato.jpg", preview_url: "/admin/photos/photo-1/preview",
        publication_state: "available", can_delete: true }] },
    ), { status: 200 }));
  });
  vi.stubGlobal("fetch", fetcher);
  render(<ClientGalleryCard person={person} parentGalleryId="gallery-1" linkedClients={[
    person, { ...person, client_id: "bia", name: "Bia" },
  ]} />);
  fireEvent.click(screen.getByRole("button", { name: /Acervo da cliente/ }));
  fireEvent.click(await screen.findByRole("button", { name: /Retratos/ }));
  expect(await screen.findByText(/Pasta compartilhada anterior/)).toBeTruthy();
  expect(screen.getByText("Bia")).toBeTruthy();
  expect(screen.getByRole("link", { name: "Processamento da pasta" }).getAttribute("href")).toBe("/admin/galleries/sources/gallery-1/edit/imagens?folder=folder-1");
  expect(screen.queryByRole("button", { name: /Processamento da pasta/ })).toBeNull();
  expect(screen.getAllByRole("button", { name: "Remover acesso" })).toHaveLength(2);
  expect(screen.queryByText("Adicionar cliente")).toBeNull();
  expect(screen.queryByRole("button", { name: "Adicionar à pasta" })).toBeNull();
  expect(fetcher.mock.calls.every(([, init]) => !init || !init.method || init.method === "GET")).toBe(true);
  const trigger = await screen.findByRole("button", { name: "Ampliar retrato.jpg" });
  fireEvent.click(trigger);
  const dialog = screen.getByRole("dialog", { name: "Prévia ampliada de retrato.jpg" });
  expect(dialog.querySelector("img")?.getAttribute("src")).toBe("/api/admin/photos/photo-1/preview");
  fireEvent.keyDown(dialog, { key: "Tab" });
  expect(document.activeElement).toBe(screen.getByRole("button", { name: "Fechar" }));
  fireEvent.keyDown(dialog, { key: "Escape" });
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  expect(document.activeElement).toBe(trigger);
});

it("aplica a cor atual ao HTML comprado sem alterar o escopo da cliente", async () => {
  const fetcher = vi.fn(async () => new Response(JSON.stringify({ folders: [] }), { status: 200 }));
  vi.stubGlobal("fetch", fetcher);
  render(<ClientGalleryCard person={{ ...person, purchased_count: 1 }} parentGalleryId="gallery-1" />);
  fireEvent.click(screen.getByRole("button", { name: "Acervo da cliente" }));
  const download = await screen.findByRole("link", { name: "Baixar fotos compradas" }) as HTMLAnchorElement;
  const previousAccent = document.documentElement.style.getPropertyValue("--mk-brand");
  try {
    document.documentElement.style.setProperty("--mk-brand", "#123456");
    download.addEventListener("click", (event) => event.preventDefault(), { once: true });
    fireEvent.click(download);
    const target = new URL(download.href);
    expect(target.pathname).toBe("/api/admin/parent-galleries/gallery-1/clients/ana/selection/export.html");
    expect(target.searchParams.get("highlight")).toBe("#123456");
  } finally {
    if (previousAccent) document.documentElement.style.setProperty("--mk-brand", previousAccent);
    else document.documentElement.style.removeProperty("--mk-brand");
  }
});

it("organiza ações, prazo, destinatárias, fotos e upload no painel da pasta", async () => {
  const fetcher = vi.fn((path: string, init?: RequestInit) => {
    if (init?.method && init.method !== "GET") throw new Error("Escrita inesperada.");
    const body = path.endsWith("/folders") ? { folders: [{
      id: "folder-1", name: "Retratos", status: "preparing", photo_count: 1,
      access_duration_days: 14, assigned_client_ids: ["ana", "bia"],
    }] } : { photos: [{
      id: "photo-1", name: "retrato.jpg", preview_url: "/admin/photos/photo-1/preview",
      publication_state: "available", can_delete: true,
    }] };
    return Promise.resolve(new Response(JSON.stringify(body), { status: 200 }));
  });
  vi.stubGlobal("fetch", fetcher);
  render(<ClientGalleryCard person={person} parentGalleryId="gallery-1" linkedClients={[
    person, { ...person, client_id: "bia", name: "Bia" },
  ]} />);

  fireEvent.click(screen.getByRole("button", { name: "Acervo da cliente" }));
  fireEvent.click(await screen.findByRole("button", { name: /Abrir pasta Retratos/ }));
  expect(await screen.findByText("retrato.jpg")).toBeTruthy();

  const management = screen.getByRole("region", { name: "Gestão da pasta Retratos" });
  const actions = within(management).getByRole("group", { name: "Ações para pasta Retratos" });
  expect(within(actions).getByRole("link", { name: "Processamento da pasta" })).toBeTruthy();
  expect(within(actions).getByRole("button", { name: "Disponibilizar fotos prontas" })).toBeTruthy();
  expect(within(actions).getByRole("button", { name: "Renomear pasta" })).toBeTruthy();
  expect(within(actions).getByRole("button", { name: "Excluir pasta" })).toBeTruthy();
  expect(screen.getAllByLabelText("Dias de acesso da pasta")).toHaveLength(2);
  expect(screen.getByRole("region", { name: "Clientes com acesso" }).textContent).toContain("Bia");
  expect(screen.getByRole("region", { name: "Fotos da pasta Retratos" }).textContent).toContain("retrato.jpg");
  expect(screen.getByRole("region", { name: "Upload para pasta Retratos" }).querySelector('input[type="file"]')).toBeTruthy();
  expect(fetcher.mock.calls.every(([, init]) => !init || !init.method || init.method === "GET")).toBe(true);
});

it("renomeia pasta restrita liberada sem alterar destinatárias ou fotos", async () => {
  let folderName = "Retratos da Ana";
  const refresh = vi.fn();
  const fetcher = vi.fn((path: string, init?: RequestInit) => {
    if (path.endsWith("/media-archive/recovery-pricing")) return Promise.resolve(new Response(JSON.stringify({
      recovery_fee_credits: 10, configured: true, owner_exempt: false,
    }), { status: 200 }));
    if (path.endsWith("/clients/ana/folders")) return Promise.resolve(new Response(JSON.stringify({ folders: [{
      id: "folder-1", name: folderName, status: "released", photo_count: 1,
      assigned_client_ids: ["ana", "bia"],
    }] }), { status: 200 }));
    if (path.endsWith("/photo-folders/folder-1/photos")) return Promise.resolve(new Response(JSON.stringify({ photos: [{
      id: "photo-1", name: "retrato.jpg", preview_url: "/preview",
      publication_state: "available", can_delete: true,
    }] }), { status: 200 }));
    if (path.endsWith("/photo-folders/folder-1") && init?.method === "PATCH") {
      folderName = JSON.parse(String(init.body)).name;
      return Promise.resolve(new Response(JSON.stringify({ id: "folder-1", name: folderName }), { status: 200 }));
    }
    throw new Error(`Chamada inesperada: ${path}`);
  });
  vi.stubGlobal("fetch", fetcher);
  vi.spyOn(window, "prompt").mockReturnValue("  Coleção renomeada  ");
  render(<ClientGalleryCard person={person} parentGalleryId="gallery-1" linkedClients={[
    person, { ...person, client_id: "bia", name: "Bia" },
  ]} onRefresh={refresh} />);
  const card = screen.getByRole("article", { name: "Cliente Ana" });
  fireEvent.click(within(card).getByRole("button", { name: "Acervo da cliente" }));
  fireEvent.click(await within(card).findByRole("button", { name: "Abrir pasta Retratos da Ana" }));
  expect(await within(card).findByText("retrato.jpg")).toBeTruthy();
  fireEvent.click(within(card).getByRole("button", { name: "Renomear pasta" }));

  expect(await within(card).findByText("Nome da pasta atualizado.")).toBeTruthy();
  expect(within(card).getByRole("button", { name: "Recolher pasta Coleção renomeada" })).toBeTruthy();
  expect(within(card).getByText("Bia")).toBeTruthy();
  expect(within(card).getByText("retrato.jpg")).toBeTruthy();
  expect(fetcher).toHaveBeenCalledWith("/api/admin/photo-folders/folder-1", expect.objectContaining({
    method: "PATCH", body: JSON.stringify({ name: "Coleção renomeada" }),
  }));
  expect(refresh).toHaveBeenCalledTimes(1);
  expect(fetcher.mock.calls.filter(([path]) => path.endsWith("/photo-folders/folder-1/photos"))).toHaveLength(1);
});

it("não altera a pasta ao cancelar e mantém o nome quando o backend recusa", async () => {
  const fetcher = vi.fn((path: string, init?: RequestInit) => {
    if (path.endsWith("/media-archive/recovery-pricing")) return Promise.resolve(new Response(JSON.stringify({
      recovery_fee_credits: 10, configured: true, owner_exempt: false,
    }), { status: 200 }));
    if (path.endsWith("/clients/ana/folders")) return Promise.resolve(new Response(JSON.stringify({ folders: [{
      id: "folder-1", name: "Retratos", status: "released", photo_count: 0, assigned_client_ids: ["ana"],
    }] }), { status: 200 }));
    if (path.endsWith("/photo-folders/folder-1") && init?.method === "PATCH") return Promise.resolve(new Response(
      JSON.stringify({ detail: "A galeria está removida e não aceita alterações." }), { status: 409 },
    ));
    if (path.endsWith("/photo-folders/folder-1/photos")) return Promise.resolve(new Response(JSON.stringify({ photos: [] }), { status: 200 }));
    throw new Error(`Chamada inesperada: ${path}`);
  });
  const refresh = vi.fn();
  vi.stubGlobal("fetch", fetcher);
  vi.spyOn(window, "prompt").mockReturnValueOnce(null).mockReturnValueOnce("Nova tentativa");
  render(<ClientGalleryCard person={person} parentGalleryId="gallery-1" linkedClients={[person]} onRefresh={refresh} />);
  const card = screen.getByRole("article", { name: "Cliente Ana" });
  fireEvent.click(within(card).getByRole("button", { name: "Acervo da cliente" }));
  fireEvent.click(await within(card).findByRole("button", { name: "Abrir pasta Retratos" }));
  fireEvent.click(within(card).getByRole("button", { name: "Renomear pasta" }));
  expect(fetcher.mock.calls.some(([, init]) => init?.method === "PATCH")).toBe(false);
  fireEvent.click(within(card).getByRole("button", { name: "Renomear pasta" }));

  expect(await within(card).findByText("A galeria está removida e não aceita alterações.")).toBeTruthy();
  expect(within(card).getByRole("button", { name: "Recolher pasta Retratos" })).toBeTruthy();
  expect(refresh).not.toHaveBeenCalled();
});

it("envia ao escolher arquivos, mostra progresso e retenta só a falha", async () => {
  const posts: string[] = [];
  const uploadBatchId = "batch-private-1";
  const fetcher = vi.fn((path: string, init?: RequestInit) => {
    if (path.endsWith("/upload-batches")) return Promise.resolve(new Response(JSON.stringify(
      init?.method === "POST" ? { id: uploadBatchId } : { batches: [] },
    ), { status: init?.method === "POST" ? 201 : 200 }));
    if (path.endsWith(`/upload-batches/${uploadBatchId}/close`)) return Promise.resolve(new Response(
      JSON.stringify({ id: uploadBatchId, status: "closed" }), { status: 200 },
    ));
    if (init?.method === "POST") {
      posts.push(String(init.body));
      return Promise.resolve(new Response(JSON.stringify({ id: `photo-${posts.length}` }), { status: 201 }));
    }
    const body = path.endsWith("/folders") ? { folders: [{ id: "folder-1", name: "Retratos",
      status: "preparing", photo_count: 0, assigned_client_ids: ["ana"] }] }
      : path.endsWith("/processing") ? { folder_id: "folder-1", folder_name: "Retratos",
        preview_mode: "custom", facial_mode: "on", preview_strength: 50, preview_exposure_tenths: 0,
        effective_preview: { mode: "custom", enabled: true, strength: 50, exposure_tenths: 0 },
        facial_available: false, facial_allowed: false, total_photos: 0,
        preview_counts: { queued: 0, processing: 0, ready: 0, failed: 0 },
        facial_counts: { queued: 0, processing: 0, completed: 0, failed: 0 }, comparison_photo_id: null }
      : { photos: [] };
    return Promise.resolve(new Response(JSON.stringify(body), { status: 200 }));
  });
  vi.stubGlobal("fetch", fetcher);
  uploads.key.mockImplementation((_gallery: string, _folder: string, file: File) =>
    Promise.resolve(`gallery/folder/${file.name}`));
  let finishFirst = () => {};
  uploads.send.mockImplementation((_path: string, file: File, _wait: () => void,
    progress: (loaded: number, total: number) => void) => {
    if (uploads.send.mock.calls.length === 1) {
      progress(1, file.size);
      return new Promise<void>((resolve) => { finishFirst = resolve; });
    }
    progress(file.size, file.size);
    return file.name === "falha.jpg" && uploads.send.mock.calls.length === 2
      ? Promise.reject(new Error("Saldo insuficiente.")) : Promise.resolve();
  });
  render(<ClientGalleryCard person={person} parentGalleryId="gallery-1" />);
  fireEvent.click(screen.getByRole("button", { name: /Acervo da cliente/ }));
  fireEvent.click(await screen.findByRole("button", { name: /Retratos/ }));
  const input = screen.getByLabelText("Adicionar fotos (JPEG)") as HTMLInputElement;
  fireEvent.change(input, { target: { files: [new File(["ok"], "ok.jpg", { type: "image/jpeg" }),
    new File(["bad"], "falha.jpg", { type: "image/jpeg" })] } });
  expect(screen.queryByRole("button", { name: "Enviar fotos" })).toBeNull();
  expect(await screen.findByText("50% desta foto")).toBeTruthy();
  expect(screen.getByText("50% desta foto").closest("[role=status]")?.querySelector("progress")?.getAttribute("value")).toBe("1");
  finishFirst();
  expect(await screen.findByText("Algumas fotos não foram enviadas")).toBeTruthy();
  expect(screen.getByText(/Saldo insuficiente/)).toBeTruthy();
  expect(screen.getByText(/1 de 2 concluída/)).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Tentar novamente 1 foto(s)" }));
  expect(await screen.findByText("Upload concluído")).toBeTruthy();
  expect(uploads.send.mock.calls.map((call) => call[1].name)).toEqual(["ok.jpg", "falha.jpg", "falha.jpg"]);
  expect(posts).toHaveLength(3);
  expect(JSON.parse(posts[1]).storage_key).toBe(JSON.parse(posts[2]).storage_key);
  expect(posts.every((body) => JSON.parse(body).upload_batch_id === uploadBatchId)).toBe(true);
  expect(fetcher.mock.calls.filter(([path]) => path.endsWith(`/upload-batches/${uploadBatchId}/close`))).toHaveLength(2);
});

it("não inicia o PUT quando a API recusa a reserva por saldo insuficiente", async () => {
  const uploadBatchId = "batch-credit-denied";
  const fetcher = vi.fn((path: string, init?: RequestInit) => {
    if (path.endsWith("/folders")) return Promise.resolve(new Response(JSON.stringify({ folders: [{
      id: "folder-1", name: "Retratos", status: "preparing", photo_count: 0,
      assigned_client_ids: ["ana"],
    }] }), { status: 200 }));
    if (path.endsWith("/processing")) return Promise.resolve(new Response(JSON.stringify({
      folder_id: "folder-1", folder_name: "Retratos", preview_mode: "custom", facial_mode: "on",
      preview_strength: 50, preview_exposure_tenths: 0,
      effective_preview: { mode: "custom", enabled: true, strength: 50, exposure_tenths: 0 },
      facial_available: false, facial_allowed: false, total_photos: 0,
      preview_counts: { queued: 0, processing: 0, ready: 0, failed: 0 },
      facial_counts: { queued: 0, processing: 0, completed: 0, failed: 0 }, comparison_photo_id: null,
    }), { status: 200 }));
    if (path.endsWith("/upload-batches")) return Promise.resolve(new Response(JSON.stringify(
      init?.method === "POST" ? { id: uploadBatchId } : { batches: [] },
    ), { status: init?.method === "POST" ? 201 : 200 }));
    if (path.endsWith(`/upload-batches/${uploadBatchId}/close`)) return Promise.resolve(new Response(
      JSON.stringify({ id: uploadBatchId, status: "closed" }), { status: 200 },
    ));
    if (path.endsWith("/photos") && init?.method === "POST") return Promise.resolve(new Response(
      JSON.stringify({ detail: "Saldo insuficiente." }), { status: 409 },
    ));
    return Promise.resolve(new Response(JSON.stringify({ photos: [] }), { status: 200 }));
  });
  vi.stubGlobal("fetch", fetcher);
  uploads.key.mockResolvedValue("gallery/folder/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.jpg");
  render(<ClientGalleryCard person={person} parentGalleryId="gallery-1" />);
  fireEvent.click(screen.getByRole("button", { name: /Acervo da cliente/ }));
  fireEvent.click(await screen.findByRole("button", { name: /Retratos/ }));
  fireEvent.change(screen.getByLabelText("Adicionar fotos (JPEG)"), { target: {
    files: [new File(["conteudo"], "retrato.jpg", { type: "image/jpeg" })],
  } });

  expect(await screen.findByText("Algumas fotos não foram enviadas")).toBeTruthy();
  expect(screen.getByText(/Saldo insuficiente/)).toBeTruthy();
  expect(uploads.send).not.toHaveBeenCalled();
});
