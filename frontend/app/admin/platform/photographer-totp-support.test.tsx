import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { PhotographerTotpSupport } from "./photographer-totp-support";

afterEach(() => vi.restoreAllMocks());

const account = { available: true, admin_id: "synthetic-photographer", email_masked: "p•••@example.test", totp_enabled: true, version: "a".repeat(64) };

async function fillSupport() {
  fireEvent.click(screen.getByRole("button", { name: "Consultar recuperação de acesso" }));
  await screen.findByText("Conta: p•••@example.test");
  fireEvent.change(screen.getByLabelText("Motivo do atendimento"), { target: { value: "lost_device" } });
  fireEvent.change(screen.getByLabelText("Sua senha para este atendimento"), { target: { value: "synthetic-owner-password" } });
  fireEvent.change(screen.getByLabelText("Seu código do autenticador para este atendimento"), { target: { value: "123456" } });
}

it("consulta só por ação explícita e envia alvo, motivo e versão na confirmação", async () => {
  let revoked = false;
  const fetchMock = vi.fn((input: string, init?: RequestInit) => {
    if (init?.method === "POST") { revoked = true; return Promise.resolve(new Response(JSON.stringify({ completed: true, replayed: false }))); }
    return Promise.resolve(new Response(JSON.stringify({ ...account, totp_enabled: !revoked, version: revoked ? null : account.version })));
  });
  vi.stubGlobal("fetch", fetchMock);
  render(<PhotographerTotpSupport tenantId="tenant-A" />);
  expect(fetchMock).not.toHaveBeenCalled();
  await fillSupport();
  fireEvent.click(screen.getByRole("button", { name: "Revogar autenticador do fotógrafo" }));
  await screen.findByText("O autenticador está desativado. O acesso continua sujeito ao estado da conta.");
  const post = fetchMock.mock.calls.find(([, init]) => init?.method === "POST")!;
  expect(post[0]).toBe("/api/admin/platform/console/tenants/tenant-A/photographers/synthetic-photographer/revoke-totp");
  expect(JSON.parse(String(post[1]!.body))).toEqual(expect.objectContaining({
    reason_code: "lost_device", expected_version: account.version, current_password: "synthetic-owner-password", totp_code: "123456",
  }));
  expect(screen.queryByLabelText("Sua senha para este atendimento")).toBeNull();
  expect(screen.getByRole("status").textContent).toContain("aviso ao e-mail enfileirado");
});

it("limpa o alvo exibido quando a confirmação perde autorização", async () => {
  vi.stubGlobal("fetch", vi.fn((_input: string, init?: RequestInit) => Promise.resolve(
    init?.method === "POST" ? new Response(null, { status: 403 }) : new Response(JSON.stringify(account)),
  )));
  render(<PhotographerTotpSupport tenantId="tenant-A" />);
  await fillSupport();
  fireEvent.click(screen.getByRole("button", { name: "Revogar autenticador do fotógrafo" }));
  await waitFor(() => expect(screen.queryByText("Conta: p•••@example.test")).toBeNull());
  expect(screen.queryByLabelText("Sua senha para este atendimento")).toBeNull();
});

it("não oferece revogação para conta sem contexto elegível", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ available: false }))));
  render(<PhotographerTotpSupport tenantId="tenant-A" />);
  fireEvent.click(screen.getByRole("button", { name: "Consultar recuperação de acesso" }));
  await screen.findByText("Esta conta não está disponível para recuperação assistida do autenticador.");
  expect(screen.queryByRole("button", { name: "Revogar autenticador do fotógrafo" })).toBeNull();
});
