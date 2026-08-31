import React, { useState } from "react";
import { CustomerUser } from "../types";
import {
  X,
  MessageSquare,
  Phone,
  ShieldCheck,
  Check,
  ArrowRight,
  Sparkles,
} from "lucide-react";

interface WhatsAppAuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentUser: CustomerUser;
  onSaveUser: (user: CustomerUser) => void;
}

export const WhatsAppAuthModal: React.FC<WhatsAppAuthModalProps> = ({
  isOpen,
  onClose,
  currentUser,
  onSaveUser,
}) => {
  const [phone, setPhone] = useState(currentUser.phone || "");
  const [name, setName] = useState(currentUser.name || "");
  const [step, setStep] = useState<"input" | "otp">("input");
  const [otpCode, setOtpCode] = useState("");
  const [generatedOtp] = useState("4829"); // Demo OTP code
  const [lgpdConsent, setLgpdConsent] = useState(
    currentUser.lgpdConsentFace ?? true,
  );
  const [otpSent, setOtpSent] = useState(false);

  if (!isOpen) return null;

  const handleSendOtp = (e: React.FormEvent) => {
    e.preventDefault();
    if (!phone || phone.length < 10) {
      alert("Por favor, insira um número de WhatsApp válido com DDD.");
      return;
    }
    if (!name.trim()) {
      alert("Por favor, informe seu nome.");
      return;
    }
    setOtpSent(true);
    setStep("otp");
  };

  const handleVerifyOtp = (e: React.FormEvent) => {
    e.preventDefault();
    if (
      otpCode.trim() === generatedOtp ||
      otpCode.trim() === "1234" ||
      otpCode.length >= 4
    ) {
      const updated: CustomerUser = {
        phone: phone.trim(),
        name: name.trim(),
        isLoggedIn: true,
        lgpdConsentFace: lgpdConsent,
      };
      onSaveUser(updated);
      onClose();
    } else {
      alert(`Código inválido. Dica de teste: use o código ${generatedOtp}`);
    }
  };

  const handleQuickDemoLogin = () => {
    const updated: CustomerUser = {
      phone: "+55 (11) 98842-1920",
      name: "Marina Alencar",
      isLoggedIn: true,
      lgpdConsentFace: true,
    };
    onSaveUser(updated);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-[#FBF9F9] border border-[#E2E2E2] rounded-xs w-full max-w-md shadow-2xl overflow-hidden animate-fade-in-up">
        {/* Header */}
        <div className="bg-white border-b border-[#E2E2E2] p-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-emerald-50 border border-emerald-200 rounded-full flex items-center justify-center text-emerald-700">
              <MessageSquare className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-display text-lg font-bold text-[#1B1C1C]">
                Login por WhatsApp
              </h3>
              <p className="text-[10px] text-[#545F72] uppercase tracking-wider">
                Acesso Rápido Sem Senhas Complexas
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="text-[#545F72] hover:text-[#1B1C1C] p-1 rounded-xs"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {step === "input" ? (
            <form onSubmit={handleSendOtp} className="space-y-4">
              <p className="text-xs text-[#545F72] leading-relaxed">
                Digite seu número de WhatsApp para acessar suas fotos
                adquiridas, consultar status de entrega e salvar suas seleções.
              </p>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-[#1B1C1C] mb-1">
                  Seu Nome Completo
                </label>
                <input
                  type="text"
                  required
                  placeholder="Ex: Marina Alencar"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-white border border-[#E2E2E2] text-xs rounded-xs text-[#1B1C1C] focus:outline-none focus:border-[#1B1C1C]"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-[#1B1C1C] mb-1">
                  WhatsApp com DDD
                </label>
                <div className="relative">
                  <span className="absolute left-3.5 top-2.5 text-xs text-[#545F72] font-mono">
                    🇧🇷 +55
                  </span>
                  <input
                    type="tel"
                    required
                    placeholder="(11) 98842-1920"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    className="w-full pl-20 pr-3.5 py-2.5 bg-white border border-[#E2E2E2] text-xs font-mono rounded-xs text-[#1B1C1C] focus:outline-none focus:border-[#1B1C1C]"
                  />
                </div>
              </div>

              {/* LGPD Consent */}
              <div className="p-3 bg-white border border-[#E2E2E2] rounded-xs flex items-start gap-2.5">
                <input
                  type="checkbox"
                  id="lgpd-auth"
                  checked={lgpdConsent}
                  onChange={(e) => setLgpdConsent(e.target.checked)}
                  className="mt-0.5 accent-[#1B1C1C] cursor-pointer"
                />
                <label
                  htmlFor="lgpd-auth"
                  className="text-[11px] text-[#545F72] leading-snug cursor-pointer"
                >
                  Concordo em receber mensagens transacionais sobre meu pedido
                  via WhatsApp e aceito os{" "}
                  <span className="text-[#1B1C1C] font-semibold underline">
                    Termos de Privacidade LGPD
                  </span>
                  .
                </label>
              </div>

              <button
                type="submit"
                className="w-full py-3 bg-[#1B1C1C] text-white hover:bg-[#2A2A2A] text-xs font-semibold uppercase tracking-widest rounded-xs flex items-center justify-center gap-2 cursor-pointer transition-colors"
              >
                <span>Enviar Código via WhatsApp</span>
                <ArrowRight className="w-4 h-4" />
              </button>

              <div className="pt-3 border-t border-[#E2E2E2] text-center">
                <button
                  type="button"
                  onClick={handleQuickDemoLogin}
                  className="text-xs text-[#545F72] hover:text-[#1B1C1C] underline font-medium cursor-pointer flex items-center justify-center gap-1.5 mx-auto"
                >
                  <Sparkles className="w-3.5 h-3.5 text-amber-600" />
                  Entrar com Perfil de Demonstração (Marina Alencar)
                </button>
              </div>
            </form>
          ) : (
            <form onSubmit={handleVerifyOtp} className="space-y-4">
              <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xs text-emerald-800 text-xs flex items-center gap-2">
                <Check className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>
                  Código enviado para <strong>{phone}</strong> via WhatsApp!
                </span>
              </div>

              <div className="text-center py-2">
                <span className="text-xs text-[#545F72] block mb-2">
                  Digite o código de 4 dígitos (Para teste, use:{" "}
                  <strong className="text-[#1B1C1C] font-mono">
                    {generatedOtp}
                  </strong>
                  )
                </span>
                <input
                  type="text"
                  maxLength={4}
                  required
                  autoFocus
                  placeholder="0000"
                  value={otpCode}
                  onChange={(e) => setOtpCode(e.target.value)}
                  className="w-40 mx-auto px-4 py-3 bg-white border-2 border-[#1B1C1C] text-center font-mono text-2xl font-bold tracking-[0.4em] rounded-xs text-[#1B1C1C] focus:outline-none"
                />
              </div>

              <button
                type="submit"
                className="w-full py-3 bg-[#1B1C1C] text-white hover:bg-[#2A2A2A] text-xs font-semibold uppercase tracking-widest rounded-xs flex items-center justify-center gap-2 cursor-pointer transition-colors"
              >
                <span>Confirmar &amp; Entrar</span>
              </button>

              <div className="flex justify-between items-center text-xs text-[#545F72] pt-2">
                <button
                  type="button"
                  onClick={() => setStep("input")}
                  className="hover:text-[#1B1C1C] underline cursor-pointer"
                >
                  Corrigir Número
                </button>
                <button
                  type="button"
                  onClick={() => setOtpCode(generatedOtp)}
                  className="text-emerald-700 font-semibold cursor-pointer"
                >
                  Preencher Código ({generatedOtp})
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
