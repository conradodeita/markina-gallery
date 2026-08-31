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
    expect(await screen.findByRole("heading", { name: "Festa escolar", level: 1 })).toBeTruthy();
    expect(screen.getByRole("region", { name: "Resumo da seleção" }).textContent).toContain("0 fotos");
    expect(screen.getByText("nova")).toBeTruthy();
    expect(screen.getByText("já comprada")).toBeTruthy();
    expect(screen.getAllByRole("button", { name: "☆ Favoritar" }).length).toBe(2);
    expect(screen.getByRole("button", { name: /Novas fotos/ })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /Já compradas/ }));
    expect(screen.getByRole("img", { name: "Prévia protegida de IMG_002.jpg" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /Todas/ }));
    expect(
      screen.getByRole("img", { name: "Prévia protegida de IMG_001.jpg" }).getAttribute("src"),
    ).toBe("/api/gallery/gallery-1/photos/new-1/preview");
    expect(screen.getByRole("img", { name: "Prévia protegida de IMG_001.jpg" }).getAttribute("draggable")).toBe("false");
    expect(screen.getByRole("img", { name: "Capa de Festa escolar" }).getAttribute("src")).toBe("/api/gallery/gallery-1/photos/new-1/preview");
    const presentation = screen.getByRole("region", { name: "Apresentação de Festa escolar" });
    const selectionSummary = screen.getByRole("region", { name: "Resumo da seleção" });
    expect(Boolean(presentation.compareDocumentPosition(selectionSummary) & Node.DOCUMENT_POSITION_FOLLOWING)).toBe(true);
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

  it("mantém fotos administrativas com seleção zerada", async () => {
    const administrativeReview = {
      ...review,
      photos: review.photos.slice(0, 1),
    };
    vi.stubGlobal("fetch", vi.fn((path: string) => Promise.resolve(new Response(JSON.stringify(
      path.endsWith("/comments") ? { comments: [] } : path.endsWith("/folders") ? { folders: [] } : administrativeReview,
    ), { status: 200 }))));
    render(<GalleryPage />);
    expect(await screen.findByRole("heading", { name: "Festa escolar" })).toBeTruthy();
    expect(screen.getByRole("region", { name: "Resumo da seleção" }).textContent).toContain("0 fotos");
    expect(screen.getByRole("img", { name: "Prévia protegida de IMG_001.jpg" })).toBeTruthy();
    expect(screen.getByText("Disponível para revisão")).toBeTruthy();
  });

  it("explica o encerramento e retorna à Galeria pública autorizada", async () => {
    const fetchMock = vi.fn((path: string, options?: RequestInit) => {
      if (options?.method === "DELETE" && path.endsWith("/selection")) {
        return Promise.resolve(new Response(null, {
          status: 204,
          headers: {
            "X-Markina-Gallery-Closed": "true",
            "X-Markina-Public-Gallery-Url": "/public-galleries/public-1",
          },
        }));
      }
      if (path.endsWith("/cart")) return Promise.resolve(new Response(JSON.stringify({ quantity: 1, items: [{ id: "new-1", name: "IMG_001.jpg" }] }), { status: 200 }));
      if (path.endsWith("/comments")) return Promise.resolve(new Response(JSON.stringify({ comments: [] }), { status: 200 }));
      if (path.endsWith("/folders")) return Promise.resolve(new Response(JSON.stringify({ folders: [] }), { status: 200 }));
      return Promise.resolve(new Response(JSON.stringify({ ...review, photos: review.photos.slice(0, 1) }), { status: 200 }));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<GalleryPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Remover do carrinho" }));
    expect(await screen.findByText("Esta galeria privada foi encerrada")).toBeTruthy();
    expect(screen.getByText(/histórico de compras continuam preservados/i)).toBeTruthy();
    expect(screen.getByRole("link", { name: "Voltar à Galeria pública" }).getAttribute("href")).toBe("/public-galleries/public-1");
    expect(screen.getByRole("link", { name: "Ver minha biblioteca" }).getAttribute("href")).toBe("/library");
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

  it("mostra o total do carrinho e cria pedido PIX pendente", async () => {
    const fetchMock = vi.fn((path: string, options?: RequestInit) => {
      if (path.endsWith("/cart")) return Promise.resolve(new Response(JSON.stringify({ quantity: 1, unit_price_cents: 700, total_cents: 700 }), { status: 200 }));
      if (path.endsWith("/checkout")) return Promise.resolve(new Response(JSON.stringify({ id: "order-1", total_cents: 700, payment_status: "pending" }), { status: 201 }));
      if (path.endsWith("/folders")) return Promise.resolve(new Response(JSON.stringify({ folders: [{ id: "folder-1", name: "Apresentação", position: 0, photo_count: 2 }] }), { status: 200 }));
      if (path.endsWith("/comments")) return Promise.resolve(new Response(JSON.stringify({ comments: [] }), { status: 200 }));
      void options;
      return Promise.resolve(new Response(JSON.stringify(review), { status: 200 }));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<GalleryPage />);
    expect(await screen.findByText(/total estimado R\$ 7,00/i)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /finalizar 1 foto por pix/i }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/gallery/gallery-1/checkout", expect.objectContaining({ method: "POST" })));
    expect(await screen.findByText(/pedido pendente de confirmação/i)).toBeTruthy();
    expect(screen.getByText(/confirmação não é automática/i)).toBeTruthy();
  });

  it("remove uma foto diretamente do carrinho privado", async () => {
    const fetchMock = vi.fn((path: string, options?: RequestInit) => {
      if (path.endsWith("/cart")) return Promise.resolve(new Response(JSON.stringify({ quantity: 1, items: [{ id: "new-1", name: "IMG_001.jpg" }] }), { status: 200 }));
      if (path.endsWith("/folders")) return Promise.resolve(new Response(JSON.stringify({ folders: [{ id: "folder-1", name: "Apresentação", position: 0, photo_count: 2 }] }), { status: 200 }));
      if (path.endsWith("/comments")) return Promise.resolve(new Response(JSON.stringify({ comments: [] }), { status: 200 }));
      void options;
      return Promise.resolve(new Response(JSON.stringify(review), { status: 200 }));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<GalleryPage />);
    expect(await screen.findByRole("list", { name: "Fotos no carrinho" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Remover do carrinho" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/gallery/gallery-1/photos/new-1/selection",
      expect.objectContaining({ method: "DELETE" }),
    ));
  });

  it("comunica o PIX e acompanha a revisão sem confirmar automaticamente", async () => {
    let reported = false;
    const fetchMock = vi.fn((path: string, options?: RequestInit) => {
      if (path.endsWith("/payment-communications") && path.includes("/orders/") && options?.method === "POST") {
        reported = true;
        return Promise.resolve(new Response(JSON.stringify({ id: "communication-1", status: "pending_review" }), { status: 201 }));
      }
      if (path.endsWith("/payment-communications")) return Promise.resolve(new Response(JSON.stringify({ orders: [{
        order_id: "order-1", total_cents: 700, payment_status: "pending",
        communication: reported ? { id: "communication-1", status: "pending_review" } : null,
        notification: null,
      }] }), { status: 200 }));
      if (path.endsWith("/cart")) return Promise.resolve(new Response(JSON.stringify({ quantity: 0 }), { status: 200 }));
      if (path.endsWith("/folders")) return Promise.resolve(new Response(JSON.stringify({ folders: [{ id: "folder-1", name: "Apresentação", position: 0, photo_count: 2 }] }), { status: 200 }));
      if (path.endsWith("/comments")) return Promise.resolve(new Response(JSON.stringify({ comments: [] }), { status: 200 }));
      return Promise.resolve(new Response(JSON.stringify(review), { status: 200 }));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<GalleryPage />);
    expect(await screen.findByText("Pagamento ainda não comunicado")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Já fiz o PIX" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/gallery/gallery-1/orders/order-1/payment-communications",
      expect.objectContaining({ method: "POST" }),
    ));
    expect(await screen.findByText("Pagamento informado · aguardando revisão")).toBeTruthy();
    expect(screen.getByText(/Aguarde a revisão do fotógrafo/i)).toBeTruthy();
  });
});
