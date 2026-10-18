import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { PrivateFolderClientOverview } from "./private-folder-client-overview";

vi.mock("next/link", () => ({ default: ({ children, href, ...props }: { children: React.ReactNode; href: string }) => <a href={href} {...props}>{children}</a> }));

afterEach(() => vi.unstubAllGlobals());

const gallery = {
  id: "private-1", name: "Ensaio Ana",
  owner: { id: "ana", name: "Ana Principal" },
  active_members: [{ id: "ana", name: "Ana Principal" }, { id: "bruna", name: "Bruna Compartilhada" }],
  folders: [{ id: "folder-private", name: "Retratos exclusivos", status: "released", photo_count: 6 }],
};

it("identifica responsável, membros ativos e pastas compartilhadas com destino privado", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ galleries: [gallery] }))));
  render(<PrivateFolderClientOverview sourceId="source-1" />);
  const region = screen.getByRole("region", { name: "Pastas de galerias privadas" });
  expect(await within(region).findByText("Responsável principal: Ana Principal")).toBeTruthy();
  expect(within(region).getByText("Acesso compartilhado — membros ativos:")).toBeTruthy();
  expect(within(region).getByText("Bruna Compartilhada")).toBeTruthy();
  expect(within(region).getByText("Retratos exclusivos")).toBeTruthy();
  expect(within(region).getByText("Disponível")).toBeTruthy();
  expect(within(region).getByRole("link", { name: "Abrir galeria privada de Ana Principal" }).getAttribute("href")).toBe("/admin/galleries/private-1");
  expect(within(region).queryByRole("button", { name: "Carregar fotos" })).toBeNull();
});

it("distingue carregamento de uma origem sem pastas privadas", async () => {
  let finish!: (response: Response) => void;
  vi.stubGlobal("fetch", vi.fn(() => new Promise<Response>((resolve) => { finish = resolve; })));
  render(<PrivateFolderClientOverview sourceId="source-1" />);
  expect(screen.getByText("Carregando pastas privadas")).toBeTruthy();
  await act(async () => finish(new Response(JSON.stringify({ galleries: [] }))));
  expect(await screen.findByText("Nenhuma pasta privada nesta galeria")).toBeTruthy();
  expect(screen.queryByText("Carregando pastas privadas")).toBeNull();
});

it("preserva a responsável sem inferir membros ativos", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ galleries: [{ ...gallery, active_members: [] }] }))));
  render(<PrivateFolderClientOverview sourceId="source-1" />);
  expect(await screen.findByText("Responsável principal: Ana Principal")).toBeTruthy();
  expect(screen.getByText("Nenhum membro ativo cadastrado.")).toBeTruthy();
  expect(screen.queryByText("Bruna Compartilhada")).toBeNull();
});

it("mostra falha sem anunciar lista vazia e permite consultar novamente", async () => {
  const fetchMock = vi.fn()
    .mockResolvedValueOnce(new Response(JSON.stringify({ detail: "Indisponível" }), { status: 503 }))
    .mockResolvedValueOnce(new Response(JSON.stringify({ galleries: [gallery] })));
  vi.stubGlobal("fetch", fetchMock);
  render(<PrivateFolderClientOverview sourceId="source-1" />);
  expect(await screen.findByRole("alert")).toBeTruthy();
  expect(screen.queryByText("Nenhuma pasta privada nesta galeria")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
  expect(await screen.findByText("Responsável principal: Ana Principal")).toBeTruthy();
  expect(screen.queryByRole("alert")).toBeNull();
});
