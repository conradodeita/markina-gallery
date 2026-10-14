import React, { useState, useEffect } from "react";
import { Photo } from "../types";
import {
  X,
  Play,
  Pause,
  ChevronLeft,
  ChevronRight,
  Maximize2,
} from "lucide-react";

interface SlideshowModalProps {
  photos: Photo[];
  isOpen: boolean;
  onClose: () => void;
}

export const SlideshowModal: React.FC<SlideshowModalProps> = ({
  photos,
  isOpen,
  onClose,
}) => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(true);

  useEffect(() => {
    if (!isOpen || !isPlaying) return;
    const interval = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % photos.length);
    }, 4000);
    return () => clearInterval(interval);
  }, [isOpen, isPlaying, photos.length]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowRight")
        setCurrentIndex((prev) => (prev + 1) % photos.length);
      if (e.key === "ArrowLeft")
        setCurrentIndex((prev) => (prev - 1 + photos.length) % photos.length);
      if (e.key === " ") {
        e.preventDefault();
        setIsPlaying((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [photos.length]);

  if (!isOpen || photos.length === 0) return null;

  const currentPhoto = photos[currentIndex];

  return (
    <div className="fixed inset-0 z-50 bg-black flex flex-col justify-between select-none animate-fade-in">
      {/* Top Overlay */}
      <div className="h-16 px-6 flex items-center justify-between text-white z-10 bg-gradient-to-b from-black/80 to-transparent">
        <div className="flex items-center gap-3">
          <span className="font-display font-bold text-sm tracking-wider uppercase">
            Markina Slideshow
          </span>
          <span className="text-gray-500">•</span>
          <span className="text-xs text-gray-300 font-mono">
            {currentIndex + 1} / {photos.length}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsPlaying(!isPlaying)}
            className="p-2 text-white hover:bg-white/10 rounded-xs transition-colors cursor-pointer"
            title={isPlaying ? "Pausar (Espaço)" : "Reproduzir (Espaço)"}
          >
            {isPlaying ? (
              <Pause className="w-5 h-5" />
            ) : (
              <Play className="w-5 h-5" />
            )}
          </button>

          <button
            onClick={onClose}
            className="p-2 text-white hover:bg-white/10 rounded-xs transition-colors cursor-pointer"
          >
            <X className="w-6 h-6" />
          </button>
        </div>
      </div>

      {/* Main Image with Ken Burns / Fade Transition */}
      <div className="relative flex-1 flex items-center justify-center overflow-hidden p-4">
        <img
          key={currentPhoto.id}
          src={currentPhoto.highResUrl}
          alt={currentPhoto.title}
          className="max-h-[85vh] max-w-[95vw] object-contain transition-opacity duration-1000 animate-fade-in"
        />

        <button
          onClick={() =>
            setCurrentIndex(
              (prev) => (prev - 1 + photos.length) % photos.length,
            )
          }
          className="absolute left-4 p-3 bg-black/40 hover:bg-black/80 text-white rounded-full transition-colors cursor-pointer"
        >
          <ChevronLeft className="w-6 h-6" />
        </button>

        <button
          onClick={() => setCurrentIndex((prev) => (prev + 1) % photos.length)}
          className="absolute right-4 p-3 bg-black/40 hover:bg-black/80 text-white rounded-full transition-colors cursor-pointer"
        >
          <ChevronRight className="w-6 h-6" />
        </button>
      </div>

      {/* Bottom Info */}
      <div className="h-16 px-6 flex items-center justify-between text-white z-10 bg-gradient-to-t from-black/80 to-transparent">
        <div>
          <p className="font-display font-bold text-sm">{currentPhoto.title}</p>
          <p className="text-[11px] text-gray-400 uppercase">
            {currentPhoto.category}
          </p>
        </div>

        {/* Progress bar */}
        <div className="w-32 h-1 bg-white/20 rounded-full overflow-hidden">
          <div
            className="h-full bg-white transition-all duration-300"
            style={{ width: `${((currentIndex + 1) / photos.length) * 100}%` }}
          />
        </div>
      </div>
    </div>
  );
};
