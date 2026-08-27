import Link from "next/link";

const navigation = [
  ["Visão geral", "/admin"],
  ["Galerias", "/admin/galleries"],
  ["Clientes e operação", "/admin/operations"],
  ["Vendas", "/admin/purchases"],
  ["Estatísticas", "/admin/statistics"],
];

export default function AdminLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <div className="admin-frame"><header className="admin-topbar"><Link className="admin-brand" href="/admin"><span>MARKINA</span><strong>Gallery</strong></Link><nav aria-label="Navegação administrativa">{navigation.map(([label, href]) => <Link href={href} key={href}>{label}</Link>)}</nav><Link className="admin-exit" href="/">Sair</Link></header><main className="admin-content">{children}</main></div>;
}
