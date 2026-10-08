import Link from "next/link";

export function ValidationHeader({ role, version }: { role: string; version?: string }) {
  return <header className="validation-header"><div><p className="eyebrow">Markina Gallery · Homologação</p><p className="validation-role">{role}</p></div><span className="environment-badge">versão {version ?? "carregando"}</span></header>;
}

export function StateCard({ title, value, detail, href }: { title: string; value: string | number; detail: string; href?: string }) {
  const content = <><span>{title}</span><strong>{value}</strong><small>{detail}</small></>;
  return href ? <Link className="state-card" href={href}>{content}</Link> : <article className="state-card">{content}</article>;
}

export function EmptyState({ title, detail }: { title: string; detail: string }) {
  return <div className="empty-state"><strong>{title}</strong><p>{detail}</p></div>;
}
