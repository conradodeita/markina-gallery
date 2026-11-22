"use client";

import Link from "next/link";

export function ClientCartLink({ href = "/library/cart", className = "client-cart-link" }: { href?: string; className?: string }) {
  return <Link className={className} href={href}>Prosseguir</Link>;
}
