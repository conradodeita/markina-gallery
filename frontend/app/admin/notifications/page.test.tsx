import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import NotificationsPage, { NotificationSetting } from "./page";

const settings: NotificationSetting[] = ["first_access", "first_selection", "private_photos_ready", "payment_reported", "payment_confirmed", "payment_refused", "order_delivery_ready"].map((event_type) => ({
  event_type, label: event_type, recipient: event_type === "private_photos_ready" || ["payment_confirmed", "payment_refused", "order_delivery_ready"].includes(event_type) ? "client" : "admin",
  allowed_variables: ["cliente", "galeria"], whatsapp_variables: ["cliente", "galeria", ...(event_type === "order_delivery_ready" ? ["link_compras"] : []), ...(event_type === "private_photos_ready" ? ["link_galeria"] : [])], version: 1, push_enabled: true, whatsapp_enabled: true,
  push_title: "Aviso", push_body: "Olá {{cliente}}", whatsapp_body: event_type === "private_photos_ready"
    ? "Essa mensagem é automática! Novas fotos disponíveis na sua galeria. Acesso no link: {{link_galeria}}."
    : "Mensagem {{galeria}}",
}));
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

async function openCard(name: string) {
  const heading = await screen.findByRole("heading", { name });
  const summary = heading.closest("summary")!;
  fireEvent.click(summary);
  return summary;
}

it("exibe sete eventos, prévias e dois interruptores sem a caixa de entrada antiga", async () => {
  const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ settings, whatsapp_editable: true })));
  vi.stubGlobal("fetch", fetch);
  render(<NotificationsPage />);
  for (const item of settings) await openCard(item.label);
  expect(screen.getAllByRole("form")).toHaveLength(7);
  expect(screen.getAllByRole("checkbox")).toHaveLength(14);
  expect(screen.getAllByText("Olá Cliente")).toHaveLength(7);
  expect(screen.queryByLabelText("Leitura")).toBeNull();
  expect(screen.queryByText("Marcar como lida")).toBeNull();
  expect(screen.getByText(/As alterações afetam os clientes da sua conta/)).toBeTruthy();
  const delivery = settings.find((item) => item.event_type === "order_delivery_ready")!;
  expect(delivery.allowed_variables).not.toContain("link_compras");
  expect(delivery.whatsapp_variables).toContain("link_compras");
  expect(screen.getByText("{{link_compras}}")).toBeTruthy();
  const privatePhotos = settings.find((item) => item.event_type === "private_photos_ready")!;
  expect(privatePhotos.allowed_variables).not.toContain("link_galeria");
  expect(privatePhotos.whatsapp_variables).toContain("link_galeria");
  expect(screen.getByText("{{link_galeria}}")).toBeTruthy();
  expect(screen.getByText(/https:\/\/fotografo\.exemplo\/public-galleries\/00000000-0000-4000-8000-000000000000/)).toBeTruthy();
  expect(fetch).toHaveBeenCalledTimes(1);
});

it("mostra prévias de pagamento para compra agrupada e pedido individual", async () => {
  const configured = settings.map((item) => item.event_type === "payment_confirmed"
    ? { ...item, whatsapp_body: "Pagamento {{contexto_pagamento}} confirmado." }
    : item);
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ settings: configured, whatsapp_editable: true }))));
  render(<NotificationsPage />);
  await openCard("payment_confirmed");
  expect(screen.getByText("Pagamento da compra 1234abcd confirmado.")).toBeTruthy();
  expect(screen.getByText("Pagamento do pedido 1234abcd da galeria Formatura confirmado.")).toBeTruthy();
});

it("inicia recolhido e preserva rascunhos e abertura independente sem chamadas adicionais", async () => {
  const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ settings, whatsapp_editable: true })));
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

it("filtra por destinatário sem perder um rascunho nem refazer a consulta", async () => {
  const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ settings, whatsapp_editable: true })));
  vi.stubGlobal("fetch", fetch);
  render(<NotificationsPage />);
  await openCard("first_access");
  const event = within(screen.getByRole("form", { name: "first_access" }));
  fireEvent.change(event.getByLabelText(/Título do push/), { target: { value: "Rascunho local" } });
  const filters = screen.getByRole("group", { name: "Filtrar notificações por destinatário" });
  fireEvent.click(within(filters).getByRole("button", { name: "Para o cliente" }));
  expect(screen.queryByRole("heading", { name: "first_access" })).toBeNull();
  expect(screen.getByRole("heading", { name: "payment_confirmed" })).toBeTruthy();
  fireEvent.click(within(filters).getByRole("button", { name: "Para o fotógrafo" }));
  expect(event.getByLabelText(/Título do push/)).toHaveProperty("value", "Rascunho local");
  expect(fetch).toHaveBeenCalledTimes(1);
});

