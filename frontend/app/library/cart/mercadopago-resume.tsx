"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { mercadoPagoState, paymentMoney, paymentRequest, type MercadoPagoPayment } from "../mercadopago";

export default function MercadoPagoResume() {
  const [payments, setPayments] = useState<MercadoPagoPayment[]>([]);
  useEffect(() => {
    let disposed = false;
    void paymentRequest<{ payments: MercadoPagoPayment[] }>("/library/mercadopago/active")
      .then((result) => { if (!disposed) setPayments(result.payments ?? []); })
      .catch(() => undefined);
    return () => { disposed = true; };
  }, []);
  const submitted = payments.filter((payment) => payment.state !== "prepared");
  if (!submitted.length) return null;
  return <section aria-label="Compras em andamento no Mercado Pago">
    {submitted.map((payment) => <aside className="unified-payment" key={payment.id}>
      <h2>Compra {payment.id.slice(0, 8)}</h2>
      <p>{mercadoPagoState[payment.state] ?? "Pagamento em conferência"} · {paymentMoney(payment.total_cents)}</p>
      <p>Estas fotos permanecem vinculadas a este pagamento.</p>
      <Link className="primary" href={`/library/checkout?payment=${payment.id}`}>Acompanhar pagamento</Link>
    </aside>)}
  </section>;
}
