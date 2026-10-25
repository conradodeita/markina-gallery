"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { mercadoPagoState, paymentMoney, paymentRequest, type MercadoPagoPayment } from "../mercadopago";

export default function MercadoPagoResume() {
  const [payment, setPayment] = useState<MercadoPagoPayment | null>(null);
  useEffect(() => {
    let disposed = false;
    void paymentRequest<{ payment: MercadoPagoPayment | null }>("/library/mercadopago/active")
      .then((result) => { if (!disposed) setPayment(result.payment ?? null); })
      .catch(() => undefined);
    return () => { disposed = true; };
  }, []);
  if (!payment || payment.state === "prepared") return null;
  return <aside className="unified-payment" aria-label="Compra em andamento no Mercado Pago">
    <h2>Compra {payment.id.slice(0, 8)}</h2>
    <p>{mercadoPagoState[payment.state] ?? "Pagamento em conferência"} · {paymentMoney(payment.total_cents)}</p>
    <p>Estas fotos permanecem vinculadas ao pagamento iniciado.</p>
    <Link className="primary" href={`/library/checkout?payment=${payment.id}`}>Acompanhar pagamento</Link>
  </aside>;
}
