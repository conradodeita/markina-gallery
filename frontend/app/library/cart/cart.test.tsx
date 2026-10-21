import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import CartPage from "./page";
import { ClientNavigation } from "../../client-navigation";
import { navigateToCardCheckout } from "./checkout-navigation";

vi.mock("next/link", () => ({ default: ({ children, href }: { children: React.ReactNode; href: string }) => <a href={href}>{children}</a> }));
vi.mock("./checkout-navigation", () => ({ navigateToCardCheckout: vi.fn() }));
afterEach(() => { vi.clearAllMocks(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });
const response = (data: object, status = 200) => Promise.resolve(new Response(JSON.stringify(data), { status }));
const group = (id: string) => ({ gallery_id: id, parent_gallery_id: id, name: `Galeria ${id}`, quantity: 1,
  total_cents: 700, error: null, browse_url: `/gallery/${id}`, selection_expires_at: null,
  items: [{ id: `photo-${id}`, name: `Foto ${id}`, folder_name: `Pasta ${id}`, preview_url: `/gallery/${id}/photos/photo-${id}/preview` }] });
const cart = { groups: [group("1"), group("2")], quantity: 2, can_prepare: true, total_cents: 1400 };
const payment = { id: "group-1", revision: "a".repeat(64), total_cents: 1400, pix_copy_paste: "PIX",
  pix_qr_code: "data:image/png;base64,AA", receiver_name: "Fotógrafo", pix_instructions: "Confira o valor" };

it("mostra mensagem comercial e finaliza sem preços nem preparar PIX", async () => {
  const external = { ...group("external"), payment_required: false, total_cents: null,
    revision: "b".repeat(64), message: "Escolha com calma.\nCombine o pacote." };
  let finalized = false;
  const fetcher = vi.fn((path: string) => {
    if (path.endsWith("/finalize")) { finalized = true; return response({ order_id: "external-order" }); }
    return response({ groups: finalized ? [] : [external], quantity: finalized ? 0 : 1,
      total_cents: null, can_prepare: false });
  });
  vi.stubGlobal("fetch", fetcher);
  render(<CartPage />);
  const finalize = await screen.findByRole("button", { name: "Finalizar seleção" });
  expect(screen.queryByRole("region", { name: "Pagamento único" })).toBeNull();
  expect(screen.queryByLabelText("Cartão de crédito")).toBeNull();
  fireEvent.click(finalize);
  expect(await screen.findByText(/Seleção finalizada/)).toBeTruthy();
  expect(fetcher.mock.calls.some(([path]) => path.endsWith("/prepare"))).toBe(false);
  expect(screen.queryByText(/R\$/)).toBeNull();
});

it("mostra a prévia protegida de uma foto canônica na revisão", async () => {
  const canonical = { ...group("canonical"), payment_required: false, total_cents: null,
    items: [{ id: "photo-canonical", name: "Ensaio.jpg", folder_name: "Pasta",
      preview_url: "/public-galleries/gallery-1/photos/photo-1/preview" }] };
  vi.stubGlobal("fetch", vi.fn(() => response({ groups: [canonical], quantity: 1,
    total_cents: null, can_prepare: false })));
  render(<CartPage />);
  const preview = await screen.findByRole("img", { name: "Prévia protegida de Ensaio.jpg" });
  expect(preview.getAttribute("src")).toBe("/api/public-galleries/gallery-1/photos/photo-1/preview");
});

it("exibe mensagens de cada galeria como texto inerte na revisão paga", async () => {
  const mixed = { ...cart, groups: [{ ...group("1"), message: "<script>teste</script>" },
    { ...group("2"), message: "Mensagem da outra galeria" }] };
  vi.stubGlobal("fetch", vi.fn((path: string) => response(path.endsWith("/prepare") ? { ...mixed, payment } : mixed)));
  render(<CartPage />);
  expect(await screen.findByText("<script>teste</script>")).toBeTruthy();
  expect(within(screen.getByRole("region", { name: "Fotos de Galeria 2" })).getByText("Mensagem da outra galeria")).toBeTruthy();
  expect(document.querySelector(".unified-cart script")).toBeNull();
});

it("permite finalizar seleção externa quando o PIX da outra galeria falha", async () => {
  const external = { ...group("external"), payment_required: false, total_cents: null, revision: "c".repeat(64) };
  let finalized = false;
  vi.stubGlobal("fetch", vi.fn((path: string) => {
    if (path.endsWith("/prepare")) return response({ detail: "PIX indisponível" }, 409);
    if (path.endsWith("/finalize")) { finalized = true; return response({ order_id: "external" }); }
    return response({ ...cart, groups: finalized ? [group("paid")] : [group("paid"), external] });
  }));
  render(<CartPage />);
  expect(await screen.findByText("PIX indisponível")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Finalizar seleção" }));
  expect(await screen.findByText(/Seleção finalizada/)).toBeTruthy();
  expect(screen.queryByRole("region", { name: "Fotos de Galeria external" })).toBeNull();
});

describe("revisão global da cliente", () => {
  it.each([5, 99])("impede cartão abaixo do mínimo de um real (%i centavos) preservando fotos e PIX", async (total) => {
    const ready = { ...cart, total_cents: total, cart_revision: "d".repeat(64),
      pix_available: true, card_available: true };
    const fetcher = vi.fn((path: string) => response(path.endsWith("/prepare")
      ? { ...ready, payment: { ...payment, total_cents: total } } : ready));
    vi.stubGlobal("fetch", fetcher);
    render(<CartPage />);
    await screen.findByRole("button", { name: "Informar pagamento" });
    fireEvent.click(screen.getByLabelText("Cartão de crédito"));
    expect(await screen.findByText(/O pagamento com cartão exige um total mínimo de R\$ 1,00/)).toBeTruthy();
    const button = screen.getByRole("button", { name: "Continuar com cartão de crédito" });
    expect(button).toHaveProperty("disabled", true);
    fireEvent.click(button);
    expect(fetcher.mock.calls.some(([path]) => path.endsWith("/prepare-card"))).toBe(false);
    expect(screen.getByText("Foto 1")).toBeTruthy();
    expect(screen.getAllByRole("link", { name: "Continuar escolhendo" })).toHaveLength(2);
    fireEvent.click(screen.getByLabelText("PIX"));
    expect(await screen.findByRole("button", { name: "Informar pagamento" })).toHaveProperty("disabled", false);
  });

  it("permite preparar cartão no total exato de um real", async () => {
    const ready = { ...cart, total_cents: 100, cart_revision: "d".repeat(64),
      pix_available: false, card_available: true };
    const fetcher = vi.fn(() => response(ready));
    vi.stubGlobal("fetch", fetcher);
    render(<CartPage />);
    expect(await screen.findByRole("button", { name: "Continuar com cartão de crédito" })).toHaveProperty("disabled", false);
    expect(screen.queryByText(/O pagamento com cartão exige um total mínimo/)).toBeNull();
  });

  it("oferece cartão utilizável sem preparar ou exibir PIX inexistente", async () => {
    const ready = { ...cart, cart_revision: "d".repeat(64), pix_available: false, card_available: true };
    const fetcher = vi.fn(() => response(ready));
    vi.stubGlobal("fetch", fetcher);
    render(<CartPage />);
    expect(await screen.findByRole("button", { name: "Continuar com cartão de crédito" })).toBeTruthy();
    expect(screen.queryByLabelText("PIX")).toBeNull();
    expect(screen.queryByText("Preparando PIX…")).toBeNull();
    expect(fetcher.mock.calls).toHaveLength(1);
  });

  it("inicia pelo PIX quando ambos os meios estão disponíveis", async () => {
    const ready = { ...cart, pix_available: true, card_available: true };
    vi.stubGlobal("fetch", vi.fn((path: string) => response(path.endsWith("/prepare") ? { ...ready, payment } : ready)));
    render(<CartPage />);
    await screen.findByRole("button", { name: "Informar pagamento" });
    expect(screen.getByLabelText("PIX")).toHaveProperty("checked", true);
    expect(screen.getByLabelText("Cartão de crédito")).toHaveProperty("checked", false);
  });

  it("separa os 5 centavos da compra anterior e permite alternar meios para fotos novas", async () => {
    const ready = { ...cart, cart_revision: "d".repeat(64), pix_available: true, card_available: true,
      card_payment: null, pending_card_payments: [{ id: "previous-unknown", status: "verification_required",
        checkout_url: null, total_cents: 5 }] };
    const fetcher = vi.fn((path: string) => response(path.endsWith("/prepare") ? { ...ready, payment } : ready));
    vi.stubGlobal("fetch", fetcher);
    render(<CartPage />);
    await screen.findByRole("button", { name: "Informar pagamento" });
    const previous = screen.getByRole("region", { name: "Compras anteriores pendentes" });
    expect(within(previous).getByText(/0,05/)).toBeTruthy();
    expect(screen.getByRole("heading", { name: /Total R\$\s*14,00/ })).toBeTruthy();
    fireEvent.click(screen.getByLabelText("Cartão de crédito"));
    expect(screen.getByRole("button", { name: "Continuar com cartão de crédito" })).toBeTruthy();
    fireEvent.click(screen.getByLabelText("PIX"));
    expect(screen.getByRole("button", { name: "Informar pagamento" })).toBeTruthy();
    expect(fetcher.mock.calls.some(([path]) => path.endsWith("/prepare-card"))).toBe(false);
    expect(within(previous).getByRole("link", { name: "Acompanhar compra anterior" }).getAttribute("href"))
      .toBe("/library/purchases#payment-previous-unknown");
  });

  it("preserva seleção e explica indisponibilidade quando nenhum meio é utilizável", async () => {
    vi.stubGlobal("fetch", vi.fn(() => response({ ...cart, can_prepare: false, pix_available: false,
      card_available: false, payment_error: "Pagamento indisponível. Sua seleção foi mantida." })));
    render(<CartPage />);
    expect(await screen.findByText("Pagamento indisponível. Sua seleção foi mantida.")).toBeTruthy();
    expect(screen.getByRole("region", { name: "Fotos de Galeria 1" })).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Continuar com cartão de crédito" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Informar pagamento" })).toBeNull();
  });
  it("permite escolher cartão e prepara uma única tentativa sem exibir o PIX como comprovante", async () => {
    const ready = { ...cart, cart_revision: "d".repeat(64), card_available: true };
    const fetcher = vi.fn((path: string, options?: RequestInit) => {
      void options;
      if (path.endsWith("/prepare-card")) return response({ id: "card-1", status: "awaiting_payment",
        checkout_url: "https://checkout.infinitepay.io/owner/invoice", total_cents: 1400 });
      if (path.endsWith("/prepare")) return response({ ...ready, payment });
      return response(ready);
    });
    vi.stubGlobal("fetch", fetcher);
    render(<CartPage />);
    fireEvent.click(await screen.findByLabelText("Cartão de crédito"));
    fireEvent.click(screen.getByRole("button", { name: "Continuar com cartão de crédito" }));
    const link = await screen.findByRole("link", { name: "Continuar para pagamento com cartão" });
    expect(link.getAttribute("href")).toBe("https://checkout.infinitepay.io/owner/invoice");
    const call = fetcher.mock.calls.find(([path]) => path.endsWith("/prepare-card"));
    expect(call?.[1]?.method).toBe("POST");
    expect(JSON.parse(String(call?.[1]?.body))).toMatchObject({ cart_revision: "d".repeat(64) });
    expect(screen.queryByRole("img", { name: /QR Code/ })).toBeNull();
    expect(fetcher.mock.calls.filter(([path]) => path.endsWith("/prepare-card"))).toHaveLength(1);
    expect(navigateToCardCheckout).toHaveBeenCalledExactlyOnceWith("https://checkout.infinitepay.io/owner/invoice");
  });

  it("permite tentar novamente com as mesmas fotos após confirmação de que o checkout não foi criado", async () => {
    const ready = { ...cart, cart_revision: "e".repeat(64), card_available: true };
    const cardKeys: string[] = [];
    let attempts = 0;
    const fetcher = vi.fn((path: string, options?: RequestInit) => {
      if (path.endsWith("/prepare-card")) {
        cardKeys.push(JSON.parse(String(options?.body)).idempotency_key);
        attempts += 1;
        return attempts === 1
          ? response({ id: "card-1", status: "failed_before_issue", checkout_url: null, total_cents: 1400 })
          : response({ id: "card-2", status: "awaiting_payment",
            checkout_url: "https://checkout.infinitepay.io/owner/retry", total_cents: 1400 });
      }
      if (path.endsWith("/prepare")) return response({ ...ready, payment });
      return response(ready);
    });
    vi.stubGlobal("fetch", fetcher);
    render(<CartPage />);
    fireEvent.click(await screen.findByLabelText("Cartão de crédito"));
    fireEvent.click(screen.getByRole("button", { name: "Continuar com cartão de crédito" }));
    expect(await screen.findByText(/A InfinitePay confirmou que não criou o checkout/)).toBeTruthy();
    expect(screen.getByText("Foto 1")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Continuar com cartão de crédito" }));
    expect(await screen.findByRole("link", { name: "Continuar para pagamento com cartão" })).toBeTruthy();
    expect(cardKeys).toHaveLength(2);
    expect(cardKeys[0]).not.toBe(cardKeys[1]);
  });

  it("envia e redireciona uma vez mesmo com duplo clique durante a resposta", async () => {
    const ready = { ...cart, cart_revision: "d".repeat(64), pix_available: false, card_available: true };
    let finish!: (value: Response) => void;
    const pending = new Promise<Response>((resolve) => { finish = resolve; });
    const fetcher = vi.fn((path: string) => path.endsWith("/prepare-card") ? pending : response(ready));
    vi.stubGlobal("fetch", fetcher);
    render(<CartPage />);
    const button = await screen.findByRole("button", { name: "Continuar com cartão de crédito" });
    fireEvent.click(button); fireEvent.click(button);
    expect(fetcher.mock.calls.filter(([path]) => path.endsWith("/prepare-card"))).toHaveLength(1);
    expect(navigateToCardCheckout).not.toHaveBeenCalled();
    finish(new Response(JSON.stringify({ id: "card-1", status: "awaiting_payment", total_cents: 1400,
      checkout_url: "https://checkout.infinitepay.io/owner/invoice" })));
    await waitFor(() => expect(navigateToCardCheckout).toHaveBeenCalledExactlyOnceWith("https://checkout.infinitepay.io/owner/invoice"));
  });

  it("preserva o link e a reserva se o navegador não conseguir redirecionar", async () => {
    const ready = { ...cart, cart_revision: "d".repeat(64), pix_available: false, card_available: true };
    vi.mocked(navigateToCardCheckout).mockImplementationOnce(() => { throw new Error("Navegação indisponível"); });
    const fetcher = vi.fn((path: string) => path.endsWith("/prepare-card")
      ? response({ id: "card-1", status: "awaiting_payment", total_cents: 1400,
        checkout_url: "https://checkout.infinitepay.io/owner/invoice" }) : response(ready));
    vi.stubGlobal("fetch", fetcher);
    render(<CartPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Continuar com cartão de crédito" }));
    await screen.findByText("Navegação indisponível");
    expect((await screen.findByRole("link", { name: "Continuar para pagamento com cartão" })).getAttribute("href"))
      .toBe("https://checkout.infinitepay.io/owner/invoice");
    expect(screen.queryByRole("button", { name: "Continuar com cartão de crédito" })).toBeNull();
    expect(fetcher.mock.calls.filter(([path]) => path.endsWith("/prepare-card"))).toHaveLength(1);
  });

  it.each([null, "", "javascript:alert(1)", "http://checkout.infinitepay.io/x",
    "https://checkout.infinitepay.io.evil.test/x", "https://user@checkout.infinitepay.io/x",
    "https://checkout.infinitepay.io:444/x", "/checkout/local"])(
    "não navega nem permite segunda cobrança quando a URL recebida não é utilizável: %s", async (url) => {
      const ready = { ...cart, cart_revision: "d".repeat(64), pix_available: false, card_available: true };
      vi.stubGlobal("fetch", vi.fn((path: string) => path.endsWith("/prepare-card")
        ? response({ id: "card-1", status: "awaiting_payment", total_cents: 1400, checkout_url: url }) : response(ready)));
      render(<CartPage />);
      fireEvent.click(await screen.findByRole("button", { name: "Continuar com cartão de crédito" }));
      await screen.findByText(/A InfinitePay não devolveu um link utilizável/);
      expect(navigateToCardCheckout).not.toHaveBeenCalled();
      expect(screen.queryByRole("link", { name: "Continuar para pagamento com cartão" })).toBeNull();
      expect(screen.queryByRole("button", { name: "Continuar com cartão de crédito" })).toBeNull();
      expect(screen.queryByRole("button", { name: "Informar pagamento" })).toBeNull();
    });

  it.each(["verification_required", "failed_before_issue", "exception", "hold", "confirmed"])(
    "não navega ao receber o estado %s mesmo com uma URL", async (status) => {
      const ready = { ...cart, cart_revision: "d".repeat(64), pix_available: false, card_available: true };
      vi.stubGlobal("fetch", vi.fn((path: string) => path.endsWith("/prepare-card")
        ? response({ id: "card-1", status, total_cents: 1400,
          checkout_url: "https://checkout.infinitepay.io/owner/invoice" }) : response(ready)));
      render(<CartPage />);
      fireEvent.click(await screen.findByRole("button", { name: "Continuar com cartão de crédito" }));
      await waitFor(() => expect(screen.queryByText("Preparando checkout…")).toBeNull());
      expect(navigateToCardCheckout).not.toHaveBeenCalled();
    });

  it("não oferece outra cobrança nem PIX quando o resultado da emissão continua incerto", async () => {
    const ready = { ...cart, cart_revision: "f".repeat(64), card_available: true };
    const fetcher = vi.fn((path: string) => path.endsWith("/prepare-card")
      ? response({ id: "card-unknown", status: "verification_required", checkout_url: null, total_cents: 1400 })
      : response(path.endsWith("/prepare") ? { ...ready, payment } : ready));
    vi.stubGlobal("fetch", fetcher);
    render(<CartPage />);
    fireEvent.click(await screen.findByLabelText("Cartão de crédito"));
    fireEvent.click(screen.getByRole("button", { name: "Continuar com cartão de crédito" }));
    expect(await screen.findByText(/A InfinitePay não devolveu um link utilizável/)).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Continuar com cartão de crédito" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Informar pagamento" })).toBeNull();
    expect(fetcher.mock.calls.filter(([path]) => path.endsWith("/prepare-card"))).toHaveLength(1);
  });

  it("retoma as mesmas fotos na mesma aba após reabertura autorizada, com PIX e chave nova para cartão", async () => {
    const ready = { ...cart, cart_revision: "f".repeat(64), card_available: true, pix_available: true };
    const uncertain = { id: "card-old", status: "verification_required", checkout_url: null, total_cents: 1400 };
    let issued = false, reopened = false;
    const keys: string[] = [];
    const fetcher = vi.fn((path: string, options?: RequestInit) => {
      if (path.endsWith("/prepare-card")) {
        keys.push(JSON.parse(String(options?.body)).idempotency_key); issued = true;
        return response(reopened ? { id: "card-new", status: "awaiting_payment", total_cents: 1400,
          checkout_url: "https://checkout.infinitepay.io/owner/new" } : uncertain);
      }
      if (issued && !reopened) return response({ ...ready, can_prepare: false, card_payment: uncertain });
      return response({ ...ready, recovery_revision: reopened ? "authorized-recovery" : null,
        ...(path.endsWith("/prepare") ? { payment } : {}) });
    });
    vi.stubGlobal("fetch", fetcher);
    render(<CartPage />);
    fireEvent.click(await screen.findByLabelText("Cartão de crédito"));
    fireEvent.click(screen.getByRole("button", { name: "Continuar com cartão de crédito" }));
    await screen.findByText(/A InfinitePay não devolveu um link utilizável/);
    fireEvent.focus(window);
    await screen.findByRole("region", { name: "Pagamento por cartão em andamento" });
    expect(screen.queryByLabelText("PIX")).toBeNull();
    expect(keys).toHaveLength(1);
    reopened = true;
    fireEvent.focus(window);
    await screen.findByText(/O fotógrafo reabriu seu carrinho/);
    expect(screen.getByText("Foto 1")).toBeTruthy();
    expect(screen.getByText("Foto 2")).toBeTruthy();
    fireEvent.click(screen.getByLabelText("PIX"));
    expect(await screen.findByRole("button", { name: "Informar pagamento" })).toBeTruthy();
    expect(keys).toHaveLength(1);
    fireEvent.click(screen.getByLabelText("Cartão de crédito"));
    fireEvent.click(screen.getByRole("button", { name: "Continuar com cartão de crédito" }));
    await screen.findByRole("link", { name: "Continuar para pagamento com cartão" });
    expect(keys).toHaveLength(2);
    expect(keys[0]).not.toBe(keys[1]);
    expect(fetcher.mock.calls.some(([path, options]) => options?.method === "DELETE" || path.includes("/selection"))).toBe(false);
  });

  it("preserva a chave da mesma tentativa após falha de rede sem recuperação administrativa", async () => {
    const ready = { ...cart, cart_revision: "e".repeat(64), card_available: true, pix_available: false };
    const keys: string[] = [];
    vi.stubGlobal("fetch", vi.fn((path: string, options?: RequestInit) => {
      if (!path.endsWith("/prepare-card")) return response(ready);
      keys.push(JSON.parse(String(options?.body)).idempotency_key);
      return keys.length === 1 ? Promise.reject(new Error("Sem resposta"))
        : response({ id: "same-attempt", status: "verification_required", checkout_url: null, total_cents: 1400 });
    }));
    render(<CartPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Continuar com cartão de crédito" }));
    await screen.findByText("Sem resposta");
    expect(navigateToCardCheckout).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Continuar com cartão de crédito" }));
    await screen.findByText(/A InfinitePay não devolveu um link utilizável/);
    expect(keys).toHaveLength(2);
    expect(keys[0]).toBe(keys[1]);
  });

  it("usa chave diferente para novas fotos com revisão diferente, preservando a compra anterior", async () => {
    let revision = "a".repeat(64);
    const keys: string[] = [];
    vi.stubGlobal("fetch", vi.fn((path: string, options?: RequestInit) => {
      if (!path.endsWith("/prepare-card")) return response({ ...cart, cart_revision: revision,
        card_available: true, pix_available: false, pending_card_payments: keys.length ? [{
          id: "old", status: "verification_required", checkout_url: null, total_cents: 5 }] : [] });
      keys.push(JSON.parse(String(options?.body)).idempotency_key);
      return Promise.reject(new Error("Sem resposta"));
    }));
    render(<CartPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Continuar com cartão de crédito" }));
    await screen.findByText("Sem resposta");
    revision = "b".repeat(64);
    fireEvent.focus(window);
    await screen.findByRole("region", { name: "Compras anteriores pendentes" });
    fireEvent.click(screen.getByRole("button", { name: "Continuar com cartão de crédito" }));
    await waitFor(() => expect(keys).toHaveLength(2));
    expect(keys[0]).not.toBe(keys[1]);
    expect(screen.getByRole("region", { name: "Compras anteriores pendentes" })).toBeTruthy();
  });

  it.each(["exception", "confirmed", "hold"])("relê o carrinho após resposta tardia %s sem projetar incerteza antiga", async (status) => {
    let changed = false;
    const ready = { ...cart, cart_revision: "c".repeat(64), card_available: true, pix_available: false };
    const fetcher = vi.fn((path: string) => {
      if (path.endsWith("/prepare-card")) { changed = true; return response({ id: "old", status, checkout_url: null }); }
      return response(changed && status !== "exception" ? { groups: [], quantity: 0, can_prepare: false }
        : { ...ready, recovery_revision: changed ? "reopened" : null });
    });
    vi.stubGlobal("fetch", fetcher);
    render(<CartPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Continuar com cartão de crédito" }));
    await waitFor(() => expect(fetcher.mock.calls.filter(([path]) => path === "/api/library/cart")).toHaveLength(2));
    expect(screen.queryByRole("region", { name: "Pagamento por cartão em andamento" })).toBeNull();
    expect(screen.queryByText(/A InfinitePay não devolveu um link utilizável/)).toBeNull();
    if (status === "exception") expect(await screen.findByText(/O fotógrafo reabriu seu carrinho/)).toBeTruthy();
    else expect(await screen.findByText("Seu carrinho está vazio.")).toBeTruthy();
  });

  it("mantém o checkout já emitido acessível mesmo quando cartão foi desabilitado para novas compras", async () => {
    const pending = { ...cart, card_available: false, card_payment: {
      id: "card-existing", status: "awaiting_payment", checkout_url: "https://checkout.infinitepay.io/owner/existing",
      total_cents: 1400,
    } };
    vi.stubGlobal("fetch", vi.fn(() => response(pending)));
    render(<CartPage />);
    const link = await screen.findByRole("link", { name: "Continuar para pagamento com cartão" });
    expect(link.getAttribute("href")).toBe("https://checkout.infinitepay.io/owner/existing");
    expect(link.getAttribute("target")).toBeNull();
    expect(navigateToCardCheckout).not.toHaveBeenCalled();
    fireEvent.focus(window);
    await waitFor(() => expect(screen.getByRole("link", { name: "Continuar para pagamento com cartão" })).toBeTruthy());
    expect(navigateToCardCheckout).not.toHaveBeenCalled();
    expect(screen.queryByLabelText("Cartão de crédito")).toBeNull();
    expect(screen.queryByRole("button", { name: "Informar pagamento" })).toBeNull();
  });

  it("abre fotos de duas galerias e pastas com um único PIX e registra uma compra", async () => {
    const fetcher = vi.fn((path: string) => response(path.endsWith("/prepare") ? { ...cart, payment }
      : path.endsWith("/report") ? { status: "pending_review" } : cart));
    vi.stubGlobal("fetch", fetcher);
    render(<CartPage />);
    expect(await screen.findByRole("button", { name: "Informar pagamento" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Revise suas fotos e escolha como pagar" })).toBeTruthy();
    expect(within(screen.getByRole("region", { name: "Fotos de Galeria 1" })).getByText("Pasta 1")).toBeTruthy();
    expect(screen.getAllByRole("img", { name: /QR Code/ })).toHaveLength(1);
    expect(screen.getByRole("heading", { name: /Total/ }).textContent).toContain("14,00");
    fireEvent.click(screen.getByRole("button", { name: "Informar pagamento" }));
    expect(await screen.findByRole("heading", { name: "Pagamento informado" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Ver compra" }).getAttribute("href")).toBe("/library/purchases#payment-group-1");
    expect(fetcher.mock.calls.filter(([path]) => path.endsWith("/report"))).toHaveLength(1);
  });

  it("restaura a seleção após remontar sem registrar compra por visitar o PIX", async () => {
    const fetcher = vi.fn((path: string) => response(path.endsWith("/prepare") ? { ...cart, payment } : cart));
    vi.stubGlobal("fetch", fetcher);
    const first = render(<CartPage />);
    await screen.findByRole("button", { name: "Informar pagamento" });
    first.unmount();
    render(<CartPage />);
    await screen.findByRole("button", { name: "Informar pagamento" });
    expect(screen.getByText("Foto 2")).toBeTruthy();
    expect(fetcher.mock.calls.some(([path]) => path.endsWith("/report"))).toBe(false);
  });

  it("retira o PIX quando a revisão muda e exige conferência novamente", async () => {
    vi.stubGlobal("fetch", vi.fn((path: string) => path.endsWith("/report")
      ? response({ detail: "O carrinho mudou. Confira o total." }, 409)
      : response(path.endsWith("/prepare") ? { ...cart, payment } : cart)));
    render(<CartPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Informar pagamento" }));
    expect(await screen.findByText("O carrinho mudou. Confira o total.")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Informar pagamento" })).toBeNull();
    expect(screen.getByRole("button", { name: "Atualizar revisão" })).toBeTruthy();
  });

  it("bloqueia total parcial e permite remover explicitamente o grupo impedido", async () => {
    let removed = false;
    const fetcher = vi.fn((path: string, options?: RequestInit) => {
      if (options?.method === "DELETE") removed = true;
      return response(removed ? { ...cart, groups: [group("2")], quantity: 1, total_cents: 700, payment }
        : { ...cart, can_prepare: false, total_cents: null, groups: [{ ...group("1"), error: "Prazo expirado" }, group("2")] });
    });
    vi.stubGlobal("fetch", fetcher);
    render(<CartPage />);
    expect(await screen.findByText("Prazo expirado")).toBeTruthy();
    expect(screen.queryByRole("img", { name: /QR Code/ })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Remover seleção de Galeria 1" }));
    await waitFor(() => expect(screen.queryByRole("region", { name: "Fotos de Galeria 1" })).toBeNull());
    expect(fetcher.mock.calls.some(([path, options]) => path === "/api/library/cart/1" && options?.method === "DELETE")).toBe(true);
  });

  it("sinaliza falha ao salvar sem apagar fotos da revisão", async () => {
    vi.stubGlobal("fetch", vi.fn((path: string, options?: RequestInit) => options?.method === "DELETE"
      ? response({}, 500) : response(path.endsWith("/prepare") ? { ...cart, payment } : cart)));
    render(<CartPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Remover Foto 1 de Galeria 1" }));
    expect(await screen.findByText(/Não foi possível salvar a remoção/)).toBeTruthy();
    expect(screen.getByText("Foto 1")).toBeTruthy();
  });

  it("não prepara PIX para carrinho vazio", async () => {
    const fetcher = vi.fn(() => response({ groups: [], quantity: 0, total_cents: null, can_prepare: false }));
    vi.stubGlobal("fetch", fetcher);
    render(<CartPage />);
    expect(await screen.findByText("Seu carrinho está vazio.")).toBeTruthy();
    expect(fetcher).toHaveBeenCalledTimes(1);
  });

  it("oculta fotos e PIX quando a sessão deixa de ter acesso", async () => {
    let authorized = true;
    vi.stubGlobal("fetch", vi.fn((path: string) => authorized
      ? response(path.endsWith("/prepare") ? { ...cart, payment } : cart) : response({}, 403)));
    render(<CartPage />);
    expect(await screen.findByRole("button", { name: "Informar pagamento" })).toBeTruthy();
    authorized = false;
    fireEvent.focus(window);
    expect(await screen.findByText("Não foi possível consultar o carrinho.")).toBeTruthy();
    expect(screen.queryByText("Foto 1")).toBeNull();
    expect(screen.queryByRole("button", { name: "Informar pagamento" })).toBeNull();
  });

  it("mantém os três destinos acessíveis e limpa contador após acesso negado", async () => {
    let authorized = true;
    vi.stubGlobal("fetch", vi.fn(() => authorized ? response({ quantity: 6 }) : response({}, 403)));
    render(<ClientNavigation />);
    expect((await screen.findByRole("link", { name: "Carrinho (6)" })).getAttribute("href")).toBe("/library/cart");
    expect(screen.getByRole("link", { name: "Galerias" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Compras" })).toBeTruthy();
    authorized = false; fireEvent.focus(window);
    expect(await screen.findByRole("link", { name: "Carrinho" })).toBeTruthy();
    expect(screen.queryByText("Carrinho (6)")).toBeNull();
  });
});
