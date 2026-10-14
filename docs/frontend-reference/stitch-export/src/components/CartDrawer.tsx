import React, { useState } from "react";
import { Gallery, Photo, CustomerUser } from "../types";
import {
  X,
  Trash2,
  ShoppingBag,
  TrendingDown,
  ArrowRight,
  Sparkles,
  ShieldCheck,
  User,
  Phone,
  CheckCircle2,
  Lock,
} from "lucide-react";
import { calculateProgressivePrice, formatCurrencyBRL } from "../utils/pricing";

interface CartDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  gallery: Gallery;
  cartPhotos: Photo[];
  onRemovePhoto: (photoId: string) => void;
  onClearCart: () => void;
  currentUser: CustomerUser;
  onProceedToCheckout: (customerName: string, customerPhone: string) => void;
  onSelectAllGalleryPhotos: () => void;
}

export const CartDrawer: React.FC<CartDrawerProps> = ({
  isOpen,
  onClose,
  gallery,
  cartPhotos,
  onRemovePhoto,
  onClearCart,
  currentUser,
  onProceedToCheckout,
  onSelectAllGalleryPhotos,
}) => {
  const [customerName, setCustomerName] = useState(currentUser.name || "");
  const [customerPhone, setCustomerPhone] = useState(currentUser.phone || "");

  if (!isOpen) return null;

  const progressive = calculateProgressivePrice(
    cartPhotos.length,
    undefined,
    gallery.basePhotoPrice,
  );

  const handleCheckoutSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!customerPhone || customerPhone.length < 10) {
      alert(
        "Por favor, informe um número de WhatsApp válido para envio do link das fotos.",
      );
      return;
    }
    if (!customerName.trim()) {
      alert("Por favor, informe seu nome para o pedido.");
      return;
    }
    onProceedToCheckout(customerName.trim(), customerPhone.trim());
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-xs flex justify-end">
      <div className="bg-[#FBF9F9] w-full max-w-lg h-full shadow-2xl flex flex-col justify-between border-l border-[#E2E2E2] animate-slide-in-right">
        {/* Header */}
        <div className="p-5 sm:p-6 bg-white border-b border-[#E2E2E2] flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-[#1B1C1C] text-white rounded-xs flex items-center justify-center">
              <ShoppingBag className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-display text-lg sm:text-xl font-bold text-[#1B1C1C]">
                Carrinho de Fotos Digitais
              </h3>
              <p className="text-[10px] uppercase tracking-wider text-[#545F72]">
                {gallery.title}
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 text-[#545F72] hover:text-[#1B1C1C] rounded-xs hover:bg-[#EFEAEA] transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 p-5 sm:p-6 overflow-y-auto space-y-6">
          {cartPhotos.length === 0 ? (
            <div className="py-16 text-center space-y-4">
              <div className="w-16 h-16 bg-[#EFEAEA] text-[#747878] rounded-full flex items-center justify-center mx-auto">
                <ShoppingBag className="w-8 h-8 stroke-[1.2]" />
              </div>
              <div>
                <h4 className="font-display text-base font-bold text-[#1B1C1C]">
                  Seu carrinho está vazio
                </h4>
                <p className="text-xs text-[#545F72] mt-1 max-w-xs mx-auto">
                  Adicione fotos individuais na galeria para aproveitar o
                  desconto progressivo.
                </p>
              </div>

              <button
                type="button"
                onClick={onSelectAllGalleryPhotos}
                className="px-4 py-2.5 bg-[#1B1C1C] text-white text-xs font-semibold uppercase tracking-wider rounded-xs cursor-pointer"
              >
                Selecionar Todas as {gallery.photos.length} Fotos do Evento
              </button>
            </div>
          ) : (
            <>
              {/* Progressive Pricing Incentive Banner */}
              <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xs space-y-2.5">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-emerald-950 flex items-center gap-1.5">
                    <TrendingDown className="w-4 h-4 text-emerald-700" />
                    Faixa Ativa: {progressive.currentTier.label}
                  </span>
                  <span className="px-2 py-0.5 bg-emerald-700 text-white font-mono font-bold text-[10px] rounded-xs">
                    {formatCurrencyBRL(progressive.unitPrice)} / foto
                  </span>
                </div>

                {progressive.nextTier &&
                progressive.photosNeededForNextTier > 0 ? (
                  <div>
                    <p className="text-[11px] text-emerald-800 leading-snug">
                      Falta apenas{" "}
                      <strong>
                        {progressive.photosNeededForNextTier} foto(s)
                      </strong>{" "}
                      para desbloquear a faixa de{" "}
                      <strong>
                        {formatCurrencyBRL(progressive.nextTierUnitPrice)}/foto
                      </strong>{" "}
                      ({progressive.nextTier.badge})!
                    </p>
                    <div className="w-full h-1.5 bg-emerald-200 rounded-full mt-2 overflow-hidden">
                      <div
                        className="h-full bg-emerald-700 transition-all duration-300"
                        style={{
                          width: `${Math.min(
                            100,
                            (cartPhotos.length /
                              (progressive.nextTier.minQty || 20)) *
                              100,
                          )}%`,
                        }}
                      />
                    </div>
                  </div>
                ) : (
                  <p className="text-[11px] text-emerald-800 font-semibold">
                    🎉 Parabéns! Você atingiu a melhor faixa de desconto
                    progressivo (52% OFF)!
                  </p>
                )}
              </div>

              {/* Items List */}
              <div className="space-y-3">
                <div className="flex items-center justify-between text-xs text-[#545F72] border-b border-[#E2E2E2] pb-2">
                  <span className="font-semibold uppercase tracking-wider">
                    Fotos Selecionadas ({cartPhotos.length})
                  </span>
                  <button
                    type="button"
                    onClick={onClearCart}
                    className="text-red-600 hover:text-red-800 text-[11px] underline cursor-pointer"
                  >
                    Esvaziar Carrinho
                  </button>
                </div>

                <div className="space-y-2.5 max-h-56 overflow-y-auto pr-1">
                  {cartPhotos.map((photo) => (
                    <div
                      key={photo.id}
                      className="p-2.5 bg-white border border-[#E2E2E2] rounded-xs flex items-center justify-between gap-3 shadow-2xs"
                    >
                      <div className="flex items-center gap-3">
                        <img
                          src={photo.url}
                          alt={photo.title}
                          className="w-12 h-12 rounded-xs object-cover border border-[#E2E2E2] shrink-0"
                        />
                        <div className="min-w-0">
                          <p className="text-xs font-bold text-[#1B1C1C] truncate max-w-[180px] sm:max-w-[220px]">
                            {photo.title}
                          </p>
                          <p className="text-[10px] text-[#747878] uppercase">
                            {photo.category} • Alta Resolução Digital
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center gap-3">
                        <span className="font-mono text-xs font-bold text-[#1B1C1C]">
                          {formatCurrencyBRL(progressive.unitPrice)}
                        </span>
                        <button
                          type="button"
                          onClick={() => onRemovePhoto(photo.id)}
                          className="text-[#747878] hover:text-red-600 p-1 transition-colors cursor-pointer"
                          title="Remover"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Customer Contact for Delivery */}
              <form
                id="cart-form"
                onSubmit={handleCheckoutSubmit}
                className="p-4 bg-white border border-[#E2E2E2] rounded-xs space-y-3"
              >
                <span className="text-xs font-bold uppercase tracking-wider text-[#1B1C1C] block">
                  Dados para Envio do Link Digital
                </span>

                <div>
                  <label className="block text-[11px] text-[#545F72] mb-1 font-medium">
                    Seu Nome Completo
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="Ex: Marina Alencar"
                    value={customerName}
                    onChange={(e) => setCustomerName(e.target.value)}
                    className="w-full px-3 py-2 bg-[#FBF9F9] border border-[#E2E2E2] text-xs rounded-xs text-[#1B1C1C] focus:outline-none focus:border-[#1B1C1C]"
                  />
                </div>

                <div>
                  <label className="block text-[11px] text-[#545F72] mb-1 font-medium">
                    WhatsApp para Recebimento das Fotos
                  </label>
                  <input
                    type="tel"
                    required
                    placeholder="(11) 98842-1920"
                    value={customerPhone}
                    onChange={(e) => setCustomerPhone(e.target.value)}
                    className="w-full px-3 py-2 bg-[#FBF9F9] border border-[#E2E2E2] text-xs font-mono rounded-xs text-[#1B1C1C] focus:outline-none focus:border-[#1B1C1C]"
                  />
                </div>
              </form>
            </>
          )}
        </div>

        {/* Footer Summary & Checkout Button */}
        {cartPhotos.length > 0 && (
          <div className="p-5 sm:p-6 bg-white border-t border-[#E2E2E2] space-y-4">
            <div className="space-y-1.5 text-xs text-[#545F72]">
              <div className="flex justify-between">
                <span>
                  Subtotal ({cartPhotos.length} fotos x{" "}
                  {formatCurrencyBRL(gallery.basePhotoPrice)})
                </span>
                <span className="font-mono">
                  {formatCurrencyBRL(progressive.originalAmount)}
                </span>
              </div>

              {progressive.savings > 0 && (
                <div className="flex justify-between text-emerald-700 font-medium">
                  <span>Desconto Progressivo Aplicado</span>
                  <span className="font-mono">
                    - {formatCurrencyBRL(progressive.savings)}
                  </span>
                </div>
              )}

              <div className="flex justify-between items-baseline pt-2 border-t border-[#E2E2E2] text-sm sm:text-base font-bold text-[#1B1C1C]">
                <span>Total a Pagar (PIX):</span>
                <span className="font-mono text-xl text-emerald-800">
                  {formatCurrencyBRL(progressive.totalAmount)}
                </span>
              </div>
            </div>

            <button
              type="submit"
              form="cart-form"
              className="w-full py-3.5 bg-[#1B1C1C] text-white hover:bg-[#2A2A2A] text-xs font-semibold uppercase tracking-widest rounded-xs flex items-center justify-center gap-2 cursor-pointer transition-colors shadow-md"
            >
              <span>Gerar Pagamento PIX Instantâneo</span>
              <ArrowRight className="w-4 h-4" />
            </button>

            <div className="flex items-center justify-center gap-2 text-[10px] text-[#747878] uppercase tracking-wider">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
              <span>Liberação Imediata • Chave PIX Segura • 100% Digital</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
