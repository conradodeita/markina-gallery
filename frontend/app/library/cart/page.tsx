"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { PurchasePreview } from "../../purchase-preview";
import { notifyCartChanged } from "../../client-navigation";
import { MarkinaButton, MarkinaLink, SystemState } from "../../ui-kit";
import MercadoPagoResume from "./mercadopago-resume";
import PaymentLogo from "../payment-logo";
import paymentStyles from "../payment-methods.module.css";
import { MERCADO_PAGO_MINIMUM_TOTAL_CENTS, paymentMoney } from "../mercadopago";
import { clientMediaStatusMessage, type MediaArchiveStatus } from "../../media-archive-status";
import library from "../library.module.css";
import styles from "./cart.module.css";

type CartGroup = { payment_required?: boolean; message?: string; revision?: string; gallery_id: string; parent_gallery_id: string; name: string; quantity: number;
  legacy_review_url?: string | null; total_cents: number | null; error: string | null; browse_url: string;
  items: Array<{ id: string; name: string; folder_name: string | null; preview_url: string | null; media_status?: MediaArchiveStatus }> };
type Payment = { id: string; revision: string; total_cents: number; pix_copy_paste: string;
  pix_qr_code: string; pix_instructions: string | null; receiver_name: string | null };
type Cart = { groups: CartGroup[]; quantity: number; can_prepare: boolean; cart_revision?: string | null;
  pix_available?: boolean; mercadopago_available?: boolean; payment_error?: string | null; total_cents: number | null; payment?: Payment };
