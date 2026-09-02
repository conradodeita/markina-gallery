import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("next/link", () => ({
  default: ({
    children,
    href,
  }: {
    children: React.ReactNode;
    href: string;
  }) => <a href={href}>{children}</a>,
}));
vi.mock("next/navigation", () => ({
  useParams: () => ({ galleryId: "private-1" }),
  useRouter: () => ({ push: vi.fn() }),
}));

import GalleriesPage from "./page";
import GalleryDetailPage from "./[galleryId]/page";

afterEach(() => vi.restoreAllMocks());

describe("telas administrativas de galerias", () => {
  it("exibe carregamento e o estado vazio de Galerias públicas", async () => {
    let resolveFetch: (value: Response) => void;
    vi.stubGlobal(
      "fetch",
      vi.fn(
        () =>
          new Promise<Response>((resolve) => {
            resolveFetch = resolve;
          }),
      ),
    );
    render(<GalleriesPage />);
    expect(screen.getByText("Carregando galerias…")).toBeTruthy();
    expect(screen.getByRole("tab", { name: "Galerias públicas" })).toBeTruthy();
    expect(screen.queryByText(/Galerias-mãe/i)).toBeNull();
    resolveFetch!(
      new Response(JSON.stringify({ parent_galleries: [] }), { status: 200 }),
    );
    expect(
      await screen.findByText("Nenhum resultado nesta visão."),
    ).toBeTruthy();
  });
  it("apresenta erro de carregamento", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(null, { status: 500 })),
    );
    render(<GalleriesPage />);
    expect((await screen.findByRole("alert")).textContent).toContain(
      "Não foi possível carregar as galerias.",
    );
  });
  it("consulta galerias privadas pelo termo de busca", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ parent_galleries: [] }), { status: 200 }),
      );
    vi.stubGlobal("fetch", fetchMock);
    render(<GalleriesPage />);
    await screen.findByText("Nenhum resultado nesta visão.");
    fireEvent.click(screen.getByRole("tab", { name: "Galerias privadas" }));
    await waitFor(() =>
      expect(fetchMock).toHaveBeenLastCalledWith(
        "/api/admin/derived-galleries?tab=active",
        { credentials: "same-origin" },
      ),
    );
    fireEvent.change(
      screen.getByLabelText("Buscar por galeria, nome ou telefone"),
      { target: { value: "Maria" } },
    );
    await waitFor(() =>
      expect(fetchMock).toHaveBeenLastCalledWith(
        "/api/admin/derived-galleries?tab=active&query=Maria",
        { credentials: "same-origin" },
      ),
    );
  });
  it("exige confirmação antes de bloquear uma galeria privada", async () => {
    const fetchMock = vi.fn((path: string) =>
      Promise.resolve(
        new Response(
          JSON.stringify(
            path.endsWith("/photos") || path.endsWith("/available-photos")
              ? { photos: [] }
              : path.endsWith("/members")
                ? { members: [] }
              : {
                  id: "private-1",
                  parent_gallery_id: "public-1",
                  name: "Família Silva",
                  link: null,
                  custom_message: "",
                  favorites_enabled: false,
                  comments_enabled: false,
                  selection_expires_at: null,
                  cover_preview_url: null,
                  client: null,
                  responsible: null,
                  frozen: false,
                  blocked: false,
                },
          ),
          { status: 200 },
        ),
      ),
    );
    vi.stubGlobal("fetch", fetchMock);
    vi.stubGlobal(
      "confirm",
      vi.fn(() => false),
    );
    render(<GalleryDetailPage />);
    await screen.findByRole("button", { name: "Bloquear acesso geral" });
    fireEvent.click(screen.getByRole("button", { name: "Bloquear acesso geral" }));
    expect(window.confirm).toHaveBeenCalledWith(
      "Bloquear o acesso desta galeria privada para todos os membros?",
    );
    expect(fetchMock).toHaveBeenCalledTimes(4);
  });

  it("organiza o acervo por pasta e mantém agregados e seleção de cada cliente", async () => {
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      const body = path.endsWith("/photos")
        ? { photos: [{ id: "photo-1", name: "FOTO_1.jpg", folder_id: "folder-1", folder_name: "Cerimônia", preview_url: "/admin/photo-assets/photo-1/watermarked-preview", origins: ["admin", "client"] }] }
        : path.endsWith("/members")
          ? { members: [{ membership_id: "member-1", client_id: "client-1", client_name: "Ana", phone_e164: "+5511999999999", status: "active", selected_count: 2, purchased_count: 1, order_count: 1, confirmed_total_cents: 700, payment_status: "confirmed" }, { membership_id: "member-2", client_id: "client-2", client_name: "Bia", phone_e164: "+5511888888888", status: "active", selected_count: 5, purchased_count: 0, order_count: 0, confirmed_total_cents: 0, payment_status: "none" }] }
          : path.endsWith("/available-photos")
            ? { photos: [{ id: "photo-1", name: "FOTO_1.jpg", folder_name: "Cerimônia", preview_url: "/preview-1" }, { id: "photo-2", name: "FOTO_2.jpg", folder_name: "Recepção", preview_url: "/preview-2" }] }
            : { id: "private-1", parent_gallery_id: "public-1", name: "Família", custom_message: "Escolha com calma", favorites_enabled: true, comments_enabled: true, selection_expires_at: null, cover_preview_url: null, frozen: false, blocked: false };
      if (init?.method === "POST") return Promise.resolve(new Response(JSON.stringify({ references_created: 1 }), { status: 200 }));
      return Promise.resolve(new Response(JSON.stringify(body), { status: 200 }));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<GalleryDetailPage />);

    expect(await screen.findByRole("heading", { name: "Família" })).toBeTruthy();
    expect(screen.getByText("Cerimônia", { selector: ".private-folder-list strong" })).toBeTruthy();
    expect(screen.getByAltText("Prévia protegida de FOTO_1.jpg")).toBeTruthy();
    expect(screen.getAllByRole("link", { name: "Abrir seleção individual" })[0].getAttribute("href")).toBe("/admin/galleries/private-1/selection?client=client-1");
    expect(screen.getByText("2", { selector: ".private-member-cards dd" })).toBeTruthy();
    expect(screen.getByText("5", { selector: ".private-member-cards dd" })).toBeTruthy();
    fireEvent.click(screen.getByText("FOTO_2.jpg").closest("label")!.querySelector("input")!);
    fireEvent.click(screen.getByRole("button", { name: "Adicionar ao acervo privado" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/admin/derived-galleries/private-1/photos",
      expect.objectContaining({ method: "POST", body: JSON.stringify({ photo_ids: ["photo-2"] }) }),
    ));
  });
});
