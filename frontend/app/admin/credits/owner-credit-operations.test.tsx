import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { OwnerCreditOperations } from "./owner-credit-operations";

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

const ownerTenant = {
  tenant_id: "owner-tenant-0001",
  status: "active",
  canonical_host: null,
  photographer_name: null,
  admin_emails: ["proprietario@example.test"],
  wallet: {
    mode: "unmetered",
    available_credits: null,
    reserved_credits: 0,
    pending_operations: 0,
    recent_consumed_credits: 0,
    recent_period_days: 30,
    can_upload_content: true,
    state: "available",
  },
};

const photographerTenant = {
  tenant_id: "photographer-tenant-01",
  status: "active",
  canonical_host: "studio.example.test",
  photographer_name: "Estúdio Aurora",
  admin_emails: ["fotografo@example.test"],
  wallet: {
    mode: "finite",
    available_credits: 4,
    reserved_credits: 1,
    pending_operations: 1,
    recent_consumed_credits: 3,
    recent_period_days: 30,
    can_upload_content: true,
    state: "available",
  },
};

const grant = {
  id: "grant-entry-01",
  type: "owner_grant",
  delta: 5,
  quantity: 5,
  revocable_quantity: 3,
  source_reference: "grant-reference-01",
  description: "Créditos concedidos pelo proprietário",
  created_at: "2026-10-31T12:00:00Z",
};

const detail = {
  wallet: photographerTenant.wallet,
  entries: [grant],
  revocable_grants: [grant],
  financial_reviews: [],
};

const financialReview = {
  purchase_id: "credit-purchase-01",
  tenant_id: photographerTenant.tenant_id,
  photographer_email: photographerTenant.admin_emails[0],
  package_name: "Pacote mensal",
  credit_quantity: 40,
  total_cents: 4900,
  currency_code: "BRL",
  payment_state: "charged_back",
  review_status: "pending",
  review_note: null,
  reviewed_by_admin_id: null,
  created_at: "2026-10-31T12:00:00Z",
  reviewed_at: null,
  events: [],
};

function searchResponse(path: string) {
  const query = new URL(path, "http://localhost").searchParams.get("query")?.toLowerCase() ?? "";
  const items = [ownerTenant, photographerTenant]
    .map((item) => ({
      tenant_id: item.tenant_id,
      status: item.status,
      canonical_host: item.canonical_host,
      photographer_name: item.photographer_name,
      admin_email: item.admin_emails[0],
    }))
    .filter((item) => item.admin_email.toLowerCase().includes(query)
      || (item.photographer_name ?? "").toLowerCase().includes(query));
  return jsonResponse({ items });
}

async function choosePhotographer() {
  const picker = await screen.findByRole("combobox", { name: "Buscar fotógrafo pelo nome ou e-mail" });
  fireEvent.change(picker, { target: { value: "fotografo" } });
  fireEvent.click(await screen.findByRole("option", { name: /fotografo@example\.test/ }));
}

