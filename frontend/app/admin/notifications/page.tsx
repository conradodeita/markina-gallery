"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { MarkinaButton, PageHeading, StatusBadge, SurfaceCard, SystemState } from "../../ui-kit";

type EventType = "private_created" | "member_joined" | "member_blocked" | "member_unblocked" | "member_unlinked";
type Notification = { id: string; event_type: EventType; admin_status: "unread" | "read"; external_status: string; parent_gallery_id: string | null; derived_gallery_id: string | null; client_id: string | null; parent_name: string | null; derived_name: string | null; client_name: string | null; created_at: string };

const eventLabels: Record<EventType, { title: string; detail: string; tone: "success" | "warning" | "dark" | "neutral" }> = {
  private_created: { title: "Nova galeria privada", detail: "Um novo acervo privado foi criado.", tone: "success" },
  member_joined: { title: "Nova cliente na privada", detail: "Uma cliente passou a compartilhar o acervo.", tone: "success" },
  member_blocked: { title: "Cliente bloqueada", detail: "O acesso operacional desta cliente foi bloqueado.", tone: "dark" },
  member_unblocked: { title: "Cliente desbloqueada", detail: "O acesso operacional desta cliente foi restaurado.", tone: "success" },
  member_unlinked: { title: "Cliente desvinculada", detail: "O vínculo terminou sem apagar cadastro ou histórico.", tone: "warning" },
};

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<Notification[] | null>(null);
  const [adminStatus, setAdminStatus] = useState("");
  const [eventType, setEventType] = useState("");
  const [message, setMessage] = useState("");
  const [busyId, setBusyId] = useState("");

  const load = useCallback(async () => {
    setNotifications(null);
    const search = new URLSearchParams();
    if (adminStatus) search.set("admin_status", adminStatus);
    if (eventType) search.set("event_type", eventType);
    const response = await fetch(`/api/admin/notifications${search.size ? `?${search}` : ""}`, { credentials: "same-origin" });
    if (!response.ok) throw new Error();
    const rows = (await response.json()).notifications as Notification[];
    setNotifications([...new Map(rows.map((item) => [item.id, item])).values()]);
  }, [adminStatus, eventType]);

  useEffect(() => {
    let active = true;
    queueMicrotask(() => {
      if (!active) return;
      load().catch(() => {
        if (!active) return;
        setNotifications([]);
        setMessage("Não foi possível carregar as notificações.");
      });
    });
    return () => { active = false; };
  }, [load]);

  async function markRead(notification: Notification) {
    if (busyId || notification.admin_status === "read") return;
    setBusyId(notification.id);
    const response = await fetch(`/api/admin/notifications/${notification.id}/read`, { method: "POST", credentials: "same-origin" });
    if (response.ok) {
      setNotifications((current) => current?.map((item) => item.id === notification.id ? { ...item, admin_status: "read" } : item) ?? current);
      setMessage("Notificação marcada como lida.");
    } else setMessage("Não foi possível marcar a notificação como lida.");
    setBusyId("");
  }

  return <div className="admin-shell admin-notifications-page">
    <PageHeading eyebrow="Eventos de acesso" title="Notificações" detail="Acompanhe novas galerias privadas e mudanças de membros sem misturar esses eventos com pagamentos ou mensagens." />
    <section className="notification-filters" aria-label="Filtros de notificações"><label>Leitura<select value={adminStatus} onChange={(event) => setAdminStatus(event.target.value)}><option value="">Todas</option><option value="unread">Não lidas</option><option value="read">Lidas</option></select></label><label>Evento<select value={eventType} onChange={(event) => setEventType(event.target.value)}><option value="">Todos</option>{Object.entries(eventLabels).map(([value, label]) => <option value={value} key={value}>{label.title}</option>)}</select></label></section>
    {message ? <p className="form-message" role="status">{message}</p> : null}
    {notifications === null ? <SystemState tone="loading" title="Carregando notificações" detail="Consultando eventos de galerias e clientes." /> : notifications.length ? <section className="notification-cards" aria-label="Notificações encontradas">{notifications.map((notification) => {
      const label = eventLabels[notification.event_type];
      return <SurfaceCard className={notification.admin_status === "unread" ? "notification-card is-unread" : "notification-card"} key={notification.id}><header><div><strong>{label.title}</strong><small>{new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" }).format(new Date(notification.created_at))}</small></div><StatusBadge tone={label.tone}>{notification.admin_status === "unread" ? "Não lida" : "Lida"}</StatusBadge></header><p>{label.detail}</p><dl><div><dt>Galeria pública</dt><dd>{notification.parent_name ?? "Indisponível"}</dd></div>{notification.derived_name ? <div><dt>Galeria privada</dt><dd>{notification.derived_name}</dd></div> : null}{notification.client_name ? <div><dt>Cliente</dt><dd>{notification.client_name}</dd></div> : null}</dl><footer>{notification.derived_gallery_id ? <Link href={`/admin/galleries/${notification.derived_gallery_id}`}>Abrir galeria</Link> : notification.parent_gallery_id ? <Link href={`/admin/galleries/sources/${notification.parent_gallery_id}`}>Abrir galeria</Link> : null}{notification.admin_status === "unread" ? <MarkinaButton type="button" variant="secondary" disabled={Boolean(busyId)} onClick={() => markRead(notification)}>{busyId === notification.id ? "Marcando…" : "Marcar como lida"}</MarkinaButton> : null}</footer></SurfaceCard>;
    })}</section> : <SystemState title="Nenhuma notificação neste filtro" detail="Novas galerias privadas e mudanças de membros aparecerão aqui." />}
  </div>;
}
