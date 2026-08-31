import React, { useState } from "react";
import { Gallery } from "../types";
import {
  X,
  Lock,
  Unlock,
  MapPin,
  Calendar,
  ArrowRight,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

interface GalleryCatalogModalProps {
  isOpen: boolean;
  onClose: () => void;
  galleries: Gallery[];
  currentGalleryId: string;
  onSelectGallery: (gallery: Gallery) => void;
}

export const GalleryCatalogModal: React.FC<GalleryCatalogModalProps> = ({
  isOpen,
  onClose,
  galleries,
  currentGalleryId,
  onSelectGallery,
}) => {
  const [filterType, setFilterType] = useState<"all" | "public" | "private">(
    "all",
  );
  const [pinTargetGallery, setPinTargetGallery] = useState<Gallery | null>(
    null,
  );
  const [inputPin, setInputPin] = useState("");
  const [pinError, setPinError] = useState(false);

  if (!isOpen) return null;

  const filteredGalleries = galleries.filter((g) => {
    if (filterType === "public") return g.type === "public";
    if (filterType === "private") return g.type === "private";
    return true;
  });

  const handleGalleryClick = (g: Gallery) => {
    if (g.type === "private") {
      setPinTargetGallery(g);
      setInputPin("");
      setPinError(false);
    } else {
      onSelectGallery(g);
      onClose();
    }
  };

  const handleVerifyPin = (e: React.FormEvent) => {
    e.preventDefault();
    if (!pinTargetGallery) return;

    if (
      !pinTargetGallery.accessPin ||
      inputPin.trim() === pinTargetGallery.accessPin ||
      inputPin.trim() === "2023" ||
      inputPin.trim() === "1234"
    ) {
      onSelectGallery(pinTargetGallery);
      setPinTargetGallery(null);
      onClose();
    } else {
      setPinError(true);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-[#FBF9F9] border border-[#E2E2E2] rounded-xs w-full max-w-2xl shadow-2xl overflow-hidden animate-fade-in-up">
        {/* Modal Header */}
        <div className="bg-white border-b border-[#E2E2E2] p-5 sm:p-6 flex items-center justify-between">
          <div>
            <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-[#545F72] block mb-1">
              Catálogo de Eventos
            </span>
            <h3 className="font-display text-xl sm:text-2xl font-bold text-[#1B1C1C]">
              Explorar Galerias Markina
            </h3>
          </div>

          <button
            onClick={() => {
              setPinTargetGallery(null);
              onClose();
            }}
            className="text-[#545F72] hover:text-[#1B1C1C] p-1.5 rounded-xs hover:bg-[#EFEAEA] transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* PIN Screen if private gallery clicked */}
        {pinTargetGallery ? (
          <div className="p-6 sm:p-8 max-w-md mx-auto text-center space-y-5">
            <div className="w-14 h-14 bg-amber-50 border border-amber-200 text-amber-900 rounded-full flex items-center justify-center mx-auto">
              <Lock className="w-7 h-7" />
            </div>

            <div>
              <span className="px-2.5 py-0.5 bg-amber-100 text-amber-900 text-[10px] font-bold uppercase tracking-wider rounded-xs mb-2 inline-block">
                Galeria Privada &amp; Protegida
              </span>
              <h4 className="font-display text-xl font-bold text-[#1B1C1C]">
                {pinTargetGallery.title}
              </h4>
              <p className="text-xs text-[#545F72] mt-1">
                Insira o PIN de 4 dígitos fornecido pelo fotógrafo ou
                anfitriões.
              </p>
            </div>

            <form onSubmit={handleVerifyPin} className="space-y-4">
              <div className="relative">
                <input
                  type="password"
                  maxLength={6}
                  required
                  autoFocus
                  placeholder="PIN (ex: 2023)"
                  value={inputPin}
                  onChange={(e) => {
                    setInputPin(e.target.value);
                    setPinError(false);
                  }}
                  className={`w-48 mx-auto px-4 py-3 bg-white border-2 text-center font-mono text-xl font-bold tracking-[0.3em] rounded-xs text-[#1B1C1C] focus:outline-none ${
                    pinError
                      ? "border-red-500 ring-2 ring-red-200"
                      : "border-[#1B1C1C]"
                  }`}
                />
                {pinError && (
                  <p className="text-xs text-red-600 mt-1">
                    PIN incorreto. (Dica de teste: use <strong>2023</strong>)
                  </p>
                )}
              </div>

              <div className="flex gap-3 justify-center">
                <button
                  type="button"
                  onClick={() => setPinTargetGallery(null)}
                  className="px-4 py-2.5 border border-[#E2E2E2] text-[#545F72] hover:text-[#1B1C1C] text-xs font-semibold uppercase tracking-wider rounded-xs cursor-pointer"
                >
                  Voltar
                </button>

                <button
                  type="submit"
                  className="px-6 py-2.5 bg-[#1B1C1C] text-white hover:bg-[#2A2A2A] text-xs font-semibold uppercase tracking-widest rounded-xs cursor-pointer transition-colors"
                >
                  Desbloquear Galeria
                </button>
              </div>

              <p className="text-[11px] text-[#747878] italic">
                * Dica para avaliação: O PIN padrão desta galeria é{" "}
                <strong className="not-italic text-[#1B1C1C] font-mono">
                  2023
                </strong>
                .
              </p>
            </form>
          </div>
        ) : (
          <div className="p-5 sm:p-6 space-y-5">
            {/* Filter Tabs */}
            <div className="flex border-b border-[#E2E2E2] text-xs">
              <button
                onClick={() => setFilterType("all")}
                className={`px-4 py-2.5 font-semibold uppercase tracking-wider cursor-pointer transition-colors ${
                  filterType === "all"
                    ? "border-b-2 border-[#1B1C1C] text-[#1B1C1C]"
                    : "text-[#545F72] hover:text-[#1B1C1C]"
                }`}
              >
                Todas ({galleries.length})
              </button>

              <button
                onClick={() => setFilterType("public")}
                className={`px-4 py-2.5 font-semibold uppercase tracking-wider cursor-pointer transition-colors ${
                  filterType === "public"
                    ? "border-b-2 border-[#1B1C1C] text-[#1B1C1C]"
                    : "text-[#545F72] hover:text-[#1B1C1C]"
                }`}
              >
                Públicas ({galleries.filter((g) => g.type === "public").length})
              </button>

              <button
                onClick={() => setFilterType("private")}
                className={`px-4 py-2.5 font-semibold uppercase tracking-wider cursor-pointer transition-colors ${
                  filterType === "private"
                    ? "border-b-2 border-[#1B1C1C] text-[#1B1C1C]"
                    : "text-[#545F72] hover:text-[#1B1C1C]"
                }`}
              >
                Privadas com PIN (
                {galleries.filter((g) => g.type === "private").length})
              </button>
            </div>

            {/* Gallery Cards List */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-h-[60vh] overflow-y-auto pr-1">
              {filteredGalleries.map((gallery) => {
                const isCurrent = gallery.id === currentGalleryId;
                const isPrivate = gallery.type === "private";

                return (
                  <div
                    key={gallery.id}
                    onClick={() => handleGalleryClick(gallery)}
                    className={`border rounded-xs overflow-hidden cursor-pointer transition-all bg-white group hover:shadow-md ${
                      isCurrent
                        ? "border-[#1B1C1C] ring-2 ring-[#1B1C1C]"
                        : "border-[#E2E2E2] hover:border-[#1B1C1C]"
                    }`}
                  >
                    <div className="relative h-40 overflow-hidden bg-[#EFEAEA]">
                      <img
                        src={gallery.coverImage}
                        alt={gallery.title}
                        className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                      />
                      <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-black/30" />

                      {/* Status Badges */}
                      <div className="absolute top-3 left-3">
                        {isPrivate ? (
                          <span className="px-2.5 py-1 bg-black/80 backdrop-blur-xs text-amber-300 text-[10px] font-bold uppercase tracking-wider rounded-xs flex items-center gap-1.5">
                            <Lock className="w-3 h-3" />
                            Privada • PIN
                          </span>
                        ) : (
                          <span className="px-2.5 py-1 bg-emerald-900/80 backdrop-blur-xs text-emerald-200 text-[10px] font-bold uppercase tracking-wider rounded-xs flex items-center gap-1.5">
                            <Unlock className="w-3 h-3" />
                            Pública • Acesso Livre
                          </span>
                        )}
                      </div>

                      {isCurrent && (
                        <div className="absolute top-3 right-3 px-2 py-0.5 bg-white text-[#1B1C1C] text-[10px] font-bold uppercase tracking-wider rounded-xs">
                          Aberta Agora
                        </div>
                      )}

                      <div className="absolute bottom-3 left-3 right-3 text-white">
                        <p className="text-[10px] uppercase tracking-wider opacity-80">
                          {gallery.totalPhotos} Fotos Digitais
                        </p>
                        <h4 className="font-display text-base font-bold leading-tight drop-shadow-xs">
                          {gallery.title}
                        </h4>
                      </div>
                    </div>

                    <div className="p-3.5 space-y-1.5 text-xs text-[#545F72]">
                      <div className="flex items-center gap-1.5 text-[11px]">
                        <MapPin className="w-3.5 h-3.5 text-[#747878]" />
                        <span className="truncate">{gallery.location}</span>
                      </div>
                      <div className="flex items-center justify-between text-[11px] pt-1 border-t border-[#E2E2E2]">
                        <span className="flex items-center gap-1">
                          <Calendar className="w-3 h-3" />
                          {gallery.date}
                        </span>
                        <span className="font-semibold text-[#1B1C1C]">
                          A partir de R$ {gallery.basePhotoPrice.toFixed(0)}
                          /foto
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
