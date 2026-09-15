import { BrandLogo } from "./brand-logo";
import Link from "next/link";
import { LogoutButton, PushControl } from "./push-control";
import styles from "./push-control.module.css";

export function ClientShell({ children }: Readonly<{ children: React.ReactNode }>) {
  return <div className="client-frame"><header className="client-topbar" style={{ flexWrap: "wrap", gap: 12 }}><Link href="/library" prefetch className="client-brand"><BrandLogo /></Link><div className={styles.actions}><Link className="client-library-link" href="/library" prefetch>Minha biblioteca</Link><PushControl /><LogoutButton /></div></header><main className="client-content">{children}</main></div>;
}
