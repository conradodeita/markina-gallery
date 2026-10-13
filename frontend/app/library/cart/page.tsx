"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { PurchasePreview } from "../../purchase-preview";
import { notifyCartChanged } from "../../client-navigation";
import { SelectionDeadline } from "../../selection-deadline";
import { SystemState } from "../../ui-kit";

type CartGroup = { payment_required?: boolean; message?: string; revision?: string; gallery_id: string; parent_gallery_id: string; name: string; quantity: number;
  legacy_review_url?: string | null;
  total_cents: number | null; error: string | null; browse_url: string; selection_expires_at: string | null;
  items: Array<{ id: string; name: string; folder_name: string | null; preview_url: string }> };
type Payment = { id: string; revision: string; total_cents: number; pix_copy_paste: string;
  pix_qr_code: string; pix_instructions: string | null; receiver_name: string | null };
type CardPayment = { id: string; status: "awaiting_payment" | "verification_required" | "failed_before_issue"; checkout_url: string | null; total_cents: number };
type Cart = { groups: CartGroup[]; quantity: number; can_prepare: boolean; cart_revision?: string | null;
  card_available?: boolean; card_payment?: CardPayment | null; total_cents: number | null; payment?: Payment };
const money = (value: number) => (value / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

export default function CartPage() {
  const [cart, setCart] = useState<Cart | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [reported, setReported] = useState<string | null>(null);
  const [method, setMethod] = useState<"pix" | "card">("pix");
  const cardCheckoutIssued = cart?.card_payment?.status === "awaiting_payment"
    && Boolean(cart.card_payment.checkout_url);
  const cardCheckoutUncertain = cart?.card_payment?.status === "verification_required";
  const cardCheckoutPending = cardCheckoutIssued || cardCheckoutUncertain;
  const sequence = useRef(0);
  const locked = useRef(false);
  const requestKey = useRef<string | null>(null);
  const cardRequestKey = useRef<string | null>(null);
  const finalizationKeys = useRef<Record<string, string>>({});
  const refresh = useCallback(async () => {
    const current = ++sequence.current;
    setError("");
    // Oculta o PIX durante revalidação para não oferecer uma revisão obsoleta.
    setCart((previous) => previous ? { ...previous, payment: undefined } : previous);
    try {
      const response = await fetch("/api/library/cart", { credentials: "same-origin", cache: "no-store" });
      if (sequence.current !== current) return;
      if (response.status === 401 || response.status === 403) setCart(null);
      if (!response.ok) throw new Error("Não foi possível consultar o carrinho.");
      const data: Cart = await response.json();
      if (sequence.current !== current) return;
      setCart(data);
      if (!data.can_prepare) return;
      const prepared = await fetch("/api/library/cart/prepare", { method: "POST", credentials: "same-origin" });
      const result = await prepared.json();
      if (sequence.current !== current) return;
      if (prepared.status === 401 || prepared.status === 403) setCart(null);
      if (!prepared.ok) throw new Error(result.detail ?? "Não foi possível preparar o PIX.");
      setCart(result);
    } catch (failure) {
      if (sequence.current === current) setError(failure instanceof Error ? failure.message : "Não foi possível consultar o carrinho.");
    }
  }, []);
  useEffect(() => {
    const initial = setTimeout(() => void refresh(), 0);
    const focus = () => { if (!locked.current) void refresh(); };
    window.addEventListener("focus", focus);
    return () => { clearTimeout(initial); sequence.current++; window.removeEventListener("focus", focus); };
  }, [refresh]);

  async function remove(group: CartGroup, photoId?: string) {
    if (locked.current) return;
    locked.current = true; setBusy(true); setNotice("");
    try {
      const path = `/api/library/cart/${group.gallery_id}${photoId ? `/photos/${photoId}` : ""}`;
      const response = await fetch(path, { method: "DELETE", credentials: "same-origin" });
      if (!response.ok) throw new Error("Não foi possível salvar a remoção. Tente novamente.");
      requestKey.current = null;
      notifyCartChanged();
      await refresh();
    } catch (failure) { setError(failure instanceof Error ? failure.message : "Não foi possível salvar."); }
    finally { locked.current = false; setBusy(false); }
  }

  async function finalize(group: CartGroup) {
    if (!group.revision || locked.current) return;
    locked.current = true; setBusy(true); setError("");
    const revisionKey = `${group.gallery_id}:${group.revision}`;
    finalizationKeys.current[revisionKey] ??= crypto.randomUUID();
    try {
      const response = await fetch(`/api/library/cart/${group.gallery_id}/finalize`, {
        method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ revision: group.revision, idempotency_key: finalizationKeys.current[revisionKey] }),
      });
      const result = await response.json();
      if (!response.ok) {
        if (response.status === 409) delete finalizationKeys.current[revisionKey];
        throw new Error(result.detail ?? "Não foi possível finalizar a seleção.");
      }
      delete finalizationKeys.current[revisionKey];
      notifyCartChanged();
      await refresh();
      setNotice("Seleção finalizada. O fotógrafo já pode conferir suas fotos. Acompanhe em Compras.");
    } catch (failure) { setError(failure instanceof Error ? failure.message : "Não foi possível finalizar a seleção."); }
    finally { locked.current = false; setBusy(false); }
  }

  async function report() {
    if (!cart?.payment || locked.current) return;
    locked.current = true; setBusy(true); setError("");
    const payment = cart.payment;
    requestKey.current ??= crypto.randomUUID();
    try {
      const response = await fetch(`/api/library/payments/${payment.id}/report`, {
        method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ revision: payment.revision, idempotency_key: requestKey.current }),
      });
      const result = await response.json();
      if (!response.ok) {
        if (response.status === 401 || response.status === 403) setCart(null);
        if (response.status === 409) {
          setCart((previous) => previous ? { ...previous, payment: undefined } : previous);
          requestKey.current = null;
        }
        throw new Error(result.detail ?? "Não foi possível informar o pagamento.");
      }
      sequence.current++;
      setReported(payment.id); setCart(null); notifyCartChanged();
    } catch (failure) { setError(failure instanceof Error ? failure.message : "Não foi possível confirmar o resultado. Tente novamente."); }
    finally { locked.current = false; setBusy(false); }
  }

  async function prepareCard() {
    if (!cart?.cart_revision || !cart.can_prepare || !cart.card_available || locked.current) return;
    locked.current = true; setBusy(true); setError("");
    cardRequestKey.current ??= crypto.randomUUID();
    try {
      const response = await fetch("/api/library/cart/prepare-card", {
        method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cart_revision: cart.cart_revision, idempotency_key: cardRequestKey.current }),
      });
      const result = await response.json();
      if (response.status === 401 || response.status === 403) setCart(null);
      if (!response.ok) {
        if (response.status === 409) cardRequestKey.current = null;
        throw new Error(result.detail ?? "Não foi possível preparar o pagamento com cartão.");
      }
      if (result.status === "failed_before_issue") {
        cardRequestKey.current = null;
        setCart((previous) => previous ? { ...previous, card_payment: null } : previous);
        setNotice("A InfinitePay confirmou que não criou o checkout. Suas fotos continuam selecionadas; você pode tentar o cartão novamente ou escolher PIX.");
        notifyCartChanged();
        return;
      }
      setCart((previous) => previous ? { ...previous, card_payment: result } : previous);
      if (result.status === "awaiting_payment" && result.checkout_url) {
        setNotice("Link seguro pronto. Confira o recebedor e pague no checkout da InfinitePay.");
      } else {
        setNotice("A InfinitePay não devolveu um link utilizável. O checkout não foi aberto e nenhum pagamento foi iniciado por esta tela. A compra segue reservada enquanto verificamos a resposta; não tente iniciar outro pagamento. Acompanhe em Compras.");
      }
      notifyCartChanged();
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Não foi possível preparar o cartão.");
    } finally { locked.current = false; setBusy(false); }
  }

  if (reported) return <section className="unified-cart"><h1>Pagamento informado</h1><p>Seu pagamento aguarda a confirmação do fotógrafo.</p><Link className="primary" href={`/library/purchases#payment-${reported}`}>Ver compra</Link><Link href="/library">Continuar nas galerias</Link></section>;
  return <section className="unified-cart">
    <h1>{cart?.groups.length && cart.groups.every((group) => group.payment_required === false) ? "Revise suas fotos" : "Revise suas fotos e escolha como pagar"}</h1>
    {notice ? <p role="status">{notice} <Link href="/library/purchases">Ver histórico</Link></p> : null}
    {error ? <div role="alert"><p>{error}</p><button type="button" className="secondary" disabled={busy} onClick={() => void refresh()}>Atualizar revisão</button></div> : null}
    {!cart && !error ? <SystemState tone="loading" title="Carregando carrinho" detail="Buscando suas fotos selecionadas." /> : null}
    {cart?.quantity === 0 ? <><p>Seu carrinho está vazio.</p><Link className="primary" href="/library">Escolher fotos</Link></> : null}
    {cart?.card_payment ? <section className="unified-payment" aria-label="Pagamento por cartão em andamento">
      <h2>Compra por cartão · {money(cart.card_payment.total_cents)}</h2>
      {cart.card_payment.status === "awaiting_payment" && cart.card_payment.checkout_url
        ? <><p>Continue o pagamento no checkout seguro da InfinitePay.</p><a className="primary" href={cart.card_payment.checkout_url} target="_blank" rel="noopener noreferrer">Continuar para pagamento com cartão</a></>
        : <p role="status">Pagamento em verificação; esta compra permanece reservada. Acompanhe em Compras e não inicie outra cobrança para essas fotos.</p>}
      <Link href={`/library/purchases#payment-${cart.card_payment.id}`}>Acompanhar compra</Link>
    </section> : null}
    {cart?.groups.map((group) => <section className="unified-cart-group" key={group.gallery_id} aria-label={`Fotos de ${group.name}`}>
      <div className="section-heading"><h2>{group.name}</h2><span>{group.quantity} foto(s){group.total_cents !== null ? ` · ${money(group.total_cents)}` : ""}</span></div>
      {group.message?.trim() ? <p style={{ whiteSpace: "pre-wrap" }}>{group.message}</p> : null}
      <SelectionDeadline expiresAt={group.selection_expires_at} />
      {group.error ? <p role="alert">{group.error}</p> : null}
      <div className="unified-cart-photos">{group.items.map((photo) => <figure key={photo.id}>
        <PurchasePreview path={photo.preview_url} name={photo.name} />
        <figcaption><strong>{photo.name}</strong>{photo.folder_name ? <small>{photo.folder_name}</small> : null}</figcaption>
        <button type="button" className="secondary" disabled={busy} aria-label={`Remover ${photo.name} de ${group.name}`} onClick={() => void remove(group, photo.id)}>Remover</button>
      </figure>)}</div>
      <div className="dashboard-actions"><Link href={group.browse_url}>Continuar escolhendo</Link><button type="button" className="secondary" disabled={busy} onClick={() => void remove(group)}>Remover seleção de {group.name}</button></div>
      {group.payment_required === false ? <button type="button" className="primary" disabled={busy || !!group.error || !group.revision} onClick={() => void finalize(group)}>{busy ? "Salvando…" : "Finalizar seleção"}</button> : null}
      {error && group.legacy_review_url ? <Link href={group.legacy_review_url}>Retomar pagamento anterior de {group.name}</Link> : null}
    </section>)}
    {cart && cart.groups.some((group) => group.payment_required !== false) ? <section className="unified-payment" aria-label="Pagamento único">
      <h2>Total {cart.total_cents === null ? "a conferir" : money(cart.total_cents)}</h2>
      <p>{cart.groups.filter((group) => group.payment_required !== false).reduce((sum, group) => sum + group.quantity, 0)} foto(s) com cobrança</p>
      {!cardCheckoutPending && cart.can_prepare && cart.card_available ? <fieldset>
        <legend>Forma de pagamento</legend>
        <label><input type="radio" name="payment-method" checked={method === "pix"} onChange={() => setMethod("pix")} /> PIX</label>
        <label><input type="radio" name="payment-method" checked={method === "card"} onChange={() => setMethod("card")} /> Cartão de crédito</label>
      </fieldset> : null}
      {!cardCheckoutPending && method === "card" && cart.card_available ? <>
        <p>O pagamento será feito no ambiente seguro da InfinitePay. O Pick-your-Pic não recebe dados do cartão.</p>
        <button type="button" className="primary" disabled={busy || !cart.cart_revision} onClick={() => void prepareCard()}>{busy ? "Preparando checkout…" : "Continuar com cartão de crédito"}</button>
      </> : null}
      {!cardCheckoutPending && (method === "pix" || !cart.card_available) ? <>
      {cart.payment ? <>
        <h3>Pague com PIX</h3>
        {cart.payment.receiver_name ? <p>Recebedor: {cart.payment.receiver_name}</p> : null}
        <img className="unified-pix-qr" src={cart.payment.pix_qr_code} alt="QR Code do PIX da compra" width={240} height={240} />
        <label htmlFor="pix-copy">PIX copia e cola</label><textarea id="pix-copy" readOnly value={cart.payment.pix_copy_paste} rows={3} />
        <button type="button" className="secondary" onClick={() => { void navigator.clipboard.writeText(cart.payment!.pix_copy_paste).then(() => setNotice("Código PIX copiado.")).catch(() => setNotice("Selecione e copie o código acima.")); }}>Copiar PIX</button>
        {cart.payment.pix_instructions ? <p>{cart.payment.pix_instructions}</p> : null}
        <p>Após pagar {money(cart.payment.total_cents)}, informe o pagamento para o fotógrafo conferir.</p>
        <button type="button" className="primary" disabled={busy} onClick={() => void report()}>{busy ? "Salvando…" : "Informar pagamento"}</button>
      </> : !error && cart.can_prepare ? <p role="status">Preparando PIX…</p> : <p>Confira os avisos acima para continuar.</p>}
      </> : null}
    </section> : null}
  </section>;
}
