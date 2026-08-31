import React, { useState } from "react";
import { Gallery, Photo } from "../types";
import {
  Heart,
  ShoppingBag,
  Scan,
  Eye,
  Sparkles,
  Grid3X3,
  Grid2X2,
  SlidersHorizontal,
  Check,
  ArrowRight,
  TrendingDown,
  Info,
  Lock,
  Play,
} from "lucide-react";
import { calculateProgressivePrice, formatCurrencyBRL } from "../utils/pricing";

interface GalleryViewProps {
  gallery: Gallery;
  onPhotoClick: (photo: Photo) => void;
  onToggleFavorite: (photoId: string) => void;
  cartPhotoIds: string[];
  onToggleCartPhoto: (photo: Photo) => void;
  onAddMultipleToCart: (photos: Photo[]) => void;
  onOpenFacialRecognition: () => void;
  matchedPhotoIds: string[];
  selfieUrl: string | null;
  onClearFaceFilter: () => void;
  onStartSlideshow: () => void;
  onOpenCart: () => void;
}

export const GalleryView: React.FC<GalleryViewProps> = ({
  gallery,
  onPhotoClick,
  onToggleFavorite,
  cartPhotoIds,
  onToggleCartPhoto,
  onAddMultipleToCart,
  onOpenFacialRecognition,
  matchedPhotoIds,
  selfieUrl,
  onClearFaceFilter,
  onStartSlideshow,
  onOpenCart,
}) => {
  const [activeCategory, setActiveCategory] = useState<string>("todas");
  const [gridColumns, setGridColumns] = useState<"2-col" | "3-col" | "masonry">(
    "masonry",
  );
  const [showFaceOnly, setShowFaceOnly] = useState<boolean>(
    matchedPhotoIds.length > 0,
  );

  // Filter photos
  const filteredPhotos = gallery.photos.filter((photo) => {
    if (showFaceOnly && matchedPhotoIds.length > 0) {
      if (!matchedPhotoIds.includes(photo.id)) return false;
    }
    if (activeCategory === "favoritas") return photo.isFavorite;
    if (activeCategory === "todas") return true;
    return photo.category === activeCategory;
  });

  const progressive = calculateProgressivePrice(
    cartPhotoIds.length,
    undefined,
    gallery.basePhotoPrice,
  );

  const matchedPhotos = gallery.photos.filter((p) =>
    matchedPhotoIds.includes(p.id),
  );

  return (
    <div className="pt-20 pb-28 px-4 sm:px-6 md:px-12 max-w-[1500px] mx-auto animate-fade-in-up">
      {/* Editorial Header */}
      <div className="py-6 border-b border-[#E2E2E2] mb-6">
        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-6">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="px-2 py-0.5 bg-[#E9E8E7] text-[#1B1C1C] text-[10px] font-bold uppercase tracking-widest rounded-xs">
                Venda de Fotos Digitais
              </span>
              <span className="text-xs text-[#545F72]">•</span>
              <span className="text-xs text-[#545F72] font-mono">
                {gallery.photos.length} Fotos no Acervo
              </span>
            </div>
            <h1 className="font-display text-2xl sm:text-4xl font-bold text-[#1B1C1C] tracking-tight">
              {gallery.title}
            </h1>
            <p className="text-xs text-[#545F72] mt-1 max-w-2xl">
              Selecione suas fotos digitais individuais tratadas em alta
              resolução. Quanto mais fotos você escolhe, menor o valor unitário.
            </p>
          </div>

          {/* Facial Recognition & Fast Actions */}
          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={onOpenFacialRecognition}
              className="px-4 py-2.5 bg-white border border-[#1B1C1C] text-[#1B1C1C] hover:bg-[#1B1C1C] hover:text-white text-xs font-semibold uppercase tracking-wider rounded-xs flex items-center gap-2 transition-all cursor-pointer shadow-xs group"
            >
              <Scan className="w-4 h-4 text-emerald-700 group-hover:text-emerald-300" />
              <span>Buscar meu Rosto (LGPD)</span>
            </button>

            <button
              onClick={onStartSlideshow}
              className="px-4 py-2.5 bg-[#F5F3F3] text-[#1B1C1C] hover:bg-[#EFEAEA] text-xs font-semibold uppercase tracking-wider rounded-xs flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>Apresentação</span>
            </button>
          </div>
        </div>

        {/* Dynamic Progressive Pricing Tier Bar */}
        <div className="mt-6 p-4 bg-white border border-[#E2E2E2] rounded-xs shadow-xs">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-emerald-50 text-emerald-800 rounded-full flex items-center justify-center font-bold text-xs shrink-0">
                <TrendingDown className="w-4 h-4" />
              </div>
              <div>
                <p className="text-xs font-bold text-[#1B1C1C] flex items-center gap-2">
                  Tabela Progressiva por Quantidade
                  {cartPhotoIds.length > 0 && (
                    <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 text-[10px] rounded-xs font-mono font-semibold">
                      {cartPhotoIds.length} selecionadas •{" "}
                      {formatCurrencyBRL(progressive.unitPrice)}/foto
                    </span>
                  )}
                </p>
                <p className="text-[11px] text-[#545F72]">
                  1-4 fotos: <strong>R$ 25</strong>/un • 5-9 fotos:{" "}
                  <strong>R$ 20</strong>/un (20% OFF) • 10-19 fotos:{" "}
                  <strong>R$ 16</strong>/un (36% OFF) • 20+:{" "}
                  <strong>R$ 12</strong>/un (52% OFF)
                </p>
              </div>
            </div>

            {/* Next Tier Incentive / Cart CTA */}
            <div className="flex items-center gap-3 self-end md:self-auto">
              {cartPhotoIds.length > 0 ? (
                <div className="flex items-center gap-2">
                  {progressive.nextTier &&
                    progressive.photosNeededForNextTier > 0 && (
                      <span className="text-[11px] text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-xs border border-emerald-200 hidden sm:inline-block font-medium">
                        + {progressive.photosNeededForNextTier} foto(s) para
                        pagar {formatCurrencyBRL(progressive.nextTierUnitPrice)}
                        /un
                      </span>
                    )}
                  <button
                    onClick={onOpenCart}
                    className="px-4 py-2 bg-[#1B1C1C] text-white hover:bg-[#2A2A2A] text-xs font-semibold uppercase tracking-wider rounded-xs flex items-center gap-2 cursor-pointer transition-colors"
                  >
                    <ShoppingBag className="w-3.5 h-3.5" />
                    <span>
                      Ver Carrinho ({cartPhotoIds.length}) •{" "}
                      {formatCurrencyBRL(progressive.totalAmount)}
                    </span>
                  </button>
                </div>
              ) : (
                <span className="text-[11px] text-[#747878] italic">
                  Clique em + Carrinho em qualquer foto para começar
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Biometric Active Match Banner if user scanned face */}
        {matchedPhotoIds.length > 0 && (
          <div className="mt-4 p-3 bg-emerald-50 border border-emerald-200 rounded-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 animate-fade-in-up">
            <div className="flex items-center gap-3">
              {selfieUrl && (
                <img
                  src={selfieUrl}
                  alt="Sua Selfie"
                  className="w-10 h-10 rounded-full object-cover border-2 border-emerald-600 shrink-0"
                />
              )}
              <div>
                <p className="text-xs font-bold text-emerald-950 flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
                  Identificamos {matchedPhotos.length} fotos suas nesta galeria!
                </p>
                <p className="text-[11px] text-emerald-800">
                  Filtro biométrico ativo com consentimento LGPD.
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() =>
                  onAddMultipleToCart(
                    matchedPhotos.filter((p) => !cartPhotoIds.includes(p.id)),
                  )
                }
                className="px-3.5 py-1.5 bg-emerald-800 hover:bg-emerald-900 text-white text-[11px] font-semibold uppercase tracking-wider rounded-xs cursor-pointer transition-colors"
              >
                Comprar Todas as Minhas Fotos
              </button>

              <button
                onClick={onClearFaceFilter}
                className="px-3 py-1.5 text-xs text-emerald-900 hover:underline cursor-pointer"
              >
                Ver Todas
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Filter and View Controls Bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
        {/* Category Pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-2 sm:pb-0 w-full sm:w-auto scrollbar-none">
          {gallery.categories.map((cat) => (
            <button
              key={cat.id}
              onClick={() => {
                setActiveCategory(cat.id);
                setShowFaceOnly(false);
              }}
              className={`px-3 py-1.5 text-xs uppercase tracking-wider rounded-xs whitespace-nowrap transition-all cursor-pointer ${
                activeCategory === cat.id && !showFaceOnly
                  ? "bg-[#1B1C1C] text-white font-semibold"
                  : "bg-white text-[#545F72] hover:bg-[#EFEAEA] border border-[#E2E2E2]"
              }`}
            >
              {cat.label} ({cat.count})
            </button>
          ))}

          {/* Favorites Filter */}
          <button
            onClick={() => {
              setActiveCategory("favoritas");
              setShowFaceOnly(false);
            }}
            className={`px-3 py-1.5 text-xs uppercase tracking-wider rounded-xs whitespace-nowrap transition-all flex items-center gap-1.5 cursor-pointer ${
              activeCategory === "favoritas" && !showFaceOnly
                ? "bg-[#1B1C1C] text-white font-semibold"
                : "bg-white text-[#545F72] hover:bg-[#EFEAEA] border border-[#E2E2E2]"
            }`}
          >
            <Heart className="w-3 h-3 fill-current text-rose-500" />
            <span>
              Favoritas ({gallery.photos.filter((p) => p.isFavorite).length})
            </span>
          </button>
        </div>

        {/* View Grid Switchers */}
        <div className="flex items-center gap-1 bg-white p-1 border border-[#E2E2E2] rounded-xs self-end sm:self-auto">
          <button
            onClick={() => setGridColumns("masonry")}
            title="Visualização Natural"
            className={`p-1.5 rounded-xs transition-colors cursor-pointer ${
              gridColumns === "masonry"
                ? "bg-[#1B1C1C] text-white"
                : "text-[#545F72] hover:text-[#1B1C1C]"
            }`}
          >
            <SlidersHorizontal className="w-4 h-4" />
          </button>

          <button
            onClick={() => setGridColumns("2-col")}
            title="Grade Editorial 2 Colunas"
            className={`p-1.5 rounded-xs transition-colors cursor-pointer ${
              gridColumns === "2-col"
                ? "bg-[#1B1C1C] text-white"
                : "text-[#545F72] hover:text-[#1B1C1C]"
            }`}
          >
            <Grid2X2 className="w-4 h-4" />
          </button>

          <button
            onClick={() => setGridColumns("3-col")}
            title="Grade Compacta 3 Colunas"
            className={`p-1.5 rounded-xs transition-colors cursor-pointer ${
              gridColumns === "3-col"
                ? "bg-[#1B1C1C] text-white"
                : "text-[#545F72] hover:text-[#1B1C1C]"
            }`}
          >
            <Grid3X3 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Photos Grid with Watermark & Digital Add to Cart */}
      {filteredPhotos.length === 0 ? (
        <div className="py-20 text-center bg-white border border-[#E2E2E2] rounded-xs p-8">
          <p className="font-display text-lg text-[#1B1C1C] mb-2">
            Nenhuma foto encontrada nesta categoria.
          </p>
          <button
            onClick={() => {
              setActiveCategory("todas");
              setShowFaceOnly(false);
            }}
            className="px-4 py-2 bg-[#1B1C1C] text-white text-xs uppercase tracking-wider rounded-xs cursor-pointer"
          >
            Ver Todas as Fotos
          </button>
        </div>
      ) : (
        <div
          className={
            gridColumns === "masonry"
              ? "columns-1 sm:columns-2 lg:columns-3 gap-6 space-y-6"
              : gridColumns === "2-col"
                ? "grid grid-cols-1 sm:grid-cols-2 gap-6"
                : "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5"
          }
        >
          {filteredPhotos.map((photo) => {
            const isCarted = cartPhotoIds.includes(photo.id);
            const isMatchedFace = matchedPhotoIds.includes(photo.id);

            return (
              <div
                key={photo.id}
                className="group relative bg-[#EFEAEA] border border-[#E2E2E2] rounded-xs overflow-hidden break-inside-avoid shadow-2xs hover:shadow-md transition-all duration-300"
              >
                {/* Photo Image Container */}
                <div
                  onClick={() => onPhotoClick(photo)}
                  className="relative cursor-pointer overflow-hidden select-none"
                >
                  <img
                    src={photo.url}
                    alt={photo.title}
                    loading="lazy"
                    className="w-full h-auto object-cover transition-transform duration-700 group-hover:scale-103"
                  />

                  {/* Watermark Overlay on Preview (Protected until payment) */}
                  <div className="absolute inset-0 flex items-center justify-center pointer-events-none opacity-40 group-hover:opacity-20 transition-opacity">
                    <span className="text-white text-xs font-mono tracking-[0.3em] uppercase rotate-[-25deg] drop-shadow-md select-none border border-white/40 px-3 py-1 bg-black/20">
                      MARKINA PREVIEW
                    </span>
                  </div>

                  {/* Biometric Matched Badge */}
                  {isMatchedFace && (
                    <div className="absolute top-3 left-3 px-2 py-0.5 bg-emerald-900/80 backdrop-blur-xs text-emerald-200 text-[10px] font-bold uppercase rounded-xs flex items-center gap-1 shadow-sm">
                      <Sparkles className="w-3 h-3 text-emerald-400" />
                      Seu Rosto ({photo.matchConfidence || 94}%)
                    </div>
                  )}

                  {/* Action Overlay in Hover */}
                  <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-black/40 opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex flex-col justify-between p-4 text-white">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] uppercase tracking-wider font-mono opacity-80">
                        {photo.cameraInfo.focalLength} •{" "}
                        {photo.cameraInfo.aperture}
                      </span>

                      {/* Favorite Button */}
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          onToggleFavorite(photo.id);
                        }}
                        className="p-2 rounded-full bg-black/40 hover:bg-black/80 text-white transition-colors cursor-pointer"
                      >
                        <Heart
                          className={`w-4 h-4 ${
                            photo.isFavorite
                              ? "fill-rose-500 text-rose-500"
                              : "text-white"
                          }`}
                        />
                      </button>
                    </div>

                    <div>
                      <h4 className="font-display text-sm font-bold text-white drop-shadow-xs line-clamp-1">
                        {photo.title}
                      </h4>
                      <p className="text-[10px] text-gray-300 uppercase tracking-wider mt-0.5">
                        {photo.category} • Arquivo Digital em Alta Resolução
                      </p>
                    </div>
                  </div>
                </div>

                {/* Bottom Card Bar: Direct Buy Button */}
                <div className="p-3 bg-white border-t border-[#E2E2E2] flex items-center justify-between gap-2">
                  <div>
                    <span className="text-[10px] text-[#747878] uppercase tracking-wider block">
                      Digital Original
                    </span>
                    <span className="font-mono text-xs font-bold text-[#1B1C1C]">
                      R$ {gallery.basePhotoPrice.toFixed(2).replace(".", ",")}
                    </span>
                  </div>

                  <button
                    type="button"
                    onClick={() => onToggleCartPhoto(photo)}
                    className={`px-3.5 py-1.5 rounded-xs text-xs font-semibold uppercase tracking-wider flex items-center gap-1.5 transition-all cursor-pointer ${
                      isCarted
                        ? "bg-emerald-700 hover:bg-emerald-800 text-white"
                        : "bg-[#1B1C1C] hover:bg-[#2A2A2A] text-white"
                    }`}
                  >
                    {isCarted ? (
                      <>
                        <Check className="w-3.5 h-3.5" />
                        <span>Selecionada</span>
                      </>
                    ) : (
                      <>
                        <ShoppingBag className="w-3.5 h-3.5" />
                        <span>+ Carrinho</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
