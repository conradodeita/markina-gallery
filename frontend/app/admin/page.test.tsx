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
    folders_preparing: 1,
    folders_released: 3,
  },
  recent_galleries: [
    {
      id: "gallery-1",
      name: "Festa da escola",
      access_enabled: true,
      selection_expires_at: null,
    },
  ],
};

describe("painel operacional", () => {
  it("prioriza ações e pendências com dados disponíveis", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(new Response(JSON.stringify(summary), { status: 200 })),
      ),
    );
    render(<AdminPage />);
    expect(
      await screen.findByRole("heading", {
        name: "Seu próximo passo está à vista.",
      }),
    ).toBeTruthy();
    expect(screen.getByText("Pastas em preparação")).toBeTruthy();
    expect(screen.getByText("Galerias públicas")).toBeTruthy();
    expect(screen.getByText("Armazenamento de fotos")).toBeTruthy();
    expect(screen.getByText("512 MB")).toBeTruthy();
    expect(screen.getByText("5 fotos")).toBeTruthy();
    expect(screen.getByText("Ritual de publicação")).toBeTruthy();
    expect(screen.getByText(/Vincule clientes e publique/)).toBeTruthy();
    expect(screen.queryByText(/responsável/i)).toBeNull();
    expect(screen.getByText("Festa da escola")).toBeTruthy();
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
      vi.stubGlobal(
        "fetch",
        vi.fn(() =>
          Promise.resolve(
            new Response(JSON.stringify({ ...summary, storage }), { status: 200 }),
          ),
        ),
      );
      render(<AdminPage />);
      expect(await screen.findByText(expectedSize)).toBeTruthy();
      expect(screen.getByText(expectedCount)).toBeTruthy();
    },
  );

  it("isola a indisponibilidade do armazenamento das demais métricas", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(
          new Response(
            JSON.stringify({
              ...summary,
              storage: { photo_count: 5, bytes: null, available: false },
            }),
            { status: 200 },
          ),
        ),
      ),
    );
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
