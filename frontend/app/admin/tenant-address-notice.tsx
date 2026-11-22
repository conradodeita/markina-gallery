"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTenantAddress } from "./tenant-address";
import styles from "./tenant-address-notice.module.css";

export function TenantAddressNotice() {
  const pathname = usePathname();
  const { address, phase } = useTenantAddress(pathname !== "/admin/settings", pathname);
  if (pathname === "/admin/settings" || phase === "hidden" || phase === "loading" ||
      (phase === "ready" && address?.choice_complete)) return null;
  return <aside className={styles.notice} aria-label="Link da sua marca">
    <p>{phase === "error" ? "Não foi possível verificar o link da sua marca. Confira em Configurações."
      : "Bem-vindo! Escolha o link da sua marca no Pick-your-Pic. Esse será o endereço na web que seus clientes usarão para acessar seu espaço."}</p>
    <Link className="mk-button mk-button--secondary" href="/admin/settings#tenant-address">
      Escolher link da minha marca
    </Link>
  </aside>;
}
