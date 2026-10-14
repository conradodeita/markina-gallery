import React from "react";
import { Gallery } from "../types";
import {
  Menu,
  ShoppingBag,
  Heart,
  Sparkles,
  SlidersHorizontal,
} from "lucide-react";

interface HeaderProps {
  currentGallery: Gallery;
  galleries: Gallery[];
  onSelectGallery: (gallery: Gallery) => void;
  cartCount: number;
  favoritesCount: number;
  onOpenCart: () => void;
  onOpenMenu: () => void;
  onOpenFavorites: () => void;
  onOpenAlbumBuilder: () => void;
  onStartSlideshow: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  currentGallery,
  galleries,
  onSelectGallery,
  cartCount,
  favoritesCount,
  onOpenCart,
  onOpenMenu,
  onOpenFavorites,
  onOpenAlbumBuilder,
  onStartSlideshow,
}) => {
  return (
    <header className="fixed top-0 left-0 w-full h-20 bg-[#FBF9F9]/95 backdrop-blur-md z-40 border-b border-[#E2E2E2] px-4 md:px-12 flex justify-between items-center transition-all duration-300">
      {/* Left Menu & Quick Switcher */}
      <div className="flex items-center gap-4">
        <button
          onClick={onOpenMenu}
          aria-label="Abrir Menu de Navegação"
          className="p-2 -ml-2 text-[#1B1C1C] hover:bg-[#EFEAEA] rounded-md transition-colors flex items-center gap-2 group cursor-pointer"
        >
          <Menu className="w-5 h-5 text-[#1B1C1C] stroke-[1.5]" />
          <span className="hidden lg:inline-block text-xs uppercase tracking-[0.15em] font-medium text-[#545F72]">
            Menu
          </span>
        </button>

        {/* Gallery Selector Dropdown */}
        <div className="hidden sm:flex items-center text-xs text-[#545F72] border-l border-[#E2E2E2] pl-4">
          <span className="mr-2 uppercase tracking-wider text-[10px] text-[#747878]">
            Galeria:
          </span>
          <select
            value={currentGallery.id}
            onChange={(e) => {
              const selected = galleries.find((g) => g.id === e.target.value);
              if (selected) onSelectGallery(selected);
            }}
            className="bg-transparent text-[#1B1C1C] font-medium focus:outline-none cursor-pointer hover:underline text-xs"
          >
            {galleries.map((g) => (
              <option
                key={g.id}
                value={g.id}
                className="bg-white text-[#1B1C1C]"
              >
                {g.title} ({g.totalPhotos} fotos)
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Brand Title */}
      <div
        className="text-center cursor-pointer"
        onClick={() => onSelectGallery(galleries[0])}
      >
        <h1 className="font-display text-2xl md:text-3xl font-bold tracking-tight text-[#1B1C1C]">
          Markina Gallery
        </h1>
        <p className="hidden md:block text-[10px] uppercase tracking-[0.25em] text-[#747878] -mt-1 font-sans-body">
          Fine Art & Wedding Photography
        </p>
      </div>

      {/* Right Actions */}
      <div className="flex items-center gap-2 md:gap-3">
        {/* Slideshow Button */}
        <button
          onClick={onStartSlideshow}
          title="Apresentação de Slides"
          className="hidden md:flex items-center gap-1.5 px-3 py-1.5 text-xs text-[#1B1C1C] hover:bg-[#EFEAEA] rounded-md transition-colors"
        >
          <Sparkles className="w-4 h-4 text-[#1B1C1C] stroke-[1.5]" />
          <span className="uppercase tracking-wider font-medium text-[11px]">
            Slides
          </span>
        </button>

        {/* Album Builder Button */}
        <button
          onClick={onOpenAlbumBuilder}
          title="Montar Álbum Físico"
          className="hidden lg:flex items-center gap-1.5 px-3 py-1.5 text-xs text-[#1B1C1C] hover:bg-[#EFEAEA] rounded-md transition-colors"
        >
          <SlidersHorizontal className="w-4 h-4 text-[#1B1C1C] stroke-[1.5]" />
          <span className="uppercase tracking-wider font-medium text-[11px]">
            Montar Álbum
          </span>
        </button>

        {/* Favorites Counter */}
        <button
          onClick={onOpenFavorites}
          title="Fotos Favoritas"
          className="relative p-2 text-[#1B1C1C] hover:bg-[#EFEAEA] rounded-md transition-colors flex items-center gap-1"
        >
          <Heart className="w-5 h-5 text-[#1B1C1C] stroke-[1.5]" />
          {favoritesCount > 0 && (
            <span className="absolute -top-0.5 -right-0.5 bg-[#1B1C1C] text-white text-[10px] w-4 h-4 rounded-full flex items-center justify-center font-medium">
              {favoritesCount}
            </span>
          )}
        </button>

        {/* Cart Button */}
        <button
          onClick={onOpenCart}
          aria-label="Abrir Carrinho de Impressões"
          className="relative p-2 text-[#1B1C1C] hover:bg-[#EFEAEA] rounded-md transition-colors flex items-center gap-2"
        >
          <ShoppingBag className="w-5 h-5 text-[#1B1C1C] stroke-[1.5]" />
          {cartCount > 0 && (
            <span className="absolute -top-0.5 -right-0.5 bg-[#1B1C1C] text-white text-[10px] w-4 h-4 rounded-full flex items-center justify-center font-medium">
              {cartCount}
            </span>
          )}
        </button>
      </div>
    </header>
  );
};
