import React from "react";
import { ActiveTab } from "../types";
import { Home, LayoutGrid, ShoppingBag, User, Scan } from "lucide-react";

interface BottomNavProps {
  activeTab: ActiveTab;
  onSelectTab: (tab: ActiveTab) => void;
  cartCount: number;
  onOpenFacialRecognition: () => void;
}

export const BottomNav: React.FC<BottomNavProps> = ({
  activeTab,
  onSelectTab,
  cartCount,
  onOpenFacialRecognition,
}) => {
  return (
    <nav className="fixed bottom-0 left-0 w-full z-40 flex justify-around items-center bg-[#FBF9F9] pb-safe px-2 h-16 md:hidden border-t border-[#E2E2E2] shadow-lg">
      {/* Home Tab */}
      <button
        onClick={() => onSelectTab("home")}
        className={`flex flex-col items-center justify-center pt-2 transition-colors flex-1 cursor-pointer ${
          activeTab === "home"
            ? "text-[#1B1C1C] border-t-2 border-[#1B1C1C]"
            : "text-[#545F72] hover:text-[#1B1C1C]"
        }`}
      >
        <Home
          className={`w-5 h-5 mb-1 ${
            activeTab === "home" ? "stroke-[2.2]" : "stroke-[1.5]"
          }`}
        />
        <span className="text-[9px] font-semibold uppercase tracking-wider">
          Capa
        </span>
      </button>

      {/* Gallery Tab */}
      <button
        onClick={() => onSelectTab("gallery")}
        className={`flex flex-col items-center justify-center pt-2 transition-colors flex-1 cursor-pointer ${
          activeTab === "gallery"
            ? "text-[#1B1C1C] border-t-2 border-[#1B1C1C]"
            : "text-[#545F72] hover:text-[#1B1C1C]"
        }`}
      >
        <LayoutGrid
          className={`w-5 h-5 mb-1 ${
            activeTab === "gallery" ? "stroke-[2.2]" : "stroke-[1.5]"
          }`}
        />
        <span className="text-[9px] font-semibold uppercase tracking-wider">
          Galeria
        </span>
      </button>

      {/* Facial Recognition Tab */}
      <button
        onClick={onOpenFacialRecognition}
        className="flex flex-col items-center justify-center pt-2 transition-colors flex-1 cursor-pointer text-[#545F72] hover:text-[#1B1C1C]"
      >
        <Scan className="w-5 h-5 mb-1 text-emerald-700 stroke-[2]" />
        <span className="text-[9px] font-semibold uppercase tracking-wider text-emerald-800">
          Rosto
        </span>
      </button>

      {/* Cart Tab */}
      <button
        onClick={() => onSelectTab("cart")}
        className={`flex flex-col items-center justify-center pt-2 transition-colors flex-1 relative cursor-pointer ${
          activeTab === "cart"
            ? "text-[#1B1C1C] border-t-2 border-[#1B1C1C]"
            : "text-[#545F72] hover:text-[#1B1C1C]"
        }`}
      >
        <div className="relative">
          <ShoppingBag
            className={`w-5 h-5 mb-1 ${
              activeTab === "cart" ? "stroke-[2.2]" : "stroke-[1.5]"
            }`}
          />
          {cartCount > 0 && (
            <span className="absolute -top-1 -right-2 bg-emerald-700 text-white text-[9px] w-4 h-4 rounded-full flex items-center justify-center font-bold">
              {cartCount}
            </span>
          )}
        </div>
        <span className="text-[9px] font-semibold uppercase tracking-wider">
          Carrinho
        </span>
      </button>

      {/* Profile / Orders Tab */}
      <button
        onClick={() => onSelectTab("profile")}
        className={`flex flex-col items-center justify-center pt-2 transition-colors flex-1 cursor-pointer ${
          activeTab === "profile"
            ? "text-[#1B1C1C] border-t-2 border-[#1B1C1C]"
            : "text-[#545F72] hover:text-[#1B1C1C]"
        }`}
      >
        <User
          className={`w-5 h-5 mb-1 ${
            activeTab === "profile" ? "stroke-[2.2]" : "stroke-[1.5]"
          }`}
        />
        <span className="text-[9px] font-semibold uppercase tracking-wider">
          Pedidos
        </span>
      </button>
    </nav>
  );
};
