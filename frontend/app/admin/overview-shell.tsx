"use client";

import Link from "next/link";
import { useState, type ReactNode } from "react";
import { AdminSessionToolbar } from "../admin-session-toolbar";
import { PRODUCT_NAME } from "../product-brand";
import { ThemeControl } from "../theme-control";
import { MarkinaLink } from "../ui-kit";
import { AdminNavigation } from "./admin-navigation";
import { OnboardingGateNotice } from "./onboarding-gate-notice";
import { OverviewIcon } from "./overview-icon";
import styles from "./overview.module.css";
import { TenantAddressNotice } from "./tenant-address-notice";

export function OverviewShell({ children }: { children: ReactNode }) {
  const [navigationOpen, setNavigationOpen] = useState(false);

  return (
    <div className={styles.shell}>
      <a className={styles.skipLink} href="#overview-content">Ir para o conteúdo</a>
      <aside className={styles.sidebar}>
        <div className={styles.sidebarHeading}>
          <Link className={styles.brand} href="/admin">
            <span className={styles.brandMark}><OverviewIcon name="photo_camera" /></span>
            <span><strong>{PRODUCT_NAME}</strong><small>Central do fotógrafo</small></span>
          </Link>
          <button type="button" className={styles.menuButton} aria-label="Menu administrativo" aria-expanded={navigationOpen} aria-controls="overview-navigation" onClick={() => setNavigationOpen(!navigationOpen)}>
            <OverviewIcon name="menu" />
          </button>
        </div>
        <div id="overview-navigation" className={styles.navigation} data-open={navigationOpen}>
          <AdminNavigation withOverviewIcons />
        </div>
        <div className={styles.sidebarFooter}>
          <div className={styles.sidebarAvatar}><OverviewIcon name="person" /></div>
          <div><strong>Fotógrafo</strong><small>Sessão ativa</small></div>
        </div>
      </aside>
      <div className={styles.workspace}>
        <header className={styles.topbar}>
          <Link className={styles.searchLink} href="/admin/galleries#gallery-search">
            <OverviewIcon name="search" />Buscar galerias, eventos e clientes
          </Link>
          <div className={styles.topbarActions}>
            <ThemeControl quickIcons={{ light: <OverviewIcon name="light_mode" />, dark: <OverviewIcon name="dark_mode" /> }} />
            <MarkinaLink href="/admin/galleries/new" className={styles.headerCreate}>
              <OverviewIcon name="add" /> Nova galeria
            </MarkinaLink>
            <details className={styles.account}>
              <summary aria-label="Opções da conta"><OverviewIcon name="person" /></summary>
              <div className={styles.accountContent}>
                <AdminSessionToolbar />
                <ThemeControl />
              </div>
            </details>
          </div>
        </header>
        <OnboardingGateNotice />
        <main id="overview-content" className={styles.content} tabIndex={-1}>
          <TenantAddressNotice />
          {children}
        </main>
      </div>
    </div>
  );
}
