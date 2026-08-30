import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("next/link", () => ({ default: ({ children, href }: { children: React.ReactNode; href: string }) => <a href={href}>{children}</a> }));
vi.mock("next/navigation", () => ({ useParams: () => ({ sourceId: "source-1" }) }));

import AdminGalleryPreviewPage from "./page";

afterEach(() => vi.restoreAllMocks());

describe("prévia administrativa da galeria", () => {
  it("reutiliza a apresentação protegida sem oferecer ações da cliente", async () => {
    vi.stubGlobal("fetch", vi.fn((path: string) => {
      if (path.endsWith("/editor")) return Promise.resolve(new Response(JSON.stringify({ gallery: { name: "Festa escolar", cover_preview_url: "/admin/photo-assets/cover/watermarked-preview", folder_display_mode: "individual", cover_title_color: "#FFFFFF", cover_title_size: 32, cover_title_font: "sans-serif", cover_title_position: "bottom-left" } }), { status: 200 }));
      if (path.endsWith("/folders")) return Promise.resolve(new Response(JSON.stringify({ folders: [{ id: "folder-1", name: "Apresentação", photo_count: 1, preview_url: "/admin/photo-assets/photo-1/watermarked-preview", position: 0 }] }), { status: 200 }));
      return Promise.resolve(new Response(JSON.stringify({ photos: [{ id: "photo-1", name: "FOTO_001.jpg", preview_url: "/admin/photo-assets/photo-1/watermarked-preview" }] }), { status: 200 }));
    }));
    render(<AdminGalleryPreviewPage />);
    expect(await screen.findByText("Modo fotógrafo")).toBeTruthy();
    expect(screen.getByRole("region", { name: "Apresentação de Festa escolar" })).toBeTruthy();
    expect(screen.getByRole("img", { name: "Prévia protegida de FOTO_001.jpg" }).getAttribute("src")).toBe("/api/admin/photo-assets/photo-1/watermarked-preview");
    expect(screen.queryByRole("button", { name: "Selecionar" })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Ampliar prévia protegida de FOTO_001.jpg" }));
    expect(await screen.findByRole("dialog", { name: "Prévia ampliada de FOTO_001.jpg" })).toBeTruthy();
    fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  });
});
