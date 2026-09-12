import { readFileSync } from "node:fs";
import { join } from "node:path";

import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const navigation = vi.hoisted(() => ({ mode: null as string | null }));
vi.mock("next/navigation", () => ({
  useParams: () => ({ galleryId: "gallery-1" }),
  useSearchParams: () => ({ get: (name: string) => name === "mode" ? navigation.mode : null }),
}));

import GalleryPage from "./[galleryId]/page";

afterEach(() => {
  vi.restoreAllMocks();
  navigation.mode = null;
});

const review = {
  gallery: { name: "Festa escolar", message: "Escolha suas favoritas", selection_expires_at: null, selection_open: true, favorites_enabled: true, comments_enabled: true, cover_preview_url: "/gallery/gallery-1/photos/new-1/preview" },
  photos: [
    { id: "new-1", name: "IMG_001.jpg", folder_id: "folder-1", preview_url: "/gallery/gallery-1/photos/new-1/preview", selected: false, favorited: false, purchase_state: "nova" },
    { id: "bought-1", name: "IMG_002.jpg", folder_id: "folder-1", preview_url: "/gallery/gallery-1/photos/bought-1/preview", selected: false, favorited: false, purchase_state: "já comprada" },
  ],
};

describe("galeria privada da cliente", () => {
  it("mostra a revisão sem aguardar a listagem complementar de pastas", async () => {
    let finishFolders!: (value: Response) => void;
    const foldersResponse = new Promise<Response>((resolve) => { finishFolders = resolve; });
    vi.stubGlobal("fetch", vi.fn((path: string) => {
      if (path.endsWith("/folders")) return foldersResponse;
      return Promise.resolve(new Response(JSON.stringify(
        path.endsWith("/comments") ? { comments: [] }
          : path.endsWith("/cart") ? { quantity: 0, items: [] }
            : path.endsWith("/payment-communications") ? { orders: [] }
              : path.endsWith("/reopening-requests") ? { request: null }
                : review,
      ), { status: 200 }));
    }));

    render(<GalleryPage />);

    expect(await screen.findByRole("heading", { name: "Festa escolar", level: 1 })).toBeTruthy();
    expect(screen.getByRole("img", { name: "Prévia protegida de IMG_001.jpg" })).toBeTruthy();

    await act(async () => {
      finishFolders(new Response(JSON.stringify({ folders: [{ id: "folder-1", name: "Apresentação", position: 0, photo_count: 2 }] }), { status: 200 }));
    });
    expect(await screen.findByRole("heading", { name: "Apresentação" })).toBeTruthy();
  });

  it("conta estados comerciais e diferencia os pedidos sem mostrar capa vazia", async () => {
    const commercialReview = {
      ...review,
      photos: [
        { ...review.photos[0], id: "available-1", name: "Disponível.jpg", commercial_state: "available" },
        { ...review.photos[0], id: "selected-1", name: "Carrinho.jpg", selected: true, commercial_state: "selected" },
        { ...review.photos[0], id: "awaiting-1", name: "Aguardando.jpg", commercial_state: "awaiting_payment" },
        { ...review.photos[0], id: "reported-1", name: "Informada.jpg", commercial_state: "payment_reported" },
        { ...review.photos[1], id: "purchased-1", name: "Comprada.jpg", commercial_state: "purchased" },
      ],
    };
    const orders = [
      { order_id: "awaiting-order", total_cents: 700, payment_status: "pending", commercial_state: "awaiting_payment", communication: null, notification: null, items: [] },
      { order_id: "reported-order", total_cents: 700, payment_status: "pending", commercial_state: "payment_reported", communication: { id: "communication-1", status: "pending_review" }, notification: null, items: [] },
      { order_id: "confirmed-order", total_cents: 700, payment_status: "confirmed", commercial_state: "purchased", communication: { id: "communication-2", status: "confirmed" }, notification: null, items: [] },
    ];
    vi.stubGlobal("fetch", vi.fn((path: string) => Promise.resolve(new Response(JSON.stringify(
      path.endsWith("/comments") ? { comments: [] }
        : path.endsWith("/folders") ? { folders: [{ id: "folder-1", name: "Apresentação", position: 0, photo_count: 5 }] }
          : path.endsWith("/cart") ? { quantity: 1, items: [] }
            : path.endsWith("/payment-communications") ? { orders }
              : path.endsWith("/reopening-requests") ? { request: null }
                : commercialReview,
    ), { status: 200 }))));

    render(<GalleryPage />);

    const filters = await screen.findByRole("navigation", { name: "Filtrar fotos" });
    expect(within(filters).getByRole("button", { name: /Todas/ }).textContent).toContain("5");
    expect(within(filters).getByRole("button", { name: /Carrinho/ }).textContent).toContain("1");
    expect(within(filters).getByRole("button", { name: /Aguardando pagamento/ }).textContent).toContain("1");
    expect(within(filters).getByRole("button", { name: /Pagamento informado/ }).textContent).toContain("1");
    expect(within(filters).getByRole("button", { name: /Compradas/ }).textContent).toContain("1");
    expect(screen.queryByText("Capa ainda não definida")).toBeNull();
    fireEvent.click(within(filters).getByRole("button", { name: /Pagamento informado/ }));
    expect(screen.getByRole("img", { name: "Prévia protegida de Informada.jpg" })).toBeTruthy();
    expect(screen.queryByRole("img", { name: "Prévia protegida de Disponível.jpg" })).toBeNull();

    expect(screen.getByRole("article", { name: /Pedido awaiting-/ }).className).toContain("client-order-resume--awaiting-payment");
    expect(screen.getByRole("article", { name: /Pedido reported-/ }).className).toContain("client-order-resume--payment-reported");
    expect(screen.getByRole("article", { name: /Pedido confirmed-/ }).className).toContain("client-order-resume--purchased");
    const css = readFileSync(join(process.cwd(), "app", "globals.css"), "utf8");
    expect(css).toContain(".client-payment-orders { display:grid; gap:18px; }");
    expect(css).toContain(".client-order-resume--awaiting-payment");
    expect(css).toContain(".client-order-resume--payment-reported");
    expect(css).toContain(".client-order-resume--purchased");
  });

  it("não expõe falha técnica do WhatsApp à cliente após confirmar o pagamento", async () => {
    const confirmedReview = {
      ...review,
      photos: [{ ...review.photos[1], commercial_state: "purchased" }],
    };
    const confirmedOrder = {
      order_id: "confirmed-order",
      total_cents: 700,
      payment_status: "confirmed",
      commercial_state: "purchased",
      communication: { id: "communication-1", status: "confirmed" },
      notification: { status: "failed", last_error: "provider timeout" },
      items: [],
    };
    vi.stubGlobal("fetch", vi.fn((path: string) => Promise.resolve(new Response(JSON.stringify(
      path.endsWith("/comments") ? { comments: [] }
        : path.endsWith("/folders") ? { folders: [{ id: "folder-1", name: "Apresentação", position: 0, photo_count: 1 }] }
          : path.endsWith("/cart") ? { quantity: 0, items: [] }
            : path.endsWith("/payment-communications") ? { orders: [confirmedOrder] }
              : path.endsWith("/reopening-requests") ? { request: null }
                : confirmedReview,
    ), { status: 200 }))));

    render(<GalleryPage />);

    expect(await screen.findByText("Pagamento confirmado")).toBeTruthy();
    expect(screen.getAllByText("Comprada").length).toBeGreaterThan(0);
    expect(screen.queryByText(/WhatsApp falhou/i)).toBeNull();
    expect(screen.queryByText(/status acima continua válido/i)).toBeNull();
    expect(screen.queryByText(/provider timeout/i)).toBeNull();
  });

  it("retoma a etapa PIX do rascunho salvo após recarregar", async () => {
    const fetchMock = vi.fn((path: string) => Promise.resolve(new Response(JSON.stringify(
      path.endsWith("/comments") ? { comments: [] }
        : path.endsWith("/folders") ? { folders: [{ id: "folder-1", name: "Apresentação", position: 0, photo_count: 2 }] }
          : path.endsWith("/cart") ? { quantity: 1, total_cents: 700, draft_order_id: "draft-1", items: [{ id: "new-1", name: "IMG_001.jpg", preview_url: "/gallery/gallery-1/photos/new-1/preview" }] }
            : path.endsWith("/orders/draft-1") ? { id: "draft-1", total_cents: 700, items: [{ photo_id: "new-1", name: "IMG_001.jpg", unit_price_cents: 700, preview_url: "/gallery/gallery-1/photos/new-1/preview" }], pix: { copy_paste: "PIX", qr_png_data_url: null, instructions: null, confirmation: "Manual" } }
              : path.endsWith("/payment-communications") ? { orders: [] }
                : path.endsWith("/reopening-requests") ? { request: null }
                  : review,
    ), { status: 200 })));
    vi.stubGlobal("fetch", fetchMock);
    render(<GalleryPage />);

    expect(await screen.findByRole("heading", { name: "Revise suas fotos e faça o PIX" })).toBeTruthy();
    expect(screen.getByText("PIX copia e cola")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Informar pagamento" })).toBeTruthy();
  });

  it("retoma carrinho e pedido comunicado com fotos após recarregar", async () => {
    const commercialReview = {
      ...review,
      photos: [
        { ...review.photos[0], selected: true, purchase_state: "selected" },
        { ...review.photos[1], selected: false, purchase_state: "payment_reported" },
      ],
    };
    const fetchMock = vi.fn((path: string) => Promise.resolve(new Response(JSON.stringify(
      path.endsWith("/comments") ? { comments: [] }
        : path.endsWith("/folders") ? { folders: [{ id: "folder-1", name: "Apresentação", position: 0, photo_count: 2 }] }
          : path.endsWith("/cart") ? { quantity: 1, total_cents: 700, items: [{ id: "new-1", name: "IMG_001.jpg", preview_url: "/gallery/gallery-1/photos/new-1/preview" }] }
            : path.endsWith("/payment-communications") ? { orders: [{ order_id: "order-1", total_cents: 700, payment_status: "pending", frozen_at: "2026-09-10T12:00:00Z", communication: { id: "communication-1", status: "pending_review" }, notification: null, items: [{ photo_id: "bought-1", name: "IMG_002.jpg", preview_url: "/gallery/gallery-1/photos/bought-1/preview", unit_price_cents: 700 }] }] }
              : path.endsWith("/reopening-requests") ? { request: null }
                : commercialReview,
    ), { status: 200 })));
    vi.stubGlobal("fetch", fetchMock);
    render(<GalleryPage />);

    expect(await screen.findByRole("link", { name: "Carrinho (1)" })).toBeTruthy();
    expect(screen.getAllByText("Pagamento informado").length).toBeGreaterThan(0);
    expect(screen.getByRole("img", { name: "Miniatura protegida de IMG_002.jpg" })).toBeTruthy();
  });

  it("mostra estados e impede nova seleção de foto já comprada", async () => {
    const fetchMock = vi.fn((path: string) => Promise.resolve(new Response(JSON.stringify(path.endsWith("/comments") ? { comments: [] } : path.endsWith("/folders") ? { folders: [{ id: "folder-1", name: "Apresentação", position: 0, photo_count: 2 }] } : review), { status: 200 })));
    vi.stubGlobal("fetch", fetchMock);
    render(<GalleryPage />);
    expect(await screen.findByRole("heading", { name: "Festa escolar", level: 1 })).toBeTruthy();
    expect(screen.queryByRole("complementary", { name: "Resumo da seleção" })).toBeNull();
    expect(screen.queryByText("nova")).toBeNull();
    expect(screen.getAllByText("Comprada").length).toBeGreaterThan(0);
    expect(screen.getAllByRole("button", { name: "Favoritar" }).length).toBe(2);
    expect(screen.queryByText("Favoritar")).toBeNull();
    expect(screen.getByRole("button", { name: /Carrinho/ })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /Compradas/ }));
    expect(screen.getByRole("img", { name: "Prévia protegida de IMG_002.jpg" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /Todas/ }));
    expect(
      screen.getByRole("img", { name: "Prévia protegida de IMG_001.jpg" }).getAttribute("src"),
    ).toBe("/api/gallery/gallery-1/photos/new-1/preview");
    expect(screen.getByRole("img", { name: "Prévia protegida de IMG_001.jpg" }).getAttribute("draggable")).toBe("false");
    expect(screen.queryByRole("img", { name: "Capa de Festa escolar" })).toBeNull();
    const presentation = screen.getByRole("region", { name: "Apresentação de Festa escolar" });
    expect(presentation).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Ampliar prévia protegida de IMG_001.jpg" }));
    expect(await screen.findByRole("dialog", { name: "Prévia ampliada de IMG_001.jpg" })).toBeTruthy();
    fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    const selectButtons = screen.getAllByRole("button", { name: "Selecionar" });
    expect(selectButtons).toHaveLength(1);
    expect(screen.getAllByText("Comprada").length).toBeGreaterThan(0);
    fireEvent.click(selectButtons[0]);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/gallery/gallery-1/photos/new-1/selection", expect.objectContaining({ method: "POST" })));
  });

  it("preserva a identificação das fotos após expirar e bloqueia nova seleção", async () => {
    const expiredReview = { ...review, gallery: { ...review.gallery, selection_open: false, selection_expires_at: "2026-08-01T23:59:59Z" } };
    const fetchMock = vi.fn((path: string, options?: RequestInit) => Promise.resolve(new Response(JSON.stringify(
      path.endsWith("/comments") ? { comments: [] }
        : path.endsWith("/folders") ? { folders: [] }
          : path.endsWith("/cart") ? { quantity: 2, total_cents: 1400 }
            : path.endsWith("/payment-communications") ? { orders: [] }
              : path.endsWith("/reopening-requests") && options?.method === "POST" ? { id: "reopening-1", status: "pending" }
                : path.endsWith("/reopening-requests") ? { request: null }
                  : expiredReview,
    ), { status: options?.method === "POST" ? 201 : 200 })));
    vi.stubGlobal("fetch", fetchMock);
    render(<GalleryPage />);
    expect(await screen.findByText(/prazo para novas seleções terminou/i)).toBeTruthy();
    expect(screen.getAllByText("IMG_001.jpg").length).toBeGreaterThan(0);
    for (const button of screen.getAllByRole("button", { name: "Selecionar" })) {
      expect((button as HTMLButtonElement).disabled).toBe(true);
    }
    expect(screen.queryByRole("complementary", { name: "Resumo da seleção" })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Solicitar reabertura da galeria" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/gallery/gallery-1/reopening-requests",
      expect.objectContaining({ method: "POST" }),
    ));
    expect(await screen.findByText(/Solicitação enviada ao fotógrafo/)).toBeTruthy();
  });

  it.each([
    {
      state: "seleção editável",
      cart: { quantity: 1, total_cents: 700 },
      orders: [],
      deadlineVisible: true,
    },
    {
      state: "pagamento informado",
      cart: { quantity: 0 },
      orders: [{ order_id: "order-reported", total_cents: 700, payment_status: "pending", commercial_state: "payment_reported", communication: { id: "communication-1", status: "pending_review" }, notification: null }],
      deadlineVisible: false,
    },
    {
      state: "sem seleção",
      cart: { quantity: 0 },
      orders: [],
      deadlineVisible: false,
    },
  ])("exibe o prazo contextual no estado $state", async ({ cart, orders, deadlineVisible }) => {
    const datedReview = {
      ...review,
      gallery: { ...review.gallery, selection_expires_at: "2026-09-30T23:59:59Z" },
    };
    vi.stubGlobal("fetch", vi.fn((path: string) => Promise.resolve(new Response(JSON.stringify(
      path.endsWith("/comments") ? { comments: [] }
        : path.endsWith("/folders") ? { folders: [] }
          : path.endsWith("/cart") ? cart
            : path.endsWith("/payment-communications") ? { orders }
              : path.endsWith("/reopening-requests") ? { request: null }
                : datedReview,
    ), { status: 200 }))));

    render(<GalleryPage />);
    expect(await screen.findByRole("heading", { name: "Festa escolar" })).toBeTruthy();
    if (deadlineVisible) {
      expect(await screen.findByText(/Seleções até 30\/09\/2026/)).toBeTruthy();
    } else {
      await waitFor(() => expect(screen.queryByText(/Seleções até/)).toBeNull());
    }
  });

  it("permite solicitar reabertura mesmo quando a galeria expirada ainda está vazia", async () => {
    const expiredEmptyReview = {
      ...review,
      gallery: { ...review.gallery, selection_open: false, selection_expires_at: "2026-08-01T23:59:59Z" },
      photos: [],
    };
    const fetchMock = vi.fn((path: string, options?: RequestInit) => Promise.resolve(new Response(JSON.stringify(
      path.endsWith("/comments") ? { comments: [] }
        : path.endsWith("/folders") ? { folders: [] }
          : path.endsWith("/cart") ? { quantity: 0, items: [] }
            : path.endsWith("/payment-communications") ? { orders: [] }
              : path.endsWith("/reopening-requests") && options?.method === "POST" ? { id: "reopening-empty", status: "pending" }
                : path.endsWith("/reopening-requests") ? { request: null }
                  : expiredEmptyReview,
    ), { status: options?.method === "POST" ? 201 : 200 })));
    vi.stubGlobal("fetch", fetchMock);

    render(<GalleryPage />);

    expect(await screen.findByText(/prazo para novas seleções terminou/i)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Solicitar reabertura da galeria" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/gallery/gallery-1/reopening-requests",
      expect.objectContaining({ method: "POST" }),
    ));
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
    expect(screen.queryByRole("complementary", { name: "Resumo da seleção" })).toBeNull();
    expect(screen.getByRole("img", { name: "Prévia protegida de IMG_001.jpg" })).toBeTruthy();
    expect(screen.queryByText("nova")).toBeNull();
    expect(screen.getByRole("button", { name: "Selecionar" })).toBeTruthy();
  });

  it("abre a revisão somente com fotos selecionadas e sem a capa editorial", async () => {
    navigation.mode = "review";
    const selectedReview = {
      ...review,
      photos: [
        { ...review.photos[0], selected: true },
        { ...review.photos[1], selected: false },
      ],
    };
    vi.stubGlobal("fetch", vi.fn((path: string) => Promise.resolve(new Response(JSON.stringify(
      path.endsWith("/comments") ? { comments: [] }
        : path.endsWith("/folders") ? { folders: [{ id: "folder-1", name: "Apresentação", position: 0, photo_count: 2 }] }
          : path.endsWith("/cart") ? { quantity: 1, total_cents: 700, items: [{ id: "new-1", name: "IMG_001.jpg" }], parcels: [{ minimum_quantity: 1, maximum_quantity: null, quantity: 1, unit_price_cents: 700, subtotal_cents: 700 }] }
            : path.endsWith("/payment-communications") ? { orders: [] }
              : selectedReview,
    ), { status: 200 }))));

    render(<GalleryPage />);

    expect(await screen.findByRole("img", { name: "Prévia protegida de IMG_001.jpg" })).toBeTruthy();
    expect(screen.queryByRole("img", { name: "Prévia protegida de IMG_002.jpg" })).toBeNull();
    expect(screen.queryByRole("img", { name: "Capa de Festa escolar" })).toBeNull();
    expect(screen.getByRole("button", { name: /Todas/ }).textContent).toContain("1");
    const summary = screen.getByLabelText("Resumo da seleção");
    expect(summary.textContent).toContain("1 foto");
    expect(summary.textContent?.replaceAll("\u00a0", " ")).toContain("R$ 7,00");
    expect(within(summary).getByText("Ver cálculo por faixas")).toBeTruthy();
    expect(within(summary).getByRole("button", { name: "Continuar para o PIX" })).toBeTruthy();
    expect(within(summary).queryByText("Revisar seleção")).toBeNull();
    expect(within(summary).queryByRole("list", { name: "Fotos no carrinho" })).toBeNull();

    fireEvent.contextMenu(screen.getByRole("button", { name: "Ampliar prévia protegida de IMG_001.jpg" }));
    expect(screen.getByRole("dialog", { name: "Conteúdo protegido por direitos autorais" })).toBeTruthy();
  });

  it("mostra e troca comentários somente no contexto da foto ampliada", async () => {
    const fetchMock = vi.fn((path: string, options?: RequestInit) => {
      if (options?.method === "DELETE" && path.endsWith("/comments/comment-1")) return Promise.resolve(new Response(null, { status: 204 }));
      if (options?.method === "POST" && path.endsWith("/photos/bought-1/comments")) return Promise.resolve(new Response(JSON.stringify({ id: "comment-3" }), { status: 201 }));
      if (path.endsWith("/comments")) return Promise.resolve(new Response(JSON.stringify({ comments: [
        { id: "comment-1", photo_id: "new-1", body: "Recortar à esquerda" },
        { id: "comment-2", photo_id: "bought-1", body: "Clarear esta foto" },
      ] }), { status: 200 }));
      if (path.endsWith("/folders")) return Promise.resolve(new Response(JSON.stringify({ folders: [{ id: "folder-1", name: "Apresentação", position: 0, photo_count: 2 }] }), { status: 200 }));
      if (path.endsWith("/cart")) return Promise.resolve(new Response(JSON.stringify({ quantity: 0 }), { status: 200 }));
      if (path.endsWith("/payment-communications")) return Promise.resolve(new Response(JSON.stringify({ orders: [] }), { status: 200 }));
      return Promise.resolve(new Response(JSON.stringify(review), { status: 200 }));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<GalleryPage />);

    fireEvent.click(await screen.findByRole("button", { name: "Ampliar prévia protegida de IMG_001.jpg" }));
    expect(screen.getByRole("region", { name: "Comentários de IMG_001.jpg" }).textContent).toContain("Recortar à esquerda");
    expect(screen.queryByText("Clarear esta foto")).toBeNull();
    expect(screen.queryByRole("combobox", { name: "Foto" })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Remover" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/gallery/gallery-1/comments/comment-1",
      expect.objectContaining({ method: "DELETE" }),
    ));

    fireEvent.keyDown(screen.getByRole("dialog"), { key: "ArrowRight" });
    const secondComments = screen.getByRole("region", { name: "Comentários de IMG_002.jpg" });
    expect(secondComments.textContent).toContain("Clarear esta foto");
    expect(screen.queryByText("Recortar à esquerda")).toBeNull();
    fireEvent.change(screen.getByRole("textbox", { name: "Comentário sobre IMG_002.jpg" }), { target: { value: "Nova observação" } });
    fireEvent.submit(screen.getByRole("button", { name: "Enviar comentário" }).closest("form")!);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/gallery/gallery-1/photos/bought-1/comments",
      expect.objectContaining({ method: "POST", body: JSON.stringify({ body: "Nova observação" }) }),
    ));
  });

  it("mantém a ampliação sem painel quando comentários estão desabilitados", async () => {
    const commentsDisabled = { ...review, gallery: { ...review.gallery, comments_enabled: false } };
    vi.stubGlobal("fetch", vi.fn((path: string) => Promise.resolve(new Response(JSON.stringify(
      path.endsWith("/comments") ? { comments: [] }
        : path.endsWith("/folders") ? { folders: [] }
          : path.endsWith("/cart") ? { quantity: 0 }
            : path.endsWith("/payment-communications") ? { orders: [] }
              : commentsDisabled,
    ), { status: 200 }))));
    render(<GalleryPage />);

    fireEvent.click(await screen.findByRole("button", { name: "Ampliar prévia protegida de IMG_001.jpg" }));
    expect(screen.getByRole("dialog", { name: "Prévia ampliada de IMG_001.jpg" })).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "Comentários" })).toBeNull();
    expect(screen.queryByRole("textbox", { name: /Comentário sobre/ })).toBeNull();
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
      return Promise.resolve(new Response(JSON.stringify({ ...review, photos: [{ ...review.photos[0], selected: true }] }), { status: 200 }));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<GalleryPage />);
    fireEvent.click(await screen.findByRole("button", { name: "✓ Desmarcar" }));
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

  it("troca a galeria e o rodapé por uma única conferência interativa com PIX", async () => {
    const checkoutReview = {
      ...review,
      photos: [
        { ...review.photos[0], selected: true, commercial_state: "selected" },
        { ...review.photos[0], id: "person-2", name: "IMG_003.jpg", selected: true, commercial_state: "selected" },
      ],
    };
    const fetchMock = vi.fn((path: string, options?: RequestInit) => {
      if (path.endsWith("/photos/new-1/favorite") && options?.method === "POST") return Promise.resolve(new Response(null, { status: 201 }));
      if (path.endsWith("/photos/new-1/selection") && options?.method === "DELETE") return Promise.resolve(new Response(null, { status: 204 }));
      if (path.endsWith("/cart")) return Promise.resolve(new Response(JSON.stringify({ quantity: 2, total_cents: 1300, base_total_cents: 1400, savings_cents: 100, items: [{ id: "new-1", name: "IMG_001.jpg" }, { id: "person-2", name: "IMG_003.jpg" }], parcels: [{ minimum_quantity: 1, maximum_quantity: 1, quantity: 1, unit_price_cents: 700, subtotal_cents: 700 }, { minimum_quantity: 2, maximum_quantity: null, quantity: 1, unit_price_cents: 600, subtotal_cents: 600 }] }), { status: 200 }));
      if (path.endsWith("/checkout")) return Promise.resolve(new Response(JSON.stringify({ id: "order-1", total_cents: 1300, payment_status: "pending" }), { status: 201 }));
      if (path.endsWith("/orders/order-1")) return Promise.resolve(new Response(JSON.stringify({ id: "order-1", total_cents: 1300, price_rule: { savings_cents: 100 }, sales_message: "Use o nome da cliente", pix: { copy_paste: "PIX-CODE", qr_png_data_url: "data:image/png;base64,AAAA", instructions: "Pagamento em análise.", confirmation: "manual" }, items: [{ photo_id: "new-1", name: "IMG_001.jpg", unit_price_cents: 700, preview_url: "/gallery/gallery-1/photos/new-1/preview" }, { photo_id: "person-2", name: "IMG_003.jpg", unit_price_cents: 600, preview_url: "/gallery/gallery-1/photos/person-2/preview" }] }), { status: 200 }));
      if (path.endsWith("/folders")) return Promise.resolve(new Response(JSON.stringify({ folders: [{ id: "folder-1", name: "Apresentação", position: 0, photo_count: 2 }] }), { status: 200 }));
      if (path.endsWith("/comments")) return Promise.resolve(new Response(JSON.stringify({ comments: [] }), { status: 200 }));
      void options;
      return Promise.resolve(new Response(JSON.stringify(checkoutReview), { status: 200 }));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<GalleryPage />);
    const footer = await screen.findByRole("complementary", { name: "Resumo da seleção" });
    const footerText = footer.textContent?.replaceAll("\u00a0", " ") ?? "";
    expect(footer.textContent).toContain("2 fotos");
    expect(footerText).toContain("R$ 13,00");
    expect(footerText).toContain("Você economiza R$ 1,00");
    fireEvent.click(screen.getByRole("button", { name: "Continuar para o PIX" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/gallery/gallery-1/checkout", expect.objectContaining({ method: "POST" })));
    expect(await screen.findByRole("heading", { name: /revise suas fotos e faça o pix/i })).toBeTruthy();
    expect(screen.queryByRole("complementary", { name: "Resumo da seleção" })).toBeNull();
    expect(screen.queryByRole("navigation", { name: "Filtrar fotos" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Carrinho (2)" })).toBeNull();
    expect(screen.getByRole("img", { name: "Prévia protegida de IMG_001.jpg" }).getAttribute("src")).toBe("/api/gallery/gallery-1/photos/new-1/preview");
    fireEvent.click(screen.getByRole("button", { name: "Ampliar prévia protegida de IMG_001.jpg" }));
    expect(screen.getByRole("dialog", { name: "Prévia ampliada de IMG_001.jpg" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Fechar" }));
    fireEvent.click(screen.getAllByRole("button", { name: "Favoritar" })[0]);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/gallery/gallery-1/photos/new-1/favorite",
      expect.objectContaining({ method: "POST" }),
    ));
    expect(screen.getByRole("heading", { name: /revise suas fotos e faça o pix/i })).toBeTruthy();
    expect(screen.getByRole("img", { name: "QR Code PIX do pedido" }).getAttribute("src")).toContain("data:image/png;base64,");
    expect(screen.getByDisplayValue("PIX-CODE")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Informar pagamento" })).toBeTruthy();

    fireEvent.click(screen.getAllByRole("button", { name: "✓ Desmarcar" })[0]);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/gallery/gallery-1/photos/new-1/selection",
      expect.objectContaining({ method: "DELETE" }),
    ));
    expect(screen.queryByRole("heading", { name: /revise suas fotos e faça o pix/i })).toBeNull();
    expect(await screen.findByRole("complementary", { name: "Resumo da seleção" })).toBeTruthy();
  });

  it("remove uma foto diretamente do carrinho privado", async () => {
    const fetchMock = vi.fn((path: string, options?: RequestInit) => {
      if (path.endsWith("/cart")) return Promise.resolve(new Response(JSON.stringify({ quantity: 1, items: [{ id: "new-1", name: "IMG_001.jpg" }] }), { status: 200 }));
      if (path.endsWith("/folders")) return Promise.resolve(new Response(JSON.stringify({ folders: [{ id: "folder-1", name: "Apresentação", position: 0, photo_count: 2 }] }), { status: 200 }));
      if (path.endsWith("/comments")) return Promise.resolve(new Response(JSON.stringify({ comments: [] }), { status: 200 }));
      void options;
      return Promise.resolve(new Response(JSON.stringify({ ...review, photos: [{ ...review.photos[0], selected: true }, review.photos[1]] }), { status: 200 }));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<GalleryPage />);
    fireEvent.click(await screen.findByRole("button", { name: "✓ Desmarcar" }));
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
    expect((await screen.findAllByText("Aguardando pagamento")).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: "Informar pagamento" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/gallery/gallery-1/orders/order-1/payment-communications",
      expect.objectContaining({ method: "POST" }),
    ));
    expect((await screen.findAllByText("Pagamento informado")).length).toBeGreaterThan(0);
    expect(screen.getByText("O pagamento está em análise.")).toBeTruthy();
  });
});
