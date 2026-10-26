import { act, cleanup, render, screen } from "@testing-library/react";
import { useEffect } from "react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import CardPayment, { type CardData } from "./card-payment";
import type { MercadoPagoPayment } from "../mercadopago";

let scriptLoads = true;
vi.mock("next/script", () => ({ default: function Script({ onReady }: { onReady(): void }) {
  useEffect(() => { if (scriptLoads) onReady(); }, [onReady]);
  return null;
} }));
type SDK = InstanceType<NonNullable<Window["MercadoPago"]>>;
type Settings = Parameters<ReturnType<SDK["bricks"]>["create"]>[2];
let settings: Settings;
const unmount = vi.fn(async () => undefined);
const create = vi.fn(async (_type: string, _id: string, value: Settings) => {
  settings = value;
  return { unmount };
});
const payment = { id: "11111111-1111-4111-8111-111111111111", public_key: "APP_USR-synthetic",
  total_cents: 1400 } as MercadoPagoPayment;
const data: CardData = { token: "synthetic", payment_method_id: "master", payer: {
  email: "buyer@example.test", identification: { type: "CPF", number: "12345678909" },
} };
async function flush() { await act(async () => { await Promise.resolve(); await Promise.resolve(); }); }
beforeEach(() => {
  vi.useFakeTimers(); vi.clearAllMocks(); scriptLoads = true;
  vi.stubGlobal("MercadoPago", function MercadoPagoMock() { return { bricks: () => ({ create }) }; });
});
afterEach(async () => { cleanup(); await flush(); vi.useRealTimers(); vi.unstubAllGlobals(); });

it("oferece recuperação se o controlador resolver antes de onReady", async () => {
  const submit = vi.fn(); render(<CardPayment payment={payment} onSubmit={submit} />);
  await flush(); expect(create).toHaveBeenCalledTimes(1);
  await act(async () => { vi.advanceTimersByTime(20000); });
  expect(screen.getByRole("alert").textContent).toMatch(/não carregaram/i);
  expect(screen.getByRole("button", { name: "Recarregar campos seguros" })).toBeTruthy();
  expect(submit).not.toHaveBeenCalled();
  await act(async () => { settings.callbacks.onReady(); });
  expect(screen.queryByRole("alert")).toBeNull();
  expect(screen.queryByRole("status")).toBeNull();
});

it("limita espera quando o script não carrega", async () => {
  scriptLoads = false; render(<CardPayment payment={payment} onSubmit={vi.fn()} />);
  await act(async () => { vi.advanceTimersByTime(20000); });
  expect(screen.getByRole("alert")).toBeTruthy(); expect(create).not.toHaveBeenCalled();
});

it("atualiza callback sem desmontar formulário e limpa instância ao sair", async () => {
  const first = vi.fn(async () => undefined), latest = vi.fn(async () => undefined);
  const view = render(<CardPayment payment={payment} onSubmit={first} />); await flush();
  await act(async () => { settings.callbacks.onReady(); });
  view.rerender(<CardPayment payment={payment} onSubmit={latest} />); await flush();
  expect(create).toHaveBeenCalledTimes(1);
  await act(async () => { await settings.callbacks.onSubmit(data); });
  expect(first).not.toHaveBeenCalled(); expect(latest).toHaveBeenCalledWith(data);
  view.unmount(); await flush(); expect(unmount).toHaveBeenCalledTimes(1);
});

it("reinicia prontidão ao trocar a tentativa e ignora onReady da anterior", async () => {
  const submit = vi.fn(async () => undefined);
  const view = render(<CardPayment payment={payment} onSubmit={submit} />); await flush();
  const previous = settings;
  await act(async () => { previous.callbacks.onReady(); });
  view.rerender(<CardPayment payment={{ ...payment, id: "22222222-2222-4222-8222-222222222222" }} onSubmit={submit} />);
  await flush();
  expect(create).toHaveBeenCalledTimes(2); expect(unmount).toHaveBeenCalledTimes(1);
  await act(async () => { previous.callbacks.onReady(); });
  expect(screen.getByRole("status")).toBeTruthy();
  await act(async () => { settings.callbacks.onReady(); });
  expect(screen.queryByRole("status")).toBeNull();
});
