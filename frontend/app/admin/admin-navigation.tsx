"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { MonitorLink } from "./system-monitor/monitor-link";
import { ConsoleLink } from "./platform/console-link";
import { OverviewIcon } from "./overview-icon";

const navigation = [
  { href: "/admin", label: "Visão geral", icon: "grid_view" },
  { href: "/admin/galleries", label: "Galerias", icon: "photo_library" },
  { href: "/admin/clients", label: "Clientes", icon: "group" },
  { href: "/admin/payments", label: "Vendas e pagamentos", icon: "payments" },
  { href: "/admin/notifications", label: "Notificações", icon: "notifications" },
  { href: "/admin/pricing", label: "Tabelas de preço", icon: "sell" },
  { href: "/admin/credits", label: "Créditos", icon: "account_balance_wallet" },
  { href: "/admin/settings", label: "Configurações", icon: "settings" },
];

export function AdminNavigation({ withOverviewIcons = false }: { withOverviewIcons?: boolean }) {
  const pathname = usePathname();
  return <nav aria-label="Navegação administrativa">{navigation.map(({ href, label, icon }) => {
    const current = href === "/admin" ? pathname === href : pathname.startsWith(href);
    return <Link aria-current={current ? "page" : undefined} href={href} key={href}>{withOverviewIcons && <OverviewIcon name={icon} />}{label}</Link>;
  })}<ConsoleLink /><MonitorLink /></nav>;
}
