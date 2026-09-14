import { BrandLogo } from "../brand-logo";
import Link from "next/link";
import { AdminNavigation } from "./admin-navigation";
import { LogoutButton, PushControl } from "../push-control";
import styles from "../push-control.module.css";

export default function AdminLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <div className="admin-frame"><header className={`admin-topbar ${styles.adminHeader}`}><Link className="admin-brand" href="/admin"><BrandLogo /><small>Central do fotógrafo</small></Link><AdminNavigation /><div className={styles.actions}><PushControl /><LogoutButton /></div></header><main className="admin-content">{children}</main></div>;
}
