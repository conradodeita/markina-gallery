import React, { useState } from "react";
import { CartItem } from "../types";
import {
  X,
  Trash2,
  ShoppingBag,
  ArrowRight,
  Check,
  Tag,
  ShieldCheck,
  Truck,
  Sparkles,
  CreditCard,
  QrCode,
} from "lucide-react";
import confetti from "canvas-confetti";

interface CartDrawerProps {
  items: CartItem[];
  onClose: () => void;
  onUpdateQuantity: (id: string, delta: number) => void;
  onRemoveItem: (id: string) => void;
  onClearCart: () => void;
}

export const CartDrawer: React.FC<CartDrawerProps> = ({
  items,
  onClose,
  onUpdateQuantity,
  onRemoveItem,
  onClearCart,
}) => {
  const [couponCode, setCouponCode] = useState("");
  const [appliedCoupon, setAppliedCoupon] = useState<{
    code: string;
    discountPercent: number;
  } | null>(null);
  const [couponError, setCouponError] = useState("");
  const [checkoutStep, setCheckoutStep] = useState<
    "cart" | "checkout" | "success"
  >("cart");
  const [paymentMethod, setPaymentMethod] = useState<"pix" | "card">("pix");

  const subtotal = items.reduce(
    (acc, item) => acc + item.price * item.quantity,
    0,
  );
  const discountAmount = appliedCoupon
    ? (subtotal * appliedCoupon.discountPercent) / 100
    : 0;
  const shipping =
    subtotal > 0
      ? subtotal > 1000 ||
        (appliedCoupon && appliedCoupon.discountPercent === 100)
        ? 0
        : 45
      : 0;
  const finalTotal = Math.max(0, subtotal - discountAmount + shipping);

  const handleApplyCoupon = (e: React.FormEvent) => {
    e.preventDefault();
    setCouponError("");
    const code = couponCode.trim().toUpperCase();

    if (code === "CASAL2023" || code === "MARINA2023") {
      setAppliedCoupon({ code: code, discountPercent: 100 });
      setCouponError("");
    } else if (code === "FINEART20") {
      setAppliedCoupon({ code: code, discountPercent: 20 });
      setCouponError("");
    } else {
      setCouponError('Cupom inválido. Experimente "CASAL2023" ou "FINEART20".');
    }
  };

  const handleCompleteOrder = () => {
    confetti({
      particleCount: 100,
      spread: 70,
      origin: { y: 0.6 },
    });
    setCheckoutStep("success");
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex justify-end">
      <div className="bg-[#FBF9F9] w-full max-w-lg h-full shadow-2xl flex flex-col justify-between border-l border-[#E2E2E2] animate-fade-in-up">
        {/* Header */}
        <div className="p-6 bg-white border-b border-[#E2E2E2] flex items-center justify-between">
          <div className="flex items-center gap-3">
            <ShoppingBag className="w-5 h-5 text-[#1B1C1C] stroke-[1.5]" />
            <h3 className="font-display text-xl font-bold text-[#1B1C1C]">
              Carrinho de Impressões Fine Art
            </h3>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 text-[#545F72] hover:text-[#1B1C1C] rounded-xs hover:bg-[#EFEAEA] transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 p-6 overflow-y-auto">
          {checkoutStep === "success" ? (
            <div className="text-center py-12 space-y-4">
              <div className="w-16 h-16 bg-emerald-100 text-emerald-800 rounded-full flex items-center justify-center mx-auto mb-4">
                <Check className="w-8 h-8" />
              </div>
              <h4 className="font-display text-2xl font-bold text-[#1B1C1C]">
                Pedido Confirmado com Sucesso!
              </h4>
              <p className="text-xs text-[#545F72] max-w-xs mx-auto leading-relaxed">
                Seu pedido foi registrado no ateliê{" "}
                <strong>Markina Studios</strong>. Nossos impressores iniciarão a
                calibração de cor e preparo artesanal.
              </p>
              <div className="p-4 bg-[#F5F3F3] border border-[#E2E2E2] rounded-xs text-xs text-left space-y-2 mt-6">
                <p>
                  <strong>Código do Pedido:</strong> #MK-88219
                </p>
                <p>
                  <strong>Prazo Estimado de Produção:</strong> 5 a 8 dias úteis
                </p>
                <p>
                  <strong>Entrega com Seguro:</strong> Sedex Especial com
                  Embalagem Rígida
                </p>
              </div>
              <button
                onClick={() => {
                  onClearCart();
                  onClose();
                }}
                className="w-full mt-6 py-3.5 bg-[#000000] text-white text-xs font-semibold uppercase tracking-widest rounded-xs"
              >
                Voltar à Galeria
              </button>
            </div>
          ) : checkoutStep === "checkout" ? (
            <div className="space-y-6">
              <div className="pb-4 border-b border-[#E2E2E2]">
                <span className="text-[10px] uppercase tracking-widest text-[#545F72] font-semibold">
                  Passo Final
                </span>
                <h4 className="font-display text-lg font-bold text-[#1B1C1C]">
                  Dados de Entrega &amp; Pagamento
                </h4>
              </div>

              {/* Delivery Address Form */}
              <div className="space-y-3">
                <label className="block text-xs font-semibold uppercase tracking-wider text-[#1B1C1C]">
                  Endereço de Entrega dos Quadros
                </label>
                <input
                  type="text"
                  defaultValue="Marina & Ricardo"
                  placeholder="Nome do Destinatário"
                  className="w-full p-2.5 bg-white border border-[#C4C7C7] text-xs text-[#1B1C1C] rounded-xs"
                />
                <input
                  type="text"
                  defaultValue="Av. Brigadeiro Faria Lima, 2400 - Apto 142"
                  placeholder="Rua, Número e Complemento"
                  className="w-full p-2.5 bg-white border border-[#C4C7C7] text-xs text-[#1B1C1C] rounded-xs"
                />
                <div className="grid grid-cols-2 gap-2">
                  <input
                    type="text"
                    defaultValue="São Paulo - SP"
                    placeholder="Cidade / UF"
                    className="p-2.5 bg-white border border-[#C4C7C7] text-xs text-[#1B1C1C] rounded-xs"
                  />
                  <input
                    type="text"
                    defaultValue="01451-000"
                    placeholder="CEP"
                    className="p-2.5 bg-white border border-[#C4C7C7] text-xs text-[#1B1C1C] rounded-xs"
                  />
                </div>
              </div>

              {/* Payment Method */}
              <div className="space-y-3 pt-4 border-t border-[#E2E2E2]">
                <label className="block text-xs font-semibold uppercase tracking-wider text-[#1B1C1C]">
                  Forma de Pagamento
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={() => setPaymentMethod("pix")}
                    className={`p-3 border rounded-xs flex items-center justify-center gap-2 text-xs font-semibold cursor-pointer ${
                      paymentMethod === "pix"
                        ? "border-[#1B1C1C] bg-white ring-1 ring-[#1B1C1C]"
                        : "border-[#E2E2E2] bg-white"
                    }`}
                  >
                    <QrCode className="w-4 h-4 text-[#1B1C1C]" />
                    PIX Instantâneo
                  </button>

                  <button
                    onClick={() => setPaymentMethod("card")}
                    className={`p-3 border rounded-xs flex items-center justify-center gap-2 text-xs font-semibold cursor-pointer ${
                      paymentMethod === "card"
                        ? "border-[#1B1C1C] bg-white ring-1 ring-[#1B1C1C]"
                        : "border-[#E2E2E2] bg-white"
                    }`}
                  >
                    <CreditCard className="w-4 h-4 text-[#1B1C1C]" />
                    Cartão de Crédito
                  </button>
                </div>

                {appliedCoupon && appliedCoupon.discountPercent === 100 && (
                  <div className="p-3 bg-emerald-50 text-emerald-800 border border-emerald-200 rounded-xs text-xs">
                    ✓ Cupom <strong>{appliedCoupon.code}</strong> aplicado:
                    Cortesia do pacote dos noivos (100% de desconto).
                  </div>
                )}
              </div>
            </div>
          ) : items.length === 0 ? (
            <div className="text-center py-20">
              <ShoppingBag className="w-12 h-12 text-[#747878] mx-auto mb-3 stroke-[1.5]" />
              <h4 className="font-display text-lg font-semibold text-[#1B1C1C]">
                Seu carrinho está vazio
              </h4>
              <p className="text-xs text-[#545F72] mt-1 mb-6">
                Explore a galeria e clique no ícone de sacola ou "Pedir
                Impressão" em qualquer fotografia para encomendar quadros Fine
                Art.
              </p>
              <button
                onClick={onClose}
                className="px-5 py-2.5 bg-[#1B1C1C] text-white text-xs uppercase tracking-wider font-medium rounded-xs"
              >
                Explorar Fotografias
              </button>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Item List */}
              <div className="space-y-4">
                {items.map((item) => (
                  <div
                    key={item.id}
                    className="p-3.5 bg-white border border-[#E2E2E2] rounded-xs flex gap-3 relative group"
                  >
                    <img
                      src={item.photoUrl}
                      alt={item.photoTitle}
                      className="w-20 h-20 object-cover rounded-xs border border-gray-100 shrink-0"
                    />

                    <div className="flex-1 flex flex-col justify-between">
                      <div>
                        <div className="flex items-start justify-between">
                          <h4 className="font-display text-xs font-bold text-[#1B1C1C] line-clamp-1">
                            {item.photoTitle}
                          </h4>
                          <button
                            onClick={() => onRemoveItem(item.id)}
                            className="text-[#747878] hover:text-rose-600 p-1 transition-colors"
                            title="Remover item"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>

                        <p className="text-[11px] text-[#545F72] mt-0.5">
                          {item.sizeLabel}
                        </p>
                        {item.frameLabel && (
                          <p className="text-[10px] text-[#747878]">
                            {item.frameLabel}
                          </p>
                        )}
                        {item.paperLabel && (
                          <p className="text-[10px] text-[#747878]">
                            {item.paperLabel}
                          </p>
                        )}
                      </div>

                      <div className="flex items-center justify-between mt-2 pt-2 border-t border-gray-100">
                        {/* Quantity */}
                        <div className="flex items-center border border-[#C4C7C7] rounded-xs text-[11px]">
                          <button
                            onClick={() => onUpdateQuantity(item.id, -1)}
                            className="px-2 py-0.5 hover:bg-[#F5F3F3]"
                          >
                            -
                          </button>
                          <span className="px-2 py-0.5 font-bold">
                            {item.quantity}
                          </span>
                          <button
                            onClick={() => onUpdateQuantity(item.id, 1)}
                            className="px-2 py-0.5 hover:bg-[#F5F3F3]"
                          >
                            +
                          </button>
                        </div>

                        <span className="font-semibold text-xs text-[#1B1C1C]">
                          R${" "}
                          {(item.price * item.quantity)
                            .toFixed(2)
                            .replace(".", ",")}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Coupon Form */}
              <form onSubmit={handleApplyCoupon} className="pt-2">
                <label className="block text-[11px] font-semibold uppercase tracking-wider text-[#545F72] mb-1.5 flex items-center gap-1.5">
                  <Tag className="w-3 h-3" />
                  Cupom de Cortesia ou Desconto
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="Ex: CASAL2023"
                    value={couponCode}
                    onChange={(e) => setCouponCode(e.target.value)}
                    className="flex-1 p-2 bg-white border border-[#C4C7C7] focus:border-[#1B1C1C] text-xs uppercase font-mono text-[#1B1C1C] rounded-xs focus:outline-none"
                  />
                  <button
                    type="submit"
                    className="px-3 py-2 bg-[#1B1C1C] text-white text-xs font-semibold uppercase tracking-wider rounded-xs cursor-pointer hover:bg-[#2A2A2A]"
                  >
                    Aplicar
                  </button>
                </div>
                {couponError && (
                  <p className="text-[11px] text-rose-600 mt-1">
                    {couponError}
                  </p>
                )}
                {appliedCoupon && (
                  <p className="text-[11px] text-emerald-700 mt-1 flex items-center gap-1">
                    <Check className="w-3.5 h-3.5" />
                    Cupom <strong>{appliedCoupon.code}</strong> (
                    {appliedCoupon.discountPercent}% OFF) ativado!
                  </p>
                )}
              </form>

              {/* Features notes */}
              <div className="space-y-2 pt-2 text-[11px] text-[#545F72]">
                <div className="flex items-center gap-2">
                  <Truck className="w-3.5 h-3.5 text-[#1B1C1C]" />
                  <span>
                    Embalagem reforçada anti-impacto com seguro total.
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-3.5 h-3.5 text-[#1B1C1C]" />
                  <span>
                    Impressão com tintas pigmentadas minerais Ultrachrome PRO.
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer with Totals and Action */}
        {items.length > 0 && checkoutStep !== "success" && (
          <div className="p-6 bg-white border-t border-[#E2E2E2] space-y-4">
            <div className="space-y-1.5 text-xs font-sans-body">
              <div className="flex justify-between text-[#545F72]">
                <span>Subtotal:</span>
                <span>R$ {subtotal.toFixed(2).replace(".", ",")}</span>
              </div>

              {discountAmount > 0 && (
                <div className="flex justify-between text-emerald-700 font-medium">
                  <span>Desconto ({appliedCoupon?.code}):</span>
                  <span>
                    - R$ {discountAmount.toFixed(2).replace(".", ",")}
                  </span>
                </div>
              )}

              <div className="flex justify-between text-[#545F72]">
                <span>Frete com Seguro:</span>
                <span>
                  {shipping === 0
                    ? "Grátis"
                    : `R$ ${shipping.toFixed(2).replace(".", ",")}`}
                </span>
              </div>

              <div className="flex justify-between pt-2 border-t border-gray-200 text-sm font-bold text-[#1B1C1C]">
                <span>Total Final:</span>
                <span className="font-display text-xl font-bold">
                  R$ {finalTotal.toFixed(2).replace(".", ",")}
                </span>
              </div>
            </div>

            {checkoutStep === "cart" ? (
              <button
                onClick={() => setCheckoutStep("checkout")}
                className="w-full py-4 bg-[#000000] text-white hover:bg-[#2A2A2A] active:scale-[0.99] text-xs font-semibold uppercase tracking-widest rounded-xs flex items-center justify-center gap-2 transition-all cursor-pointer shadow-md"
              >
                <span>Prosseguir para Envio</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            ) : (
              <div className="flex gap-2">
                <button
                  onClick={() => setCheckoutStep("cart")}
                  className="px-4 py-3.5 border border-[#C4C7C7] text-[#1B1C1C] text-xs uppercase tracking-wider font-semibold rounded-xs hover:bg-[#F5F3F3]"
                >
                  Voltar
                </button>
                <button
                  onClick={handleCompleteOrder}
                  className="flex-1 py-3.5 bg-[#000000] text-white hover:bg-[#2A2A2A] text-xs font-semibold uppercase tracking-widest rounded-xs flex items-center justify-center gap-2 transition-all cursor-pointer shadow-md"
                >
                  <Check className="w-4 h-4 text-emerald-400" />
                  <span>
                    Confirmar Pedido (R${" "}
                    {finalTotal.toFixed(2).replace(".", ",")})
                  </span>
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
