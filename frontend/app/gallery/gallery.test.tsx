import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ useParams: () => ({ galleryId: "gallery-1" }) }));

import GalleryPage from "./[galleryId]/page";

afterEach(() => vi.restoreAllMocks());

const review = {
  gallery: { name: "Festa escolar", message: "Escolha suas favoritas", selection_expires_at: null, selection_open: true, favorites_enabled: true, comments_enabled: true },
  photos: [
    { id: "new-1", name: "IMG_001.jpg", preview_url: "/gallery/gallery-1/photos/new-1/preview", selected: false, favorited: false, purchase_state: "nova" },
    { id: "bought-1", name: "IMG_002.jpg", preview_url: "/gallery/gallery-1/photos/bought-1/preview", selected: false, favorited: false, purchase_state: "já comprada" },
  ],
};

describe("galeria privada da cliente", () => {
  it("mostra estados e impede nova seleção de foto já comprada", async () => {
    const fetchMock = vi.fn((path: string) => Promise.resolve(new Response(JSON.stringify(path.endsWith("/comments") ? { comments: [] } : review), { status: 200 })));
    vi.stubGlobal("fetch", fetchMock);
    render(<GalleryPage />);
    expect(await screen.findByText("Festa escolar")).toBeTruthy();
    expect(screen.getByText("nova")).toBeTruthy();
    expect(screen.getByText("já comprada")).toBeTruthy();
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
});
