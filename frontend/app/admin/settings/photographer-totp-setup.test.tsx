import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { PhotographerTotpSetup } from "./photographer-totp-setup";

afterEach(() => { vi.restoreAllMocks(); vi.useRealTimers(); });

const secret = "JBSWY3DPEHPK3PXP";
const codes = Array.from({ length: 10 }, (_, index) => `synthetic-recovery-${index}`);

async function begin() {
  fireEvent.click(screen.getByRole("button", { name: "Configurar autenticador" }));
  fireEvent.change(screen.getByLabelText("Senha para ativar autenticador"), { target: { value: "synthetic-password-only" } });
  await act(async () => fireEvent.submit(screen.getByRole("button", { name: "Preparar autenticador" }).closest("form")!));
}

function mockEnrollment() {
  vi.stubGlobal("fetch", vi.fn((url: string) => Promise.resolve(new Response(JSON.stringify(
    url.endsWith("/confirm") ? { codes } : {
      enrollment_id: "synthetic-attempt", secret, qr_data_url: "data:image/png;base64,c3ludGhldGlj",
      expires_at: new Date(Date.now() + 300_000).toISOString(),
    },
  ), { status: 200 }))));
}

it("mostra a chave só durante configuração e limpa o material após confirmar", async () => {
  mockEnrollment();
  render(<PhotographerTotpSetup enabled={false} />);
  await begin();
  expect(screen.getByText(secret)).toBeTruthy();
  expect(screen.queryByLabelText("Senha para ativar autenticador")).toBeNull();
  expect(screen.getByAltText("QR Code para adicionar o Pick-your-Pic ao autenticador")).toBeTruthy();
  fireEvent.change(screen.getByLabelText("2. Código do aplicativo"), { target: { value: "123456" } });
  await act(async () => fireEvent.submit(screen.getByRole("button", { name: "Ativar autenticador" }).closest("form")!));
  expect(screen.queryByText(secret)).toBeNull();
  expect(screen.getByLabelText("Novos códigos de recuperação").children).toHaveLength(10);
  fireEvent.click(screen.getByRole("button", { name: "Já guardei: limpar códigos da tela" }));
  expect(screen.queryByText(codes[0])).toBeNull();
  expect(screen.queryByRole("button", { name: "Configurar autenticador" })).toBeNull();
  expect(screen.getByText(/Ativo: o código será exigido/)).toBeTruthy();
});

it("remove chave e QR da página quando a tentativa expira", async () => {
  vi.useFakeTimers();
  mockEnrollment();
  render(<PhotographerTotpSetup enabled={false} />);
  await begin();
  expect(screen.getByText(secret)).toBeTruthy();
  act(() => vi.advanceTimersByTime(300_001));
  expect(screen.queryByText(secret)).toBeNull();
  expect(screen.queryByAltText(/QR Code/)).toBeNull();
  expect(screen.getByRole("status").textContent).toContain("expirou");
});

it("não oferece novo enrollment para um fator já ativo", () => {
  render(<PhotographerTotpSetup enabled />);
  expect(screen.queryByRole("button", { name: "Configurar autenticador" })).toBeNull();
  expect(screen.getByText(/Ativo: o código será exigido/)).toBeTruthy();
});
