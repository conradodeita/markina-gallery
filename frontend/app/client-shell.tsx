import Link from "next/link";

export function ClientShell({ children }: Readonly<{ children: React.ReactNode }>) {
  return <div className="client-frame"><header className="client-topbar"><Link href="/library" className="client-brand"><span>MARKINA GALLERY</span><strong>Suas fotos</strong><small>Memórias preparadas para você</small></Link><Link className="client-library-link" href="/library">Minha biblioteca</Link></header><main className="client-content">{children}</main></div>;
}
