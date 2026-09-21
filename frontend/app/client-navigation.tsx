"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

export function notifyCartChanged() {
  window.dispatchEvent(new Event("client-cart-changed"));
}

export function useCartCount(refreshKey = 0) {
  const [count, setCount] = useState<number | null>(null);
  useEffect(() => {
    let controller: AbortController | null = null;
    const refresh = () => {
      controller?.abort();
      controller = new AbortController();
      const current = controller;
      fetch("/api/library/cart", { credentials: "same-origin", cache: "no-store", signal: current.signal })
        .then(async (response) => {
          if (!response.ok) throw new Error();
          const result = await response.json();
          if (!current.signal.aborted) setCount(typeof result.quantity === "number" ? result.quantity : null);
        })
        .catch(() => { if (!current.signal.aborted) setCount(null); });
    };
    refresh();
    window.addEventListener("focus", refresh);
    window.addEventListener("client-cart-changed", refresh);
    return () => {
      controller?.abort();
      window.removeEventListener("focus", refresh);
      window.removeEventListener("client-cart-changed", refresh);
    };
  }, [refreshKey]);
  return count;
}

export function ClientNavigation() {
  const count = useCartCount();
  return <nav className="client-commerce-nav" aria-label="Navegação da cliente">
    <Link href="/library">Galerias</Link>
    <Link href="/library/cart">Carrinho{count === null ? "" : ` (${count})`}</Link>
    <Link href="/library/purchases">Compras</Link>
  </nav>;
}
