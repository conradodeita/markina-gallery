import React, { useState, useEffect } from "react";
import { Photo } from "../types";
import {
  X,
  ChevronLeft,
  ChevronRight,
  Heart,
  ShoppingBag,
  Info,
  ZoomIn,
  ZoomOut,
  Check,
  Sparkles,
  Camera,
  ShieldAlert,
} from "lucide-react";
import { formatCurrencyBRL } from "../utils/pricing";

interface PhotoLightboxProps {
  photo: Photo;
  photos: Photo[];
  onClose: () => void;
  onSelectPhoto: (photo: Photo) => void;
  onToggleFavorite: (photoId: string) => void;
  isCarted: boolean;
  onToggleCart: () => void;
  unitPrice: number;
}

export const PhotoLightbox: React.FC<PhotoLightboxProps> = ({
  photo,
  photos,
  onClose,
  onSelectPhoto,
  onToggleFavorite,
  isCarted,
  onToggleCart,
  unitPrice,
}) => {
  const [isZoomed, setIsZoomed] = useState(false);
  const [showInfo, setShowInfo] = useState(false);

  const currentIndex = photos.findIndex((p) => p.id === photo.id);

  const handlePrev = () => {
    const prevIndex = (currentIndex - 1 + photos.length) % photos.length;
    onSelectPhoto(photos[prevIndex]);
  };

  const handleNext = () => {
    const nextIndex = (currentIndex + 1) % photos.length;
    onSelectPhoto(photos[nextIndex]);
  };

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowLeft") handlePrev();
      if (e.key === "ArrowRight") handleNext();
      if (e.key === "f" || e.key === "F") onToggleFavorite(photo.id);
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [currentIndex, photo.id]);

  return (
    <div className="fixed inset-0 z-50 bg-black/95 flex flex-col justify-between overflow-hidden select-none animate-fade-in">
      {/* Top Bar */}
      <div className="h-16 px-4 sm:px-6 flex items-center justify-between text-white z-20 bg-gradient-to-b from-black/80 to-transparent">
        <div className="flex items-center gap-3">
          <span className="font-mono text-xs text-gray-400">
            {currentIndex + 1} de {photos.length}
          </span>
          <span className="text-gray-600 hidden sm:inline">•</span>
          <span className="text-xs text-gray-300 uppercase tracking-widest hidden sm:inline">
            {photo.title}
          </span>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          {/* Favorite */}
          <button
            onClick={() => onToggleFavorite(photo.id)}
            className="p-2 text-gray-300 hover:text-white rounded-xs hover:bg-white/10 transition-colors cursor-pointer"
            title="Favoritar (F)"
          >
            <Heart
              className={`w-5 h-5 ${
                photo.isFavorite
                  ? "fill-rose-500 text-rose-500"
                  : "stroke-[1.5]"
              }`}
            />
          </button>

          {/* Toggle EXIF info */}
          <button
            onClick={() => setShowInfo(!showInfo)}
            className={`p-2 rounded-xs transition-colors cursor-pointer ${
              showInfo
                ? "bg-white/20 text-white"
                : "text-gray-300 hover:text-white hover:bg-white/10"
            }`}
            title="Detalhes Técnicos EXIF"
          >
            <Info className="w-5 h-5" />
          </button>

          {/* Zoom */}
          <button
            onClick={() => setIsZoomed(!isZoomed)}
            className="p-2 text-gray-300 hover:text-white rounded-xs hover:bg-white/10 transition-colors cursor-pointer hidden sm:block"
            title={isZoomed ? "Reduzir Zoom" : "Ampliar Imagem"}
          >
            {isZoomed ? (
              <ZoomOut className="w-5 h-5" />
            ) : (
              <ZoomIn className="w-5 h-5" />
            )}
          </button>

          {/* Close */}
          <button
            onClick={onClose}
            className="p-2 text-gray-300 hover:text-white rounded-xs hover:bg-white/10 transition-colors cursor-pointer ml-2"
          >
            <X className="w-6 h-6" />
          </button>
        </div>
      </div>

      {/* Main Image Stage */}
      <div className="relative flex-1 flex items-center justify-center p-2 sm:p-6 overflow-hidden">
        <div
          className={`relative max-h-full max-w-full flex items-center justify-center transition-transform duration-300 ${
            isZoomed ? "scale-150 cursor-zoom-out" : "scale-100 cursor-zoom-in"
          }`}
          onClick={() => setIsZoomed(!isZoomed)}
        >
          <img
            src={photo.highResUrl}
            alt={photo.title}
            className="max-h-[75vh] max-w-[90vw] object-contain shadow-2xl transition-opacity duration-300"
          />

          {/* Watermark Notice */}
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none opacity-30 select-none">
            <span className="text-white text-sm sm:text-base font-mono tracking-[0.4em] uppercase rotate-[-25deg] px-4 py-1.5 border border-white/50 bg-black/30">
              MARKINA DIGITAL PREVIEW
            </span>
          </div>
        </div>

        {/* Prev / Next buttons */}
        <button
          onClick={handlePrev}
          className="absolute left-2 sm:left-6 p-3 bg-black/40 hover:bg-black/80 text-white rounded-full transition-all cursor-pointer z-10"
        >
          <ChevronLeft className="w-6 h-6" />
        </button>

        <button
          onClick={handleNext}
          className="absolute right-2 sm:right-6 p-3 bg-black/40 hover:bg-black/80 text-white rounded-full transition-all cursor-pointer z-10"
        >
          <ChevronRight className="w-6 h-6" />
        </button>

        {/* Technical EXIF Drawer */}
        {showInfo && (
          <div className="absolute top-4 right-4 bg-black/80 backdrop-blur-md border border-white/20 p-5 rounded-xs text-white max-w-xs z-30 shadow-2xl text-xs space-y-3 animate-fade-in">
            <div className="flex items-center justify-between pb-2 border-b border-white/20">
              <span className="font-bold uppercase tracking-wider text-[10px] text-gray-300 flex items-center gap-1.5">
                <Camera className="w-3.5 h-3.5" />
                Dados EXIF da Captura
              </span>
              <button
                onClick={() => setShowInfo(false)}
                className="text-gray-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-1 text-gray-300 font-mono text-[11px]">
              <p>
                <strong>Câmera:</strong> {photo.cameraInfo.camera}
              </p>
              <p>
                <strong>Lente:</strong> {photo.cameraInfo.lens}
              </p>
              <p>
                <strong>Distância Focal:</strong> {photo.cameraInfo.focalLength}
              </p>
              <p>
                <strong>Abertura:</strong> {photo.cameraInfo.aperture}
              </p>
              <p>
                <strong>Velocidade:</strong> {photo.cameraInfo.shutterSpeed}
              </p>
              <p>
                <strong>ISO:</strong> {photo.cameraInfo.iso}
              </p>
              <p>
                <strong>Horário:</strong> {photo.cameraInfo.time}
              </p>
            </div>

            <div className="pt-2 border-t border-white/20 text-[10px] text-amber-300 flex items-start gap-1">
              <ShieldAlert className="w-3.5 h-3.5 shrink-0 mt-0.5" />
              <span>
                A foto original enviada após o pagamento é entregue em 45 MP sem
                compressão nem marca d'água.
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Bottom Action Footer */}
      <div className="h-20 px-4 sm:px-8 flex items-center justify-between text-white z-20 bg-gradient-to-t from-black/80 to-transparent">
        <div>
          <h4 className="font-display text-sm sm:text-base font-bold truncate max-w-xs sm:max-w-md">
            {photo.title}
          </h4>
          <p className="text-[11px] text-gray-400">
            Foto Digital em Alta Resolução • Entrega via Google Photos &amp;
            Download Direto
          </p>
        </div>

        {/* Add to Cart CTA */}
        <div className="flex items-center gap-3">
          <button
            onClick={onToggleCart}
            className={`px-5 py-3 rounded-xs text-xs font-semibold uppercase tracking-widest flex items-center gap-2 cursor-pointer transition-all ${
              isCarted
                ? "bg-emerald-700 hover:bg-emerald-800 text-white"
                : "bg-white hover:bg-gray-100 text-[#1B1C1C]"
            }`}
          >
            {isCarted ? (
              <>
                <Check className="w-4 h-4" />
                <span>Foto no Carrinho</span>
              </>
            ) : (
              <>
                <ShoppingBag className="w-4 h-4" />
                <span>
                  Comprar Foto Digital ({formatCurrencyBRL(unitPrice)})
                </span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
