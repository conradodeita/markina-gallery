import { BrandLogo } from "../brand-logo";
import Link from "next/link";
import { AdminNavigation } from "./admin-navigation";

export default function AdminLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <div className="admin-frame"><header className="admin-topbar"><Link className="admin-brand" href="/admin"><BrandLogo /><small>Central do fotógrafo</small></Link><AdminNavigation /><Link className="admin-exit" href="/">Sair</Link></header><main className="admin-content">{children}</main></div>;
}
