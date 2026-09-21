import { BrandLogo } from "./brand-logo";
import Link from "next/link";
import { LogoutButton, PushControl } from "./push-control";
import styles from "./push-control.module.css";
import { ClientNavigation } from "./client-navigation";

export function ClientShell({ children }: Readonly<{ children: React.ReactNode }>) {
  return <div className="client-frame"><header className="client-topbar" style={{ flexWrap: "wrap", gap: 12 }}><Link href="/library" prefetch className="client-brand"><BrandLogo /></Link><div className={styles.actions}><PushControl /><LogoutButton /></div></header><ClientNavigation /><main className="client-content">{children}</main></div>;
}
