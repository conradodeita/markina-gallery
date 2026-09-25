import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { OrderDeliveryForm, type OrderDelivery } from "./order-delivery";

const album = "https://photos.app.goo.gl/Synthetic";
const initial: OrderDelivery = { album_url: null, version: 0, can_send: true, can_resend: false };
const saved = { ...initial, album_url: album, version: 1, can_resend: true };
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

it("digitar não envia; Enviar persiste e informa agendamento sem alegar entrega", async () => {
  const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ delivery: saved, notification: { channels: ["push"] } })));
  vi.stubGlobal("fetch", fetch);
  const refresh = vi.fn().mockResolvedValue(undefined);
  render(<OrderDeliveryForm orderId="order-1" delivery={initial} onRefresh={refresh} />);
  fireEvent.change(screen.getByLabelText("Link do álbum no Google Photos"), { target: { value: album } });
  expect(fetch).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Enviar" }));
  expect(await screen.findByRole("status")).toHaveProperty("textContent", "Fotos disponíveis em Compras. Aviso agendado.");
  expect(fetch).toHaveBeenCalledWith("/api/admin/orders/order-1/delivery", expect.objectContaining({ method: "PUT", body: JSON.stringify({ album_url: album, version: 0 }) }));
  expect(refresh).toHaveBeenCalledOnce();
});

it("preserva rascunho na falha e rejeita destino que não seja Google Photos", async () => {
  const fetch = vi.fn().mockRejectedValue(new Error("Failed to fetch")); vi.stubGlobal("fetch", fetch);
  render(<OrderDeliveryForm orderId="order-1" delivery={initial} onRefresh={vi.fn()} />);
  const input = screen.getByLabelText("Link do álbum no Google Photos");
  fireEvent.change(input, { target: { value: "https://attacker.invalid/album" } });
  fireEvent.click(screen.getByRole("button", { name: "Enviar" }));
  expect(fetch).not.toHaveBeenCalled();
  fireEvent.change(input, { target: { value: album } });
  fireEvent.click(screen.getByRole("button", { name: "Enviar" }));
  expect(await screen.findByRole("alert")).toHaveProperty("textContent", expect.stringContaining("Tente novamente"));
  expect(input).toHaveProperty("value", album);
});

it("bloqueia envio e reenvio sem pagamento confirmado, permitindo remover", async () => {
  vi.spyOn(window, "confirm").mockReturnValue(true);
  const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ delivery: initial, notification: null })));
  vi.stubGlobal("fetch", fetch);
  render(<OrderDeliveryForm orderId="order-1" delivery={{ ...saved, can_send: false, can_resend: false }} onRefresh={vi.fn()} />);
  expect(screen.getByRole("button", { name: "Enviar" })).toHaveProperty("disabled", true);
  expect(screen.getByRole("button", { name: "Reenviar aviso" })).toHaveProperty("disabled", true);
  expect(screen.getByText("Confirme o pagamento para disponibilizar as fotos.")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Remover link" }));
  expect(await screen.findByRole("status")).toHaveProperty("textContent", expect.stringContaining("Link removido"));
});

it("reenvio reutiliza operação após erro de rede e cria outra só após sucesso", async () => {
  vi.spyOn(window, "confirm").mockReturnValue(true);
  const result = () => new Response(JSON.stringify({ delivery: saved, notification: { channels: ["whatsapp"] } }));
  const fetch = vi.fn().mockRejectedValueOnce(new Error("Failed to fetch")).mockImplementation(() => Promise.resolve(result()));
  vi.stubGlobal("fetch", fetch);
  render(<OrderDeliveryForm orderId="order-1" delivery={saved} onRefresh={vi.fn()} />);
  fireEvent.click(screen.getByRole("button", { name: "Reenviar aviso" }));
  await screen.findByRole("alert");
  fireEvent.click(screen.getByRole("button", { name: "Reenviar aviso" }));
  await screen.findByRole("status");
  expect(fetch.mock.calls[0][1].body).toBe(fetch.mock.calls[1][1].body);
  await waitFor(() => expect(screen.getByRole("button", { name: "Reenviar aviso" })).toHaveProperty("disabled", false));
  fireEvent.click(screen.getByRole("button", { name: "Reenviar aviso" }));
  await waitFor(() => expect(fetch).toHaveBeenCalledTimes(3));
  expect(fetch.mock.calls[1][1].body).not.toBe(fetch.mock.calls[2][1].body);
});

it("impede reenvio de rascunho diferente e confirma remoção", () => {
  const fetch = vi.fn(); vi.stubGlobal("fetch", fetch);
  vi.spyOn(window, "confirm").mockReturnValue(false);
  render(<OrderDeliveryForm orderId="order-1" delivery={saved} onRefresh={vi.fn()} />);
  fireEvent.change(screen.getByLabelText("Link do álbum no Google Photos"), { target: { value: `${album}2` } });
  expect(screen.getByRole("button", { name: "Reenviar aviso" })).toHaveProperty("disabled", true);
  fireEvent.click(screen.getByRole("button", { name: "Remover link" }));
  expect(fetch).not.toHaveBeenCalled();
});

it("duplo clique durante requisição pendente não duplica aviso", async () => {
  vi.spyOn(window, "confirm").mockReturnValue(true);
  let finish!: (value: Response) => void;
  const fetch = vi.fn(() => new Promise<Response>((resolve) => { finish = resolve; }));
  vi.stubGlobal("fetch", fetch);
  render(<OrderDeliveryForm orderId="order-1" delivery={saved} onRefresh={vi.fn()} />);
  const button = screen.getByRole("button", { name: "Reenviar aviso" });
  fireEvent.click(button); fireEvent.click(button);
  expect(fetch).toHaveBeenCalledOnce();
  finish(new Response(JSON.stringify({ delivery: saved, notification: { channels: ["push"] } })));
  await screen.findByRole("status");
});

it("explica quando não há canal disponível e acompanha correção financeira", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ delivery: saved, notification: { channels: [] } }))));
  const { rerender } = render(<OrderDeliveryForm orderId="order-1" delivery={initial} onRefresh={vi.fn()} />);
  fireEvent.change(screen.getByLabelText("Link do álbum no Google Photos"), { target: { value: album } });
  fireEvent.click(screen.getByRole("button", { name: "Enviar" }));
  expect(await screen.findByRole("status")).toHaveProperty("textContent", expect.stringContaining("Nenhum aviso agendado"));
  rerender(<OrderDeliveryForm orderId="order-1" delivery={{ ...saved, version: 2, can_send: false }} onRefresh={vi.fn()} />);
  expect(screen.getByRole("button", { name: "Reenviar aviso" })).toHaveProperty("disabled", true);
  expect(screen.getByLabelText("Link do álbum no Google Photos")).toHaveProperty("value", album);
});
