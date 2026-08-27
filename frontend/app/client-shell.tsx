import Link from "next/link";

export function ClientShell({ children }: Readonly<{ children: React.ReactNode }>) {
  return <div className="client-frame"><header className="client-topbar"><Link href="/library" className="client-brand"><span>MARKINA</span><strong>Suas fotos</strong></Link><Link className="client-library-link" href="/library">Biblioteca</Link></header><main className="client-content">{children}</main></div>;
}
