import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    ...props
  }: React.AnchorHTMLAttributes<HTMLAnchorElement>) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

import AdminPage from "./page";

afterEach(() => vi.unstubAllGlobals());

it("falha temporária da visão geral não orienta logout ou novo login", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 503 })));
  render(<AdminPage />);
  await screen.findByText("Acesso administrativo indisponível");
  expect(screen.queryByText(/Entre novamente/)).toBeNull();
  expect(screen.getByText("Não foi possível carregar os dados. Recarregue a página para tentar novamente.")).toBeTruthy();
});

const summary = {
  environment: "development",
  version: "test",
  storage: {
    photo_count: 5,
    bytes: 512 * 1024 * 1024,
    available: true,
  },
  counts: {
    clients: 2,
    parent_galleries: 1,
    derived_galleries: 2,
    imports: { processing: 1 },
    folders_with_active_imports: 1,
    photos_in_folders_with_active_imports: 4,
    folders_preparing: 1,
    folders_released: 3,
  },
  recent_galleries: [
    {
      id: "gallery-1",
      name: "Festa da escola",
      active: true,
      event_name: "Formatura",
    },
    {
      id: "gallery-2",
      name: "Ensaio bloqueado",
      active: false,
      event_name: null,
    },
  ],
  recent_selections: [
    {
      scope_id: "derived-1",
      client: { id: "client-1", name: "Ana Silva" },
      gallery: { id: "derived-1", name: "Álbum da formatura" },
      parent_gallery: { id: "gallery-1", name: "Festa da escola" },
      selected_count: 3,
      selection_started_at: "2026-11-05T12:00:00+00:00",
      last_selected_at: "2026-11-05T12:05:00+00:00",
    },
    {
      scope_id: "gallery-2",
      client: { id: "client-2", name: "Bia Souza" },
      gallery: { id: "gallery-2", name: "Ensaio bloqueado" },
      parent_gallery: { id: "gallery-2", name: "Ensaio bloqueado" },
      selected_count: 1,
      selection_started_at: null,
      last_selected_at: "2026-11-05T12:05:00+00:00",
    },
  ],
};

type TestWallet = {
  mode: "finite" | "unmetered";
  available_credits: number | null;
  reserved_credits: number;
  pending_operations: number;
  recent_consumed_credits: number;
  recent_period_days: number;
  can_upload_content: boolean;
};

const finiteWallet: TestWallet = {
  mode: "finite",
  available_credits: 4,
  reserved_credits: 1,
  pending_operations: 1,
  recent_consumed_credits: 3,
  recent_period_days: 30,
  can_upload_content: true,
};

const ownerWallet: TestWallet = {
  mode: "unmetered",
  available_credits: null,
  reserved_credits: 0,
  pending_operations: 0,
  recent_consumed_credits: 0,
  recent_period_days: 30,
  can_upload_content: true,
};

function dashboardFetcher(summaryPayload: unknown = summary, wallet: TestWallet = finiteWallet, entries: unknown[] = []) {
  return vi.fn((input: string | URL | Request) => {
    if (String(input) === "/api/admin/credits/wallet") {
      return Promise.resolve(new Response(JSON.stringify({ wallet, entries }), { status: 200 }));
    }
    return Promise.resolve(new Response(JSON.stringify(summaryPayload), { status: 200 }));
  });
}

