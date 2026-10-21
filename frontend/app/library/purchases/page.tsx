"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { LibraryOrderCard, type Order } from "../purchase-card";
import { SystemState } from "../../ui-kit";

import { RemovedMovements, type RemovedMovement } from "../../removed-movements";

type PurchaseGroup = { id: string; total_cents: number; orders: Order[] };
type ProviderPaymentGroup = { id: string; state: string; checkout_url: string | null; total_cents: number; orders: Order[];
  cart_reopened_at?: string | null };
const isReopened = (group: ProviderPaymentGroup) => group.state === "exception" && Boolean(group.cart_reopened_at);
const cardStateLabel: Record<string, string> = {
  creating: "Preparando checkout",
  awaiting_payment: "Aguardando pagamento",
  verification_required: "Verificando pagamento",
  confirmed: "Pagamento confirmado",
  failed_before_issue: "Checkout não iniciado",
  exception: "Pagamento em análise",
  hold: "Pagamento em revisão",
};

export default function PurchasesPage() {
  const [result, setResult] = useState<{ orders: Order[]; payment_groups: PurchaseGroup[]; provider_payment_groups: ProviderPaymentGroup[]; removed_movements: RemovedMovement[] } | null>(null);
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
        if (!controller.signal.aborted) { setResult({ orders: data.orders ?? [], payment_groups: data.payment_groups ?? [], provider_payment_groups: data.provider_payment_groups ?? [], removed_movements: data.removed_movements ?? [] }); setFailed(false); }
      }).catch(() => { if (!controller.signal.aborted) setFailed(true); });
    const refresh = () => setRequest((previous) => previous + 1);
    window.addEventListener("focus", refresh);
    return () => { controller.abort(); window.removeEventListener("focus", refresh); };
  }, [request]);
  return <section className="library-history">
    <h1>Compras</h1>
    {failed ? <><SystemState tone="error" title="Não foi possível carregar as compras" detail="Você pode continuar nas galerias ou no carrinho." /><button className="secondary" type="button" onClick={() => { setFailed(false); setResult(null); setRequest((previous) => previous + 1); }}>Tentar novamente</button></> : !result ? <SystemState tone="loading" title="Carregando compras" detail="Buscando seu histórico." /> : <>
      {!result.orders.length && !result.payment_groups.length && !result.provider_payment_groups.length ? <p>Nenhuma compra.</p> : null}
      {result.payment_groups.map((group) => <section className="unified-purchase" key={group.id} id={`payment-${group.id}`} aria-label={`Compra ${group.id.slice(0, 8)}`}>
        <h2>Compra {group.id.slice(0, 8)}</h2><p>PIX único · {(group.total_cents / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}</p>
        {group.orders.map((order) => <LibraryOrderCard key={order.id} order={order} />)}
      </section>)}
      {result.provider_payment_groups.map((group) => <section className="unified-purchase" key={group.id} id={`payment-${group.id}`} aria-label={`Compra de cartão ${group.id.slice(0, 8)}`}>
        <h2>Compra {group.id.slice(0, 8)}</h2>
        <p>Cartão de crédito · {isReopened(group) ? "Carrinho reaberto" : cardStateLabel[group.state] ?? "Pagamento em análise"} · {group.total_cents ? (group.total_cents / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" }) : ""}</p>
        {group.state === "awaiting_payment" && group.checkout_url ? <a className="order-album-button order-album-button--available" href={group.checkout_url} target="_blank" rel="noopener noreferrer">Continuar pagamento</a> : null}
        {group.state === "verification_required" ? <p>A InfinitePay não devolveu um link utilizável. O checkout não foi aberto e nenhum pagamento foi iniciado por esta tela. A compra permanece reservada enquanto verificamos se o link chegou a ser criado. Não tente iniciar outro pagamento enquanto estiver em conferência.</p> : null}
        {isReopened(group) ? <><p>O fotógrafo devolveu as fotos desta compra ao carrinho. Elas já estão selecionadas; confira o total atual e escolha como pagar.</p>
          <Link className="order-album-button order-album-button--available" href="/library/cart">Abrir carrinho</Link></>
          : group.state === "hold" || group.state === "exception" ? <p>Esta compra está em conferência; o acesso às fotos permanece suspenso.</p> : null}
        {group.orders.map((order) => <LibraryOrderCard key={order.id} order={order} />)}
      </section>)}
      <RemovedMovements items={result.removed_movements} />
      {result.orders.map((order) => <LibraryOrderCard key={order.id} order={order} />)}
    </>}
    <Link href="/library">Continuar nas galerias</Link>
  </section>;
}
