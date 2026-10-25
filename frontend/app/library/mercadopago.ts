export type MercadoPagoPayment = {
  id: string; provider: "mercadopago"; method: "credit_card" | "pix"; state: string;
  active: boolean; total_cents: number; cart_revision: string; public_key?: string | null;
  pix_copy_paste?: string | null; pix_qr_code?: string | null; can_cancel: boolean;
  provider_order_id?: string | null; provider_payment_id?: string | null;
  order_status?: string | null; order_detail?: string | null;
  transaction_status?: string | null; transaction_detail?: string | null;
  test_account?: boolean;
  items: Array<{ name: string; unit_price_cents: number; order_id: string }>;
};

export const mercadoPagoState: Record<string, string> = {
  prepared: "Confira os dados para pagar",
  sending: "Enviando pagamento",
  initiated: "Pagamento iniciado",
  pending: "Aguardando pagamento",
  processing: "Pagamento em processamento",
  confirmed: "Pagamento confirmado",
  rejected: "Pagamento recusado",
  canceled: "Pagamento cancelado",
  expired: "Pagamento expirado",
  refunded: "Pagamento reembolsado",
  partially_refunded: "Pagamento parcialmente reembolsado",
  charged_back: "Pagamento contestado",
  verification_required: "Verificando pagamento",
  duplicate_review: "Pagamento em conferência com o fotógrafo",
  abandoned: "Checkout encerrado",
};

export const paymentMoney = (cents: number) => (cents / 100).toLocaleString(
  "pt-BR", { style: "currency", currency: "BRL" });

export async function paymentRequest<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`/api${path}`, {
    credentials: "same-origin", cache: "no-store",
    ...(body !== undefined ? {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    } : {}),
  });
  const result = await response.json().catch(() => null);
  if (!response.ok) throw new Error(
    typeof result?.detail === "string" ? result.detail : "Não foi possível consultar o pagamento. Tente atualizar.");
  return result as T;
}
