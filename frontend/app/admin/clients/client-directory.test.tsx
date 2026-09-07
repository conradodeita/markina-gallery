import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ClientDirectory } from "./client-directory";

function response(payload: unknown, status = 200) {
  return Promise.resolve(
    new Response(status === 204 ? null : JSON.stringify(payload), {
      status,
      headers: { "content-type": "application/json" },
    }),
  );
}

const emptyPage = { clients: [], page: { has_more: false, next_cursor: null } };

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("diretório global de clientes", () => {
  it("expõe estados de carregamento e erro acionável", async () => {
    vi.stubGlobal("fetch", vi.fn(() => response({ detail: "Sessão administrativa expirada" }, 403)));
    render(<ClientDirectory />);
    expect(screen.getByText("Carregando clientes")).toBeTruthy();
    expect(await screen.findByRole("alert")).toHaveProperty(
      "textContent",
      expect.stringContaining("Sessão administrativa expirada"),
    );
  });

  it("funciona sem galerias e permite cadastrar a primeira cliente", async () => {
    let created = false;
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path === "/api/admin/clients" && init?.method === "POST") {
        created = true;
        return response({ id: "client-1" }, 201);
      }
      if (String(path).startsWith("/api/admin/clients?")) {
        return response(
          created
            ? {
                clients: [
                  {
                    id: "client-1",
                    name: "Ana Cliente",
                    phone: "+55 11 99999-9999",
                    aggregates: { public_galleries: 0, private_galleries: 0, orders: 0 },
                    deletion_eligible: true,
                  },
                ],
                page: { has_more: false, next_cursor: null },
              }
            : emptyPage,
        );
      }
      return response({}, 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<ClientDirectory />);

    expect(await screen.findByText("Ainda não há clientes")).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Nome completo"), {
      target: { value: "Ana Cliente" },
    });
    fireEvent.change(screen.getByLabelText("Número do WhatsApp"), {
      target: { value: "+55 11 99999-9999" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Cadastrar cliente" }));

    expect(await screen.findByText("Cliente cadastrada no diretório global.")).toBeTruthy();
    expect(await screen.findByText("Ana Cliente")).toBeTruthy();
  });

  it("mantém vinculadas visíveis, pagina e busca pelo contrato administrativo", async () => {
    const fetchMock = vi.fn((path: string) => {
      const url = String(path);
      if (url.includes("cursor=next-page")) {
        return response({
          clients: [
            {
              id: "client-2",
              name: "Bia Cliente",
              phone: "+5511888888888",
              aggregates: { public_galleries: 0, private_galleries: 0, orders: 0 },
              deletion_eligible: true,
            },
          ],
          page: { has_more: false, next_cursor: null },
        });
      }
      return response({
        clients: [
          {
            id: "client-1",
            name: "Ana Vinculada",
            phone: "+5511999999999",
            aggregates: { public_galleries: 2, private_galleries: 1, orders: 3 },
            deletion_eligible: false,
          },
        ],
        page: { has_more: true, next_cursor: "next-page" },
      });
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<ClientDirectory />);

    const card = (await screen.findByText("Ana Vinculada")).closest("article")!;
    expect(within(card).getByText("Já vinculada")).toBeTruthy();
    expect(within(card).getByText("3")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Carregar mais" }));
    expect(await screen.findByText("Bia Cliente")).toBeTruthy();

    fireEvent.change(screen.getByLabelText("Buscar por nome ou WhatsApp"), {
      target: { value: "Ana" },
    });
    await waitFor(() =>
      expect(
        fetchMock.mock.calls.some(([path]) => String(path).includes("query=Ana")),
      ).toBe(true),
    );
  });

  it("confirma uma vez, envia idempotência e remove imediatamente da lista", async () => {
    const person = {
      id: "client-1",
      name: "Cliente Operacional",
      phone: "+5511999999999",
      aggregates: { public_galleries: 1, private_galleries: 1, orders: 0 },
      deletion_eligible: true,
    };
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (String(path).endsWith("/deletion-inventory")) {
        return response({
          client_id: person.id,
          operational_removable: {
            client: 1,
            public_gallery_registrations: 1,
            private_galleries_exclusive: 1,
          },
          commercial_protected: { orders: 0 },
          can_delete: true,
        });
      }
      if (path === `/api/admin/clients/${person.id}` && init?.method === "DELETE") {
        return response({
          receipt_id: "receipt-1",
          client_id: person.id,
          status: "completed",
          counts: { clients: 1 },
          completed_at: "2026-09-07T12:00:00+00:00",
        });
      }
      return response({ clients: [person], page: { has_more: false, next_cursor: null } });
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<ClientDirectory />);

    fireEvent.click(await screen.findByRole("button", { name: "Editar" }));
    fireEvent.click(screen.getByRole("button", { name: "Verificar exclusão" }));
    expect(await screen.findByText("Consequências desta exclusão")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Excluir cadastro definitivamente" }));

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        `/api/admin/clients/${person.id}`,
        expect.objectContaining({
          method: "DELETE",
          headers: expect.objectContaining({ "Idempotency-Key": expect.any(String) }),
        }),
      ),
    );
    expect(screen.queryByText("Cliente Operacional")).toBeNull();
    expect(screen.getByText(/Cadastro e estado operacional excluídos/)).toBeTruthy();
  });

  it("explica o bloqueio comercial sem oferecer exclusão inoperante", async () => {
    const person = {
      id: "client-1",
      name: "Cliente com compra",
      phone: "+5511999999999",
      aggregates: { public_galleries: 1, private_galleries: 1, orders: 1 },
      deletion_eligible: false,
    };
    const fetchMock = vi.fn((path: string) =>
      String(path).endsWith("/deletion-inventory")
        ? response({
            client_id: person.id,
            operational_removable: { client: 1 },
            commercial_protected: { orders: 1, payment_communications: 1 },
            can_delete: false,
          })
        : response({ clients: [person], page: { has_more: false, next_cursor: null } }),
    );
    vi.stubGlobal("fetch", fetchMock);
    render(<ClientDirectory />);

    fireEvent.click(await screen.findByRole("button", { name: "Editar" }));
    fireEvent.click(screen.getByRole("button", { name: "Verificar exclusão" }));
    expect(await screen.findByText("Exclusão bloqueada pelo histórico comercial")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Excluir cadastro definitivamente" })).toBeNull();
    expect(screen.getByText(/Edite o telefone ou administre os vínculos/)).toBeTruthy();
    expect(screen.getByRole("link", { name: "Administrar vínculos nas galerias" })).toHaveProperty(
      "href",
      expect.stringContaining("/admin/galleries"),
    );
  });
});