const money = (value: number) => (value / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

export default function CartPage() {
  const [cart, setCart] = useState<Cart | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [reported, setReported] = useState<string | null>(null);
  const sequence = useRef(0);
  const locked = useRef(false);
  const requestKey = useRef<string | null>(null);
  const finalizationKeys = useRef<Record<string, string>>({});

  const refresh = useCallback(async () => {
    const current = ++sequence.current;
    setError("");
    setCart((previous) => previous ? { ...previous, payment: undefined } : previous);
    try {
      const response = await fetch("/api/library/cart", { credentials: "same-origin", cache: "no-store" });
      if (sequence.current !== current) return;
      if (response.status === 401 || response.status === 403) setCart(null);
      if (!response.ok) throw new Error("Não foi possível consultar o carrinho.");
      const data: Cart = await response.json();
      if (sequence.current !== current) return;
      setCart(data);
      if (!data.can_prepare || data.pix_available === false) return;
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
        if (response.status === 409) { setCart((previous) => previous ? { ...previous, payment: undefined } : previous); requestKey.current = null; }
        throw new Error(result.detail ?? "Não foi possível informar o pagamento.");
      }
      sequence.current++;
      setReported(payment.id); setCart(null); notifyCartChanged();
    } catch (failure) { setError(failure instanceof Error ? failure.message : "Não foi possível confirmar o resultado. Tente novamente."); }
    finally { locked.current = false; setBusy(false); }
  }

  if (reported) return <section className={`${library.library} ${styles.receipt}`}>
    <header className={library.heading}>
      <h1>Pagamento informado</h1>
      <p>Seu pagamento aguarda a confirmação do fotógrafo.</p>
    </header>
    <div className={styles.actions}>
      <MarkinaLink className={styles.primary} href={`/library/purchases#payment-${reported}`}>Ver compra</MarkinaLink>
      <MarkinaLink href="/library" variant="secondary">Continuar nas galerias</MarkinaLink>
    </div>
  </section>;

  const chargedGroups = cart?.groups.filter((group) => group.payment_required !== false) ?? [];
  return <div className={library.library}>
    <header className={library.heading}>
      <h1>{!cart?.groups.length ? "Seu carrinho" : chargedGroups.length ? "Revise suas fotos e escolha como pagar" : "Revise suas fotos"}</h1>
    </header>
    <div className={library.content}>
      <MercadoPagoResume />
      {notice ? <p className={styles.notice} role="status">{notice} <Link href="/library/purchases">Ver histórico</Link></p> : null}
      {error ? <div className={library.error}>
        <SystemState tone="error" title="Não foi possível completar esta etapa" detail={error} />
        <MarkinaButton type="button" variant="secondary" disabled={busy} onClick={() => void refresh()}>Atualizar revisão</MarkinaButton>
      </div> : null}
      {!cart && !error ? <SystemState tone="loading" title="Carregando carrinho" detail="Buscando suas fotos selecionadas." /> : null}
      {cart?.quantity === 0 ? <div className={styles.receipt}><p>Seu carrinho está vazio.</p><MarkinaLink href="/library" className={styles.primary}>Escolher fotos</MarkinaLink></div> : null}
      <div className={chargedGroups.length ? styles.twoColumn : undefined}>
        <div className={library.content}>
          {cart?.groups.map((group) => <section className={styles.group} key={group.gallery_id} aria-label={`Fotos de ${group.name}`}>
            <div className={styles.groupHeading}><h2>{group.name}</h2><span>{group.quantity} foto(s){group.total_cents !== null ? ` · ${money(group.total_cents)}` : ""}</span></div>
            {group.message?.trim() ? <p className={styles.message}>{group.message}</p> : null}
            {group.error ? <p role="alert">{group.error}</p> : null}
            <div className={styles.photos}>{group.items.map((photo) => <figure key={photo.id}>
              {photo.preview_url ? <PurchasePreview path={photo.preview_url} name={photo.name} /> : <div className="purchase-preview-unavailable" role="img" aria-label={`Prévia indisponível de ${photo.name}`}>Prévia indisponível no momento</div>}
              <figcaption><strong>{photo.name}</strong>{photo.folder_name ? <small>{photo.folder_name}</small> : null}{photo.media_status && photo.media_status !== "available" ? <small>{clientMediaStatusMessage(photo.media_status)}</small> : null}</figcaption>
              <MarkinaButton type="button" variant="secondary" disabled={busy} aria-label={`Remover ${photo.name} de ${group.name}`} onClick={() => void remove(group, photo.id)}>Remover</MarkinaButton>
            </figure>)}</div>
            <div className={styles.actions}>
              <MarkinaLink href={group.browse_url} variant="secondary">Continuar escolhendo</MarkinaLink>
              <MarkinaButton type="button" variant="secondary" disabled={busy} onClick={() => void remove(group)}>Remover seleção de {group.name}</MarkinaButton>
              {group.payment_required === false ? <MarkinaButton type="button" className={styles.primary} disabled={busy || !!group.error || !group.revision} onClick={() => void finalize(group)}>{busy ? "Salvando…" : "Finalizar seleção"}</MarkinaButton> : null}
            </div>
            {error && group.legacy_review_url ? <Link href={group.legacy_review_url}>Retomar pagamento anterior de {group.name}</Link> : null}
          </section>)}
        </div>
        {cart && chargedGroups.length ? <section className={styles.payment} aria-label="Resumo do pedido e pagamento">
          <header className={styles.summary}>
            <h2>Resumo do pedido</h2>
            <div><span>{chargedGroups.reduce((sum, group) => sum + group.quantity, 0)} foto(s) com cobrança</span><strong>Total {cart.total_cents === null ? "a conferir" : money(cart.total_cents)}</strong></div>
          </header>
          {cart.payment_error ? <p role="alert">{cart.payment_error}</p> : null}
          <div className={`${paymentStyles.choices} ${styles.methods}`} role="group" aria-label="Formas de pagamento">
            {cart.pix_available !== false ? <a className={paymentStyles.option} href="#cart-system-pix" aria-label="Pagar com PIX do sistema">
              <PaymentLogo provider="pix" /><span><strong>PIX do sistema</strong><small>Pague pelo QR Code. O fotógrafo confere seu pagamento.</small></span>
            </a> : null}
            {cart.mercadopago_available && cart.cart_revision ? cart.total_cents !== null &&
              cart.total_cents < MERCADO_PAGO_MINIMUM_TOTAL_CENTS ? <div className={paymentStyles.option}
                aria-disabled="true" aria-label="Mercado Pago indisponível para este valor">
                <PaymentLogo provider="mercadopago" /><span><strong>Mercado Pago</strong>
                  <small>Disponível a partir de {paymentMoney(MERCADO_PAGO_MINIMUM_TOTAL_CENTS)}. Selecione mais fotos ou use o PIX do sistema.</small></span>
              </div> : <Link className={paymentStyles.option}
                aria-label="Pagar com Mercado Pago" data-mp-checkout-cta="checkout-api" href="/library/checkout">
                <PaymentLogo provider="mercadopago" /><span><strong>Pagar com Mercado Pago</strong><small>Cartão de crédito ou PIX · confirmação automática</small></span>
              </Link> : null}
          </div>
          <div id="cart-system-pix" className={paymentStyles.manualPix}>
            {cart.pix_available !== false ? cart.payment ? <>
              <h3>Pague com PIX</h3>
              {cart.payment.receiver_name ? <p>Recebedor: {cart.payment.receiver_name}</p> : null}
              <img className={styles.qr} src={cart.payment.pix_qr_code} alt="QR Code do PIX da compra" width={240} height={240} />
              <div className={styles.pixCode}><label htmlFor="pix-copy">PIX copia e cola</label><textarea id="pix-copy" readOnly value={cart.payment.pix_copy_paste} rows={3} /></div>
              <MarkinaButton type="button" variant="secondary" onClick={() => { void navigator.clipboard.writeText(cart.payment!.pix_copy_paste).then(() => setNotice("Código PIX copiado.")).catch(() => setNotice("Selecione e copie o código acima.")); }}>Copiar PIX</MarkinaButton>
              {cart.payment.pix_instructions ? <p>{cart.payment.pix_instructions}</p> : null}
              <p>Após pagar {money(cart.payment.total_cents)}, informe o pagamento para o fotógrafo conferir.</p>
              <MarkinaButton type="button" className={styles.primary} disabled={busy} onClick={() => void report()}>{busy ? "Salvando…" : "Informar pagamento"}</MarkinaButton>
            </> : !error && cart.can_prepare ? <p role="status">Preparando PIX…</p> : <p>Confira os avisos acima para continuar.</p>
              : <p>O PIX do sistema não está disponível para esta compra.</p>}
          </div>
        </section> : null}
      </div>
    </div>
  </div>;
}
