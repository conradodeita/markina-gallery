"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { LibraryOrderCard, type Order } from "../purchase-card";
import { SystemState } from "../../ui-kit";

import { RemovedMovements, type RemovedMovement } from "../../removed-movements";

type PurchaseGroup = { id: string; total_cents: number; orders: Order[] };

export default function PurchasesPage() {
  const [result, setResult] = useState<{ orders: Order[]; payment_groups: PurchaseGroup[]; removed_movements: RemovedMovement[] } | null>(null);
  const [failed, setFailed] = useState(false);
  const [request, setRequest] = useState(0);
  useEffect(() => {
    if (!result || !window.location.hash.startsWith("#order-")) return;
    document.getElementById(window.location.hash.slice(1))?.scrollIntoView({ block: "start" });
  }, [result]);
  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/library/purchases", { credentials: "same-origin", cache: "no-store", signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error();
        const data = await response.json();
        if (!controller.signal.aborted) { setResult({ orders: data.orders ?? [], payment_groups: data.payment_groups ?? [], removed_movements: data.removed_movements ?? [] }); setFailed(false); }
      }).catch(() => { if (!controller.signal.aborted) setFailed(true); });
    const refresh = () => setRequest((previous) => previous + 1);
    window.addEventListener("focus", refresh);
    return () => { controller.abort(); window.removeEventListener("focus", refresh); };
  }, [request]);
  return <section className="library-history">
    <h1>Compras</h1>
    {failed ? <><SystemState tone="error" title="Não foi possível carregar as compras" detail="Você pode continuar nas galerias ou no carrinho." /><button className="secondary" type="button" onClick={() => { setFailed(false); setResult(null); setRequest((previous) => previous + 1); }}>Tentar novamente</button></> : !result ? <SystemState tone="loading" title="Carregando compras" detail="Buscando seu histórico." /> : <>
      {!result.orders.length && !result.payment_groups.length ? <p>Nenhuma compra.</p> : null}
      {result.payment_groups.map((group) => <section className="unified-purchase" key={group.id} id={`payment-${group.id}`} aria-label={`Compra ${group.id.slice(0, 8)}`}>
        <h2>Compra {group.id.slice(0, 8)}</h2><p>PIX único · {(group.total_cents / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}</p>
        {group.orders.map((order) => <LibraryOrderCard key={order.id} order={order} />)}
      </section>)}
      <RemovedMovements items={result.removed_movements} />
      {result.orders.map((order) => <LibraryOrderCard key={order.id} order={order} />)}
    </>}
    <Link href="/library">Continuar nas galerias</Link>
  </section>;
}
