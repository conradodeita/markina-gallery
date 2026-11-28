"use client";

import { useEffect, useState } from "react";
import { LibraryOrderCard, type Order } from "../purchase-card";
import { MarkinaButton, MarkinaLink, SystemState } from "../../ui-kit";
import { mercadoPagoState, paymentMoney } from "../mercadopago";
import { RemovedMovements, type RemovedMovement } from "../../removed-movements";
import library from "../library.module.css";
import styles from "./purchases.module.css";

type PurchaseGroup = { id: string; total_cents: number; orders: Order[] };
type ProviderPaymentGroup = { id: string; state: string; total_cents: number; orders: Order[]; capture_method?: "credit_card" | "pix" | null; cart_reopened_at?: string | null; requires_reconciliation?: boolean };
type MercadoPagoGroup = { id: string; state: string; active: boolean; method: string; total_cents: number; test_account?: boolean; orders: Order[] };
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
  const [result, setResult] = useState<{ orders: Order[]; payment_groups: PurchaseGroup[]; provider_payment_groups: ProviderPaymentGroup[]; mercadopago_payment_groups: MercadoPagoGroup[]; removed_movements: RemovedMovement[] } | null>(null);
  const [failed, setFailed] = useState(false);
  const [request, setRequest] = useState(0);
  useEffect(() => {
    if (!result || !/^#(order|payment)-/.test(window.location.hash)) return;
    document.getElementById(window.location.hash.slice(1))?.scrollIntoView({ block: "start" });
  }, [result]);
  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/library/purchases", { credentials: "same-origin", cache: "no-store", signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error();
        const data = await response.json();
        if (!controller.signal.aborted) { setResult({ orders: data.orders ?? [], payment_groups: data.payment_groups ?? [], provider_payment_groups: data.provider_payment_groups ?? [], mercadopago_payment_groups: data.mercadopago_payment_groups ?? [], removed_movements: data.removed_movements ?? [] }); setFailed(false); }
      }).catch(() => { if (!controller.signal.aborted) setFailed(true); });
    const refresh = () => setRequest((previous) => previous + 1);
    window.addEventListener("focus", refresh);
    return () => { controller.abort(); window.removeEventListener("focus", refresh); };
  }, [request]);
  return <div className={`${library.library} ${styles.history}`}>
    <header className={library.heading}>
      <h1>Minhas compras</h1>
      <p>Acompanhe seus pedidos e veja as fotos liberadas pelo fotógrafo.</p>
    </header>
    {failed ? <div className={library.error}>
      <SystemState tone="error" title="Não foi possível carregar as compras" detail="Você pode continuar nas galerias ou no carrinho." />
      <MarkinaButton variant="secondary" type="button" onClick={() => { setFailed(false); setResult(null); setRequest((previous) => previous + 1); }}>Tentar novamente</MarkinaButton>
    </div> : !result ? <SystemState tone="loading" title="Carregando compras" detail="Buscando seu histórico." /> : <div className={library.content}>
      {!result.orders.length && !result.payment_groups.length && !result.provider_payment_groups.length && !result.mercadopago_payment_groups.length ? <SystemState title="Nenhuma compra." detail="Pedidos e seleções finalizadas aparecerão aqui." /> : null}
      {result.mercadopago_payment_groups.map((group) => <section className={styles.group} key={group.id}
        id={`payment-${group.id}`} aria-label={`Compra Mercado Pago ${group.id.slice(0, 8)}`}>
        <h2>Compra {group.id.slice(0, 8)}</h2>
        <p>Mercado Pago{group.test_account ? " · TESTE" : ""} · {group.method === "pix" ? "PIX" : "Cartão de crédito"} · {paymentMoney(group.total_cents)}</p>
        <p role="status">{mercadoPagoState[group.state] ?? "Pagamento em conferência"}</p>
        {group.active ? <MarkinaLink href={`/library/checkout?payment=${group.id}`} variant="secondary">Acompanhar pagamento</MarkinaLink> : null}
        {group.orders.map((order) => <LibraryOrderCard key={order.id} order={order} />)}
      </section>)}
      {result.payment_groups.map((group) => <section className={styles.group} key={group.id} id={`payment-${group.id}`} aria-label={`Compra ${group.id.slice(0, 8)}`}>
        <h2>Compra {group.id.slice(0, 8)}</h2><p>PIX único · {(group.total_cents / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}</p>
        {group.orders.map((order) => <LibraryOrderCard key={order.id} order={order} />)}
      </section>)}
      {result.provider_payment_groups.map((group) => <section className={styles.group} key={group.id} id={`payment-${group.id}`} aria-label={`Registro legado InfinitePay ${group.id.slice(0, 8)}`}>
        <h2>Compra {group.id.slice(0, 8)}</h2>
        <p>InfinitePay · {group.cart_reopened_at && group.requires_reconciliation && group.state !== "confirmed" ? "Conferência após reabertura" : cardStateLabel[group.state] ?? "estado preservado"} · {group.total_cents ? (group.total_cents / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" }) : ""}</p>
        <p>Registro histórico somente para consulta. O checkout não está mais disponível.</p>
        {group.cart_reopened_at && group.requires_reconciliation && group.state !== "confirmed" ? <p>Há evidência tardia da tentativa anterior. Esta ocorrência não confirma pagamento nem altera o carrinho.</p> : null}
        {group.orders.map((order) => <LibraryOrderCard key={order.id} order={order} />)}
      </section>)}
      <RemovedMovements items={result.removed_movements} />
      {result.orders.map((order) => <LibraryOrderCard key={order.id} order={order} />)}
    </div>}
    <footer className={styles.footer}><MarkinaLink href="/library" variant="secondary">Continuar nas galerias</MarkinaLink></footer>
  </div>;
}
