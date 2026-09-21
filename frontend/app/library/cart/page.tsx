"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { PurchasePreview } from "../../purchase-preview";
import { notifyCartChanged } from "../../client-navigation";
import { SelectionDeadline } from "../../selection-deadline";
import { SystemState } from "../../ui-kit";

type CartGroup = { gallery_id: string; parent_gallery_id: string; name: string; quantity: number;
  legacy_review_url?: string | null;
  total_cents: number | null; error: string | null; browse_url: string; selection_expires_at: string | null;
  items: Array<{ id: string; name: string; folder_name: string | null; preview_url: string }> };
type Payment = { id: string; revision: string; total_cents: number; pix_copy_paste: string;
  pix_qr_code: string; pix_instructions: string | null; receiver_name: string | null };
type Cart = { groups: CartGroup[]; quantity: number; can_prepare: boolean; total_cents: number | null; payment?: Payment };
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

  if (reported) return <section className="unified-cart"><h1>Pagamento informado</h1><p>Seu pagamento aguarda a confirmação do fotógrafo.</p><Link className="primary" href={`/library/purchases#payment-${reported}`}>Ver compra</Link><Link href="/library">Continuar nas galerias</Link></section>;
  return <section className="unified-cart">
    <h1>Revise suas fotos e faça o PIX</h1>
    {error ? <div role="alert"><p>{error}</p><button type="button" className="secondary" disabled={busy} onClick={() => void refresh()}>Atualizar revisão</button></div> : null}
    {!cart && !error ? <SystemState tone="loading" title="Carregando carrinho" detail="Buscando suas fotos selecionadas." /> : null}
    {cart?.quantity === 0 ? <><p>Seu carrinho está vazio.</p><Link className="primary" href="/library">Escolher fotos</Link></> : null}
    {cart?.groups.map((group) => <section className="unified-cart-group" key={group.gallery_id} aria-label={`Fotos de ${group.name}`}>
      <div className="section-heading"><h2>{group.name}</h2><span>{group.quantity} foto(s){group.total_cents !== null ? ` · ${money(group.total_cents)}` : ""}</span></div>
      <SelectionDeadline expiresAt={group.selection_expires_at} />
      {group.error ? <p role="alert">{group.error}</p> : null}
      <div className="unified-cart-photos">{group.items.map((photo) => <figure key={photo.id}>
        <PurchasePreview path={photo.preview_url} name={photo.name} />
        <figcaption><strong>{photo.name}</strong>{photo.folder_name ? <small>{photo.folder_name}</small> : null}</figcaption>
        <button type="button" className="secondary" disabled={busy} aria-label={`Remover ${photo.name} de ${group.name}`} onClick={() => void remove(group, photo.id)}>Remover</button>
      </figure>)}</div>
      <div className="dashboard-actions"><Link href={group.browse_url}>Continuar escolhendo</Link><button type="button" className="secondary" disabled={busy} onClick={() => void remove(group)}>Remover seleção de {group.name}</button></div>
      {error && group.legacy_review_url ? <Link href={group.legacy_review_url}>Retomar pagamento anterior de {group.name}</Link> : null}
    </section>)}
    {cart && cart.quantity > 0 ? <section className="unified-payment" aria-label="Pagamento único">
      <h2>Total {cart.total_cents === null ? "a conferir" : money(cart.total_cents)}</h2>
      <p>{cart.quantity} foto(s)</p>
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
      {notice ? <p role="status">{notice}</p> : null}
    </section> : null}
  </section>;
}