describe("operações do proprietário nas carteiras", () => {
  it("inicia limpo e combina a opção de consulta com o e-mail no servidor", async () => {
    const queries: URLSearchParams[] = [];
    const fetcher = vi.fn((input: string | URL | Request) => {
      const path = String(input);
      if (path === "/api/admin/platform/credit-purchases/reviews") return Promise.resolve(jsonResponse({ items: [] }));
      if (path.startsWith("/api/admin/platform/credit-tenants/search?")) {
        queries.push(new URL(path, "http://localhost").searchParams);
        return Promise.resolve(searchResponse(path));
      }
      throw new Error(`Rota inesperada: ${path}`);
    });
    vi.stubGlobal("fetch", fetcher);
    render(<OwnerCreditOperations />);
    const mode = screen.getByRole("combobox", { name: "Visualizar fotógrafos" });
    const picker = screen.getByRole("combobox", { name: "Buscar fotógrafo pelo nome ou e-mail" });
    expect(mode).toHaveProperty("value", "");
    expect(picker).toHaveProperty("value", "");
    await act(async () => { await new Promise((resolve) => setTimeout(resolve, 300)); });
    expect(queries).toHaveLength(0);
    expect(screen.queryByRole("listbox")).toBeNull();

    fireEvent.change(mode, { target: { value: "all" } });
    expect(await screen.findByRole("option", { name: /fotografo@example\.test/ })).toBeTruthy();
    expect(queries.at(-1)?.get("mode")).toBe("all");
    expect(queries.at(-1)?.get("offset")).toBe("0");
    fireEvent.change(mode, { target: { value: "alphabetical" } });
    await waitFor(() => expect(queries.at(-1)?.get("mode")).toBe("alphabetical"));
    fireEvent.change(mode, { target: { value: "recent" } });
    await waitFor(() => expect(queries.at(-1)?.get("mode")).toBe("recent"));
    fireEvent.change(picker, { target: { value: "fotografo" } });
    await waitFor(() => expect(queries.at(-1)?.get("query")).toBe("fotografo"));
    expect(queries.at(-1)?.get("mode")).toBe("recent");
    expect(queries.at(-1)?.get("offset")).toBe("0");
    expect(fetcher.mock.calls.some(([path]) => String(path) === "/api/admin/platform/credit-tenants")).toBe(false);
  });

  it("encontra pelo nome cadastrado e abre a carteira correspondente", async () => {
    const fetcher = vi.fn((input: string | URL | Request) => {
      const path = String(input);
      if (path === "/api/admin/platform/credit-purchases/reviews") return Promise.resolve(jsonResponse({ items: [] }));
      if (path.startsWith("/api/admin/platform/credit-tenants/search?")) return Promise.resolve(searchResponse(path));
      if (path === `/api/admin/platform/credit-tenants/${photographerTenant.tenant_id}`) return Promise.resolve(jsonResponse(detail));
      throw new Error(`Rota inesperada: ${path}`);
    });
    vi.stubGlobal("fetch", fetcher);
    render(<OwnerCreditOperations />);
    const picker = screen.getByRole("combobox", { name: "Buscar fotógrafo pelo nome ou e-mail" });
    fireEvent.change(picker, { target: { value: "aurora" } });
    const suggestion = await screen.findByRole("option", { name: /Estúdio Aurora · fotografo@example\.test/ });
    fireEvent.click(suggestion);
    expect(await screen.findByRole("heading", { name: "Conceder créditos" })).toBeTruthy();
    expect(screen.getByText("Créditos disponíveis")).toBeTruthy();
    expect(fetcher.mock.calls.some(([path]) => String(path) === `/api/admin/platform/credit-tenants/${photographerTenant.tenant_id}`)).toBe(true);
  });

  it("carrega a próxima página sem duplicar itens e preserva a ordem retornada", async () => {
    const first = { tenant_id: "first", photographer_name: null, admin_email: "a@example.test", status: "active", canonical_host: null };
    const second = { tenant_id: "second", photographer_name: null, admin_email: "b@example.test", status: "active", canonical_host: null };
    const third = { tenant_id: "third", photographer_name: null, admin_email: "c@example.test", status: "active", canonical_host: null };
    const offsets: string[] = [];
    vi.stubGlobal("fetch", vi.fn((input: string | URL | Request) => {
      const path = String(input);
      if (path === "/api/admin/platform/credit-purchases/reviews") return Promise.resolve(jsonResponse({ items: [] }));
      const offset = new URL(path, "http://localhost").searchParams.get("offset") ?? "0";
      offsets.push(offset);
      return Promise.resolve(jsonResponse(offset === "0"
        ? { items: [first, second], has_more: true }
        : { items: [second, third], has_more: false }));
    }));
    render(<OwnerCreditOperations />);
    fireEvent.change(screen.getByRole("combobox", { name: "Visualizar fotógrafos" }), { target: { value: "alphabetical" } });
    fireEvent.click(await screen.findByRole("button", { name: "Carregar mais" }));
    expect(await screen.findByRole("option", { name: /c@example\.test/ })).toBeTruthy();
    const list = screen.getByRole("listbox", { name: "Sugestões de fotógrafos" });
    expect(within(list).getAllByRole("option").map((item) => item.textContent)).toEqual([
      expect.stringContaining("a@example.test"), expect.stringContaining("b@example.test"), expect.stringContaining("c@example.test"),
    ]);
    expect(offsets).toEqual(["0", "2"]);
    expect(screen.queryByRole("button", { name: "Carregar mais" })).toBeNull();
  });

  it("fecha sugestões ao selecionar e Limpar restaura o estado inicial sem nova listagem", async () => {
    const fetcher = vi.fn((input: string | URL | Request) => {
      const path = String(input);
      if (path === "/api/admin/platform/credit-purchases/reviews") return Promise.resolve(jsonResponse({ items: [] }));
      if (path.startsWith("/api/admin/platform/credit-tenants/search?")) return Promise.resolve(searchResponse(path));
      if (path === `/api/admin/platform/credit-tenants/${photographerTenant.tenant_id}`) return Promise.resolve(jsonResponse(detail));
      throw new Error(`Rota inesperada: ${path}`);
    });
    vi.stubGlobal("fetch", fetcher);
    render(<OwnerCreditOperations />);
    const mode = screen.getByRole("combobox", { name: "Visualizar fotógrafos" });
    fireEvent.change(mode, { target: { value: "all" } });
    fireEvent.click(await screen.findByRole("option", { name: /fotografo@example\.test/ }));
    expect(await screen.findByRole("heading", { name: "Conceder créditos" })).toBeTruthy();
    const listingCount = fetcher.mock.calls.filter(([path]) => String(path).includes("/search?")).length;
    await act(async () => { await new Promise((resolve) => setTimeout(resolve, 300)); });
    expect(fetcher.mock.calls.filter(([path]) => String(path).includes("/search?"))).toHaveLength(listingCount);
    expect(mode).toHaveProperty("value", "all");
    expect(screen.queryByRole("listbox")).toBeNull();
    expect(screen.queryByText("Nenhum fotógrafo encontrado")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Limpar" }));
    expect(mode).toHaveProperty("value", "");
    expect(screen.getByRole("combobox", { name: "Buscar fotógrafo pelo nome ou e-mail" })).toHaveProperty("value", "");
    expect(screen.queryByRole("heading", { name: "Conceder créditos" })).toBeNull();
    expect(screen.queryByRole("listbox")).toBeNull();
  });

  it("ignora uma página atrasada após trocar o filtro e reinicia no offset zero", async () => {
    let resolveMore: ((response: Response) => void) | undefined;
    const requests: URLSearchParams[] = [];
    vi.stubGlobal("fetch", vi.fn((input: string | URL | Request) => {
      const path = String(input);
      if (path === "/api/admin/platform/credit-purchases/reviews") return Promise.resolve(jsonResponse({ items: [] }));
      const parameters = new URL(path, "http://localhost").searchParams;
      requests.push(parameters);
      if (parameters.get("offset") === "1") return new Promise<Response>((resolve) => { resolveMore = resolve; });
      return Promise.resolve(jsonResponse({
        items: [{ tenant_id: "owner", photographer_name: null, admin_email: "owner@example.test", status: "active", canonical_host: null }],
        has_more: parameters.get("mode") === "all",
      }));
    }));
    render(<OwnerCreditOperations />);
    const mode = screen.getByRole("combobox", { name: "Visualizar fotógrafos" });
    fireEvent.change(mode, { target: { value: "all" } });
    fireEvent.click(await screen.findByRole("button", { name: "Carregar mais" }));
    await waitFor(() => expect(resolveMore).toBeTypeOf("function"));
    fireEvent.change(mode, { target: { value: "recent" } });
    await waitFor(() => expect(requests.at(-1)?.get("mode")).toBe("recent"));
    await act(async () => { resolveMore?.(jsonResponse({ items: [{
      tenant_id: "stale", photographer_name: null, admin_email: "stale@example.test", status: "active", canonical_host: null,
    }], has_more: true })); });
    expect(screen.queryByRole("option", { name: /stale@example\.test/ })).toBeNull();
    expect(requests.at(-1)?.get("offset")).toBe("0");
    expect(screen.queryByRole("button", { name: "Carregar mais" })).toBeNull();
  });

  it("mantém a página visível quando carregar mais falha e permite repetir", async () => {
    let attempts = 0;
    vi.stubGlobal("fetch", vi.fn((input: string | URL | Request) => {
      const path = String(input);
      if (path === "/api/admin/platform/credit-purchases/reviews") return Promise.resolve(jsonResponse({ items: [] }));
      const offset = new URL(path, "http://localhost").searchParams.get("offset");
      if (offset === "1") {
        attempts += 1;
        return Promise.resolve(attempts === 1 ? jsonResponse({ detail: "Página temporariamente indisponível" }, 503)
          : jsonResponse({ items: [], has_more: false }));
      }
      return Promise.resolve(jsonResponse({ items: [{
        tenant_id: "existing", photographer_name: null, admin_email: "existing@example.test", status: "active", canonical_host: null,
      }], has_more: true }));
    }));
    render(<OwnerCreditOperations />);
    fireEvent.change(screen.getByRole("combobox", { name: "Visualizar fotógrafos" }), { target: { value: "all" } });
    fireEvent.click(await screen.findByRole("button", { name: "Carregar mais" }));
    expect(await screen.findByRole("alert")).toHaveProperty("textContent", "Página temporariamente indisponível");
    expect(screen.getByRole("option", { name: /existing@example\.test/ })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Carregar mais" }));
    await waitFor(() => expect(screen.queryByRole("button", { name: "Carregar mais" })).toBeNull());
    expect(attempts).toBe(2);
  });

  it("limpa os campos de concessão e revogação ao trocar a busca do tenant", async () => {
    vi.stubGlobal("fetch", vi.fn((input: string | URL | Request) => {
      const path = String(input);
      if (path === "/api/admin/platform/credit-purchases/reviews") return Promise.resolve(jsonResponse({ items: [] }));
      if (path.startsWith("/api/admin/platform/credit-tenants/search?")) return Promise.resolve(searchResponse(path));
      if (path === `/api/admin/platform/credit-tenants/${photographerTenant.tenant_id}`) {
        return Promise.resolve(jsonResponse(detail));
      }
      throw new Error(`Rota inesperada: ${path}`);
    }));

    render(<OwnerCreditOperations />);
    await choosePhotographer();
    await screen.findByRole("heading", { name: "Conceder créditos" });
    fireEvent.change(screen.getAllByLabelText("Quantidade", { selector: "input" })[0], { target: { value: "7" } });
    fireEvent.change(screen.getByLabelText("Referência da concessão"), { target: { value: "referência A" } });
    fireEvent.change(screen.getAllByLabelText("Senha atual")[0], { target: { value: "senha sintética" } });
    fireEvent.change(screen.getAllByLabelText("Código do autenticador")[0], { target: { value: "123456" } });
    fireEvent.change(screen.getByLabelText("Concessão de origem"), { target: { value: grant.id } });
    fireEvent.change(screen.getAllByLabelText("Quantidade", { selector: "input" })[1], { target: { value: "2" } });
    fireEvent.change(screen.getByLabelText("Referência da revogação"), { target: { value: "referência B" } });
    fireEvent.change(screen.getAllByLabelText("Senha atual")[1], { target: { value: "outra senha sintética" } });
    fireEvent.change(screen.getAllByLabelText("Código do autenticador")[1], { target: { value: "654321" } });

    const picker = screen.getByRole("combobox", { name: "Buscar fotógrafo pelo nome ou e-mail" });
    fireEvent.change(picker, { target: { value: "semresultado" } });
    expect(await screen.findByText("Nenhum fotógrafo encontrado")).toBeTruthy();
    fireEvent.change(picker, { target: { value: "fotografo" } });
    fireEvent.click(await screen.findByRole("option", { name: /fotografo@example\.test/ }));

    expect(await screen.findByRole("heading", { name: "Conceder créditos" })).toBeTruthy();
    expect(screen.getAllByLabelText("Quantidade", { selector: "input" })).toHaveLength(2);
    for (const input of screen.getAllByLabelText("Quantidade", { selector: "input" })) {
      expect(input).toHaveProperty("value", "");
    }
    expect(screen.getByLabelText("Referência da concessão")).toHaveProperty("value", "");
    expect(screen.getByLabelText("Concessão de origem")).toHaveProperty("value", "");
    expect(screen.getByLabelText("Referência da revogação")).toHaveProperty("value", "");
    for (const input of screen.getAllByLabelText("Senha atual")) expect(input).toHaveProperty("value", "");
    for (const input of screen.getAllByLabelText("Código do autenticador")) expect(input).toHaveProperty("value", "");
  });

  it("mantém o tenant fixo e bloqueia campos enquanto uma concessão aguarda resposta", async () => {
    let finishGrant: ((response: Response) => void) | null = null;
    vi.stubGlobal("fetch", vi.fn((input: string | URL | Request, init?: RequestInit) => {
      const path = String(input);
      if (path === "/api/admin/platform/credit-purchases/reviews") return Promise.resolve(jsonResponse({ items: [] }));
      if (path.startsWith("/api/admin/platform/credit-tenants/search?")) return Promise.resolve(searchResponse(path));
      if (path === `/api/admin/platform/credit-tenants/${photographerTenant.tenant_id}`) {
        return Promise.resolve(jsonResponse(detail));
      }
      if (path === "/api/admin/platform/credit-grants" && init?.method === "POST") {
        return new Promise<Response>((resolve) => { finishGrant = resolve; });
      }
      throw new Error(`Rota inesperada: ${path}`);
    }));

    render(<OwnerCreditOperations />);
    await choosePhotographer();
    await screen.findByRole("heading", { name: "Conceder créditos" });
    fireEvent.change(screen.getAllByLabelText("Quantidade", { selector: "input" })[0], { target: { value: "7" } });
    fireEvent.change(screen.getByLabelText("Referência da concessão"), { target: { value: "referência pendente" } });
    fireEvent.change(screen.getAllByLabelText("Senha atual")[0], { target: { value: "senha sintética" } });
    fireEvent.change(screen.getAllByLabelText("Código do autenticador")[0], { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Conceder créditos" }));

    await waitFor(() => {
      expect(screen.getByRole("combobox", { name: "Buscar fotógrafo pelo nome ou e-mail" })).toHaveProperty("disabled", true);
      expect(screen.getByLabelText("Visualizar fotógrafos")).toHaveProperty("disabled", true);
      expect(screen.getAllByLabelText("Senha atual")[0]).toHaveProperty("disabled", true);
      expect(screen.getByLabelText("Referência da concessão")).toHaveProperty("disabled", true);
    });
    expect(screen.getByText(`Tenant ${photographerTenant.tenant_id}`)).toBeTruthy();

    await act(async () => {
      if (!finishGrant) throw new Error("A concessão não iniciou a requisição pendente.");
      finishGrant(jsonResponse({ entry: grant, wallet: photographerTenant.wallet }, 201));
    });
    expect(await screen.findByText("Concessão registrada e auditada.")).toBeTruthy();
    expect(screen.getByText(`Tenant ${photographerTenant.tenant_id}`)).toBeTruthy();
  });

  it("lista e seleciona fotógrafos, mostra saldo e restringe a conta ilimitada", async () => {
    const fetcher = vi.fn((input: string | URL | Request) => {
      const path = String(input);
      if (path.startsWith("/api/admin/platform/credit-tenants/search?")) return Promise.resolve(searchResponse(path));
      if (path === `/api/admin/platform/credit-tenants/${photographerTenant.tenant_id}`) {
        return Promise.resolve(jsonResponse(detail));
      }
      if (path === `/api/admin/platform/credit-tenants/${ownerTenant.tenant_id}`) {
        return Promise.resolve(jsonResponse({ wallet: ownerTenant.wallet, entries: [], revocable_grants: [], financial_reviews: [] }));
      }
      throw new Error(`Rota inesperada: ${path}`);
    });
    vi.stubGlobal("fetch", fetcher);

    render(<OwnerCreditOperations />);
    const picker = await screen.findByRole("combobox", { name: "Buscar fotógrafo pelo nome ou e-mail" });
    fireEvent.change(picker, { target: { value: "fotografo" } });
    fireEvent.click(await screen.findByRole("option", { name: /fotografo@example\.test/ }));
    expect(await screen.findByText("4")).toBeTruthy();
    expect(screen.getByText("Créditos disponíveis")).toBeTruthy();
    expect(screen.getByText(/3 de 5 crédito\(s\) disponível\(is\)/)).toBeTruthy();
    expect(screen.getAllByLabelText("Quantidade", { selector: "input" })).toHaveLength(2);
    expect(screen.getByLabelText("Referência da concessão")).toHaveProperty("value", "");
    fireEvent.change(picker, { target: { value: "proprietario" } });
    fireEvent.click(await screen.findByRole("option", { name: /proprietario@example\.test/ }));
    expect(await screen.findByText("Ilimitado")).toBeTruthy();
    expect(screen.getByText("Conta ilimitada do proprietário")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Conceder créditos" })).toBeNull();
    expect(fetcher.mock.calls.some(([path]) => String(path) === "/api/admin/platform/credit-tenants")).toBe(false);
  });

  it("sugere enquanto digita e aceita seleção por teclado", async () => {
    const fetcher = vi.fn((input: string | URL | Request) => {
      const path = String(input);
      if (path.startsWith("/api/admin/platform/credit-tenants/search?")) return Promise.resolve(searchResponse(path));
      if (path === `/api/admin/platform/credit-tenants/${photographerTenant.tenant_id}`) {
        return Promise.resolve(jsonResponse(detail));
      }
      throw new Error(`Rota inesperada: ${path}`);
    });
    vi.stubGlobal("fetch", fetcher);

    render(<OwnerCreditOperations />);
    const picker = await screen.findByRole("combobox", { name: "Buscar fotógrafo pelo nome ou e-mail" });
    fireEvent.change(picker, { target: { value: "f" } });
    expect(fetcher.mock.calls.some(([path]) => String(path).includes("/search?"))).toBe(false);
    fireEvent.change(picker, { target: { value: "fotografo" } });
    const suggestion = await screen.findByRole("option", { name: /fotografo@example\.test/ });
    fireEvent.keyDown(picker, { key: "ArrowDown" });
    expect(picker.getAttribute("aria-activedescendant")).toBe(suggestion.id);
    fireEvent.keyDown(picker, { key: "Enter" });
    expect(await screen.findByRole("heading", { name: "Conceder créditos" })).toBeTruthy();
    expect(screen.queryByText("Nenhum fotógrafo encontrado")).toBeNull();
  });

  it("ignora resultados atrasados da busca anterior", async () => {
    const deferred: {
      previous?: (response: Response) => void;
      current?: (response: Response) => void;
    } = {};
    const fetcher = vi.fn((input: string | URL | Request) => {
      const query = new URL(String(input), "http://localhost").searchParams.get("query");
      if (query === "foto") {
        return new Promise<Response>((resolve) => { deferred.previous = resolve; });
      }
      if (query === "pro") {
        return new Promise<Response>((resolve) => { deferred.current = resolve; });
      }
      throw new Error(`Consulta inesperada: ${query}`);
    });
    vi.stubGlobal("fetch", fetcher);

    render(<OwnerCreditOperations />);
    const picker = await screen.findByRole("combobox", { name: "Buscar fotógrafo pelo nome ou e-mail" });
    fireEvent.change(picker, { target: { value: "foto" } });
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(1));
    fireEvent.change(picker, { target: { value: "pro" } });
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2));

    await act(async () => {
      deferred.previous?.(jsonResponse({ items: [{
        tenant_id: photographerTenant.tenant_id,
        status: photographerTenant.status,
        canonical_host: photographerTenant.canonical_host,
        photographer_name: photographerTenant.photographer_name,
        admin_email: photographerTenant.admin_emails[0],
      }] }));
    });
    expect(screen.queryByRole("listbox", { name: "Sugestões de fotógrafos" })).toBeNull();

    await act(async () => {
      deferred.current?.(jsonResponse({ items: [{
        tenant_id: ownerTenant.tenant_id,
        status: ownerTenant.status,
        canonical_host: ownerTenant.canonical_host,
        photographer_name: ownerTenant.photographer_name,
        admin_email: ownerTenant.admin_emails[0],
      }] }));
    });
    expect(await screen.findByRole("option", { name: /proprietario@example\.test/ })).toBeTruthy();
  });

  it("diferencia a busca sem resultados da falha do serviço", async () => {
    let status = 200;
    vi.stubGlobal("fetch", vi.fn((input: string | URL | Request) => {
      const path = String(input);
      if (path.startsWith("/api/admin/platform/credit-tenants/search?")) {
        return Promise.resolve(jsonResponse(status === 200 ? { items: [] } : { detail: "Indisponível" }, status));
      }
      throw new Error(`Rota inesperada: ${path}`);
    }));

    const { unmount } = render(<OwnerCreditOperations />);
    const picker = await screen.findByRole("combobox", { name: "Buscar fotógrafo pelo nome ou e-mail" });
    fireEvent.change(picker, { target: { value: "semresultado" } });
    expect(await screen.findByText("Nenhum fotógrafo encontrado")).toBeTruthy();
    unmount();

    status = 503;
    render(<OwnerCreditOperations />);
    fireEvent.change(screen.getByRole("combobox", { name: "Buscar fotógrafo pelo nome ou e-mail" }), {
      target: { value: "erro" },
    });
    expect(await screen.findByText("Busca de fotógrafos indisponível")).toBeTruthy();
  });

  it("repete concessão com a mesma chave idempotente quando a resposta falha", async () => {
    const requests: Array<{ path: string; init?: RequestInit }> = [];
    let grantAttempts = 0;
    const fetcher = vi.fn((input: string | URL | Request, init?: RequestInit) => {
      const path = String(input);
      requests.push({ path, init });
      if (path === "/api/admin/platform/credit-purchases/reviews") return Promise.resolve(jsonResponse({ items: [] }));
      if (path.startsWith("/api/admin/platform/credit-tenants/search?")) return Promise.resolve(searchResponse(path));
      if (path === `/api/admin/platform/credit-tenants/${photographerTenant.tenant_id}`) {
        return Promise.resolve(jsonResponse(detail));
      }
      if (path === "/api/admin/platform/credit-grants" && init?.method === "POST") {
        grantAttempts++;
        return Promise.resolve(grantAttempts === 1
          ? jsonResponse({ detail: "Resposta temporariamente indisponível." }, 503)
          : jsonResponse({ entry: grant, wallet: photographerTenant.wallet }, 201));
      }
      throw new Error(`Rota inesperada: ${path}`);
    });
    vi.stubGlobal("fetch", fetcher);

    render(<OwnerCreditOperations />);
    await choosePhotographer();
    await screen.findByRole("heading", { name: "Conceder créditos" });
    fireEvent.change(screen.getAllByLabelText("Quantidade", { selector: "input" })[0], { target: { value: "7" } });
    fireEvent.change(screen.getByLabelText("Referência da concessão"), { target: { value: "decisão do proprietário" } });
    fireEvent.change(screen.getAllByLabelText("Senha atual")[0], { target: { value: "synthetic-owner-password" } });
    fireEvent.change(screen.getAllByLabelText("Código do autenticador")[0], { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Conceder créditos" }));
    expect(await screen.findByRole("alert")).toHaveProperty("textContent", expect.stringContaining("temporariamente"));
    fireEvent.change(screen.getAllByLabelText("Código do autenticador")[0], { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Conceder créditos" }));

    expect(await screen.findByText("Concessão registrada e auditada.")).toBeTruthy();
    const grantBodies = requests
      .filter((request) => request.path === "/api/admin/platform/credit-grants" && request.init?.method === "POST")
      .map((request) => JSON.parse(String(request.init?.body)));
    expect(grantBodies).toHaveLength(2);
    expect(grantBodies[0]).toEqual(grantBodies[1]);
    expect(grantBodies[0]).toMatchObject({
      tenant_id: photographerTenant.tenant_id,
      quantity: 7,
      reference: "decisão do proprietário",
      current_password: "synthetic-owner-password",
      totp_code: "123456",
    });
    expect(grantBodies[0].request_id).toMatch(/^[0-9a-f-]{36}$/i);
    expect(grantBodies[0].idempotency_key).toMatch(/^owner-credit-/);
  });

  it("revoga somente a quantidade escolhida da concessão de origem", async () => {
    const requests: Array<{ path: string; init?: RequestInit }> = [];
    const fetcher = vi.fn((input: string | URL | Request, init?: RequestInit) => {
      const path = String(input);
      requests.push({ path, init });
      if (path.startsWith("/api/admin/platform/credit-tenants/search?")) return Promise.resolve(searchResponse(path));
      if (path === `/api/admin/platform/credit-tenants/${photographerTenant.tenant_id}`) {
        return Promise.resolve(jsonResponse(detail));
      }
      if (path === `/api/admin/platform/credit-grants/${grant.id}/revoke`) {
        return Promise.resolve(jsonResponse({ entry: { ...grant, delta: -2 }, wallet: photographerTenant.wallet }, 201));
      }
      throw new Error(`Rota inesperada: ${path}`);
    });
    vi.stubGlobal("fetch", fetcher);

    render(<OwnerCreditOperations />);
    await choosePhotographer();
    await screen.findByText(/3 livre\(s\)/);
    fireEvent.change(screen.getByLabelText("Concessão de origem"), { target: { value: grant.id } });
    fireEvent.change(screen.getAllByLabelText("Quantidade", { selector: "input" })[1], { target: { value: "2" } });
    fireEvent.change(screen.getByLabelText("Referência da revogação"), { target: { value: "ajuste aprovado" } });
    fireEvent.change(screen.getAllByLabelText("Senha atual")[1], { target: { value: "synthetic-owner-password" } });
    fireEvent.change(screen.getAllByLabelText("Código do autenticador")[1], { target: { value: "654321" } });
    fireEvent.click(screen.getByRole("button", { name: "Revogar créditos" }));

    expect(await screen.findByText("Revogação registrada e auditada na concessão de origem.")).toBeTruthy();
    const request = requests.find((item) => item.path.endsWith(`/${grant.id}/revoke`));
    expect(request?.init?.cache).toBe("no-store");
    expect(JSON.parse(String(request?.init?.body))).toMatchObject({
      tenant_id: photographerTenant.tenant_id,
      quantity: 2,
      reference: "ajuste aprovado",
      current_password: "synthetic-owner-password",
      totp_code: "654321",
    });
    expect(JSON.parse(String(request?.init?.body)).request_id).toMatch(/^[0-9a-f-]{36}$/i);
  });

  it("permite ao proprietário decidir um chargeback com justificativa auditável", async () => {
    const requests: Array<{ path: string; init?: RequestInit }> = [];
    let queue = [financialReview];
    let reviewAttempts = 0;
    const fetcher = vi.fn((input: string | URL | Request, init?: RequestInit) => {
      const path = String(input);
      requests.push({ path, init });
      if (path === "/api/admin/platform/credit-purchases/reviews") {
        return Promise.resolve(jsonResponse({ items: queue }));
      }
      if (path === `/api/admin/platform/credit-purchases/${financialReview.purchase_id}/review`
        && init?.method === "POST") {
        reviewAttempts++;
        if (reviewAttempts === 1) {
          return Promise.resolve(jsonResponse({ detail: "Revisão temporariamente indisponível." }, 503));
        }
        queue = [];
        return Promise.resolve(jsonResponse({ ...detail, financial_reviews: [{
          ...financialReview,
          review_status: "released",
          review_note: "Comprovantes conferidos pelo proprietário",
          reviewed_by_admin_id: "platform-owner-id",
          reviewed_at: "2026-10-31T12:30:00Z",
          events: [{
            event_type: "owner_reviewed",
            occurred_at: "2026-10-31T12:30:00Z",
            details: {
              decision: "release",
              reason: "Comprovantes conferidos pelo proprietário",
              actor_admin_id: "platform-owner-id",
            },
          }],
        }] }));
      }
      throw new Error(`Rota inesperada: ${path}`);
    });
    vi.stubGlobal("fetch", fetcher);

    render(<OwnerCreditOperations />);
    expect(await screen.findByText(/chargeback/i)).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Justificativa desta decisão"), {
      target: { value: "Comprovantes conferidos pelo proprietário" },
    });
    fireEvent.change(screen.getByLabelText("Senha atual para revisão financeira"), { target: { value: "synthetic-owner-password" } });
    fireEvent.change(screen.getByLabelText("Código do autenticador para revisão financeira"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Liberar conta" }));

    expect(await screen.findByRole("alert")).toHaveProperty("textContent", expect.stringContaining("temporariamente"));
    fireEvent.change(screen.getByLabelText("Código do autenticador para revisão financeira"), { target: { value: "654321" } });
    fireEvent.click(screen.getByRole("button", { name: "Liberar conta" }));
    expect(await screen.findByText("Nenhuma compra aguardando revisão")).toBeTruthy();
    expect(await screen.findByText(/Revisão registrada\. Outros bloqueios financeiros/)).toBeTruthy();
    const reviewRequests = requests.filter((request) => request.path.endsWith("/review"));
    expect(reviewRequests).toHaveLength(2);
    expect(reviewRequests[0].init?.method).toBe("POST");
    const firstBody = JSON.parse(String(reviewRequests[0].init?.body));
    const secondBody = JSON.parse(String(reviewRequests[1].init?.body));
    expect(firstBody.request_id).toBe(secondBody.request_id);
    expect(firstBody).toMatchObject({
      decision: "release",
      reason: "Comprovantes conferidos pelo proprietário",
      current_password: "synthetic-owner-password",
      totp_code: "123456",
    });
    expect(secondBody).toMatchObject({
      decision: "release",
      reason: "Comprovantes conferidos pelo proprietário",
      current_password: "synthetic-owner-password",
      totp_code: "654321",
    });
    expect(firstBody.request_id).toMatch(/^[0-9a-f-]{36}$/i);
  });
});
