import React, { useState, useEffect } from "react";
import { Photo } from "../types";
import {
  X,
  Play,
  Pause,
  ChevronLeft,
  ChevronRight,
  Volume2,
  VolumeX,
  Sparkles,
} from "lucide-react";

interface SlideshowModalProps {
  photos: Photo[];
  onClose: () => void;
}

export const SlideshowModal: React.FC<SlideshowModalProps> = ({
  photos,
  onClose,
}) => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(true);
  const [musicPlaying, setMusicPlaying] = useState(false);

  useEffect(() => {
    let timer: any;
    if (isPlaying) {
      timer = setInterval(() => {
        setCurrentIndex((prev) => (prev + 1) % photos.length);
      }, 4500);
    }
    return () => clearInterval(timer);
  }, [isPlaying, photos.length]);

  const currentPhoto = photos[currentIndex];

  const handlePrev = () => {
    setCurrentIndex((prev) => (prev === 0 ? photos.length - 1 : prev - 1));
  };

  const handleNext = () => {
    setCurrentIndex((prev) => (prev + 1) % photos.length);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black flex flex-col justify-between overflow-hidden select-none">
      {/* Top Bar */}
      <div className="h-16 px-6 flex items-center justify-between text-white z-20 bg-gradient-to-b from-black/60 to-transparent">
        <div className="flex items-center gap-3">
          <Sparkles className="w-4 h-4 text-amber-300" />
          <span className="text-xs uppercase tracking-[0.2em] font-medium text-gray-300">
            Apresentação Cinematográfica
          </span>
          <span className="text-gray-500">•</span>
          <span className="text-xs text-gray-400 font-mono">
            {currentIndex + 1} de {photos.length}
          </span>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setMusicPlaying(!musicPlaying)}
            className="p-2 text-gray-300 hover:text-white rounded-xs hover:bg-white/10 transition-colors"
            title={musicPlaying ? "Pausar Trilha" : "Tocar Trilha Suave"}
          >
            {musicPlaying ? (
              <Volume2 className="w-5 h-5" />
            ) : (
              <VolumeX className="w-5 h-5" />
            )}
          </button>

          <button
            onClick={onClose}
            className="p-2 text-gray-300 hover:text-white rounded-xs hover:bg-white/10 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Main Center Stage with Ken Burns Transition */}
      <div className="relative flex-1 flex items-center justify-center p-4">
        {currentPhoto && (
          <div className="relative max-h-[85vh] max-w-[95vw] flex flex-col items-center justify-center">
            <img
              key={currentPhoto.id}
              src={currentPhoto.highResUrl}
              alt={currentPhoto.title}
              className="max-h-[80vh] max-w-full object-contain shadow-2xl transition-all duration-1000 transform scale-100 hover:scale-105"
              style={{ borderRadius: 0 }}
            />

            {/* Photo Title Overlay */}
            <div className="mt-4 text-center">
              <h3 className="font-display text-lg sm:text-xl font-medium text-white tracking-wide">
                {currentPhoto.title}
              </h3>
              <p className="text-xs text-gray-400 uppercase tracking-widest mt-0.5">
                {currentPhoto.category} • {currentPhoto.cameraInfo.focalLength}
              </p>
            </div>
          </div>
        )}

        {/* Prev / Next Click Zones */}
        <button
          onClick={handlePrev}
          className="absolute left-6 p-3 bg-black/40 hover:bg-black/80 text-white rounded-full transition-all"
        >
          <ChevronLeft className="w-6 h-6" />
        </button>

        <button
          onClick={handleNext}
          className="absolute right-6 p-3 bg-black/40 hover:bg-black/80 text-white rounded-full transition-all"
        >
          <ChevronRight className="w-6 h-6" />
        </button>
      </div>

      {/* Bottom Progress Bar & Controls */}
      <div className="h-16 px-6 flex flex-col justify-center text-white z-20 bg-gradient-to-t from-black/60 to-transparent">
        {/* Progress Timeline */}
        <div className="w-full h-1 bg-white/20 rounded-full mb-3 overflow-hidden">
          <div
            className="h-full bg-white transition-all duration-500"
            style={{ width: `${((currentIndex + 1) / photos.length) * 100}%` }}
          />
        </div>

        <div className="flex items-center justify-between text-xs text-gray-400">
          <span>Fazenda Vila Rica • Markina Studios</span>

          <button
            onClick={() => setIsPlaying(!isPlaying)}
            className="flex items-center gap-1.5 px-3 py-1 bg-white/10 hover:bg-white/20 text-white rounded-xs transition-colors"
          >
            {isPlaying ? (
              <Pause className="w-3.5 h-3.5" />
            ) : (
              <Play className="w-3.5 h-3.5" />
            )}
            <span>{isPlaying ? "Pausar" : "Reproduzir"}</span>
          </button>

          <span>Pressione Esc para fechar</span>
        </div>
      </div>
    </div>
  );
};