describe("painel operacional", () => {
  it("mostra o estado vazio da seleção e preserva os atalhos de galerias recentes", async () => {
    vi.stubGlobal("fetch", dashboardFetcher({ ...summary, recent_selections: [] }));
    render(<AdminPage />);
    expect(await screen.findByText("Nenhuma cliente está selecionando fotos agora.")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Festa da escola" }).getAttribute("href"))
      .toBe("/admin/galleries/sources/gallery-1");
  });

  it("prioriza ações e pendências com dados disponíveis", async () => {
    vi.stubGlobal("fetch", dashboardFetcher(summary, finiteWallet, [{
      id: "entry-1",
      type: "upload_consumption",
      delta: -1,
      source_reference: "photo-1",
      description: "Upload consumiu um crédito",
      created_at: "2026-10-31T12:00:00Z",
    }]));
    render(<AdminPage />);
    expect(
      await screen.findByRole("heading", {
        name: "Seu próximo passo está à vista.",
      }),
    ).toBeTruthy();
    expect(screen.getByText("Pastas com importação ativa")).toBeTruthy();
    expect(screen.getByText("4 fotos nas pastas ativas")).toBeTruthy();
    expect(screen.getByText("Galerias públicas")).toBeTruthy();
    expect(screen.getByText("Armazenamento de fotos")).toBeTruthy();
    expect(screen.getByText("512 MB")).toBeTruthy();
    expect(screen.getByText("5 fotos")).toBeTruthy();
    expect(screen.getByText("Prática de publicação")).toBeTruthy();
    expect(screen.getByText(/Vincule clientes e publique/)).toBeTruthy();
    expect(screen.queryByText(/responsável/i)).toBeNull();
    expect(
      screen.getByRole("link", { name: "Festa da escola" }).getAttribute("href"),
    ).toBe("/admin/galleries/sources/gallery-1");
    expect(
      screen.getByRole("link", { name: "Ensaio bloqueado" }).getAttribute("href"),
    ).toBe("/admin/galleries/sources/gallery-2");
    expect(screen.getByText("Ativa")).toBeTruthy();
    expect(screen.getByText("Bloqueada")).toBeTruthy();
    expect(screen.getByText("Formatura")).toBeTruthy();
    expect(screen.getByText("Galerias recentes")).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Clientes com seleção em andamento" })).toBeTruthy();
    expect(screen.getByText(`3 foto(s) · Iniciada em ${new Date("2026-11-05T12:00:00+00:00").toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })}`)).toBeTruthy();
    expect(screen.getByText("1 foto(s) · Iniciada em Horário não registrado")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Ana Silva" }).getAttribute("href"))
      .toBe("/admin/payments?client_id=client-1&parent_gallery_id=gallery-1#open-selection-derived-1-client-1");
    expect(screen.getByText("Créditos disponíveis")).toBeTruthy();
    expect(screen.getByText("Consumo nos últimos 30 dias")).toBeTruthy();
    expect(screen.getByText("Uploads pendentes")).toBeTruthy();
    expect(screen.getByText("Upload consumiu um crédito")).toBeTruthy();
    expect(screen.queryByText("Galerias privadas")).toBeNull();
  });

  it.each([
    [{ photo_count: 0, bytes: 0, available: true }, "0 MB", "0 fotos"],
    [
      { photo_count: 1, bytes: 1536 * 1024, available: true },
      "1,5 MB",
      "1 foto",
    ],
    [
      { photo_count: 2048, bytes: 1536 * 1024 * 1024, available: true },
      "1,5 GB",
      "2048 fotos",
    ],
  ])(
    "formata o armazenamento físico e a quantidade de fotos",
    async (storage, expectedSize, expectedCount) => {
      vi.stubGlobal("fetch", dashboardFetcher({ ...summary, storage }));
      render(<AdminPage />);
      expect(await screen.findByText(expectedSize)).toBeTruthy();
      expect(screen.getByText(expectedCount)).toBeTruthy();
    },
  );

  it("isola a indisponibilidade do armazenamento das demais métricas", async () => {
    vi.stubGlobal("fetch", dashboardFetcher({
      ...summary,
      storage: { photo_count: 5, bytes: null, available: false },
    }));
    render(<AdminPage />);
    expect(await screen.findByText("Indisponível")).toBeTruthy();
    expect(screen.getByText("Galerias públicas")).toBeTruthy();
    expect(screen.getByText("5 fotos")).toBeTruthy();
  });

  it("explica falha sem parecer um painel vazio", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(new Response(null, { status: 503 }))),
    );
    render(<AdminPage />);
    await waitFor(() =>
      expect(screen.getByRole("alert").textContent).toContain(
        "Acesso administrativo indisponível",
      ),
    );
  });
});


it("mantém a Visão Geral sem card nem consultas de diagnóstico mesmo para proprietário autorizado", async () => {
  const fetcher = dashboardFetcher(summary, ownerWallet);
  vi.stubGlobal("fetch", fetcher);
  render(<AdminPage />);
  await screen.findByRole("heading", { name: "Seu próximo passo está à vista." });
  expect(await screen.findByText("Ilimitado")).toBeTruthy();
  expect(screen.queryByText("Diagnóstico sob demanda")).toBeNull();
  expect(screen.queryByRole("heading", { name: "Capacidade e filas" })).toBeNull();
  expect(fetcher.mock.calls.map(([url]) => String(url))).toEqual([
    "/api/admin/validation-summary",
    "/api/admin/credits/wallet",
  ]);
});

it("preserva o resumo operacional quando a API da carteira está indisponível", async () => {
  const fetcher = vi.fn((input: string | URL | Request) => String(input) === "/api/admin/credits/wallet"
    ? Promise.resolve(new Response(JSON.stringify({ detail: "Indisponível" }), { status: 503 }))
    : Promise.resolve(new Response(JSON.stringify(summary), { status: 200 })));
  vi.stubGlobal("fetch", fetcher);
  render(<AdminPage />);

  expect(await screen.findByRole("heading", { name: "Seu próximo passo está à vista." })).toBeTruthy();
  expect(await screen.findByText("Saldo indisponível")).toBeTruthy();
  expect(screen.getByText("Galerias públicas")).toBeTruthy();
  expect(screen.getByText("512 MB")).toBeTruthy();
  expect(screen.queryByText("0", { selector: "strong" })).toBeNull();
});

it("apresenta a insuficiência informada pelo snapshot do servidor sem substituir a API no upload", async () => {
  vi.stubGlobal("fetch", dashboardFetcher(summary, { ...finiteWallet, available_credits: 0, can_upload_content: false }));
  render(<AdminPage />);

  const alert = await screen.findByRole("alert");
  expect(alert.textContent).toContain("Saldo insuficiente para novos uploads");
  expect(alert.textContent).not.toMatch(/carteira consultada|API|reserva por foto/i);
  expect(screen.getByRole("link", { name: "Adquira um pacote →" }).getAttribute("href"))
    .toBe("/admin/credits#credit-packages");
  expect(screen.getByText("Galerias públicas")).toBeTruthy();
  expect(screen.getByText("0", { selector: "strong" })).toBeTruthy();
});
