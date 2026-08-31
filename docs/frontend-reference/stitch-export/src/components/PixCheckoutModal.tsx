import React, { useState, useEffect } from "react";
import { Order } from "../types";
import {
  X,
  Copy,
  Check,
  Upload,
  Clock,
  ShieldCheck,
  MessageSquare,
  Sparkles,
  QrCode,
  FileText,
  AlertCircle,
  ArrowRight,
} from "lucide-react";
import { formatCurrencyBRL } from "../utils/pricing";

interface PixCheckoutModalProps {
  order: Order;
  onClose: () => void;
  onConfirmOrderPayment: (orderId: string, proofName?: string) => void;
  onViewOrderStatus: (orderId: string) => void;
}

export const PixCheckoutModal: React.FC<PixCheckoutModalProps> = ({
  order,
  onClose,
  onConfirmOrderPayment,
  onViewOrderStatus,
}) => {
  const [copiedPix, setCopiedPix] = useState(false);
  const [timeLeftSeconds, setTimeLeftSeconds] = useState(15 * 60); // 15 min
  const [proofFile, setProofFile] = useState<string | null>(null);
  const [isSimulating, setIsSimulating] = useState(false);

  useEffect(() => {
    const timer = setInterval(() => {
      setTimeLeftSeconds((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const formatTimer = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  const handleCopyPix = () => {
    navigator.clipboard.writeText(order.pixCode);
    setCopiedPix(true);
    setTimeout(() => setCopiedPix(false), 2500);
  };

  const handleProofChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setProofFile(file.name);
    }
  };

  const handleSimulateInstantPayment = () => {
    setIsSimulating(true);
    setTimeout(() => {
      onConfirmOrderPayment(
        order.id,
        proofFile || "comprovante_pix_instantaneo.pdf",
      );
      setIsSimulating(false);
      onViewOrderStatus(order.id);
      onClose();
    }, 1200);
  };

  const handleNotifyPhotographerWhatsApp = () => {
    const msg = encodeURIComponent(
      `Olá Markina Studios! Realizei o pagamento PIX no valor de ${formatCurrencyBRL(
        order.totalAmount,
      )} referente ao pedido #${order.id} (${order.totalPhotos} fotos de ${order.galleryTitle}). Meu nome: ${
        order.customerName
      }.`,
    );
    window.open(`https://wa.me/5511988421920?text=${msg}`, "_blank");
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-xs flex items-center justify-center p-3 sm:p-6 overflow-y-auto">
      <div className="bg-[#FBF9F9] border border-[#E2E2E2] rounded-xs w-full max-w-lg shadow-2xl overflow-hidden animate-fade-in-up my-auto">
        {/* Header */}
        <div className="bg-white border-b border-[#E2E2E2] p-5 sm:p-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-emerald-700 text-white rounded-xs flex items-center justify-center font-bold text-sm">
              PIX
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-display text-lg font-bold text-[#1B1C1C]">
                  Pagamento PIX Instantâneo
                </h3>
                <span className="px-2 py-0.5 bg-amber-100 text-amber-900 text-[10px] font-bold uppercase rounded-xs">
                  Pedido #{order.id}
                </span>
              </div>
              <p className="text-[11px] text-[#545F72]">
                {order.totalPhotos} fotos digitais • Total:{" "}
                <strong>{formatCurrencyBRL(order.totalAmount)}</strong>
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="text-[#545F72] hover:text-[#1B1C1C] p-1.5 rounded-xs hover:bg-[#EFEAEA] transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-5 sm:p-6 space-y-5">
          {/* Timer Banner */}
          <div className="flex items-center justify-between p-3 bg-amber-50 border border-amber-200 rounded-xs text-xs text-amber-900">
            <span className="flex items-center gap-1.5 font-medium">
              <Clock className="w-4 h-4 text-amber-700" />
              Este QR Code expira em:
            </span>
            <span className="font-mono text-base font-bold text-amber-950">
              {formatTimer(timeLeftSeconds)}
            </span>
          </div>

          {/* QR Code & Amount Stage */}
          <div className="p-5 bg-white border border-[#E2E2E2] rounded-xs text-center space-y-4 shadow-2xs">
            <div className="inline-block p-3 bg-white border-2 border-[#1B1C1C] rounded-xs shadow-xs">
              <img
                src={order.pixQrCodeUrl}
                alt="QR Code PIX"
                className="w-48 h-48 sm:w-52 sm:h-52 mx-auto object-contain"
              />
            </div>

            <div>
              <span className="text-[10px] uppercase tracking-wider text-[#545F72] block">
                Valor Total do Pedido
              </span>
              <span className="font-display text-2xl sm:text-3xl font-bold text-emerald-800">
                {formatCurrencyBRL(order.totalAmount)}
              </span>
              <p className="text-[11px] text-[#545F72] mt-0.5">
                Economia progressiva de{" "}
                <strong>{formatCurrencyBRL(order.savings)}</strong> inclusa
              </p>
            </div>

            {/* PIX Copia e Cola */}
            <div className="pt-2">
              <label className="block text-[11px] font-bold uppercase tracking-wider text-[#1B1C1C] mb-1.5 text-left">
                PIX Copia e Cola:
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  readOnly
                  value={order.pixCode}
                  className="flex-1 px-3 py-2 bg-[#F5F3F3] border border-[#E2E2E2] text-xs font-mono text-[#545F72] rounded-xs truncate select-all"
                />
                <button
                  type="button"
                  onClick={handleCopyPix}
                  className={`px-4 py-2 text-xs font-semibold uppercase tracking-wider rounded-xs flex items-center gap-1.5 cursor-pointer transition-all ${
                    copiedPix
                      ? "bg-emerald-700 text-white"
                      : "bg-[#1B1C1C] hover:bg-[#2A2A2A] text-white"
                  }`}
                >
                  {copiedPix ? (
                    <Check className="w-4 h-4" />
                  ) : (
                    <Copy className="w-4 h-4" />
                  )}
                  <span>{copiedPix ? "Copiado!" : "Copiar"}</span>
                </button>
              </div>
            </div>
          </div>

          {/* Proof Upload Optional Simulation */}
          <div className="p-4 bg-white border border-[#E2E2E2] rounded-xs space-y-3">
            <span className="text-xs font-bold uppercase tracking-wider text-[#1B1C1C] block">
              Comprovante de Pagamento (Opcional)
            </span>
            <div className="flex items-center gap-3">
              <label className="flex-1 px-3 py-2 bg-[#F5F3F3] border border-dashed border-[#747878] hover:border-[#1B1C1C] rounded-xs text-xs text-[#545F72] flex items-center justify-center gap-2 cursor-pointer transition-colors">
                <Upload className="w-3.5 h-3.5" />
                <span className="truncate">
                  {proofFile ? proofFile : "Anexar Comprovante (PDF/PNG)"}
                </span>
                <input
                  type="file"
                  accept="image/*,application/pdf"
                  onChange={handleProofChange}
                  className="hidden"
                />
              </label>

              <button
                type="button"
                onClick={handleNotifyPhotographerWhatsApp}
                className="px-3.5 py-2 bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-300 text-xs font-semibold rounded-xs flex items-center gap-1.5 cursor-pointer"
                title="Avisar via WhatsApp"
              >
                <MessageSquare className="w-3.5 h-3.5" />
                <span>Avisar no WhatsApp</span>
              </button>
            </div>
          </div>

          {/* Action Simulation Buttons */}
          <div className="space-y-2 pt-1">
            <button
              type="button"
              onClick={handleSimulateInstantPayment}
              disabled={isSimulating}
              className="w-full py-3.5 bg-emerald-800 hover:bg-emerald-900 text-white text-xs font-semibold uppercase tracking-widest rounded-xs flex items-center justify-center gap-2 cursor-pointer transition-all shadow-md"
            >
              {isSimulating ? (
                <span>Confirmando Pagamento...</span>
              ) : (
                <>
                  <Sparkles className="w-4 h-4 text-amber-300" />
                  <span>Simular Pagamento Concluído (Ambiente Demo)</span>
                </>
              )}
            </button>

            <button
              type="button"
              onClick={() => {
                onViewOrderStatus(order.id);
                onClose();
              }}
              className="w-full py-2.5 bg-white border border-[#1B1C1C] text-[#1B1C1C] hover:bg-[#F5F3F3] text-xs font-semibold uppercase tracking-wider rounded-xs cursor-pointer text-center"
            >
              Ver Status do Pedido na Área do Cliente
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
