import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import NotificationsPage, { NotificationSetting } from "./page";

const settings: NotificationSetting[] = ["first_access", "first_selection", "private_photos_ready", "payment_reported", "payment_confirmed", "payment_refused"].map((event_type) => ({
  event_type, label: event_type, recipient: event_type === "private_photos_ready" || ["payment_confirmed", "payment_refused"].includes(event_type) ? "client" : "admin",
  allowed_variables: ["cliente", "galeria"], version: 1, push_enabled: true, whatsapp_enabled: true,
  push_title: "Aviso", push_body: "Olá {{cliente}}", whatsapp_body: "Mensagem {{galeria}}",
}));
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

it("exibe seis eventos, prévias e dois interruptores sem a caixa de entrada antiga", async () => {
  const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ settings })));
  vi.stubGlobal("fetch", fetch);
  render(<NotificationsPage />);
  await screen.findByRole("form", { name: "first_access" });
  expect(screen.getAllByRole("form")).toHaveLength(6);
  expect(screen.getAllByRole("checkbox")).toHaveLength(12);
  expect(screen.getAllByText("Olá Cliente")).toHaveLength(6);
  expect(screen.queryByLabelText("Leitura")).toBeNull();
  expect(screen.queryByText("Marcar como lida")).toBeNull();
  expect(screen.getByText(/As alterações são globais/)).toBeTruthy();
});

it("salva somente o evento escolhido com versão e canais independentes", async () => {
  const fetch = vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({ settings })))
    .mockResolvedValueOnce(new Response(JSON.stringify({ ...settings[0], version: 2, push_enabled: false })));
  vi.stubGlobal("fetch", fetch);
  render(<NotificationsPage />);
  const form = within(await screen.findByRole("form", { name: "first_access" }));
  fireEvent.click(form.getByLabelText("Enviar notificação Push"));
  fireEvent.change(form.getByLabelText(/Mensagem do WhatsApp/), { target: { value: "Novo texto {{cliente}}" } });
  fireEvent.click(form.getByRole("button", { name: "Salvar evento" }));
  expect(await form.findByText("Configuração global salva.")).toBeTruthy();
  expect(fetch).toHaveBeenLastCalledWith("/api/admin/notification-settings/first_access", expect.objectContaining({ method: "PUT", body: JSON.stringify({ version: 1, whatsapp_enabled: true, push_enabled: false, whatsapp_body: "Novo texto {{cliente}}", push_title: "Aviso", push_body: "Olá {{cliente}}" }) }));
});

it("preserva rascunho em erro e explica conflito de versão", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({ settings })))
    .mockResolvedValueOnce(new Response(JSON.stringify({ detail: "A configuração mudou. Atualize a página antes de salvar." }), { status: 422 })));
  render(<NotificationsPage />);
  const form = within(await screen.findByRole("form", { name: "first_access" }));
  fireEvent.change(form.getByLabelText(/Título do push/), { target: { value: "Rascunho" } });
  fireEvent.click(form.getByRole("button", { name: "Salvar evento" }));
  expect(await form.findByRole("alert")).toHaveProperty("textContent", expect.stringContaining("Atualize"));
  expect(form.getByLabelText(/Título do push/)).toHaveProperty("value", "Rascunho");
});

it("permite recuperar falha na carga sem enviar alterações", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValueOnce(new Error()).mockResolvedValueOnce(new Response(JSON.stringify({ settings }))));
  render(<NotificationsPage />);
  fireEvent.click(await screen.findByRole("button", { name: "Tentar novamente" }));
  await screen.findByRole("form", { name: "first_access" });
});
