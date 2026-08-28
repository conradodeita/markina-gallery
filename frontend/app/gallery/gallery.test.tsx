import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ useParams: () => ({ galleryId: "gallery-1" }) }));

import GalleryPage from "./[galleryId]/page";

afterEach(() => vi.restoreAllMocks());

const review = {
  gallery: { name: "Festa escolar", message: "Escolha suas favoritas", selection_expires_at: null, selection_open: true, favorites_enabled: true, comments_enabled: true, cover_preview_url: "/gallery/gallery-1/photos/new-1/preview" },
  photos: [
    { id: "new-1", name: "IMG_001.jpg", folder_id: "folder-1", preview_url: "/gallery/gallery-1/photos/new-1/preview", selected: false, favorited: false, purchase_state: "nova" },
    { id: "bought-1", name: "IMG_002.jpg", folder_id: "folder-1", preview_url: "/gallery/gallery-1/photos/bought-1/preview", selected: false, favorited: false, purchase_state: "já comprada" },
  ],
};

describe("galeria privada da cliente", () => {
  it("mostra estados e impede nova seleção de foto já comprada", async () => {
    const fetchMock = vi.fn((path: string) => Promise.resolve(new Response(JSON.stringify(path.endsWith("/comments") ? { comments: [] } : path.endsWith("/folders") ? { folders: [{ id: "folder-1", name: "Apresentação", position: 0, photo_count: 2 }] } : review), { status: 200 })));
    vi.stubGlobal("fetch", fetchMock);
    render(<GalleryPage />);
    expect(await screen.findByText("Festa escolar")).toBeTruthy();
    expect(screen.getByRole("region", { name: "Resumo da seleção" }).textContent).toContain("0 fotos");
    expect(screen.getByText("nova")).toBeTruthy();
    expect(screen.getByText("já comprada")).toBeTruthy();
    expect(screen.getByRole("button", { name: /Novas fotos/ })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /Já compradas/ }));
    expect(screen.getByRole("img", { name: "Prévia protegida de IMG_002.jpg" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /Todas/ }));
    expect(
      screen.getByRole("img", { name: "Prévia protegida de IMG_001.jpg" }).getAttribute("src"),
    ).toBe("/api/gallery/gallery-1/photos/new-1/preview");
    expect(screen.getByRole("img", { name: "Capa de Festa escolar" }).getAttribute("src")).toBe("/api/gallery/gallery-1/photos/new-1/preview");
    fireEvent.click(screen.getByRole("button", { name: "Ampliar prévia protegida de IMG_001.jpg" }));
    expect(await screen.findByRole("dialog", { name: "Prévia ampliada de IMG_001.jpg" })).toBeTruthy();
    fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    const selectButtons = screen.getAllByRole("button", { name: "Selecionar" });
    expect((selectButtons[1] as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(selectButtons[0]);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/gallery/gallery-1/photos/new-1/selection", expect.objectContaining({ method: "POST" })));
  });

  it("preserva a identificação das fotos após expirar e bloqueia nova seleção", async () => {
    const expiredReview = { ...review, gallery: { ...review.gallery, selection_open: false, selection_expires_at: "2026-08-01T23:59:59Z" } };
    vi.stubGlobal("fetch", vi.fn((path: string) => Promise.resolve(new Response(JSON.stringify(path.endsWith("/comments") ? { comments: [] } : expiredReview), { status: 200 }))));
    render(<GalleryPage />);
    expect(await screen.findByText(/prazo para novas seleções terminou/i)).toBeTruthy();
    expect(screen.getAllByText("IMG_001.jpg").length).toBeGreaterThan(0);
    for (const button of screen.getAllByRole("button", { name: "Selecionar" })) {
      expect((button as HTMLButtonElement).disabled).toBe(true);
    }
  });

  it("navega somente entre pastas liberadas pelo contrato da cliente", async () => {
    const groupedReview = { ...review, photos: [...review.photos, { id: "folder-2-photo", name: "IMG_003.jpg", folder_id: "folder-2", preview_url: "/gallery/gallery-1/photos/folder-2-photo/preview", selected: false, favorited: false, purchase_state: "nova" }] };
    vi.stubGlobal("fetch", vi.fn((path: string) => Promise.resolve(new Response(JSON.stringify(path.endsWith("/comments") ? { comments: [] } : path.endsWith("/folders") ? { folders: [{ id: "folder-1", name: "Apresentação", position: 0, photo_count: 2 }, { id: "folder-2", name: "Encerramento", position: 1, photo_count: 1 }] } : groupedReview), { status: 200 }))));
    render(<GalleryPage />);
    const secondFolder = await screen.findByRole("button", { name: /Encerramento/ });
    fireEvent.click(secondFolder);
    expect(screen.getByRole("img", { name: "Prévia protegida de IMG_003.jpg" })).toBeTruthy();
    expect(screen.queryByRole("img", { name: "Prévia protegida de IMG_001.jpg" })).toBeNull();
  });

  it("explicita falha de autorização em vez de confundir com galeria vazia", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(new Response(null, { status: 403 }))));
    render(<GalleryPage />);
    expect((await screen.findByRole("alert")).textContent).toContain("Não foi possível abrir esta galeria");
    expect(screen.getByText(/conta correta/i)).toBeTruthy();
  });
});
