import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useEffect } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import CreditsPage from "./page";

vi.mock("next/script", () => ({ default: function ScriptMock({ onReady }: { onReady(): void }) {
  useEffect(() => { onReady(); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  return null;
} }));

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const finiteWallet = {
  mode: "finite" as const,
  available_credits: 4,
  reserved_credits: 1,
  pending_operations: 1,
  recent_consumed_credits: 3,
  recent_period_days: 30,
  can_upload_content: true,
  financial_review_hold: false,
  financial_review_count: 0,
  as_of: "2026-10-31T12:00:00Z",
};

const ownerWallet = {
  mode: "unmetered" as const,
  available_credits: null,
  reserved_credits: 0,
  pending_operations: 0,
  recent_consumed_credits: 0,
  recent_period_days: 30,
  can_upload_content: true,
  financial_review_hold: false,
  financial_review_count: 0,
  as_of: "2026-10-31T12:00:00Z",
};

const packageItem = {
  id: "package-1",
  name: "Pacote configurado",
  description: null,
  credit_quantity: 20,
  price_cents: null,
  currency_code: null,
  active: false,
  created_at: "2026-10-31T12:00:00Z",
  updated_at: "2026-10-31T12:00:00Z",
};

const preparedCreditPurchase = {
  id: "purchase-1",
  package_id: "package-1",
  package_name: "Pacote ativo para fotógrafos",
  credit_quantity: 40,
  total_cents: 4900,
  currency_code: "BRL",
  method: null,
  state: "prepared",
  active: true,
  public_key: "APP_USR-public-key",
  created_at: "2026-10-31T12:00:00Z",
};

describe("carteira de créditos", () => {
  it("reutiliza a preparação idempotente e falha fechada se o saldo não atualizar", async () => {
    let preparationCalls = 0;
    let walletCalls = 0;
    const fetcher = vi.fn((input: string | URL | Request, init?: RequestInit) => {
      const path = String(input);
      if (path.startsWith("/api/admin/credits/history?")) return Promise.resolve(jsonResponse({ items: [{
        id: "folder:one", type: "folder_upload", delta: -3, photo_count: 3,
        folder_id: "folder-one", description: "Pasta de teste", gallery_name: "Galeria de teste",
        source_reference: "folder-one", created_at: finiteWallet.as_of,
      }], has_more: false, as_of: finiteWallet.as_of }));
      if (path === "/api/admin/credits/wallet") {
        walletCalls += 1;
        if (walletCalls === 2) {
          return Promise.resolve(jsonResponse({ detail: "Saldo temporariamente indisponível" }, 503));
        }
        return Promise.resolve(jsonResponse({
          wallet: finiteWallet,
          entries: [{
            id: "entry-1",
            type: "upload_consumption",
            delta: -1,
            source_reference: "photo-1",
            description: "Upload da foto",
            created_at: "2026-10-31T12:00:00Z",
          }],
        }));
      }
      if (path === "/api/admin/credits/capabilities") {
        return Promise.resolve(jsonResponse({ manage_packages: false }));
      }
      if (path === "/api/admin/credits/packages") {
        return Promise.resolve(jsonResponse({ items: [{
          ...packageItem,
          name: "Pacote ativo para fotógrafos",
          credit_quantity: 40,
          price_cents: 4900,
          currency_code: "BRL",
          active: true,
        }] }));
      }
      if (path === "/api/admin/onboarding/checkout-identity") {
        return Promise.resolve(jsonResponse({
          name: "Fotógrafo sintético", email: "photographer@example.test",
          identification_number: "52998224725",
          address: {
            zip_code: "01311000", street_name: "Avenida Paulista", street_number: "1000",
            neighborhood: "Bela Vista", city: "São Paulo", state: "SP", complement: "",
          },
        }));
      }
      if (path === "/api/admin/credits/purchases?limit=20") return Promise.resolve(jsonResponse({ items: [] }));
      if (path === "/api/admin/credits/purchases/active") return Promise.resolve(jsonResponse({ items: [] }));
      if (path === "/api/admin/credits/purchases/prepare" && init?.method === "POST") {
        preparationCalls += 1;
        return Promise.resolve(preparationCalls === 1
          ? jsonResponse({ detail: "Falha temporária" }, 503)
          : jsonResponse(preparedCreditPurchase));
      }
      if (path === "/api/admin/credits/purchases/purchase-1/submit" && init?.method === "POST") {
        return Promise.resolve(jsonResponse({
          ...preparedCreditPurchase, method: "pix", state: "confirmed", active: false,
          confirmed_at: "2026-11-14T12:00:00Z",
        }));
      }
      if (path === "/api/admin/media-archive/recovery-pricing") {
        return Promise.resolve(jsonResponse({
          recovery_fee_credits: null, configured: false, owner_exempt: false,
          available_credits: 4, duration_days: [7, 14, 30], can_manage: false,
        }));
      }
      if (path === "/api/admin/media-archive/recovery-candidates"
        || path === "/api/admin/media-archive/recoveries?limit=50") {
        return Promise.resolve(jsonResponse({ items: [] }));
      }
      throw new Error(`Rota inesperada: ${path}`);
    });
    vi.stubGlobal("fetch", fetcher);

    render(<CreditsPage />);

    expect(await screen.findByText("4")).toBeTruthy();
    expect(screen.getByText("Consumo nos últimos 30 dias")).toBeTruthy();
    expect(screen.getByText("Créditos reservados")).toBeTruthy();
    expect(await screen.findByText("3 fotos cobradas")).toBeTruthy();
    expect(screen.getByText("Uploads · Pasta de teste")).toBeTruthy();
    expect(await screen.findByRole("heading", { name: "Pacotes disponíveis" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Pacote ativo para fotógrafos" })).toBeTruthy();
    expect(screen.getByText("40")).toBeTruthy();
    expect(screen.getByText(/49,00/)).toBeTruthy();
    const buyButton = screen.getByRole("button", { name: "Comprar pacote" });
    expect(buyButton).toHaveProperty("disabled", false);
    expect(screen.queryByRole("heading", { name: "Carteiras dos fotógrafos" })).toBeNull();
    const wallet = screen.getByRole("region", { name: "Resumo da carteira" });
    const catalogHeading = screen.getByRole("heading", { name: "Pacotes disponíveis" });
    expect(wallet.compareDocumentPosition(catalogHeading) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    const paths = fetcher.mock.calls.map(([path]) => String(path));
    expect(paths).toContain("/api/admin/credits/packages");
    expect(paths).not.toContain("/api/admin/platform/credit-packages");

    const randomUUID = vi.fn()
      .mockReturnValueOnce("first-request-key")
      .mockReturnValueOnce("second-request-key");
    vi.stubGlobal("crypto", { randomUUID });
    fireEvent.click(buyButton);
    expect(await screen.findByRole("alert")).toHaveProperty("textContent", "Falha temporária");
    fireEvent.click(buyButton);
    expect(await screen.findByText("Checkout transparente · Mercado Pago")).toBeTruthy();
    expect(screen.getByRole("radio", { name: "PIX Mercado Pago" })).toBeTruthy();
    expect(screen.queryByRole("radio", { name: /PIX do sistema/i })).toBeNull();
    const prepareRequests = fetcher.mock.calls.filter(([path]) =>
      String(path) === "/api/admin/credits/purchases/prepare",
    );
    expect(prepareRequests.map(([, init]) => JSON.parse(String(init?.body)))).toEqual([
      { package_id: "package-1", idempotency_key: "first-request-key" },
      { package_id: "package-1", idempotency_key: "first-request-key" },
    ]);
    expect(randomUUID).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole("radio", { name: "PIX Mercado Pago" }));
    fireEvent.click(screen.getByRole("button", { name: "Gerar PIX de R$ 49,00" }));
    expect(await screen.findByText("Pagamento confirmado. Os créditos já foram adicionados à carteira.")).toBeTruthy();
    expect(await screen.findByText("Saldo aguardando atualização")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Atualizar saldo" }));
    expect(await screen.findByRole("region", { name: "Resumo da carteira" })).toBeTruthy();
  });

  it("distingue catálogo vazio de falha de leitura", async () => {
    let catalogStatus = 200;
    vi.stubGlobal("fetch", vi.fn((input: string | URL | Request) => {
      const path = String(input);
      if (path.startsWith("/api/admin/credits/history?")) return Promise.resolve(jsonResponse({ items: [], has_more: false }));
      if (path === "/api/admin/credits/wallet") return Promise.resolve(jsonResponse({ wallet: finiteWallet, entries: [] }));
      if (path === "/api/admin/credits/capabilities") return Promise.resolve(jsonResponse({ manage_packages: false }));
      if (path === "/api/admin/credits/packages") {
        return Promise.resolve(jsonResponse(catalogStatus === 200 ? { items: [] } : { detail: "Consulta indisponível" }, catalogStatus));
      }
      if (path === "/api/admin/credits/purchases?limit=20" || path === "/api/admin/credits/purchases/active") {
        return Promise.resolve(jsonResponse({ items: [] }));
      }
      throw new Error(`Rota inesperada: ${path}`);
    }));

    const { unmount } = render(<CreditsPage />);
    expect(await screen.findByText("Nenhum pacote disponível")).toBeTruthy();
    unmount();

    catalogStatus = 503;
    render(<CreditsPage />);
    expect(await screen.findByRole("alert")).toHaveProperty("textContent", expect.stringContaining("Catálogo indisponível"));
  });

  it("mantém o proprietário ilimitado e não preenche preço nem quantidade comerciais", async () => {
    const fetcher = vi.fn((input: string | URL | Request) => {
      const path = String(input);
      if (path.startsWith("/api/admin/credits/history?")) return Promise.resolve(jsonResponse({ items: [], has_more: false }));
      if (path === "/api/admin/credits/wallet") {
        return Promise.resolve(jsonResponse({ wallet: ownerWallet, entries: [] }));
      }
      if (path === "/api/admin/credits/capabilities") {
        return Promise.resolve(jsonResponse({ manage_packages: true }));
      }
      if (path === "/api/admin/platform/credit-tenants") return Promise.resolve(jsonResponse({ items: [] }));
      if (path === "/api/admin/platform/credit-packages") {
        return Promise.resolve(jsonResponse({ items: [] }));
      }
      throw new Error(`Rota inesperada: ${path}`);
    });
    vi.stubGlobal("fetch", fetcher);

    render(<CreditsPage />);

    expect(await screen.findByText("Ilimitado")).toBeTruthy();
    expect(await screen.findByRole("heading", { name: "Pacotes de créditos" })).toBeTruthy();
    expect(screen.getByLabelText("Nome do pacote")).toHaveProperty("value", "");
    expect(screen.getByLabelText("Quantidade de créditos")).toHaveProperty("value", "");
    expect(screen.getByLabelText("Preço em centavos (opcional)")).toHaveProperty("value", "");
    expect(screen.getByLabelText("Moeda ISO (opcional)")).toHaveProperty("value", "");
    expect(screen.getByLabelText("Ativar pacote")).toHaveProperty("checked", false);
    expect(screen.getByText(/A compra usa a conta Mercado Pago configurada pelo proprietário/)).toBeTruthy();
    expect(fetcher.mock.calls.map(([path]) => String(path))).not.toContain("/api/admin/credits/packages");
  });

  it("cria pacote com valores informados pelo proprietário e mantém-no inativo sem preço", async () => {
    const requests: Array<{ path: string; init?: RequestInit }> = [];
    let items: typeof packageItem[] = [];
    const fetcher = vi.fn((input: string | URL | Request, init?: RequestInit) => {
      const path = String(input);
      if (path.startsWith("/api/admin/credits/history?")) return Promise.resolve(jsonResponse({ items: [], has_more: false }));
      requests.push({ path, init });
      if (path === "/api/admin/credits/wallet") {
        return Promise.resolve(jsonResponse({ wallet: ownerWallet, entries: [] }));
      }
      if (path === "/api/admin/credits/capabilities") {
        return Promise.resolve(jsonResponse({ manage_packages: true }));
      }
      if (path === "/api/admin/platform/credit-tenants") return Promise.resolve(jsonResponse({ items: [] }));
      if (path === "/api/admin/platform/credit-packages" && init?.method === "POST") {
        const body = JSON.parse(String(init.body)) as Omit<typeof packageItem, "id" | "created_at" | "updated_at">;
        items = [{ ...packageItem, ...body }];
        return Promise.resolve(jsonResponse(items[0], 201));
      }
      if (path === "/api/admin/platform/credit-packages") {
        return Promise.resolve(jsonResponse({ items }));
      }
      throw new Error(`Rota inesperada: ${path}`);
    });
    vi.stubGlobal("fetch", fetcher);

    render(<CreditsPage />);
    await screen.findByText("Nenhum pacote configurado");
    fireEvent.change(screen.getByLabelText("Nome do pacote"), { target: { value: "Pacote de teste" } });
    fireEvent.change(screen.getByLabelText("Quantidade de créditos"), { target: { value: "25" } });
    fireEvent.change(screen.getByLabelText("Senha atual para alterar pacote"), { target: { value: "synthetic-owner-password" } });
    fireEvent.change(screen.getByLabelText("Código do autenticador para alterar pacote"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Criar pacote" }));

    expect(await screen.findByText("Pacote criado como configurado.")).toBeTruthy();
    expect(await screen.findByRole("heading", { name: "Pacote de teste" })).toBeTruthy();
    const createRequest = requests.find((request) => request.init?.method === "POST");
    expect(JSON.parse(String(createRequest?.init?.body))).toMatchObject({
      name: "Pacote de teste",
      description: null,
      credit_quantity: 25,
      price_cents: null,
      currency_code: null,
      active: false,
      current_password: "synthetic-owner-password",
      totp_code: "123456",
    });
    expect(JSON.parse(String(createRequest?.init?.body)).request_id).toMatch(/^[0-9a-f-]{36}$/i);
  });

  it("exibe insuficiência retornada pela carteira e não converte falha de consulta em saldo zero", async () => {
    const fetcher = vi.fn((input: string | URL | Request) => {
      const path = String(input);
      if (path.startsWith("/api/admin/credits/history?")) return Promise.resolve(jsonResponse({ items: [], has_more: false }));
      if (path === "/api/admin/credits/wallet") {
        return Promise.resolve(jsonResponse({
          wallet: { ...finiteWallet, available_credits: 0, can_upload_content: false },
          entries: [],
        }));
      }
      if (path === "/api/admin/credits/capabilities") {
        return Promise.resolve(jsonResponse({ manage_packages: false }));
      }
      if (path === "/api/admin/credits/packages") return Promise.resolve(jsonResponse({ items: [] }));
      if (path === "/api/admin/credits/purchases?limit=20" || path === "/api/admin/credits/purchases/active") {
        return Promise.resolve(jsonResponse({ items: [] }));
      }
      throw new Error(`Rota inesperada: ${path}`);
    });
    vi.stubGlobal("fetch", fetcher);

    const { unmount } = render(<CreditsPage />);

    expect(await screen.findByText("Saldo insuficiente para novos uploads")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Adquira um pacote →" }).getAttribute("href"))
      .toBe("/admin/credits#credit-packages");
    unmount();

    vi.unstubAllGlobals();
    vi.stubGlobal("fetch", vi.fn((input: string | URL | Request) => {
      const path = String(input);
      if (path.startsWith("/api/admin/credits/history?")) return Promise.resolve(jsonResponse({ items: [], has_more: false }));
      if (path === "/api/admin/credits/wallet") return Promise.resolve(jsonResponse({ detail: "Indisponível" }, 503));
      if (path === "/api/admin/credits/capabilities") return Promise.resolve(jsonResponse({ manage_packages: true }));
      if (path === "/api/admin/platform/credit-tenants") return Promise.resolve(jsonResponse({ items: [] }));
      return Promise.resolve(jsonResponse({ items: [] }));
    }));
    render(<CreditsPage />);
    expect(await screen.findByText("Saldo indisponível")).toBeTruthy();
    expect(await screen.findByRole("heading", { name: "Pacotes de créditos" })).toBeTruthy();
    expect(screen.queryByText("0")).toBeNull();
  });

  it("distingue bloqueio financeiro de saldo insuficiente e pausa compras", async () => {
    const fetcher = vi.fn((input: string | URL | Request) => {
      const path = String(input);
      if (path.startsWith("/api/admin/credits/history?")) return Promise.resolve(jsonResponse({ items: [], has_more: false }));
      if (path === "/api/admin/credits/wallet") {
        return Promise.resolve(jsonResponse({
          wallet: {
            ...finiteWallet,
            available_credits: 8,
            can_upload_content: false,
            financial_review_hold: true,
            financial_review_count: 1,
          },
          entries: [],
        }));
      }
      if (path === "/api/admin/credits/capabilities") return Promise.resolve(jsonResponse({ manage_packages: false }));
      if (path === "/api/admin/credits/packages") return Promise.resolve(jsonResponse({ items: [{
        ...packageItem,
        name: "Pacote ativo para fotógrafos",
        credit_quantity: 40,
        price_cents: 4900,
        currency_code: "BRL",
        active: true,
      }] }));
      if (path === "/api/admin/credits/purchases?limit=20" || path === "/api/admin/credits/purchases/active") {
        return Promise.resolve(jsonResponse({ items: [] }));
      }
      throw new Error(`Rota inesperada: ${path}`);
    });
    vi.stubGlobal("fetch", fetcher);

    render(<CreditsPage />);

    expect(await screen.findByText("Conta bloqueada para revisão financeira")).toBeTruthy();
    expect(screen.queryByText("Saldo insuficiente para novos uploads")).toBeNull();
    expect(screen.getByRole("button", { name: "Comprar pacote" })).toHaveProperty("disabled", true);
  });

  it("permite editar pacote já configurado pelo proprietário", async () => {
    const requests: Array<{ path: string; init?: RequestInit }> = [];
    const fetcher = vi.fn((input: string | URL | Request, init?: RequestInit) => {
      const path = String(input);
      if (path.startsWith("/api/admin/credits/history?")) return Promise.resolve(jsonResponse({ items: [], has_more: false }));
      requests.push({ path, init });
      if (path === "/api/admin/credits/wallet") return Promise.resolve(jsonResponse({ wallet: ownerWallet, entries: [] }));
      if (path === "/api/admin/credits/capabilities") return Promise.resolve(jsonResponse({ manage_packages: true }));
      if (path === "/api/admin/platform/credit-tenants") return Promise.resolve(jsonResponse({ items: [] }));
      if (path === "/api/admin/platform/credit-packages/package-1" && init?.method === "PUT") {
        return Promise.resolve(jsonResponse({ ...packageItem, credit_quantity: 30 }));
      }
      if (path === "/api/admin/platform/credit-packages") return Promise.resolve(jsonResponse({ items: [packageItem] }));
      throw new Error(`Rota inesperada: ${path}`);
    });
    vi.stubGlobal("fetch", fetcher);

    render(<CreditsPage />);
    await screen.findByRole("heading", { name: packageItem.name });
    fireEvent.click(screen.getByRole("button", { name: "Editar pacote" }));
    fireEvent.change(screen.getByLabelText("Quantidade de créditos"), { target: { value: "30" } });
    fireEvent.change(screen.getByLabelText("Senha atual para alterar pacote"), { target: { value: "synthetic-owner-password" } });
    fireEvent.change(screen.getByLabelText("Código do autenticador para alterar pacote"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Salvar alterações" }));

    expect(await screen.findByText("Pacote atualizado.")).toBeTruthy();
    await waitFor(() => expect(requests.some((request) => request.path.endsWith("/package-1") && request.init?.method === "PUT")).toBe(true));
  });
});
