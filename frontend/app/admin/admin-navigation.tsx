"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navigation = [
  { href: "/admin", label: "Visão geral" },
  { href: "/admin/galleries", label: "Galerias" },
  { href: "/admin/clients", label: "Clientes" },
  { href: "/admin/payments", label: "Vendas e pagamentos" },
  { href: "/admin/notifications", label: "Notificações" },
  { href: "/admin/pricing", label: "Tabelas de preço" },
  { href: "/admin/statistics", label: "Estatísticas" },
  { href: "/admin/settings", label: "Configurações" },
];

export function AdminNavigation() {
  const pathname = usePathname();
  return <nav aria-label="Navegação administrativa">{navigation.map(({ href, label }) => {
    const current = href === "/admin" ? pathname === href : pathname.startsWith(href);
    return <Link aria-current={current ? "page" : undefined} href={href} key={href}>{label}</Link>;
  })}</nav>;
}
