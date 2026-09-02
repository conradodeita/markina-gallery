import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/link", () => ({ default: ({ children, href, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement>) => <a href={href} {...props}>{children}</a> }));

import NotificationsPage from "./page";

const notification = {
  id: "notice-1",
  event_type: "member_joined",
  admin_status: "unread",
  external_status: "skipped",
  parent_gallery_id: "parent-1",
  derived_gallery_id: "private-1",
  client_id: "client-1",
  parent_name: "Formatura 2026",
  derived_name: "Família Silva",
  client_name: "Maria Silva",
  phone_e164: "+5511999999999",
  total_cents: 39000,
  created_at: "2026-09-01T12:00:00Z",
};

describe("notificações administrativas", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("deduplica eventos, omite dados comerciais e permite marcar como lida", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify({ notifications: [notification, notification] }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ id: notification.id, status: "read" }), { status: 200 }));

    render(<NotificationsPage />);

    expect(await screen.findByText("Maria Silva")).toBeTruthy();
    expect(screen.getAllByText("Nova cliente na privada", { selector: "strong" })).toHaveLength(1);
    expect(screen.queryByText("+5511999999999")).toBeNull();
    expect(screen.queryByText("R$ 390,00")).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Marcar como lida" }));
    await waitFor(() => expect(screen.getByText("Notificação marcada como lida.")).toBeTruthy());
    expect(fetchMock).toHaveBeenLastCalledWith("/api/admin/notifications/notice-1/read", { method: "POST", credentials: "same-origin" });
    expect(screen.queryByRole("button", { name: "Marcar como lida" })).toBeNull();
  });

  it("aplica filtros básicos na consulta", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ notifications: [] }), { status: 200 }));
    render(<NotificationsPage />);
    await screen.findByText("Nenhuma notificação neste filtro");

    fireEvent.change(screen.getByLabelText("Leitura"), { target: { value: "unread" } });
    fireEvent.change(screen.getByLabelText("Evento"), { target: { value: "member_blocked" } });

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/admin/notifications?admin_status=unread&event_type=member_blocked",
      { credentials: "same-origin" },
    ));
  });
});
