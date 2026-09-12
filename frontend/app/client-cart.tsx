import Link from "next/link";

export function ClientCartLink({ count, href, className = "client-cart-link" }: { count: number; href: string; className?: string }) {
  if (count < 1) return null;
  return <Link className={className} href={href}>Carrinho ({count})</Link>;
}
