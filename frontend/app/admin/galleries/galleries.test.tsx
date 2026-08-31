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
            path.endsWith("/clients")
              ? { clients: [] }
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
    await screen.findByRole("button", { name: "Bloquear acesso" });
    fireEvent.click(screen.getByRole("button", { name: "Bloquear acesso" }));
    expect(window.confirm).toHaveBeenCalledWith(
      "Bloquear o acesso desta galeria privada?",
    );
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
