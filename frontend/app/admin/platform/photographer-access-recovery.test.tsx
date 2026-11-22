import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { PhotographerAccessRecovery } from "./photographer-access-recovery";

afterEach(() => vi.restoreAllMocks());
const base = "/api/admin/platform/console/tenants/tenant-A/access-recovery";
const target = { available: true, version: "a".repeat(64), email_masked: "p•••@example.test", totp_enabled: true, requests: [] };
const pending = { request_id: "request-A", state: "email_verified", created_at: "2026-11-10T12:00:00Z", expires_at: "2026-11-10T12:15:00Z", reset_totp: false, reason_code: "lost_email" };

it("consulta sob demanda e inicia atendimento com declaração e revogação explícitas", async () => {
  const fetchMock = vi.fn((_path: string, init?: RequestInit) => Promise.resolve(new Response(JSON.stringify(init?.method ? {} : target))));
  vi.stubGlobal("fetch", fetchMock);
  render(<PhotographerAccessRecovery tenantId="tenant-A" />);
  expect(fetchMock).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Consultar atendimentos de recuperação" }));
  await screen.findByText("Contato atual: p•••@example.test");
  fireEvent.change(screen.getByLabelText("Novo e-mail do fotógrafo"), { target: { value: "new@example.test" } });
  fireEvent.click(screen.getByLabelText(/Confirmei fora do sistema/));
  fireEvent.click(screen.getByLabelText(/também perdeu o autenticador/));
  fireEvent.click(screen.getByRole("button", { name: "Solicitar link para o novo e-mail" }));
  await screen.findByText(/Atendimento registrado/);
  const post = fetchMock.mock.calls.find(([, init]) => init?.method === "POST")!;
  expect(post[0]).toBe(base);
  expect(JSON.parse(String(post[1]!.body))).toEqual(expect.objectContaining({ expected_version: target.version,
    new_email: "new@example.test", identity_confirmed: true, reason_code: "lost_email", reset_totp: true }));
});

it("somente após confirmação do e-mail oferece conclusão e apaga os campos secretos", async () => {
  const fetchMock = vi.fn((_path: string, init?: RequestInit) => Promise.resolve(new Response(JSON.stringify(init?.method ? {} : { ...target, requests: [pending] }))));
  vi.stubGlobal("fetch", fetchMock);
  render(<PhotographerAccessRecovery tenantId="tenant-A" />);
  fireEvent.click(screen.getByRole("button", { name: "Consultar atendimentos de recuperação" }));
  fireEvent.change(await screen.findByLabelText("Sua senha de proprietário"), { target: { value: "synthetic-owner-password" } });
  fireEvent.change(screen.getByLabelText("Seu código do autenticador"), { target: { value: "123456" } });
  fireEvent.click(screen.getByRole("button", { name: "Concluir recuperação de acesso" }));
  await screen.findByText(/Credenciais atualizadas/);
  expect(fetchMock).toHaveBeenCalledWith(`${base}/request-A/commit`, expect.objectContaining({
    method: "POST", body: JSON.stringify({ current_password: "synthetic-owner-password", totp_code: "123456" }),
  }));
  expect((screen.getByLabelText("Sua senha de proprietário") as HTMLInputElement).value).toBe("");
  expect(screen.getByText(/Não reabre uma conta encerrada nem retira suspensão/)).toBeTruthy();
});

it("remove o alvo e os controles ao perder autorização na conclusão", async () => {
  vi.stubGlobal("fetch", vi.fn((_path: string, init?: RequestInit) => Promise.resolve(init?.method
    ? new Response(null, { status: 403 }) : new Response(JSON.stringify({ ...target, requests: [pending] })))));
  render(<PhotographerAccessRecovery tenantId="tenant-A" />);
  fireEvent.click(screen.getByRole("button", { name: "Consultar atendimentos de recuperação" }));
  await screen.findByLabelText("Sua senha de proprietário");
  fireEvent.submit(screen.getByLabelText("Sua senha de proprietário").closest("form")!);
  await waitFor(() => expect(screen.queryByLabelText("Sua senha de proprietário")).toBeNull());
  expect(screen.queryByText("Contato atual: p•••@example.test")).toBeNull();
});
