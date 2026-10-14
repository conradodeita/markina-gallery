import React from "react";
import { Gallery } from "../types";
import { Calendar, Camera, ArrowRight, Lock, Sparkles } from "lucide-react";

interface HeroCoverProps {
  gallery: Gallery;
  onEnterGallery: () => void;
  onOpenPinModal?: () => void;
}

export const HeroCover: React.FC<HeroCoverProps> = ({
  gallery,
  onEnterGallery,
}) => {
  return (
    <main className="min-h-screen flex flex-col md:flex-row relative bg-[#FBF9F9] pt-20 md:pt-0">
      {/* Image Section (Hero Cover) */}
      <section className="w-full md:w-3/5 h-[480px] sm:h-[530px] md:h-screen relative overflow-hidden order-1 md:order-2">
        <div
          className="absolute inset-0 bg-cover bg-center w-full h-full transform transition-transform duration-1000 ease-out hover:scale-105"
          style={{ backgroundImage: `url('${gallery.coverImage}')` }}
          role="img"
          aria-label={gallery.title}
        />
        {/* Subtle Dark Gradient Overlay for Mobile readability */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/30 via-transparent to-transparent md:hidden pointer-events-none" />

        {/* Floating badge for high-res badge & location */}
        <div className="absolute top-6 right-6 hidden md:flex items-center gap-2 bg-[#FBF9F9]/90 backdrop-blur-md px-3.5 py-1.5 rounded-sm border border-[#E2E2E2] shadow-xs">
          <Sparkles className="w-3.5 h-3.5 text-[#545F72]" />
          <span className="text-[11px] uppercase tracking-wider font-medium text-[#1B1C1C]">
            {gallery.location}
          </span>
        </div>
      </section>

      {/* Content / Text Section */}
      <section className="w-full md:w-2/5 flex flex-col justify-center px-6 sm:px-10 py-12 md:py-16 md:px-16 md:h-screen order-2 md:order-1 bg-[#FBF9F9] z-10 relative">
        <div className="max-w-md mx-auto md:mx-0 w-full animate-fade-in-up">
          <div className="mb-8 md:mb-10">
            {/* Category / Metadata Capsule */}
            <div className="flex items-center gap-2 mb-4">
              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 bg-[#E9E8E7] text-[#1B1C1C] text-[11px] font-semibold uppercase tracking-[0.15em] rounded-xs">
                <Lock className="w-3 h-3 text-[#545F72]" />
                Galeria Privada
              </span>
              <span className="text-[#747878]">•</span>
              <span className="text-xs uppercase tracking-[0.15em] font-semibold text-[#545F72]">
                {gallery.totalPhotos} Fotos
              </span>
            </div>

            {/* Main Headline */}
            <h2 className="font-display text-4xl sm:text-5xl md:text-[56px] lg:text-[62px] text-[#1B1C1C] font-bold mb-6 leading-[1.1] tracking-tight">
              {gallery.title.includes("&") ? (
                <>
                  {gallery.title.split("&")[0].trim()} &amp; <br />
                  {gallery.title.split("&")[1].trim()}
                </>
              ) : (
                gallery.title
              )}
            </h2>

            {/* Event Metadata (Date & Photographer) */}
            <div className="space-y-3 mb-6">
              <p className="font-sans-body text-base text-[#444748] flex items-center gap-3">
                <Calendar className="w-4 h-4 text-[#747878] stroke-[1.5]" />
                <span>{gallery.date}</span>
              </p>
              <p className="font-sans-body text-base text-[#444748] flex items-center gap-3">
                <Camera className="w-4 h-4 text-[#747878] stroke-[1.5]" />
                <span>{gallery.photographer}</span>
              </p>
            </div>

            {/* Editorial Quote */}
            <p className="font-sans-body text-base md:text-lg text-[#1B1C1C] mb-8 italic border-l-2 border-[#C4C7C7] pl-4 leading-relaxed font-light">
              {gallery.quote}
            </p>
          </div>

          {/* Primary Action Button */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
            <button
              onClick={onEnterGallery}
              className="w-full sm:w-auto bg-[#000000] text-white px-8 py-4 flex items-center justify-center gap-3 hover:bg-[#2A2A2A] active:scale-[0.99] transition-all duration-300 group cursor-pointer shadow-sm rounded-xs"
            >
              <span className="font-sans-body text-base font-medium tracking-wide">
                Entrar na Galeria
              </span>
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1.5 transition-transform duration-300" />
            </button>
          </div>

          {/* Subtext info */}
          <p className="text-[11px] text-[#747878] mt-4 uppercase tracking-wider">
            Acesso exclusivo para noivos, familiares e convidados de honra
          </p>
        </div>
      </section>
    </main>
  );
};
