import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("next/link", () => ({ default: ({ children, href }: { children: React.ReactNode; href: string }) => <a href={href}>{children}</a> }));
vi.mock("next/navigation", () => ({ useParams: () => ({ galleryId: "public-1" }) }));

import PublicGalleryPage from "./[galleryId]/page";

afterEach(() => vi.restoreAllMocks());

function response(value: object, status = 200) { return Promise.resolve(new Response(JSON.stringify(value), { status })); }

describe("Galeria pública da cliente", () => {
  it("carrega somente após autorização e cria a privada na primeira seleção", async () => {
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/photos/photo-1/selection") && init?.method === "POST") return response({ status: "selected", private_gallery_id: "private-1", gallery_created: true, reference_created: true, selection_created: true }, 201);
      if (path.endsWith("/photos")) return response({ photos: [{ id: "photo-1", name: "Foto 1", preview_url: "/public-galleries/public-1/photos/photo-1/preview" }] });
      return response({ id: "public-1", name: "Festa escolar", event_name: "Formatura", description: "Escolha suas fotos", access_mode: "standard", photos_url: "/public-galleries/public-1/photos" });
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<PublicGalleryPage />);
    expect(screen.getByText("Abrindo Galeria pública")).toBeTruthy();
    fireEvent.click(await screen.findByRole("button", { name: "Selecionar foto" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/public-galleries/public-1/photos/photo-1/selection",
      expect.objectContaining({ method: "POST", credentials: "same-origin" }),
    ));
    expect(await screen.findByText("Sua galeria privada foi criada com esta seleção.")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Abrir minha galeria privada" }).getAttribute("href")).toBe("/gallery/private-1");
    expect((screen.getByRole("button", { name: "Selecionada" }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("não mostra grade coletiva ou não autorizada quando o backend nega", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "Acesso não autorizado." }), { status: 403 })));
    render(<PublicGalleryPage />);
    expect(await screen.findByText("Galeria indisponível")).toBeTruthy();
    expect(screen.queryByRole("img")).toBeNull();
    expect(screen.queryByRole("button", { name: "Selecionar foto" })).toBeNull();
  });

  it("mantém a grade e informa erro sem simular seleção", async () => {
    vi.stubGlobal("fetch", vi.fn((path: string, init?: RequestInit) => {
      if (init?.method === "POST") return response({ detail: "Prazo de seleção expirado." }, 409);
      if (path.endsWith("/photos")) return response({ photos: [{ id: "photo-1", name: "Foto 1", preview_url: "/preview" }] });
      return response({ id: "public-1", name: "Festa", event_name: null, description: null, access_mode: "invite_only", photos_url: "/photos" });
    }));
    render(<PublicGalleryPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Selecionar foto" }));
    expect(await screen.findByText("Prazo de seleção expirado.")).toBeTruthy();
    expect((screen.getByRole("button", { name: "Selecionar foto" }) as HTMLButtonElement).disabled).toBe(false);
  });
});
