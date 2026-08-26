"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

export default function AdminPage() {
  const [authorized, setAuthorized] = useState<boolean | null>(null);
  useEffect(() => { fetch("/api/admin", { credentials: "same-origin" }).then((r) => setAuthorized(r.ok)).catch(() => setAuthorized(false)); }, []);
  if (authorized === null) return <main className="admin-shell">Carregando área administrativa…</main>;
  if (!authorized) return <main className="admin-shell"><h1>Acesso restrito</h1><p>Entre como fotógrafo para continuar.</p><Link href="/">Voltar para entrada</Link></main>;
  return <main className="admin-shell"><p className="eyebrow">Markina Gallery · Fotógrafo</p><h1>Área administrativa</h1><p className="intro">Acompanhe suas vendas e confira as fotos compradas.</p><section className="admin-card"><h2>Operação</h2><p><Link href="/admin/statistics">Abrir estatísticas e exportações</Link></p><p><Link href="/admin/purchases">Conferir fotos compradas</Link></p><Link href="/admin/previews">Abrir conferência por identificador</Link></section></main>;
}
