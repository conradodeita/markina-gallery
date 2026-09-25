import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import NotificationsPage, { NotificationSetting } from "./page";

const settings: NotificationSetting[] = ["first_access", "first_selection", "private_photos_ready", "payment_reported", "payment_confirmed", "payment_refused", "order_delivery_ready"].map((event_type) => ({
  event_type, label: event_type, recipient: event_type === "private_photos_ready" || ["payment_confirmed", "payment_refused", "order_delivery_ready"].includes(event_type) ? "client" : "admin",
  allowed_variables: ["cliente", "galeria"], version: 1, push_enabled: true, whatsapp_enabled: true,
  push_title: "Aviso", push_body: "Olá {{cliente}}", whatsapp_body: "Mensagem {{galeria}}",
}));
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

async function openCard(name: string) {
  const heading = await screen.findByRole("heading", { name });
  const summary = heading.closest("summary")!;
  fireEvent.click(summary);
  return summary;
}

it("exibe sete eventos, prévias e dois interruptores sem a caixa de entrada antiga", async () => {
  const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ settings })));
  vi.stubGlobal("fetch", fetch);
  render(<NotificationsPage />);
  for (const item of settings) await openCard(item.label);
  expect(screen.getAllByRole("form")).toHaveLength(7);
  expect(screen.getAllByRole("checkbox")).toHaveLength(14);
  expect(screen.getAllByText("Olá Cliente")).toHaveLength(7);
  expect(screen.queryByLabelText("Leitura")).toBeNull();
  expect(screen.queryByText("Marcar como lida")).toBeNull();
  expect(screen.getByText(/As alterações são globais/)).toBeTruthy();
  expect(fetch).toHaveBeenCalledTimes(1);
});

it("inicia recolhido e preserva rascunhos e abertura independente sem chamadas adicionais", async () => {
  const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ settings })));
  vi.stubGlobal("fetch", fetch);
  const { container } = render(<NotificationsPage />);
  await screen.findByRole("heading", { name: "first_access" });
  expect(container.querySelectorAll("details")).toHaveLength(7);
  expect(container.querySelectorAll("details[open]")).toHaveLength(0);
  // A visibilidade nativa de details é validada no QA de navegador; jsdom não faz layout.
  const summary = await openCard("first_access");
  const form = within(screen.getByRole("form", { name: "first_access" }));
  fireEvent.change(form.getByLabelText(/Título do push/), { target: { value: "Rascunho" } });
  fireEvent.click(form.getByLabelText("Enviar notificação Push"));
  const other = await openCard("private_photos_ready");
  fireEvent.click(summary);
  expect(summary.parentElement).toHaveProperty("open", false);
  expect(other.parentElement).toHaveProperty("open", true);
  fireEvent.click(summary);
  expect(form.getByLabelText(/Título do push/)).toHaveProperty("value", "Rascunho");
  expect(form.getByLabelText("Enviar notificação Push")).toHaveProperty("checked", false);
  expect(fetch).toHaveBeenCalledTimes(1);
});

it("salva somente o evento escolhido com versão e canais independentes", async () => {
  const fetch = vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({ settings })))
    .mockResolvedValueOnce(new Response(JSON.stringify({ ...settings[0], version: 2, push_enabled: false })));
  vi.stubGlobal("fetch", fetch);
  render(<NotificationsPage />);
  await openCard("first_access");
  const form = within(await screen.findByRole("form", { name: "first_access" }));
  fireEvent.click(form.getByLabelText("Enviar notificação Push"));
  fireEvent.change(form.getByLabelText(/Mensagem do WhatsApp/), { target: { value: "Novo texto {{cliente}}" } });
  fireEvent.click(form.getByRole("button", { name: "Salvar evento" }));
  expect(await form.findByText("Configuração global salva.")).toBeTruthy();
  expect(fetch).toHaveBeenCalledTimes(2);
  expect(fetch).toHaveBeenLastCalledWith("/api/admin/notification-settings/first_access", expect.objectContaining({ method: "PUT", body: JSON.stringify({ version: 1, whatsapp_enabled: true, push_enabled: false, whatsapp_body: "Novo texto {{cliente}}", push_title: "Aviso", push_body: "Olá {{cliente}}" }) }));
});

it("preserva rascunho em erro e explica conflito de versão", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({ settings })))
    .mockResolvedValueOnce(new Response(JSON.stringify({ detail: "A configuração mudou. Atualize a página antes de salvar." }), { status: 422 })));
  render(<NotificationsPage />);
  const summary = await openCard("first_access");
  const form = within(await screen.findByRole("form", { name: "first_access" }));
  fireEvent.change(form.getByLabelText(/Título do push/), { target: { value: "Rascunho" } });
  fireEvent.click(form.getByRole("button", { name: "Salvar evento" }));
  expect(await form.findByRole("alert")).toHaveProperty("textContent", expect.stringContaining("Atualize"));
  fireEvent.click(summary);
  fireEvent.click(summary);
  expect(form.getByRole("alert")).toHaveProperty("textContent", expect.stringContaining("Atualize"));
  expect(form.getByLabelText(/Título do push/)).toHaveProperty("value", "Rascunho");
});

it("permite recuperar falha na carga sem enviar alterações", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValueOnce(new Error()).mockResolvedValueOnce(new Response(JSON.stringify({ settings }))));
  render(<NotificationsPage />);
  fireEvent.click(await screen.findByRole("button", { name: "Tentar novamente" }));
  expect((await screen.findByRole("heading", { name: "first_access" })).closest("details")).toHaveProperty("open", false);
});
