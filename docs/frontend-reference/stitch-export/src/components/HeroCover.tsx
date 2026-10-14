import React from "react";
import { Gallery } from "../types";
import {
  Calendar,
  Camera,
  ArrowRight,
  Lock,
  Unlock,
  Scan,
  TrendingDown,
  ShieldCheck,
  ExternalLink,
  Sparkles,
} from "lucide-react";
import { formatCurrencyBRL } from "../utils/pricing";

interface HeroCoverProps {
  gallery: Gallery;
  onEnterGallery: () => void;
  onOpenFacialRecognition: () => void;
}

export const HeroCover: React.FC<HeroCoverProps> = ({
  gallery,
  onEnterGallery,
  onOpenFacialRecognition,
}) => {
  const isPrivate = gallery.type === "private";

  return (
    <main className="min-h-screen flex flex-col md:flex-row relative bg-[#FBF9F9] pt-20 md:pt-0">
      {/* Image Section (Hero Cover) */}
      <section className="w-full md:w-3/5 h-[460px] sm:h-[520px] md:h-screen relative overflow-hidden order-1 md:order-2">
        <div
          className="absolute inset-0 bg-cover bg-center w-full h-full transform transition-transform duration-1000 ease-out hover:scale-105"
          style={{ backgroundImage: `url('${gallery.coverImage}')` }}
          role="img"
          aria-label={gallery.title}
        />
        {/* Subtle Dark Gradient Overlay */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/40 via-transparent to-black/20 md:bg-transparent pointer-events-none" />

        {/* Floating badge for high-res badge & location */}
        <div className="absolute top-6 right-6 flex items-center gap-2 bg-[#FBF9F9]/90 backdrop-blur-md px-3.5 py-1.5 rounded-xs border border-[#E2E2E2] shadow-xs">
          <Sparkles className="w-3.5 h-3.5 text-emerald-700" />
          <span className="text-[11px] uppercase tracking-wider font-semibold text-[#1B1C1C]">
            {gallery.location}
          </span>
        </div>

        {/* Bottom Feature Pill on Mobile/Desktop */}
        <div className="absolute bottom-6 left-6 right-6 hidden sm:flex items-center justify-between bg-black/75 backdrop-blur-md text-white px-4 py-3 rounded-xs border border-white/20">
          <div className="flex items-center gap-2 text-xs">
            <TrendingDown className="w-4 h-4 text-emerald-400" />
            <span>
              Preço Progressivo: <strong>R$ 25</strong> a <strong>R$ 12</strong>{" "}
              / foto digital
            </span>
          </div>
          <div className="flex items-center gap-2 text-[11px] text-gray-300">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>Entrega Digital Google Photos &amp; PIX</span>
          </div>
        </div>
      </section>

      {/* Content / Text Section */}
      <section className="w-full md:w-2/5 flex flex-col justify-center px-6 sm:px-10 py-10 md:py-16 md:px-14 md:h-screen order-2 md:order-1 bg-[#FBF9F9] z-10 relative">
        <div className="max-w-md mx-auto md:mx-0 w-full animate-fade-in-up">
          <div className="mb-6 md:mb-8">
            {/* Category / Metadata Capsule */}
            <div className="flex items-center gap-2 mb-3">
              <span
                className={`inline-flex items-center gap-1.5 px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.15em] rounded-xs ${
                  isPrivate
                    ? "bg-amber-100 text-amber-950 border border-amber-300"
                    : "bg-emerald-100 text-emerald-950 border border-emerald-300"
                }`}
              >
                {isPrivate ? (
                  <Lock className="w-3 h-3 text-amber-800" />
                ) : (
                  <Unlock className="w-3 h-3 text-emerald-800" />
                )}
                {isPrivate
                  ? "Galeria Privada • PIN"
                  : "Galeria Pública • Aberta"}
              </span>
              <span className="text-[#747878]">•</span>
              <span className="text-xs uppercase tracking-[0.15em] font-semibold text-[#545F72]">
                {gallery.totalPhotos} Fotos Digitais
              </span>
            </div>

            {/* Main Headline */}
            <h2 className="font-display text-3xl sm:text-4xl md:text-[50px] lg:text-[56px] text-[#1B1C1C] font-bold mb-4 leading-[1.1] tracking-tight">
              {gallery.title}
            </h2>

            {/* Event Metadata (Date & Photographer) */}
            <div className="space-y-1.5 mb-5 text-xs text-[#545F72]">
              <p className="flex items-center gap-2">
                <Calendar className="w-3.5 h-3.5 text-[#747878]" />
                <span>
                  {gallery.date} • {gallery.location}
                </span>
              </p>
              <p className="flex items-center gap-2">
                <Camera className="w-3.5 h-3.5 text-[#747878]" />
                <span>
                  Fotógrafo: <strong>{gallery.photographer}</strong>
                </span>
              </p>
            </div>

            {/* Editorial Quote */}
            <p className="text-xs md:text-sm text-[#545F72] mb-6 italic border-l-2 border-[#1B1C1C] pl-3.5 leading-relaxed">
              "{gallery.quote}"
            </p>

            {/* Progressive Pricing Highlight Box */}
            <div className="p-3.5 bg-white border border-[#E2E2E2] rounded-xs mb-6 shadow-2xs">
              <div className="flex items-center justify-between text-xs mb-1.5">
                <span className="font-bold text-[#1B1C1C] flex items-center gap-1.5">
                  <TrendingDown className="w-4 h-4 text-emerald-700" />
                  Preço Progressivo por Volume
                </span>
                <span className="text-emerald-800 font-mono font-bold text-[11px]">
                  Até 52% OFF
                </span>
              </div>
              <p className="text-[11px] text-[#545F72] leading-tight">
                Compre suas fotos digitais tratadas em alta resolução. De R$
                25/un por até <strong>R$ 12/un</strong> para pacotes completos.
              </p>
            </div>
          </div>

          {/* Primary Action Buttons */}
          <div className="flex flex-col gap-2.5">
            <button
              onClick={onEnterGallery}
              className="w-full bg-[#000000] text-white px-6 py-3.5 flex items-center justify-center gap-2 hover:bg-[#2A2A2A] active:scale-[0.99] transition-all duration-300 group cursor-pointer shadow-sm rounded-xs text-xs font-semibold uppercase tracking-wider"
            >
              <span>Ver Fotos &amp; Comprar</span>
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </button>

            <button
              onClick={onOpenFacialRecognition}
              className="w-full bg-white border border-[#1B1C1C] text-[#1B1C1C] px-6 py-3 flex items-center justify-center gap-2 hover:bg-[#1B1C1C] hover:text-white transition-all duration-300 cursor-pointer rounded-xs text-xs font-semibold uppercase tracking-wider group"
            >
              <Scan className="w-4 h-4 text-emerald-700 group-hover:text-emerald-300" />
              <span>Buscar meu Rosto (LGPD)</span>
            </button>
          </div>

          {/* Subtext info */}
          <p className="text-[10px] text-[#747878] mt-4 uppercase tracking-wider text-center md:text-left">
            Pagamento instantâneo via PIX • Download direto &amp; Google Photos
          </p>
        </div>
      </section>
    </main>
  );
};
