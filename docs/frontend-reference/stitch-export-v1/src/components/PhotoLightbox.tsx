import React, { useState, useEffect } from "react";
import { Photo } from "../types";
import {
  X,
  ChevronLeft,
  ChevronRight,
  Heart,
  Download,
  ShoppingBag,
  Info,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Camera,
  Layers,
  Calendar,
  Sparkles,
  Share2,
  Check,
} from "lucide-react";

interface PhotoLightboxProps {
  photo: Photo;
  photos: Photo[];
  onClose: () => void;
  onSelectPhoto: (photo: Photo, index: number) => void;
  onToggleFavorite: (photoId: string) => void;
  onOpenPrintModal: (photo: Photo) => void;
}

export const PhotoLightbox: React.FC<PhotoLightboxProps> = ({
  photo,
  photos,
  onClose,
  onSelectPhoto,
  onToggleFavorite,
  onOpenPrintModal,
}) => {
  const [showExif, setShowExif] = useState(false);
  const [zoomLevel, setZoomLevel] = useState(1);
  const [copiedLink, setCopiedLink] = useState(false);
  const [downloading, setDownloading] = useState(false);

  const currentIndex = photos.findIndex((p) => p.id === photo.id);
  const hasPrev = currentIndex > 0;
  const hasNext = currentIndex < photos.length - 1;

  const handlePrev = () => {
    if (hasPrev) {
      setZoomLevel(1);
      onSelectPhoto(photos[currentIndex - 1], currentIndex - 1);
    }
  };

  const handleNext = () => {
    if (hasNext) {
      setZoomLevel(1);
      onSelectPhoto(photos[currentIndex + 1], currentIndex + 1);
    }
  };

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowLeft") handlePrev();
      if (e.key === "ArrowRight") handleNext();
      if (e.key === "f" || e.key === "F") onToggleFavorite(photo.id);
      if (e.key === "i" || e.key === "I") setShowExif((prev) => !prev);
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [currentIndex, photos, photo.id]);

  const handleShare = () => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(window.location.href);
      setCopiedLink(true);
      setTimeout(() => setCopiedLink(false), 2500);
    }
  };

  const handleDownloadOriginal = () => {
    setDownloading(true);
    setTimeout(() => {
      setDownloading(false);
      const link = document.createElement("a");
      link.href = photo.highResUrl;
      link.download = `${photo.title.replace(/\s+/g, "_")}_MarkinaGallery_HighRes.jpg`;
      link.target = "_blank";
      link.click();
    }, 1000);
  };

  return (
    <div className="fixed inset-0 z-50 bg-[#121212]/95 backdrop-blur-xl flex flex-col justify-between select-none animate-fade-in-up">
      {/* Top Controls Bar */}
      <div className="h-16 px-4 md:px-8 flex items-center justify-between border-b border-white/10 text-white z-20">
        <div className="flex items-center gap-3">
          <span className="text-xs uppercase tracking-[0.2em] font-medium text-gray-400">
            {currentIndex + 1} / {photos.length}
          </span>
          <span className="text-gray-600">•</span>
          <h3 className="font-display text-sm md:text-base font-semibold text-white tracking-wide truncate max-w-[200px] sm:max-w-xs md:max-w-md">
            {photo.title}
          </h3>
        </div>

        {/* Action icons */}
        <div className="flex items-center gap-1 sm:gap-2">
          {/* Zoom controls */}
          <div className="hidden sm:flex items-center bg-white/10 rounded-xs mr-2">
            <button
              onClick={() => setZoomLevel((z) => Math.max(1, z - 0.5))}
              disabled={zoomLevel <= 1}
              className="p-2 hover:text-white text-gray-300 disabled:opacity-30 cursor-pointer"
              title="Diminuir Zoom"
            >
              <ZoomOut className="w-4 h-4" />
            </button>
            <span className="text-[10px] text-gray-400 px-1 font-mono">
              {Math.round(zoomLevel * 100)}%
            </span>
            <button
              onClick={() => setZoomLevel((z) => Math.min(3, z + 0.5))}
              disabled={zoomLevel >= 3}
              className="p-2 hover:text-white text-gray-300 disabled:opacity-30 cursor-pointer"
              title="Aumentar Zoom"
            >
              <ZoomIn className="w-4 h-4" />
            </button>
            {zoomLevel > 1 && (
              <button
                onClick={() => setZoomLevel(1)}
                className="p-2 text-gray-400 hover:text-white"
                title="Resetar Zoom"
              >
                <RotateCcw className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* Share */}
          <button
            onClick={handleShare}
            className="p-2 text-gray-300 hover:text-white hover:bg-white/10 rounded-xs transition-colors cursor-pointer"
            title="Compartilhar Link"
          >
            {copiedLink ? (
              <Check className="w-4 h-4 text-emerald-400" />
            ) : (
              <Share2 className="w-4 h-4" />
            )}
          </button>

          {/* EXIF Info toggle */}
          <button
            onClick={() => setShowExif(!showExif)}
            className={`p-2 rounded-xs transition-colors cursor-pointer ${
              showExif
                ? "bg-white text-black"
                : "text-gray-300 hover:text-white hover:bg-white/10"
            }`}
            title="Informações Técnicas da Câmera (EXIF)"
          >
            <Info className="w-4 h-4" />
          </button>

          {/* Favorite Toggle */}
          <button
            onClick={() => onToggleFavorite(photo.id)}
            className="p-2 text-gray-300 hover:text-rose-400 hover:bg-white/10 rounded-xs transition-colors cursor-pointer"
            title="Marcar como Favorita"
          >
            <Heart
              className={`w-4 h-4 ${
                photo.isFavorite
                  ? "fill-rose-500 text-rose-500"
                  : "stroke-[1.5]"
              }`}
            />
          </button>

          {/* Direct Print Store */}
          <button
            onClick={() => onOpenPrintModal(photo)}
            className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 bg-white text-black hover:bg-gray-200 text-xs font-semibold uppercase tracking-wider rounded-xs transition-colors cursor-pointer ml-2"
          >
            <ShoppingBag className="w-3.5 h-3.5" />
            <span>Pedir Impressão</span>
          </button>

          {/* Close Modal */}
          <button
            onClick={onClose}
            className="p-2 text-gray-300 hover:text-white hover:bg-white/10 rounded-xs transition-colors cursor-pointer ml-1"
            title="Fechar (Esc)"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Main Image Stage */}
      <div className="relative flex-1 flex items-center justify-center p-4 overflow-hidden">
        {/* Previous Button */}
        {hasPrev && (
          <button
            onClick={handlePrev}
            className="absolute left-4 z-20 p-3 bg-black/40 hover:bg-black/80 text-white rounded-full backdrop-blur-md transition-all hover:scale-105 cursor-pointer"
            title="Foto Anterior (Seta Esquerda)"
          >
            <ChevronLeft className="w-6 h-6" />
          </button>
        )}

        {/* Photo Canvas */}
        <div
          className="relative max-h-[80vh] max-w-[90vw] flex items-center justify-center transition-transform duration-200 ease-out"
          style={{ transform: `scale(${zoomLevel})` }}
        >
          <img
            src={photo.highResUrl}
            alt={photo.title}
            className="max-h-[80vh] max-w-full object-contain shadow-2xl transition-all"
            style={{ borderRadius: 0 }}
          />
        </div>

        {/* Next Button */}
        {hasNext && (
          <button
            onClick={handleNext}
            className="absolute right-4 z-20 p-3 bg-black/40 hover:bg-black/80 text-white rounded-full backdrop-blur-md transition-all hover:scale-105 cursor-pointer"
            title="Próxima Foto (Seta Direita)"
          >
            <ChevronRight className="w-6 h-6" />
          </button>
        )}

        {/* EXIF Metadata Sidebar Drawer */}
        {showExif && (
          <div className="absolute right-0 top-0 bottom-0 w-80 bg-[#1A1A1A]/95 border-l border-white/10 backdrop-blur-md p-6 text-white overflow-y-auto z-30 animate-fade-in-up">
            <div className="flex items-center justify-between pb-4 border-b border-white/10 mb-5">
              <h4 className="font-display text-base font-semibold flex items-center gap-2">
                <Camera className="w-4 h-4 text-gray-400" />
                Dados Técnicos (EXIF)
              </h4>
              <button
                onClick={() => setShowExif(false)}
                className="text-gray-400 hover:text-white p-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-4 text-xs font-sans-body">
              <div>
                <span className="text-[10px] uppercase tracking-wider text-gray-400 block mb-1">
                  Câmera &amp; Sensor
                </span>
                <p className="font-medium text-gray-100">
                  {photo.cameraInfo.camera}
                </p>
              </div>

              <div>
                <span className="text-[10px] uppercase tracking-wider text-gray-400 block mb-1">
                  Lente Óptica
                </span>
                <p className="font-medium text-gray-100">
                  {photo.cameraInfo.lens}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3 pt-2 border-t border-white/5">
                <div>
                  <span className="text-[10px] uppercase tracking-wider text-gray-400 block mb-1">
                    Distância Focal
                  </span>
                  <p className="font-mono text-gray-100">
                    {photo.cameraInfo.focalLength}
                  </p>
                </div>
                <div>
                  <span className="text-[10px] uppercase tracking-wider text-gray-400 block mb-1">
                    Abertura
                  </span>
                  <p className="font-mono text-gray-100">
                    {photo.cameraInfo.aperture}
                  </p>
                </div>
                <div>
                  <span className="text-[10px] uppercase tracking-wider text-gray-400 block mb-1">
                    Obturador
                  </span>
                  <p className="font-mono text-gray-100">
                    {photo.cameraInfo.shutterSpeed}
                  </p>
                </div>
                <div>
                  <span className="text-[10px] uppercase tracking-wider text-gray-400 block mb-1">
                    ISO
                  </span>
                  <p className="font-mono text-gray-100">
                    {photo.cameraInfo.iso}
                  </p>
                </div>
              </div>

              <div className="pt-2 border-t border-white/5">
                <span className="text-[10px] uppercase tracking-wider text-gray-400 block mb-1">
                  Resolução de Impressão
                </span>
                <p className="font-mono text-gray-100">
                  8192 × 5464 px (45 Megapixels • 300 DPI)
                </p>
              </div>

              <div className="pt-4 border-t border-white/10 space-y-2">
                <button
                  onClick={() => onOpenPrintModal(photo)}
                  className="w-full py-2.5 bg-white text-black font-medium uppercase tracking-wider text-xs flex items-center justify-center gap-2 rounded-xs hover:bg-gray-200 transition-colors"
                >
                  <ShoppingBag className="w-3.5 h-3.5" />
                  Encomendar Quadro
                </button>
                <button
                  onClick={handleDownloadOriginal}
                  disabled={downloading}
                  className="w-full py-2.5 bg-white/10 text-white font-medium uppercase tracking-wider text-xs flex items-center justify-center gap-2 rounded-xs hover:bg-white/20 transition-colors"
                >
                  <Download className="w-3.5 h-3.5" />
                  {downloading ? "Baixando..." : "Baixar Original (JPEG 45MP)"}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Bottom Bar Controls */}
      <div className="h-16 px-4 md:px-8 flex items-center justify-between border-t border-white/10 text-white z-20">
        <div className="flex items-center gap-2 text-xs text-gray-400">
          <span className="hidden sm:inline">
            Use as teclas ← e → para navegar
          </span>
          <span className="hidden sm:inline">•</span>
          <span className="hidden sm:inline">Pressione F para favoritar</span>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleDownloadOriginal}
            disabled={downloading}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-white/10 hover:bg-white/20 text-white text-xs uppercase tracking-wider font-medium rounded-xs transition-colors cursor-pointer"
          >
            <Download className="w-3.5 h-3.5" />
            <span>{downloading ? "Preparando..." : "Baixar Original"}</span>
          </button>

          <button
            onClick={() => onOpenPrintModal(photo)}
            className="flex sm:hidden items-center gap-1.5 px-3 py-1.5 bg-white text-black text-xs uppercase tracking-wider font-medium rounded-xs transition-colors cursor-pointer"
          >
            <ShoppingBag className="w-3.5 h-3.5" />
            <span>Quadro</span>
          </button>
        </div>
      </div>
    </div>
  );
};
