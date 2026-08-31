import React from "react";
import { Gallery, CustomerUser } from "../types";
import {
  Menu,
  ShoppingBag,
  Heart,
  Scan,
  User,
  ShieldCheck,
  Sparkles,
  Lock,
  Unlock,
  FolderOpen,
  MessageSquare,
  Sliders,
} from "lucide-react";

interface HeaderProps {
  currentGallery: Gallery;
  galleries: Gallery[];
  onOpenCatalog: () => void;
  cartCount: number;
  favoritesCount: number;
  onOpenCart: () => void;
  onOpenMenu: () => void;
  onOpenFavorites: () => void;
  onOpenFacialRecognition: () => void;
  onOpenWhatsAppAuth: () => void;
  onOpenProfile: () => void;
  onOpenAdmin: () => void;
  currentUser: CustomerUser;
}

export const Header: React.FC<HeaderProps> = ({
  currentGallery,
  galleries,
  onOpenCatalog,
  cartCount,
  favoritesCount,
  onOpenCart,
  onOpenMenu,
  onOpenFavorites,
  onOpenFacialRecognition,
  onOpenWhatsAppAuth,
  onOpenProfile,
  onOpenAdmin,
  currentUser,
}) => {
  return (
    <header className="fixed top-0 left-0 w-full h-20 bg-[#FBF9F9]/95 backdrop-blur-md z-40 border-b border-[#E2E2E2] px-4 sm:px-6 md:px-12 flex justify-between items-center transition-all duration-300">
      {/* Left Menu & Quick Switcher */}
      <div className="flex items-center gap-3">
        <button
          onClick={onOpenMenu}
          aria-label="Abrir Menu de Navegação"
          className="p-2 -ml-2 text-[#1B1C1C] hover:bg-[#EFEAEA] rounded-xs transition-colors flex items-center gap-2 group cursor-pointer"
        >
          <Menu className="w-5 h-5 text-[#1B1C1C] stroke-[1.5]" />
          <span className="hidden lg:inline-block text-xs uppercase tracking-[0.15em] font-semibold text-[#545F72]">
            Menu
          </span>
        </button>

        {/* Catalog Button */}
        <button
          onClick={onOpenCatalog}
          className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 bg-white border border-[#E2E2E2] hover:border-[#1B1C1C] text-[#1B1C1C] text-xs font-semibold rounded-xs transition-all cursor-pointer shadow-2xs"
        >
          {currentGallery.type === "private" ? (
            <Lock className="w-3.5 h-3.5 text-amber-700" />
          ) : (
            <Unlock className="w-3.5 h-3.5 text-emerald-700" />
          )}
          <span className="truncate max-w-[140px] md:max-w-[200px]">
            {currentGallery.title}
          </span>
          <span className="text-[10px] text-[#747878] uppercase">Trocar</span>
        </button>
      </div>

      {/* Brand Title */}
      <div
        className="text-center cursor-pointer select-none"
        onClick={() => onOpenCatalog()}
      >
        <h1 className="font-display text-xl sm:text-2xl md:text-3xl font-bold tracking-tight text-[#1B1C1C]">
          Markina Gallery
        </h1>
        <p className="hidden md:block text-[9px] uppercase tracking-[0.25em] text-[#747878] -mt-0.5 font-sans">
          Venda Digital de Fotos • Preço Progressivo
        </p>
      </div>

      {/* Right Actions */}
      <div className="flex items-center gap-2 sm:gap-3">
        {/* Facial Recognition Quick CTA */}
        <button
          onClick={onOpenFacialRecognition}
          title="Buscar Fotos com Reconhecimento Facial (LGPD)"
          className="hidden md:flex items-center gap-1.5 px-3 py-1.5 text-xs text-[#1B1C1C] bg-white border border-[#E2E2E2] hover:border-[#1B1C1C] rounded-xs transition-all cursor-pointer shadow-2xs group"
        >
          <Scan className="w-4 h-4 text-emerald-700 group-hover:scale-110 transition-transform" />
          <span className="uppercase tracking-wider font-semibold text-[10px]">
            Buscar Rosto
          </span>
        </button>

        {/* Admin Shortcut */}
        <button
          onClick={onOpenAdmin}
          title="Área Administrativa do Fotógrafo"
          className="hidden lg:flex items-center gap-1.5 px-2.5 py-1.5 text-xs text-[#545F72] hover:text-[#1B1C1C] hover:bg-[#EFEAEA] rounded-xs transition-colors cursor-pointer"
        >
          <Sliders className="w-3.5 h-3.5" />
          <span className="uppercase tracking-wider font-semibold text-[10px]">
            Painel Fotógrafo
          </span>
        </button>

        {/* WhatsApp Login / Client Profile */}
        <button
          onClick={currentUser.isLoggedIn ? onOpenProfile : onOpenWhatsAppAuth}
          className="p-2 text-[#1B1C1C] hover:bg-[#EFEAEA] rounded-xs transition-colors flex items-center gap-1.5 cursor-pointer"
          title={
            currentUser.isLoggedIn
              ? `Área do Cliente (${currentUser.name})`
              : "Entrar com WhatsApp"
          }
        >
          {currentUser.isLoggedIn ? (
            <div className="flex items-center gap-1.5">
              <div className="w-6 h-6 bg-emerald-700 text-white rounded-full flex items-center justify-center text-[10px] font-bold">
                {currentUser.name.charAt(0).toUpperCase()}
              </div>
              <span className="hidden xl:inline-block text-xs font-semibold text-[#1B1C1C]">
                {currentUser.name.split(" ")[0]}
              </span>
            </div>
          ) : (
            <div className="flex items-center gap-1">
              <MessageSquare className="w-4 h-4 text-emerald-600" />
              <span className="hidden sm:inline-block text-xs font-semibold text-[#1B1C1C]">
                Entrar
              </span>
            </div>
          )}
        </button>

        {/* Favorites Counter */}
        <button
          onClick={onOpenFavorites}
          title="Fotos Favoritas"
          className="relative p-2 text-[#1B1C1C] hover:bg-[#EFEAEA] rounded-xs transition-colors flex items-center gap-1 cursor-pointer"
        >
          <Heart className="w-5 h-5 stroke-[1.5]" />
          {favoritesCount > 0 && (
            <span className="absolute -top-0.5 -right-0.5 bg-[#1B1C1C] text-white text-[10px] w-4 h-4 rounded-full flex items-center justify-center font-bold">
              {favoritesCount}
            </span>
          )}
        </button>

        {/* Digital Cart Button */}
        <button
          onClick={onOpenCart}
          aria-label="Abrir Carrinho de Fotos Digitais"
          className="relative p-2 text-[#1B1C1C] hover:bg-[#EFEAEA] rounded-xs transition-colors flex items-center gap-2 cursor-pointer"
        >
          <ShoppingBag className="w-5 h-5 stroke-[1.5]" />
          {cartCount > 0 && (
            <span className="absolute -top-0.5 -right-0.5 bg-emerald-700 text-white text-[10px] w-4.5 h-4.5 rounded-full flex items-center justify-center font-bold">
              {cartCount}
            </span>
          )}
        </button>
      </div>
    </header>
  );
};
