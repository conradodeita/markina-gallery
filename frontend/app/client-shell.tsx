import { BrandLogo } from "./brand-logo";
import Link from "next/link";

export function ClientShell({ children }: Readonly<{ children: React.ReactNode }>) {
  return <div className="client-frame"><header className="client-topbar"><Link href="/library" prefetch className="client-brand"><BrandLogo /></Link><Link className="client-library-link" href="/library" prefetch>Minha biblioteca</Link></header><main className="client-content">{children}</main></div>;
}
