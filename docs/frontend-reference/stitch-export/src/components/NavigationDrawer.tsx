import React from "react";
import { Gallery, ActiveTab, CustomerUser } from "../types";
import {
  X,
  Image as ImageIcon,
  ShoppingBag,
  User,
  Sparkles,
  ShieldCheck,
  Scan,
  ArrowRight,
  Lock,
  Unlock,
  Sliders,
  Download,
  FolderOpen,
  MessageSquare,
} from "lucide-react";

interface NavigationDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  galleries: Gallery[];
  currentGallery: Gallery;
  onSelectGallery: (g: Gallery) => void;
  onNavigateTab: (tab: ActiveTab) => void;
  onOpenCatalog: () => void;
  onOpenFacialRecognition: () => void;
  onOpenWhatsAppAuth: () => void;
  onOpenAdmin: () => void;
  cartCount: number;
  currentUser: CustomerUser;
}

export const NavigationDrawer: React.FC<NavigationDrawerProps> = ({
  isOpen,
  onClose,
  galleries,
  currentGallery,
  onSelectGallery,
  onNavigateTab,
  onOpenCatalog,
  onOpenFacialRecognition,
  onOpenWhatsAppAuth,
  onOpenAdmin,
  cartCount,
  currentUser,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-xs flex">
      <div className="bg-[#FBF9F9] w-full max-w-sm h-full shadow-2xl flex flex-col justify-between border-r border-[#E2E2E2] animate-slide-in-left">
        {/* Header */}
        <div className="p-6 bg-white border-b border-[#E2E2E2] flex items-center justify-between">
          <div>
            <h3 className="font-display text-xl font-bold text-[#1B1C1C]">
              Markina Gallery
            </h3>
            <p className="text-[10px] uppercase tracking-[0.2em] text-[#747878]">
              Menu de Navegação
            </p>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 text-[#545F72] hover:text-[#1B1C1C] rounded-xs hover:bg-[#EFEAEA] transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Links & Switcher */}
        <div className="flex-1 p-6 overflow-y-auto space-y-6">
          {/* User WhatsApp Status Bar */}
          <div className="p-3.5 bg-white border border-[#E2E2E2] rounded-xs flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 bg-[#1B1C1C] text-white rounded-full flex items-center justify-center text-xs font-bold font-display">
                {currentUser.name
                  ? currentUser.name.charAt(0).toUpperCase()
                  : "M"}
              </div>
              <div className="min-w-0">
                <p className="text-xs font-bold text-[#1B1C1C] truncate max-w-[140px]">
                  {currentUser.name || "Visitante"}
                </p>
                <p className="text-[10px] text-emerald-700 font-mono">
                  {currentUser.isLoggedIn ? currentUser.phone : "Não conectado"}
                </p>
              </div>
            </div>

            <button
              onClick={() => {
                onOpenWhatsAppAuth();
                onClose();
              }}
              className="text-xs text-emerald-800 hover:underline font-semibold"
            >
              {currentUser.isLoggedIn ? "Alterar" : "Conectar"}
            </button>
          </div>

          {/* Main Navigation */}
          <div>
            <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-[#545F72] block mb-2">
              Navegação
            </span>
            <div className="space-y-1">
              <button
                onClick={() => {
                  onNavigateTab("home");
                  onClose();
                }}
                className="w-full text-left p-2.5 rounded-xs text-xs font-semibold uppercase tracking-wider text-[#1B1C1C] hover:bg-[#EFEAEA] flex items-center justify-between group cursor-pointer"
              >
                <span>Capa Editorial</span>
                <ArrowRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity" />
              </button>

              <button
                onClick={() => {
                  onNavigateTab("gallery");
                  onClose();
                }}
                className="w-full text-left p-2.5 rounded-xs text-xs font-semibold uppercase tracking-wider text-[#1B1C1C] hover:bg-[#EFEAEA] flex items-center justify-between group cursor-pointer"
              >
                <span>Galeria de Fotos ({currentGallery.totalPhotos})</span>
                <ArrowRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity" />
              </button>

              <button
                onClick={() => {
                  onOpenFacialRecognition();
                  onClose();
                }}
                className="w-full text-left p-2.5 rounded-xs text-xs font-semibold uppercase tracking-wider text-[#1B1C1C] hover:bg-[#EFEAEA] flex items-center justify-between group cursor-pointer"
              >
                <span className="flex items-center gap-2">
                  <Scan className="w-3.5 h-3.5 text-emerald-700" />
                  <span>Reconhecimento Facial (LGPD)</span>
                </span>
                <span className="px-1.5 py-0.5 bg-emerald-100 text-emerald-800 text-[9px] font-bold rounded-xs">
                  NOVO
                </span>
              </button>

              <button
                onClick={() => {
                  onOpenCatalog();
                  onClose();
                }}
                className="w-full text-left p-2.5 rounded-xs text-xs font-semibold uppercase tracking-wider text-[#1B1C1C] hover:bg-[#EFEAEA] flex items-center justify-between group cursor-pointer"
              >
                <span className="flex items-center gap-2">
                  <FolderOpen className="w-3.5 h-3.5 text-[#545F72]" />
                  <span>Explorar Todas as Galerias</span>
                </span>
                <ArrowRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity" />
              </button>

              <button
                onClick={() => {
                  onNavigateTab("profile");
                  onClose();
                }}
                className="w-full text-left p-2.5 rounded-xs text-xs font-semibold uppercase tracking-wider text-[#1B1C1C] hover:bg-[#EFEAEA] flex items-center justify-between group cursor-pointer"
              >
                <span>Meus Pedidos &amp; Google Photos</span>
                <Download className="w-3.5 h-3.5 text-emerald-700" />
              </button>

              <button
                onClick={() => {
                  onNavigateTab("cart");
                  onClose();
                }}
                className="w-full text-left p-2.5 rounded-xs text-xs font-semibold uppercase tracking-wider text-[#1B1C1C] hover:bg-[#EFEAEA] flex items-center justify-between group cursor-pointer"
              >
                <span>Carrinho de Fotos Digitais</span>
                {cartCount > 0 && (
                  <span className="px-2 py-0.5 bg-emerald-700 text-white text-[10px] font-bold rounded-full font-mono">
                    {cartCount}
                  </span>
                )}
              </button>
            </div>
          </div>

          {/* Admin Switcher */}
          <div className="pt-2 border-t border-[#E2E2E2]">
            <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-[#545F72] block mb-2">
              Acesso Restrito
            </span>
            <button
              onClick={() => {
                onOpenAdmin();
                onClose();
              }}
              className="w-full text-left p-3 rounded-xs text-xs font-semibold uppercase tracking-wider text-white bg-[#1B1C1C] hover:bg-[#2A2A2A] flex items-center justify-between cursor-pointer transition-colors shadow-xs"
            >
              <span className="flex items-center gap-2">
                <Sliders className="w-4 h-4 text-emerald-400" />
                <span>Painel do Fotógrafo (Admin)</span>
              </span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Progressive Pricing Teaser */}
          <div className="p-4 bg-emerald-50/70 border border-emerald-200 rounded-xs space-y-1.5 text-xs text-emerald-950">
            <h5 className="font-bold text-[11px] uppercase tracking-wider flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-700" />
              Garantia Markina Digital
            </h5>
            <p className="text-[11px] text-emerald-800 leading-relaxed">
              Fotos tratadas individualmente, entregues via álbum dedicado no
              Google Photos e arquivo ZIP em 45 MP.
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="p-6 bg-white border-t border-[#E2E2E2] text-xs text-[#747878] flex items-center justify-between">
          <div>
            <p>© 2026 Markina Gallery.</p>
            <p className="text-[10px] mt-0.5">PWA Digital Ready</p>
          </div>
        </div>
      </div>
    </div>
  );
};
