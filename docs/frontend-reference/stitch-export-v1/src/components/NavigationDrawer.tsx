import React from "react";
import { Gallery, ActiveTab } from "../types";
import {
  X,
  Image as ImageIcon,
  ShoppingBag,
  User,
  BookOpen,
  Sparkles,
  ShieldCheck,
  Info,
  Mail,
  ArrowRight,
  Lock,
} from "lucide-react";

interface NavigationDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  galleries: Gallery[];
  currentGallery: Gallery;
  onSelectGallery: (g: Gallery) => void;
  onNavigateTab: (tab: ActiveTab) => void;
  favoritesCount: number;
  cartCount: number;
}

export const NavigationDrawer: React.FC<NavigationDrawerProps> = ({
  isOpen,
  onClose,
  galleries,
  currentGallery,
  onSelectGallery,
  onNavigateTab,
  favoritesCount,
  cartCount,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex">
      <div className="bg-[#FBF9F9] w-full max-w-sm h-full shadow-2xl flex flex-col justify-between border-r border-[#E2E2E2] animate-fade-in-up">
        {/* Header */}
        <div className="p-6 bg-white border-b border-[#E2E2E2] flex items-center justify-between">
          <div>
            <h3 className="font-display text-xl font-bold text-[#1B1C1C]">
              Markina Gallery
            </h3>
            <p className="text-[10px] uppercase tracking-[0.2em] text-[#747878] font-sans-body">
              Menu Principal
            </p>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 text-[#545F72] hover:text-[#1B1C1C] rounded-xs hover:bg-[#EFEAEA] transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Links & Gallery Switcher */}
        <div className="flex-1 p-6 overflow-y-auto space-y-8">
          {/* Main Navigation */}
          <div>
            <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-[#545F72] block mb-3">
              Navegação
            </span>
            <div className="space-y-1">
              <button
                onClick={() => {
                  onNavigateTab("home");
                  onClose();
                }}
                className="w-full text-left p-2.5 rounded-xs text-xs font-semibold uppercase tracking-wider text-[#1B1C1C] hover:bg-[#EFEAEA] flex items-center justify-between group"
              >
                <span>Capa Editorial</span>
                <ArrowRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity" />
              </button>

              <button
                onClick={() => {
                  onNavigateTab("gallery");
                  onClose();
                }}
                className="w-full text-left p-2.5 rounded-xs text-xs font-semibold uppercase tracking-wider text-[#1B1C1C] hover:bg-[#EFEAEA] flex items-center justify-between group"
              >
                <span>Galeria de Fotos ({currentGallery.totalPhotos})</span>
                <ArrowRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity" />
              </button>

              <button
                onClick={() => {
                  onNavigateTab("album-builder");
                  onClose();
                }}
                className="w-full text-left p-2.5 rounded-xs text-xs font-semibold uppercase tracking-wider text-[#1B1C1C] hover:bg-[#EFEAEA] flex items-center justify-between group"
              >
                <span>Montar Álbum Físico</span>
                <BookOpen className="w-3.5 h-3.5 text-[#545F72]" />
              </button>

              <button
                onClick={() => {
                  onNavigateTab("cart");
                  onClose();
                }}
                className="w-full text-left p-2.5 rounded-xs text-xs font-semibold uppercase tracking-wider text-[#1B1C1C] hover:bg-[#EFEAEA] flex items-center justify-between group"
              >
                <span>Carrinho de Quadros</span>
                {cartCount > 0 && (
                  <span className="px-2 py-0.5 bg-[#1B1C1C] text-white text-[10px] rounded-full">
                    {cartCount}
                  </span>
                )}
              </button>

              <button
                onClick={() => {
                  onNavigateTab("profile");
                  onClose();
                }}
                className="w-full text-left p-2.5 rounded-xs text-xs font-semibold uppercase tracking-wider text-[#1B1C1C] hover:bg-[#EFEAEA] flex items-center justify-between group"
              >
                <span>Área do Cliente (PIN &amp; Downloads)</span>
                <Lock className="w-3.5 h-3.5 text-[#545F72]" />
              </button>
            </div>
          </div>

          {/* Switch Private Galleries */}
          <div>
            <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-[#545F72] block mb-3">
              Coleções &amp; Galerias Privadas
            </span>
            <div className="space-y-2">
              {galleries.map((g) => (
                <div
                  key={g.id}
                  onClick={() => {
                    onSelectGallery(g);
                    onClose();
                  }}
                  className={`p-3 border rounded-xs cursor-pointer transition-all ${
                    g.id === currentGallery.id
                      ? "border-[#1B1C1C] bg-white ring-1 ring-[#1B1C1C]"
                      : "border-[#E2E2E2] bg-white hover:border-[#747878]"
                  }`}
                >
                  <p className="text-xs font-bold text-[#1B1C1C]">{g.title}</p>
                  <p className="text-[10px] text-[#545F72] mt-0.5">
                    {g.subtitle}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Fine Art Standards */}
          <div className="p-4 bg-white border border-[#E2E2E2] rounded-xs space-y-2 text-xs text-[#545F72]">
            <h5 className="font-display text-xs font-bold text-[#1B1C1C]">
              Padrão Museológico Fine Art
            </h5>
            <p className="text-[11px] leading-relaxed">
              Impressões em papéis 100% algodão Hahnemühle com tintas minerais
              de longevidade centenária.
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="p-6 bg-white border-t border-[#E2E2E2] text-xs text-[#747878]">
          <p>© 2026 Markina Gallery &amp; Studios.</p>
          <p className="text-[10px] mt-0.5">São Paulo • Paraty • Trancoso</p>
        </div>
      </div>
    </div>
  );
};
