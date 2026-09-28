import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { ClientGalleryCard, type ClientGalleryRow } from "./client-gallery-card";

const person: ClientGalleryRow = {
  client_id: "ana", name: "Ana", phone: "+5511999999999", registration_status: "active",
  derived_gallery_id: null, available_count: 0, selected_count: 0, purchased_count: 0,
  gallery_status: "active", access_status: "active",
};

const uploads = vi.hoisted(() => ({ key: vi.fn(), send: vi.fn() }));
vi.mock("../../upload-jpeg", () => ({ jpegStorageKey: uploads.key, uploadJpeg: uploads.send }));

afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); uploads.key.mockReset(); uploads.send.mockReset(); });

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
      folder_id: "folder-1", folder_name: "Pasta 01", preview_mode: "inherit", facial_mode: "inherit",
      preview_strength: 50, preview_exposure_tenths: 0,
      effective_preview: { mode: "inherit", enabled: false, strength: 50, exposure_tenths: 0 },
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

it("mostra destinatárias legadas sem oferecer nova atribuição", async () => {
  const fetcher = vi.fn((path: string, init?: RequestInit) => {
    if (init?.method && init.method !== "GET") throw new Error("Escrita inesperada.");
    return Promise.resolve(new Response(JSON.stringify(
    path.endsWith("/folders") ? { folders: [{ id: "folder-1", name: "Retratos", status: "released",
      photo_count: 0, assigned_client_ids: ["ana", "bia"] }] }
      : path.endsWith("/processing") ? {
        folder_id: "folder-1", folder_name: "Retratos", preview_mode: "inherit", facial_mode: "inherit",
        preview_strength: 50, preview_exposure_tenths: 0,
        effective_preview: { mode: "inherit", enabled: false, strength: 50, exposure_tenths: 0 },
        facial_available: false, facial_allowed: false, total_photos: 0,
        preview_counts: { queued: 0, processing: 0, ready: 0, failed: 0 },
        facial_counts: { queued: 0, processing: 0, completed: 0, failed: 0 }, comparison_photo_id: null,
      } : { photos: [{ id: "photo-1", name: "retrato.jpg", preview_url: "/admin/photos/photo-1/preview",
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
  expect(await screen.findByRole("button", { name: "Salvar configuração" })).toBeTruthy();
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

it("envia ao escolher arquivos, mostra progresso e retenta só a falha", async () => {
  const posts: string[] = [];
  const fetcher = vi.fn((path: string, init?: RequestInit) => {
    if (init?.method === "POST") {
      posts.push(String(init.body));
      return Promise.resolve(new Response(JSON.stringify({ id: `photo-${posts.length}` }), { status: 201 }));
    }
    const body = path.endsWith("/folders") ? { folders: [{ id: "folder-1", name: "Retratos",
      status: "preparing", photo_count: 0, assigned_client_ids: ["ana"] }] }
      : path.endsWith("/processing") ? { folder_id: "folder-1", folder_name: "Retratos",
        preview_mode: "inherit", facial_mode: "inherit", preview_strength: 50, preview_exposure_tenths: 0,
        effective_preview: { mode: "inherit", enabled: false, strength: 50, exposure_tenths: 0 },
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
      ? Promise.reject(new Error("Conexão interrompida")) : Promise.resolve();
  });
  render(<ClientGalleryCard person={person} parentGalleryId="gallery-1" />);
  fireEvent.click(screen.getByRole("button", { name: /Acervo da cliente/ }));
  fireEvent.click(await screen.findByRole("button", { name: /Retratos/ }));
  const input = screen.getByLabelText("Adicionar JPEGs") as HTMLInputElement;
  fireEvent.change(input, { target: { files: [new File(["ok"], "ok.jpg", { type: "image/jpeg" }),
    new File(["bad"], "falha.jpg", { type: "image/jpeg" })] } });
  expect(screen.queryByRole("button", { name: "Enviar fotos" })).toBeNull();
  expect(await screen.findByText("50% desta foto")).toBeTruthy();
  expect(screen.getByText("50% desta foto").closest("[role=status]")?.querySelector("progress")?.getAttribute("value")).toBe("1");
  finishFirst();
  expect(await screen.findByText("Algumas fotos não foram enviadas")).toBeTruthy();
  expect(screen.getByText(/1 de 2 concluída/)).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Tentar novamente 1 foto(s)" }));
  expect(await screen.findByText("Upload concluído")).toBeTruthy();
  expect(uploads.send.mock.calls.map((call) => call[1].name)).toEqual(["ok.jpg", "falha.jpg", "falha.jpg"]);
  expect(posts).toHaveLength(3);
  expect(JSON.parse(posts[1]).storage_key).toBe(JSON.parse(posts[2]).storage_key);
});
