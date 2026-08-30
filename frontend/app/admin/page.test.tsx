import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("next/link", () => ({ default: ({ children, href, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement>) => <a href={href} {...props}>{children}</a> }));

import AdminPage from "./page";

afterEach(() => vi.unstubAllGlobals());

const summary = {
  environment: "development",
  version: "test",
  counts: { clients: 2, parent_galleries: 1, derived_galleries: 2, imports: { processing: 1 }, folders_preparing: 1, folders_released: 3 },
  recent_galleries: [{ id: "gallery-1", name: "Festa da escola", access_enabled: true, selection_expires_at: null }],
};

describe("painel operacional", () => {
  it("prioriza ações e pendências com dados disponíveis", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(new Response(JSON.stringify(summary), { status: 200 }))));
    render(<AdminPage />);
    expect(await screen.findByRole("heading", { name: "Seu próximo passo está à vista." })).toBeTruthy();
    expect(screen.getByText("Pastas em preparação")).toBeTruthy();
    expect(screen.getByText("Ritual de publicação")).toBeTruthy();
    expect(screen.getByText("Festa da escola")).toBeTruthy();
  });

  it("explica falha sem parecer um painel vazio", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(new Response(null, { status: 503 }))));
    render(<AdminPage />);
    await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("Acesso administrativo indisponível"));
  });
});
