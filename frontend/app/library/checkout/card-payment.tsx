"use client";

import Script from "next/script";
import { useEffect, useRef, useState } from "react";
import type { MercadoPagoPayment } from "../mercadopago";
import styles from "./checkout.module.css";

export type CardData = {
  token: string; payment_method_id: string;
  payer: { email: string; identification: { type: string; number: string } };
};
type Controller = { unmount(): Promise<void> };
let brickLifecycle = Promise.resolve();
type BrickSettings = {
  initialization: { amount: number };
  customization: { paymentMethods: {
    types: { excluded: string[] }; minInstallments: number; maxInstallments: number;
  } };
  callbacks: {
    onReady(): void; onError(): void;
    onSubmit(data: CardData, additional?: { paymentTypeId?: string }): Promise<void>;
  };
};
declare global {
  interface Window {
    MercadoPago?: new (key: string, options: { locale: string }) => {
      bricks(): { create(type: "cardPayment", id: string, settings: BrickSettings): Promise<Controller> };
    };
  }
}

export default function CardPayment({
  payment, onSubmit,
}: { payment: MercadoPagoPayment; onSubmit(data: CardData): Promise<void> }) {
  const [sdkReady, setSdkReady] = useState(false);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");
  const controller = useRef<Controller | null>(null);

  useEffect(() => {
    if (!sdkReady || !payment.public_key || !window.MercadoPago) return;
    let disposed = false;
    const sdk = new window.MercadoPago(payment.public_key, { locale: "pt-BR" });
    const timer = window.setTimeout(() => {
      if (!controller.current) setError("Os campos seguros não carregaram. Atualize a página ou escolha PIX.");
    }, 20000);
    brickLifecycle = brickLifecycle.catch(() => undefined).then(async () => {
      if (disposed) return;
      const instance = await sdk.bricks().create("cardPayment", "mp-card-payment", {
      initialization: { amount: payment.total_cents / 100 },
      customization: { paymentMethods: {
        types: { excluded: ["debit_card", "prepaid_card"] }, minInstallments: 1, maxInstallments: 1,
      } },
      callbacks: {
        onReady: () => { if (!disposed) { setReady(true); setError(""); } },
        onError: () => { if (!disposed) setError("Confira os campos do cartão. Se não carregarem, atualize ou escolha PIX."); },
        onSubmit: async (data, additional) => {
          if (disposed) return;
          if (additional?.paymentTypeId && additional.paymentTypeId !== "credit_card") {
            setError("Escolha um cartão de crédito ou pague com PIX.");
            throw new Error("Método indisponível.");
          }
          await onSubmit(data);
        },
      },
      });
      if (disposed) await instance.unmount();
      else controller.current = instance;
    }).catch(() => {
      if (!disposed) setError("Não foi possível carregar o formulário seguro. Atualize ou escolha PIX.");
    });
    return () => {
      disposed = true; window.clearTimeout(timer);
      brickLifecycle = brickLifecycle.catch(() => undefined).then(async () => {
        const previous = controller.current; controller.current = null;
        if (previous) await previous.unmount();
      });
    };
  }, [sdkReady, payment.id, payment.public_key, payment.total_cents, onSubmit]);

  return <div className={styles.card}>
    <Script src="https://sdk.mercadopago.com/js/v2" strategy="afterInteractive"
      onReady={() => setSdkReady(true)}
      onError={() => setError("Não foi possível carregar os campos seguros. Confira sua conexão e atualize.")} />
    {!ready && !error ? <p role="status">Carregando campos seguros do cartão…</p> : null}
    {error ? <p role="alert">{error}</p> : null}
    <div id="mp-card-payment" className={styles.brick} aria-label="Pagamento seguro com cartão de crédito" />
    <small>Dados do cartão protegidos pelo Mercado Pago · pagamento em uma parcela.</small>
  </div>;
}
