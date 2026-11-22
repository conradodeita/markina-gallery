"use client";

import Image from "next/image";
import { FormEvent, useEffect, useState } from "react";

import CardPayment, { type CardData } from "../../library/checkout/card-payment";
import {
  MERCADO_PAGO_MINIMUM_TOTAL_CENTS,
  PaymentRequestError,
  mercadoPagoState,
  paymentMoney,
  paymentRequest,
} from "../../library/mercadopago";
import { MarkinaButton, StatusBadge, SurfaceCard } from "../../ui-kit";
import styles from "./credits.module.css";

export type CreditPurchase = {
  id: string;
  package_id: string;
  package_name: string;
  credit_quantity: number;
  total_cents: number;
  currency_code: string;
  method: "credit_card" | "pix" | null;
  state: string;
  active: boolean;
  public_key?: string | null;
  provider_order_id?: string | null;
  provider_payment_id?: string | null;
  order_status?: string | null;
  order_detail?: string | null;
  transaction_status?: string | null;
  transaction_detail?: string | null;
  pix_copy_paste?: string | null;
  pix_qr_code?: string | null;
  test_account?: boolean;
  created_at: string;
  confirmed_at?: string | null;
};

type Props = {
  purchase: CreditPurchase;
  onClose(): void;
  onUpdated(purchase: CreditPurchase): void;
};

type PayerAddress = {
  zip_code: string;
  street_name: string;
  street_number: string;
  neighborhood: string;
  city: string;
  state: string;
  complement: string;
};

const emptyPayerAddress: PayerAddress = {
  zip_code: "",
  street_name: "",
  street_number: "",
  neighborhood: "",
  city: "",
  state: "",
  complement: "",
};

function readPayerAddress(value: unknown): PayerAddress | null {
  if (!value || typeof value !== "object") return null;
  const address = value as Record<string, unknown>;
  const required = ["zip_code", "street_name", "street_number", "neighborhood", "city", "state"];
  if (required.some((key) => typeof address[key] !== "string")) return null;
  return {
    zip_code: address.zip_code as string,
    street_name: address.street_name as string,
    street_number: address.street_number as string,
    neighborhood: address.neighborhood as string,
    city: address.city as string,
    state: address.state as string,
    complement: typeof address.complement === "string" ? address.complement : "",
  };
}

const brazilianStates = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"];

function purchaseStatus(state: string): string {
  return mercadoPagoState[state] ?? "Compra em conferência";
}

