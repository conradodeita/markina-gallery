import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const push = vi.fn();

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
  useRouter: () => ({ push }),
}));

import GalleriesPage from "./page";
import GalleryDetailPage from "./[galleryId]/page";

afterEach(() => {
  vi.restoreAllMocks();
  push.mockReset();
});

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
            path.endsWith("/photos")
              ? { photos: [] }
              : path.endsWith("/members")
                ? { members: [] }
              : path.endsWith("/folders")
                ? { folders: [] }
              : path.endsWith("/facial-index")
                ? { state: "waiting", progress: { ready: 0, total: 0 }, coverage: { photos_with_faces: 0, total: 0, percent: 0, detected_faces: 0 } }
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
    expect(fetchMock).toHaveBeenCalledTimes(5);
  });

  it("organiza o acervo por pasta e mantém agregados e seleção de cada cliente", async () => {
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      const body = path.endsWith("/photos")
        ? { photos: [{ id: "photo-1", name: "FOTO_1.jpg", folder_id: "folder-1", folder_name: "Cerimônia", preview_url: "/admin/photo-assets/photo-1/watermarked-preview", origins: ["client"], ownership: "public_reference" }] }
        : path.endsWith("/members")
          ? { members: [{ membership_id: "member-1", client_id: "client-1", client_name: "Ana", phone_e164: "+5511999999999", status: "active", selected_count: 2, purchased_count: 1, order_count: 1, confirmed_total_cents: 700, payment_status: "confirmed" }, { membership_id: "member-2", client_id: "client-2", client_name: "Bia", phone_e164: "+5511888888888", status: "active", selected_count: 5, purchased_count: 0, order_count: 0, confirmed_total_cents: 0, payment_status: "none" }] }
          : path.endsWith("/folders")
            ? { folders: [] }
          : path.endsWith("/facial-index")
            ? { state: "completed", progress: { ready: 1, total: 1 }, coverage: { photos_with_faces: 1, total: 1, percent: 100, detected_faces: 1 } }
            : { id: "private-1", parent_gallery_id: "public-1", name: "Família", custom_message: "Escolha com calma", favorites_enabled: true, comments_enabled: true, selection_expires_at: null, cover_preview_url: null, frozen: false, blocked: false };
      if (init?.method === "POST") return Promise.resolve(new Response(JSON.stringify({ references_created: 1 }), { status: 200 }));
      return Promise.resolve(new Response(JSON.stringify(body), { status: 200 }));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<GalleryDetailPage />);

    expect(await screen.findByRole("heading", { name: "Família" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Seleções vindas da Galeria pública" })).toBeTruthy();
    expect(screen.getByText("Cerimônia")).toBeTruthy();
    expect(screen.getByAltText("Prévia protegida de FOTO_1.jpg")).toBeTruthy();
    expect(screen.getAllByRole("link", { name: "Abrir seleção individual" })[0].getAttribute("href")).toBe("/admin/galleries/private-1/selection?client=client-1");
    expect(screen.getByText("2", { selector: ".private-member-cards dd" })).toBeTruthy();
    expect(screen.getByText("5", { selector: ".private-member-cards dd" })).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Adicionar ao acervo privado" })).toBeNull();
  });

  it("abre a privada preservada sem consultar fotos de uma origem removida", async () => {
    const fetchMock = vi.fn((path: string) => {
      if (path.endsWith("/photos")) return Promise.resolve(new Response(JSON.stringify({ photos: [] }), { status: 200 }));
      if (path.endsWith("/members")) return Promise.resolve(new Response(JSON.stringify({ members: [] }), { status: 200 }));
      return Promise.resolve(new Response(JSON.stringify({ id: "private-1", parent_gallery_id: "public-removed", name: "Privada preservada", custom_message: "", favorites_enabled: false, comments_enabled: false, selection_expires_at: null, cover_preview_url: null, origin_active: false, frozen: false, blocked: false }), { status: 200 }));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<GalleryDetailPage />);

    expect(await screen.findByRole("heading", { name: "Privada preservada" })).toBeTruthy();
    expect(screen.getByText("Galeria pública de origem removida")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Excluir galeria privada" })).toBeTruthy();
    expect(screen.queryByRole("link", { name: "Carregar novos JPEGs na pública" })).toBeNull();
    expect(fetchMock).not.toHaveBeenCalledWith(
      "/api/admin/parent-galleries/public-removed/available-photos",
    );
  });

  it("confirma e exclui uma galeria privada preservando o histórico", async () => {
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      const body = path.endsWith("/photos") || path.endsWith("/available-photos")
        ? { photos: [] }
        : path.endsWith("/members")
          ? { members: [] }
          : { id: "private-1", parent_gallery_id: "public-1", name: "Família Silva", custom_message: "", favorites_enabled: false, comments_enabled: false, selection_expires_at: null, cover_preview_url: null, frozen: false, blocked: false };
      if (path === "/api/admin/derived-galleries/private-1" && init?.method === "DELETE") return Promise.resolve(new Response(null, { status: 204 }));
      return Promise.resolve(new Response(JSON.stringify(body), { status: 200 }));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<GalleryDetailPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Excluir galeria privada" }));
    const dialog = await screen.findByRole("dialog", { name: "Excluir “Família Silva”?" });
    expect(dialog.textContent).toContain("histórico comercial serão preservados");
    fireEvent.click(screen.getByRole("button", { name: "Confirmar exclusão" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/admin/derived-galleries/private-1",
      expect.objectContaining({ method: "DELETE" }),
    ));
    expect(push).toHaveBeenCalledWith("/admin/galleries");
  });

  it("mantém a falha de exclusão visível dentro da confirmação da privada", async () => {
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      const body = path.endsWith("/photos") || path.endsWith("/available-photos")
        ? { photos: [] }
        : path.endsWith("/members")
          ? { members: [] }
          : { id: "private-1", parent_gallery_id: "public-1", name: "Família Protegida", custom_message: "", favorites_enabled: false, comments_enabled: false, selection_expires_at: null, cover_preview_url: null, frozen: false, blocked: false };
      if (path === "/api/admin/derived-galleries/private-1" && init?.method === "DELETE") return Promise.resolve(new Response(JSON.stringify({ detail: "Pagamento comunicado aguarda revisão administrativa." }), { status: 409, headers: { "content-type": "application/json" } }));
      return Promise.resolve(new Response(JSON.stringify(body), { status: 200 }));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<GalleryDetailPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Excluir galeria privada" }));
    fireEvent.click(screen.getByRole("button", { name: "Confirmar exclusão" }));
    const dialog = await screen.findByRole("dialog", { name: "Excluir “Família Protegida”?" });
    expect(await within(dialog).findByRole("alert")).toHaveProperty("textContent", "Pagamento comunicado aguarda revisão administrativa.");
    expect(push).not.toHaveBeenCalled();
  });

  it("carrega JPEGs do dispositivo somente em pasta própria da privada", async () => {
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/photos") && !init?.method) return Promise.resolve(new Response(JSON.stringify({ photos: [] }), { status: 200 }));
      if (path.endsWith("/folders") && !init?.method) return Promise.resolve(new Response(JSON.stringify({ folders: [{ id: "folder-private", name: "Uploads", status: "preparing", photo_count: 0 }] }), { status: 200 }));
      if (path.endsWith("/members")) return Promise.resolve(new Response(JSON.stringify({ members: [] }), { status: 200 }));
      if (path.endsWith("/facial-index")) return Promise.resolve(new Response(JSON.stringify({ state: "waiting", progress: { ready: 0, total: 0 }, coverage: { photos_with_faces: 0, total: 0, percent: 0, detected_faces: 0 } }), { status: 200 }));
      if (path === "/api/admin/photo-folders/folder-private/photos" && init?.method === "POST") return Promise.resolve(new Response(JSON.stringify({ id: "photo-private" }), { status: 201 }));
      if (init?.method === "PUT" || path.endsWith("/publish")) return Promise.resolve(new Response(JSON.stringify({ status: "preparing" }), { status: 202 }));
      return Promise.resolve(new Response(JSON.stringify({ id: "private-1", parent_gallery_id: "public-1", name: "Família", custom_message: "", selection_expires_at: null, frozen: false, blocked: false }), { status: 200 }));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<GalleryDetailPage />);
    await screen.findByRole("heading", { name: "Família" });
    fireEvent.change(screen.getByLabelText("Pasta"), { target: { value: "folder-private" } });
    const file = new File([new Uint8Array([0xff, 0xd8, 0xff, 0xd9])], "nova.jpg", { type: "image/jpeg" });
    fireEvent.change(screen.getByLabelText("JPEGs do dispositivo"), { target: { files: [file] } });
    fireEvent.submit(screen.getByLabelText("JPEGs do dispositivo").closest("form")!);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/admin/photo-assets/photo-private/source",
      expect.objectContaining({ method: "PUT", body: file }),
    ));
    const registration = fetchMock.mock.calls.find(([path, init]) => path === "/api/admin/photo-folders/folder-private/photos" && init?.method === "POST");
    expect(String(registration?.[1]?.body)).toContain("private/private-1/folder-private/");
  });
});
