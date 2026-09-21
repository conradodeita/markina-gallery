"use client";

import Link from "next/link";
import { useCartCount } from "./client-navigation";

export function ClientCartLink({ count, className = "client-cart-link" }: { count: number; href?: string; className?: string }) {
  const total = useCartCount(count);
  return <Link className={className} href="/library/cart">Carrinho{total === null ? "" : ` (${total})`}</Link>;
}