it("salva somente o evento escolhido com versão e canais independentes", async () => {
  const fetch = vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({ settings, whatsapp_editable: true })))
    .mockResolvedValueOnce(new Response(JSON.stringify({ ...settings[0], version: 2, push_enabled: false })));
  vi.stubGlobal("fetch", fetch);
  render(<NotificationsPage />);
  await openCard("first_access");
  const form = within(await screen.findByRole("form", { name: "first_access" }));
  fireEvent.click(form.getByLabelText("Enviar notificação Push"));
  fireEvent.change(form.getByLabelText(/Mensagem do WhatsApp/), { target: { value: "Novo texto {{cliente}}" } });
  fireEvent.click(form.getByRole("button", { name: "Salvar evento" }));
  expect(await form.findByText("Configuração da sua conta salva.")).toBeTruthy();
  expect(fetch).toHaveBeenCalledTimes(2);
  expect(fetch).toHaveBeenLastCalledWith("/api/admin/notification-settings/first_access", expect.objectContaining({ method: "PUT", body: JSON.stringify({ version: 1, whatsapp_enabled: true, push_enabled: false, whatsapp_body: "Novo texto {{cliente}}", push_title: "Aviso", push_body: "Olá {{cliente}}" }) }));
});

it("preserva rascunho em erro e explica conflito de versão", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({ settings, whatsapp_editable: true })))
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
  vi.stubGlobal("fetch", vi.fn().mockRejectedValueOnce(new Error()).mockResolvedValueOnce(new Response(JSON.stringify({ settings, whatsapp_editable: true }))));
  render(<NotificationsPage />);
  fireEvent.click(await screen.findByRole("button", { name: "Tentar novamente" }));
  expect((await screen.findByRole("heading", { name: "first_access" })).closest("details")).toHaveProperty("open", false);
});

it("bloqueia WhatsApp sem conexão e permite editar e salvar push", async () => {
  const fetch = vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({ settings, whatsapp_editable: false })))
    .mockResolvedValueOnce(new Response(JSON.stringify({ ...settings[0], version: 2, push_body: "Novo push" })));
  vi.stubGlobal("fetch", fetch);
  render(<NotificationsPage />);
  await openCard("first_access");
  expect(screen.getByRole("link", { name: "Configurar WhatsApp" }).getAttribute("href")).toBe("/admin/settings#whatsapp");
  const form = within(screen.getByRole("form", { name: "first_access" }));
  expect(form.getByLabelText(/Mensagem do WhatsApp/).closest("fieldset")).toHaveProperty("disabled", true);
  expect(form.getByLabelText("Enviar WhatsApp").closest("fieldset")).toHaveProperty("disabled", true);
  expect(form.getByLabelText(/Mensagem do push/)).not.toHaveProperty("disabled", true);
  fireEvent.change(form.getByLabelText(/Mensagem do push/), { target: { value: "Novo push" } });
  fireEvent.click(form.getByRole("button", { name: "Salvar evento" }));
  await form.findByText("Configuração da sua conta salva.");
  const payload = JSON.parse(fetch.mock.calls[1][1].body);
  expect(payload.whatsapp_body).toBe(settings[0].whatsapp_body);
  expect(payload.push_body).toBe("Novo push");
  expect(screen.queryByText(/Evolution API/)).toBeNull();
});

it("falha fechada quando a resposta não traz capacidade WhatsApp", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ settings }))));
  render(<NotificationsPage />);
  await openCard("first_access");
  const form = within(screen.getByRole("form", { name: "first_access" }));
  expect(form.getByLabelText(/Mensagem do WhatsApp/).closest("fieldset")).toHaveProperty("disabled", true);
  expect(form.getByLabelText(/Título do push/)).not.toHaveProperty("disabled", true);
});

it("bloqueia os controles se o canal cair entre a consulta e o salvamento", async () => {
  const fetch = vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({ settings, whatsapp_editable: true })))
    .mockResolvedValueOnce(new Response(
      JSON.stringify({ detail: { code: "whatsapp_channel_required", message: "Conecte seu WhatsApp em Configurações." } }),
      { status: 409 },
    ))
    .mockResolvedValueOnce(new Response(JSON.stringify({ ...settings[0], version: 2, push_body: "Push após queda" })));
  vi.stubGlobal("fetch", fetch);
  render(<NotificationsPage />);
  await openCard("first_access");
  const form = within(screen.getByRole("form", { name: "first_access" }));
  fireEvent.change(form.getByLabelText(/Mensagem do WhatsApp/), { target: { value: "Rascunho" } });
  fireEvent.click(form.getByRole("button", { name: "Salvar evento" }));
  await form.findByRole("alert");
  expect(form.getByLabelText(/Mensagem do WhatsApp/).closest("fieldset")).toHaveProperty("disabled", true);
  expect(form.getByLabelText(/Título do push/)).not.toHaveProperty("disabled", true);
  fireEvent.change(form.getByLabelText(/Mensagem do push/), { target: { value: "Push após queda" } });
  fireEvent.click(form.getByRole("button", { name: "Salvar evento" }));
  await form.findByText("Configuração da sua conta salva.");
  const payload = JSON.parse(fetch.mock.calls[2][1].body);
  expect(payload.whatsapp_body).toBe(settings[0].whatsapp_body);
  expect(payload.push_body).toBe("Push após queda");
});