export default function CreditPurchaseCheckout({ purchase, onClose, onUpdated }: Props) {
  const [method, setMethod] = useState<"credit_card" | "pix">(purchase.method ?? "credit_card");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [identity, setIdentity] = useState<{ name: string; email: string; identification_number: string; address: PayerAddress } | null>(null);
  const [payerAddress, setPayerAddress] = useState<PayerAddress | null>(null);
  const [identityState, setIdentityState] = useState<"loading" | "profile" | "manual">("loading");

  useEffect(() => {
    if (purchase.state !== "prepared") return;
    let cancelled = false;
    fetch("/api/admin/onboarding/checkout-identity", { credentials: "same-origin", cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) throw new Error("Checkout identity unavailable");
        const data = await response.json() as {
          name?: unknown;
          email?: unknown;
          identification_number?: unknown;
          address?: unknown;
        };
        const address = readPayerAddress(data.address);
        if (typeof data.name !== "string" || typeof data.email !== "string"
            || typeof data.identification_number !== "string" || !address) {
          throw new Error("Checkout identity incomplete");
        }
        if (cancelled) return;
        setIdentity({
          name: data.name,
          email: data.email,
          identification_number: data.identification_number,
          address,
        });
        setPayerAddress(address);
        setIdentityState("profile");
      })
      .catch(() => {
        if (cancelled) return;
        setIdentity(null);
        setPayerAddress({ ...emptyPayerAddress });
        setIdentityState("manual");
      });
    return () => { cancelled = true; };
  }, [purchase.state]);

  async function submit(data: {
    token?: string;
    payment_method_id?: string;
    email: string;
    identification_number: string;
    payer_address: PayerAddress;
  }) {
    if (busy) return;
    if (!payerAddress || Object.values(payerAddress).slice(0, 6).some((value) => !value.trim())) {
      setError("Confira o endereço do pagador antes de continuar.");
      return;
    }
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const updated = await paymentRequest<CreditPurchase>(
        `/admin/credits/purchases/${purchase.id}/submit`, {
          method,
          ...data,
        payer_address: { ...payerAddress, zip_code: payerAddress.zip_code.replace(/\D/g, ""), state: payerAddress.state.toUpperCase() },
        },
      );
      onUpdated(updated);
      if (updated.state === "confirmed") {
        setNotice("Pagamento confirmado. Os créditos já foram adicionados à carteira.");
      }
    } catch (failure) {
      if (!(failure instanceof PaymentRequestError) || failure.status >= 500) {
        onUpdated({ ...purchase, method, state: "verification_required", active: true });
        setError("O envio pode ter sido recebido. Atualize o pagamento antes de tentar novamente.");
      } else {
        setError(failure.message);
      }
    } finally {
      setBusy(false);
    }
  }

  async function submitCard(data: CardData) {
    await submit({
      token: data.token,
      payment_method_id: data.payment_method_id,
      email: data.payer.email,
      identification_number: data.payer.identification.number,
      payer_address: payerAddress!,
    });
  }

  function submitPix(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const fields = new FormData(event.currentTarget);
    void submit({
      email: String(fields.get("email") ?? ""),
      identification_number: String(fields.get("cpf") ?? "").replace(/\D/g, ""),
      payer_address: payerAddress!,
    });
  }

  async function reconcile() {
    if (busy) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const updated = await paymentRequest<CreditPurchase>(
        `/admin/credits/purchases/${purchase.id}/reconcile`, {},
      );
      onUpdated(updated);
      if (updated.state === "confirmed") {
        setNotice("Pagamento confirmado. Os créditos já foram adicionados à carteira.");
      } else {
        setNotice("Estado atualizado pela consulta ao Mercado Pago.");
      }
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Não foi possível atualizar a compra.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <SurfaceCard className={`${styles.card} ${styles.purchaseCheckout}`}>
      <div className={styles.sectionHeading}>
        <div>
          <p className="eyebrow">Checkout transparente · Mercado Pago</p>
          <h2>{purchase.package_name}</h2>
          <p>{new Intl.NumberFormat("pt-BR").format(purchase.credit_quantity)} créditos · {paymentMoney(purchase.total_cents)}</p>
        </div>
        <StatusBadge tone={purchase.state === "confirmed" ? "success" : "neutral"}>
          {purchaseStatus(purchase.state)}
        </StatusBadge>
      </div>

      {purchase.test_account ? <p className={styles.testNotice}>TESTE · Pagamento de teste, sem cobrança real.</p> : null}
      {error ? <p role="alert" className={styles.purchaseError}>{error}</p> : null}
      {notice ? <p role="status">{notice}</p> : null}

      {purchase.state === "prepared" ? <fieldset className={styles.purchasePayerAddress} disabled={busy}>
        <legend>Endereço do pagador</legend>
        <p>{identityState === "manual"
          ? "Informe os dados do pagador para esta compra; eles não alteram seu perfil."
          : "Preenchido com seu cadastro. Você pode ajustar os dados para esta compra sem alterar seu perfil."}</p>
        {identityState === "manual" ? <p role="status">
          Não foi possível preencher os dados salvos. Informe o endereço para esta compra; ele não será salvo no perfil.
        </p> : null}
        {payerAddress ? <div className={styles.purchaseAddressGrid}>
          <label>CEP<input autoComplete="postal-code" inputMode="numeric" required value={payerAddress.zip_code} onChange={(event) => setPayerAddress({ ...payerAddress, zip_code: event.target.value })} /></label>
          <label>Estado<select autoComplete="address-level1" required value={payerAddress.state} onChange={(event) => setPayerAddress({ ...payerAddress, state: event.target.value })}>
            <option value="">Selecione</option>{brazilianStates.map((state) => <option key={state} value={state}>{state}</option>)}
          </select></label>
          <label className={styles.purchaseAddressWide}>Logradouro<input autoComplete="address-line1" required value={payerAddress.street_name} onChange={(event) => setPayerAddress({ ...payerAddress, street_name: event.target.value })} /></label>
          <label>Número<input autoComplete="address-line2" required value={payerAddress.street_number} onChange={(event) => setPayerAddress({ ...payerAddress, street_number: event.target.value })} /></label>
          <label>Bairro<input required value={payerAddress.neighborhood} onChange={(event) => setPayerAddress({ ...payerAddress, neighborhood: event.target.value })} /></label>
          <label>Cidade<input autoComplete="address-level2" required value={payerAddress.city} onChange={(event) => setPayerAddress({ ...payerAddress, city: event.target.value })} /></label>
          <label className={styles.purchaseAddressWide}>Complemento<input autoComplete="address-line3" value={payerAddress.complement} onChange={(event) => setPayerAddress({ ...payerAddress, complement: event.target.value })} /></label>
        </div> : <p role="status">Carregando os dados do cadastro…</p>}
      </fieldset> : null}

      {purchase.state === "prepared" ? (
        purchase.total_cents < MERCADO_PAGO_MINIMUM_TOTAL_CENTS ? (
          <p role="alert" className={styles.purchaseError}>
            O Mercado Pago aceita compras a partir de {paymentMoney(MERCADO_PAGO_MINIMUM_TOTAL_CENTS)}.
          </p>
        ) : (
          <>
            <fieldset className={styles.purchaseMethods} disabled={busy}>
              <legend>Como deseja pagar?</legend>
              <label data-selected={method === "credit_card"}>
                <input type="radio" name="credit-purchase-method" checked={method === "credit_card"}
                  onChange={() => setMethod("credit_card")} />
                Cartão de crédito · Mercado Pago
              </label>
              <label data-selected={method === "pix"}>
                <input type="radio" name="credit-purchase-method" checked={method === "pix"}
                  onChange={() => setMethod("pix")} />
                PIX Mercado Pago
              </label>
            </fieldset>
            {method === "credit_card" ? (
              purchase.public_key ? (
                <CardPayment payment={{ ...purchase, payer: identity ? { email: identity.email, identification: { type: "CPF", number: identity.identification_number } } : undefined }} onSubmit={submitCard} />
              ) : (
                <p role="alert" className={styles.purchaseError}>Os campos seguros do cartão estão indisponíveis no momento.</p>
              )
            ) : (
              <form className={styles.purchasePixForm} onSubmit={submitPix}>
                <label>E-mail para o pagamento<input name="email" type="email" autoComplete="email" required maxLength={254} defaultValue={identity?.email ?? ""} /></label>
                <label>CPF do pagador<input name="cpf" inputMode="numeric" autoComplete="off" required pattern="[0-9]{11}" maxLength={11} defaultValue={identity?.identification_number ?? ""} /></label>
                <MarkinaButton type="submit" disabled={busy}>
                  {busy ? "Preparando pagamento…" : `Gerar PIX de ${paymentMoney(purchase.total_cents)}`}
                </MarkinaButton>
              </form>
            )}
          </>
        )
      ) : (
        <div className={styles.purchaseResult} aria-live="polite">
          <p>{purchase.method === "pix" ? "PIX Mercado Pago" : purchase.method === "credit_card" ? "Cartão · Mercado Pago" : "Compra de créditos"}</p>
          {purchase.state === "confirmed" ? <p>Pagamento recebido. Confira o novo saldo e o lançamento no histórico da carteira.</p> : null}
          {purchase.state === "pending" && purchase.pix_copy_paste ? (
            <>
              {purchase.pix_qr_code ? <Image src={purchase.pix_qr_code} alt="QR Code PIX Mercado Pago"
                width={240} height={240} unoptimized /> : null}
              <label>PIX copia e cola<textarea readOnly value={purchase.pix_copy_paste} rows={4} /></label>
              <MarkinaButton type="button" variant="secondary" onClick={() => void navigator.clipboard.writeText(
                purchase.pix_copy_paste!).then(() => setNotice("PIX copiado.")).catch(
                () => setNotice("Selecione e copie o código acima."))}>Copiar PIX</MarkinaButton>
            </>
          ) : null}
          {purchase.active && purchase.state !== "prepared" ? (
            <MarkinaButton type="button" variant="secondary" disabled={busy} onClick={() => void reconcile()}>
              {busy ? "Consultando…" : "Atualizar pagamento"}
            </MarkinaButton>
          ) : null}
        </div>
      )}

      <div className={styles.purchaseActions}>
        <MarkinaButton type="button" variant="secondary" onClick={onClose}>Fechar checkout</MarkinaButton>
      </div>
    </SurfaceCard>
  );
}
