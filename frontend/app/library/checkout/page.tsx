"use client";

import Link from "next/link";
import { type FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { notifyCartChanged } from "../../client-navigation";
import { SystemState } from "../../ui-kit";
import { mercadoPagoState, paymentMoney, paymentRequest, PaymentRequestError,
  MERCADO_PAGO_MINIMUM_TOTAL_CENTS,
  type MercadoPagoPayment } from "../mercadopago";
import CardPayment, { type CardData } from "./card-payment";
import PaymentLogo from "../payment-logo";
import styles from "./checkout.module.css";

type Cart = {
  mercadopago_available?: boolean; cart_revision: string | null; total_cents: number | null;
  groups: Array<{ name: string; payment_required?: boolean;
    items: Array<{ id: string; name: string }>; quantity: number }>;
};
const retryable = new Set(["rejected", "canceled", "expired", "abandoned"]);

export default function CheckoutPage() {
  const [payment, setPayment] = useState<MercadoPagoPayment | null>(null);
  const [cart, setCart] = useState<Cart | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loaded, setLoaded] = useState(false);
  const locked = useRef(false);
  const mounted = useRef(true);

  const prepare = useCallback(async (current: Cart, method: "credit_card" | "pix") => {
    if (!current.mercadopago_available || !current.cart_revision) {
      throw new Error("Mercado Pago indisponível para esta seleção. Volte ao carrinho para conferir.");
    }
    if (current.total_cents === null || current.total_cents < MERCADO_PAGO_MINIMUM_TOTAL_CENTS) {
      throw new Error(`Para pagar com Mercado Pago, selecione fotos que somem pelo menos ${paymentMoney(MERCADO_PAGO_MINIMUM_TOTAL_CENTS)}.`);
    }
    const result = await paymentRequest<MercadoPagoPayment>("/library/mercadopago/prepare", {
      cart_revision: current.cart_revision, idempotency_key: crypto.randomUUID(), method,
    });
    if (mounted.current) setPayment(result);
  }, []);

  useEffect(() => {
    mounted.current = true;
    let disposed = false;
    async function load() {
      try {
        const selectedId = new URLSearchParams(window.location.search).get("payment");
        const [currentCart, active] = await Promise.all([
          paymentRequest<Cart>("/library/cart"),
          selectedId
            ? paymentRequest<MercadoPagoPayment>(`/library/mercadopago/${encodeURIComponent(selectedId)}`)
            : paymentRequest<{ payment: MercadoPagoPayment | null }>("/library/mercadopago/active")
              .then((result) => result.payment),
        ]);
        if (disposed) return;
        setCart(currentCart);
        if (active) setPayment(active);
        else if (currentCart.total_cents === null || currentCart.total_cents < MERCADO_PAGO_MINIMUM_TOTAL_CENTS) {
          setNotice(`O Mercado Pago está disponível para compras a partir de ${paymentMoney(MERCADO_PAGO_MINIMUM_TOTAL_CENTS)}. Sua seleção foi mantida.`);
        } else await prepare(currentCart, "credit_card");
      } catch (failure) {
        if (!disposed) setError((failure as Error).message);
      } finally { if (!disposed) setLoaded(true); }
    }
    void load();
    return () => { disposed = true; mounted.current = false; };
  }, [prepare]);

  useEffect(() => {
    if (!payment?.active || payment.state === "prepared") return;
    const timer = window.setInterval(() => {
      void paymentRequest<MercadoPagoPayment>(`/library/mercadopago/${payment.id}`).then((result) => {
        if (mounted.current) {
          setPayment(result);
          if (result.state !== payment.state || result.active !== payment.active) notifyCartChanged();
        }
      }).catch(() => undefined);
    }, 10000);
    return () => window.clearInterval(timer);
  }, [payment?.id, payment?.active, payment?.state]);

  const submit = useCallback(async (body: { token?: string; payment_method_id?: string;
    email: string; identification_number: string }) => {
    if (!payment || locked.current) return;
    locked.current = true; setBusy(true); setError("");
    try {
      const result = await paymentRequest<MercadoPagoPayment>(
        `/library/mercadopago/${payment.id}/submit`, body);
      if (mounted.current) { setPayment(result); notifyCartChanged(); }
    } catch (failure) {
      if (mounted.current) {
        if (failure instanceof PaymentRequestError && failure.status === 409) {
          setError(failure.message);
        } else {
          setPayment({ ...payment, state: "verification_required" });
          setError("O resultado ainda precisa ser conferido. Atualize o pagamento antes de tentar novamente.");
        }
      }
    } finally { locked.current = false; if (mounted.current) setBusy(false); }
  }, [payment]);

  const submitCard = useCallback(async (data: CardData) => {
    await submit({ token: data.token, payment_method_id: data.payment_method_id,
      email: data.payer.email, identification_number: data.payer.identification.number });
  }, [submit]);

  async function switchMethod(method: "credit_card" | "pix") {
    if (!payment || !cart || locked.current || payment.method === method) return;
    locked.current = true; setBusy(true); setError("");
    try { await prepare(cart, method); }
    catch (failure) { setError((failure as Error).message); }
    finally { locked.current = false; setBusy(false); }
  }

  async function action(kind: "cancel" | "reconcile") {
    if (!payment || locked.current) return;
    locked.current = true; setBusy(true); setError("");
    try {
      const result = await paymentRequest<MercadoPagoPayment>(
        `/library/mercadopago/${payment.id}/${kind}`, {});
      setPayment(result); notifyCartChanged();
      if (kind === "cancel" && !result.active) setNotice("Checkout encerrado. Sua seleção disponível está no carrinho.");
      else if (kind === "cancel" && result.state === "processing") setNotice(
        "Esta tentativa está em processamento. Aguarde o resultado; a seleção vinculada não pode ser cancelada ou editada agora.");
      else if (kind === "cancel") setNotice("O cancelamento ainda não foi confirmado. Aguarde a conferência.");
    } catch (failure) { setError((failure as Error).message); }
    finally { locked.current = false; setBusy(false); }
  }

  async function retry() {
    if (locked.current) return;
    locked.current = true; setBusy(true); setError("");
    try {
      const current = await paymentRequest<Cart>("/library/cart");
      setCart(current);
      await prepare(current, payment?.method ?? "credit_card");
    } catch (failure) { setError((failure as Error).message); }
    finally { locked.current = false; setBusy(false); }
  }

  function submitPix(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const fields = new FormData(event.currentTarget);
    void submit({ email: String(fields.get("email") ?? ""),
      identification_number: String(fields.get("cpf") ?? "").replace(/\D/g, "") });
  }

  const photos = payment?.items?.length ? payment.items.map((item) => item.name)
    : cart?.groups.filter((group) => group.payment_required !== false).flatMap(
      (group) => group.items.map((item) => item.name)) ?? [];
  return <section className={styles.checkout}>
    <header><p className="eyebrow">Sua compra</p><h1>Pagamento</h1>
      <p>Confira suas fotos e escolha como pagar.</p></header>
    {error ? <p role="alert" className={styles.error}>{error}</p> : null}
    {notice ? <p role="status">{notice}</p> : null}
    {!loaded ? <SystemState tone="loading" title="Preparando pagamento" detail="Conferindo sua seleção." /> : null}
    {payment ? <>
      <section className={styles.summary} aria-label="Resumo da compra">
        <h2>{photos.length} foto(s) · {paymentMoney(payment.total_cents)}</h2>
        <p>Compra {payment.id.slice(0, 8)}</p>
        <details><summary>Ver fotografias</summary><ul>{photos.map((name, index) => <li key={index}>{name}</li>)}</ul></details>
      </section>
      {payment.state === "prepared" ? payment.total_cents < MERCADO_PAGO_MINIMUM_TOTAL_CENTS ?
        <p role="alert" className={styles.error}>
          Para pagar com Mercado Pago, selecione fotos que somem pelo menos {paymentMoney(MERCADO_PAGO_MINIMUM_TOTAL_CENTS)}. Sua seleção foi mantida.
        </p> : <>
        <fieldset className={styles.methods} disabled={busy}><legend>Como você quer pagar?</legend>
          <label data-selected={payment.method === "credit_card"}><input type="radio" name="payment-method" checked={payment.method === "credit_card"}
            aria-label="Cartão de crédito" onChange={() => void switchMethod("credit_card")} /><PaymentLogo provider="mercadopago" /> Cartão de crédito</label>
          <label data-selected={payment.method === "pix"}><input type="radio" name="payment-method" checked={payment.method === "pix"}
            aria-label="PIX Mercado Pago" onChange={() => void switchMethod("pix")} /><PaymentLogo provider="pix" /> PIX Mercado Pago</label>
        </fieldset>
        {payment.method === "credit_card" ? <CardPayment payment={payment} onSubmit={submitCard} />
          : <form className={styles.pixForm} onSubmit={submitPix}>
            <label>E-mail para o pagamento<input name="email" type="email" autoComplete="email" required maxLength={254} /></label>
            <label>CPF do pagador<input name="cpf" inputMode="numeric" autoComplete="off" required pattern="[0-9]{11}" maxLength={11} /></label>
            <button className="primary" disabled={busy}>{busy ? "Preparando PIX…" : "Gerar PIX"}</button>
          </form>}
      </> : <section className={styles.result} aria-live="polite">
        <h2>{mercadoPagoState[payment.state] ?? "Pagamento em conferência"}</h2>
        <p>{payment.method === "pix" ? "PIX Mercado Pago" : "Cartão de crédito · Mercado Pago"}</p>
        {payment.state === "confirmed" ? <p>Pagamento recebido. Acompanhe a entrega das fotografias em Compras.</p> : null}
        {payment.state === "rejected" ? <p>Confira os dados ou tente outro cartão. Suas fotos disponíveis voltaram ao carrinho.</p> : null}
        {payment.state === "processing" ? <p role="status">Esta tentativa está em processamento. Aguarde o resultado; a seleção vinculada não pode ser cancelada ou editada agora.</p> : null}
        {["verification_required", "sending"].includes(payment.state)
          ? <p>Aguarde a confirmação. Você pode sair e acompanhar esta compra depois.</p> : null}
        {payment.state === "pending" && payment.pix_copy_paste ? <>
          {payment.pix_qr_code ? <img src={payment.pix_qr_code} alt="QR Code PIX Mercado Pago" width={240} height={240} /> : null}
          <label>PIX copia e cola<textarea readOnly value={payment.pix_copy_paste} rows={4} /></label>
          <button type="button" className="secondary" onClick={() => void navigator.clipboard.writeText(
            payment.pix_copy_paste!).then(() => setNotice("PIX copiado.")).catch(
              () => setNotice("Selecione e copie o código acima."))}>Copiar PIX</button>
          <p>A confirmação é automática após o recebimento.</p>
        </> : null}
        {payment.active ? <button className="secondary" disabled={busy} onClick={() => void action("reconcile")}>Atualizar pagamento</button> : null}
        {retryable.has(payment.state) ? <button className="primary" disabled={busy} onClick={() => void retry()}>Tentar novamente</button> : null}
      </section>}
      {busy ? <p role="status">Conferindo pagamento…</p> : null}
      <nav className={styles.actions} aria-label="Ações da compra">
        {payment.can_cancel ? <button className="secondary" disabled={busy} onClick={() => void action("cancel")}>
          {payment.state === "prepared" ? "Encerrar checkout" : "Cancelar tentativa e editar seleção"}</button> : null}
        <Link href="/library/cart">Voltar ao carrinho</Link>
        <Link href="/library/purchases">Ver compras</Link>
      </nav>
      {payment.active && payment.state !== "prepared" ? <small>Voltar ao carrinho não cancela o pagamento.</small> : null}
    </> : loaded && cart && cart.total_cents !== null && cart.total_cents < MERCADO_PAGO_MINIMUM_TOTAL_CENTS ? <>
      <p role="status" className={styles.error}>
        Para pagar com Mercado Pago, selecione fotos que somem pelo menos {paymentMoney(MERCADO_PAGO_MINIMUM_TOTAL_CENTS)}. Sua seleção foi mantida.
      </p><Link className="primary" href="/library/cart">Voltar ao carrinho</Link>
    </> : loaded ? <Link className="primary" href="/library/cart">Voltar ao carrinho</Link> : null}
  </section>;
}
