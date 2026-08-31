import React, { useState, useMemo } from "react";
import { Gallery, Photo, PhotoCategory } from "../types";
import {
  Heart,
  Eye,
  ShoppingBag,
  SlidersHorizontal,
  Sparkles,
  Download,
  Filter,
  Grid3X3,
  Columns2,
  Search,
  CheckCircle2,
  Share2,
  Info,
} from "lucide-react";

interface GalleryViewProps {
  gallery: Gallery;
  onPhotoClick: (photo: Photo, index: number) => void;
  onToggleFavorite: (photoId: string) => void;
  onOpenPrintModal: (photo: Photo) => void;
  onStartSlideshow: () => void;
  onOpenAlbumBuilder: () => void;
  favoritesOnly?: boolean;
}

export const GalleryView: React.FC<GalleryViewProps> = ({
  gallery,
  onPhotoClick,
  onToggleFavorite,
  onOpenPrintModal,
  onStartSlideshow,
  onOpenAlbumBuilder,
  favoritesOnly = false,
}) => {
  const [activeCategory, setActiveCategory] = useState<string>(
    favoritesOnly ? "favoritas" : "todas",
  );
  const [layoutMode, setLayoutMode] = useState<"masonry" | "grid-2" | "grid-3">(
    "masonry",
  );
  const [searchQuery, setSearchQuery] = useState("");
  const [selectionMode, setSelectionMode] = useState(false);
  const [selectedPhotoIds, setSelectedPhotoIds] = useState<string[]>([]);
  const [downloadSuccessMsg, setDownloadSuccessMsg] = useState<string | null>(
    null,
  );

  // Filtered photos
  const filteredPhotos = useMemo(() => {
    return gallery.photos.filter((photo) => {
      // Category filter
      if (activeCategory === "favoritas") {
        if (!photo.isFavorite) return false;
      } else if (activeCategory !== "todas") {
        if (photo.category !== activeCategory) return false;
      }

      // Search query filter
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesTitle = photo.title.toLowerCase().includes(q);
        const matchesCategory = photo.category.toLowerCase().includes(q);
        const matchesCamera =
          photo.cameraInfo.camera.toLowerCase().includes(q) ||
          photo.cameraInfo.lens.toLowerCase().includes(q);
        if (!matchesTitle && !matchesCategory && !matchesCamera) return false;
      }

      return true;
    });
  }, [gallery.photos, activeCategory, searchQuery]);

  const favoritesCount = gallery.photos.filter((p) => p.isFavorite).length;

  const toggleSelectPhoto = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedPhotoIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id],
    );
  };

  const handleSelectAll = () => {
    if (selectedPhotoIds.length === filteredPhotos.length) {
      setSelectedPhotoIds([]);
    } else {
      setSelectedPhotoIds(filteredPhotos.map((p) => p.id));
    }
  };

  const handleDownloadBatch = () => {
    const count =
      selectedPhotoIds.length > 0
        ? selectedPhotoIds.length
        : filteredPhotos.length;
    setDownloadSuccessMsg(
      `Iniciando download do pacote ZIP com ${count} fotos em altíssima resolução (45MP / 300 DPI)...`,
    );
    setTimeout(() => {
      setDownloadSuccessMsg(null);
    }, 4500);
  };

  return (
    <div className="min-h-screen bg-[#FBF9F9] pt-24 pb-28 px-4 sm:px-8 md:px-16 max-w-[1440px] mx-auto">
      {/* Top Gallery Header Bar */}
      <div className="mb-10 animate-fade-in-up">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 pb-6 border-b border-[#E2E2E2]">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#545F72] mb-2">
              Galeria Completa • {gallery.location}
            </p>
            <h2 className="font-display text-3xl sm:text-4xl md:text-5xl font-bold text-[#1B1C1C] tracking-tight">
              {gallery.title}
            </h2>
          </div>

          {/* Quick Action Buttons */}
          <div className="flex flex-wrap items-center gap-2 sm:gap-3">
            <button
              onClick={onStartSlideshow}
              className="px-4 py-2.5 bg-white border border-[#C4C7C7] hover:border-[#1B1C1C] text-[#1B1C1C] text-xs uppercase tracking-wider font-medium flex items-center gap-2 rounded-xs transition-colors cursor-pointer"
            >
              <Sparkles className="w-3.5 h-3.5 text-[#545F72]" />
              Slideshow
            </button>

            <button
              onClick={onOpenAlbumBuilder}
              className="px-4 py-2.5 bg-white border border-[#C4C7C7] hover:border-[#1B1C1C] text-[#1B1C1C] text-xs uppercase tracking-wider font-medium flex items-center gap-2 rounded-xs transition-colors cursor-pointer"
            >
              <SlidersHorizontal className="w-3.5 h-3.5 text-[#545F72]" />
              Montar Álbum ({favoritesCount} fav)
            </button>

            <button
              onClick={() => setSelectionMode(!selectionMode)}
              className={`px-4 py-2.5 text-xs uppercase tracking-wider font-medium flex items-center gap-2 rounded-xs transition-colors cursor-pointer ${
                selectionMode
                  ? "bg-[#1B1C1C] text-white"
                  : "bg-white border border-[#C4C7C7] text-[#1B1C1C] hover:border-[#1B1C1C]"
              }`}
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              {selectionMode ? "Concluir Seleção" : "Modo Seleção"}
            </button>
          </div>
        </div>

        {/* Download notification banner */}
        {downloadSuccessMsg && (
          <div className="mt-4 p-4 bg-[#1B1C1C] text-white text-xs font-sans-body flex items-center justify-between animate-fade-in-up rounded-xs">
            <div className="flex items-center gap-2">
              <Download className="w-4 h-4 text-emerald-400" />
              <span>{downloadSuccessMsg}</span>
            </div>
            <span className="text-[10px] text-gray-400 uppercase tracking-widest">
              Markina Cloud Sync
            </span>
          </div>
        )}

        {/* Selection Bar when active */}
        {selectionMode && (
          <div className="mt-4 p-4 bg-[#EFEDED] border border-[#C4C7C7] flex flex-wrap items-center justify-between gap-4 rounded-xs">
            <div className="flex items-center gap-3">
              <span className="text-xs font-semibold text-[#1B1C1C] tracking-wide">
                {selectedPhotoIds.length} fotos selecionadas
              </span>
              <button
                onClick={handleSelectAll}
                className="text-xs text-[#545F72] hover:text-[#1B1C1C] underline cursor-pointer"
              >
                {selectedPhotoIds.length === filteredPhotos.length
                  ? "Desmarcar Todas"
                  : "Selecionar Visíveis"}
              </button>
            </div>

            <div className="flex items-center gap-2">
              <button
                disabled={selectedPhotoIds.length === 0}
                onClick={handleDownloadBatch}
                className="px-3 py-1.5 bg-[#1B1C1C] text-white disabled:opacity-40 text-xs font-medium uppercase tracking-wider flex items-center gap-1.5 rounded-xs cursor-pointer"
              >
                <Download className="w-3.5 h-3.5" />
                Baixar Seleção ({selectedPhotoIds.length})
              </button>
              <button
                onClick={onOpenAlbumBuilder}
                disabled={selectedPhotoIds.length === 0}
                className="px-3 py-1.5 bg-white border border-[#1B1C1C] text-[#1B1C1C] disabled:opacity-40 text-xs font-medium uppercase tracking-wider flex items-center gap-1.5 rounded-xs cursor-pointer"
              >
                Adicionar ao Álbum
              </button>
            </div>
          </div>
        )}

        {/* Filter and View Toolbar */}
        <div className="mt-6 flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          {/* Category Tabs */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-2 scrollbar-none">
            <button
              onClick={() => setActiveCategory("todas")}
              className={`px-3.5 py-2 text-xs uppercase tracking-wider font-medium whitespace-nowrap rounded-xs transition-all cursor-pointer ${
                activeCategory === "todas"
                  ? "bg-[#1B1C1C] text-white shadow-xs"
                  : "bg-white text-[#545F72] hover:text-[#1B1C1C] border border-[#E2E2E2]"
              }`}
            >
              Todas ({gallery.totalPhotos})
            </button>

            {gallery.categories
              .filter((c) => c.id !== "todas")
              .map((category) => (
                <button
                  key={category.id}
                  onClick={() => setActiveCategory(category.id)}
                  className={`px-3.5 py-2 text-xs uppercase tracking-wider font-medium whitespace-nowrap rounded-xs transition-all cursor-pointer ${
                    activeCategory === category.id
                      ? "bg-[#1B1C1C] text-white shadow-xs"
                      : "bg-white text-[#545F72] hover:text-[#1B1C1C] border border-[#E2E2E2]"
                  }`}
                >
                  {category.label} ({category.count})
                </button>
              ))}

            {/* Favorites Tab */}
            <button
              onClick={() => setActiveCategory("favoritas")}
              className={`px-3.5 py-2 text-xs uppercase tracking-wider font-medium whitespace-nowrap rounded-xs transition-all flex items-center gap-1.5 cursor-pointer ${
                activeCategory === "favoritas"
                  ? "bg-[#1B1C1C] text-white shadow-xs"
                  : "bg-white text-[#545F72] hover:text-[#1B1C1C] border border-[#E2E2E2]"
              }`}
            >
              <Heart
                className={`w-3.5 h-3.5 ${favoritesCount > 0 ? "fill-rose-500 text-rose-500" : ""}`}
              />
              Favoritas ({favoritesCount})
            </button>
          </div>

          {/* Search and Layout Grid Mode Switcher */}
          <div className="flex items-center gap-3 self-end lg:self-auto">
            {/* Search Input */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-[#747878] absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Buscar momento, lente..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-8 pr-3 py-1.5 bg-white border border-[#E2E2E2] focus:border-[#1B1C1C] text-xs text-[#1B1C1C] placeholder:text-[#747878] rounded-xs focus:outline-none w-44 sm:w-56"
              />
            </div>

            {/* Grid Layout Toggle */}
            <div className="hidden sm:flex items-center bg-white border border-[#E2E2E2] rounded-xs p-0.5">
              <button
                onClick={() => setLayoutMode("masonry")}
                title="Layout Masonry Natural"
                className={`p-1.5 rounded-xs transition-colors ${
                  layoutMode === "masonry"
                    ? "bg-[#1B1C1C] text-white"
                    : "text-[#545F72] hover:text-[#1B1C1C]"
                }`}
              >
                <Filter className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setLayoutMode("grid-2")}
                title="Grid Editorial 2 Colunas"
                className={`p-1.5 rounded-xs transition-colors ${
                  layoutMode === "grid-2"
                    ? "bg-[#1B1C1C] text-white"
                    : "text-[#545F72] hover:text-[#1B1C1C]"
                }`}
              >
                <Columns2 className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setLayoutMode("grid-3")}
                title="Grid Compacto 3 Colunas"
                className={`p-1.5 rounded-xs transition-colors ${
                  layoutMode === "grid-3"
                    ? "bg-[#1B1C1C] text-white"
                    : "text-[#545F72] hover:text-[#1B1C1C]"
                }`}
              >
                <Grid3X3 className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Photo Grid Section */}
      {filteredPhotos.length === 0 ? (
        <div className="py-24 text-center border border-dashed border-[#C4C7C7] rounded-xs bg-[#F5F3F3]">
          <Heart className="w-8 h-8 text-[#747878] mx-auto mb-3 stroke-[1.5]" />
          <h3 className="font-display text-xl font-semibold text-[#1B1C1C] mb-1">
            Nenhuma fotografia encontrada
          </h3>
          <p className="text-xs text-[#545F72] max-w-sm mx-auto mb-4">
            {activeCategory === "favoritas"
              ? "Você ainda não marcou nenhuma foto com coração. Clique no ícone de coração em qualquer foto para salvá-la aqui."
              : "Tente ajustar sua busca ou categoria para visualizar mais fotografias."}
          </p>
          <button
            onClick={() => {
              setActiveCategory("todas");
              setSearchQuery("");
            }}
            className="px-4 py-2 bg-[#1B1C1C] text-white text-xs uppercase tracking-wider font-medium rounded-xs"
          >
            Ver Todas as Fotos
          </button>
        </div>
      ) : (
        <div
          className={
            layoutMode === "masonry"
              ? "columns-1 sm:columns-2 lg:columns-3 gap-6 space-y-6"
              : layoutMode === "grid-2"
                ? "grid grid-cols-1 md:grid-cols-2 gap-8"
                : "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5"
          }
        >
          {filteredPhotos.map((photo, index) => {
            const isSelected = selectedPhotoIds.includes(photo.id);

            return (
              <div
                key={photo.id}
                onClick={() => {
                  if (selectionMode) {
                    toggleSelectPhoto(photo.id, {} as any);
                  } else {
                    onPhotoClick(photo, index);
                  }
                }}
                className={`group relative bg-white border transition-all duration-300 break-inside-avoid cursor-pointer overflow-hidden ${
                  isSelected
                    ? "border-[#1B1C1C] ring-2 ring-[#1B1C1C]"
                    : "border-[#E2E2E2] hover:border-[#747878] hover:shadow-sm"
                }`}
                style={{ borderRadius: 0 }} // Per brand spec: 0px corner radius for photos
              >
                {/* Image Container */}
                <div className="relative overflow-hidden bg-[#EFEAEA]">
                  <img
                    src={photo.url}
                    alt={photo.title}
                    loading="lazy"
                    className="w-full object-cover transition-transform duration-700 ease-out group-hover:scale-[1.03]"
                    style={{
                      aspectRatio:
                        layoutMode === "grid-2"
                          ? "4/3"
                          : layoutMode === "grid-3"
                            ? "1/1"
                            : photo.aspectRatio === "portrait"
                              ? "3/4"
                              : photo.aspectRatio === "square"
                                ? "1/1"
                                : "16/10",
                    }}
                  />

                  {/* Top Bar Floating Badges / Action Controls */}
                  <div className="absolute top-3 left-3 right-3 flex items-center justify-between opacity-90 sm:opacity-0 group-hover:opacity-100 transition-opacity duration-300 z-10 pointer-events-auto">
                    {/* Selection Checkbox */}
                    {selectionMode ? (
                      <button
                        onClick={(e) => toggleSelectPhoto(photo.id, e)}
                        className={`w-7 h-7 rounded-xs flex items-center justify-center transition-colors ${
                          isSelected
                            ? "bg-[#1B1C1C] text-white"
                            : "bg-white/90 text-transparent border border-black/30"
                        }`}
                      >
                        <CheckCircle2 className="w-4 h-4 text-white" />
                      </button>
                    ) : (
                      <span className="text-[10px] uppercase tracking-wider font-semibold px-2 py-1 bg-[#1B1C1C]/80 backdrop-blur-xs text-white rounded-xs">
                        {photo.cameraInfo.focalLength} •{" "}
                        {photo.cameraInfo.aperture}
                      </span>
                    )}

                    {/* Action buttons (Favorite & Print) */}
                    <div
                      className="flex items-center gap-1.5"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onToggleFavorite(photo.id);
                        }}
                        title={
                          photo.isFavorite
                            ? "Remover dos favoritos"
                            : "Favoritar"
                        }
                        className={`p-2 rounded-xs backdrop-blur-md transition-transform active:scale-90 ${
                          photo.isFavorite
                            ? "bg-white text-rose-500 shadow-xs"
                            : "bg-white/90 text-[#1B1C1C] hover:bg-white hover:text-rose-500"
                        }`}
                      >
                        <Heart
                          className={`w-4 h-4 ${
                            photo.isFavorite
                              ? "fill-rose-500 text-rose-500"
                              : "stroke-[1.5]"
                          }`}
                        />
                      </button>

                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onOpenPrintModal(photo);
                        }}
                        title="Pedir Impressão Fine Art"
                        className="p-2 bg-white/90 hover:bg-white text-[#1B1C1C] rounded-xs backdrop-blur-md transition-colors"
                      >
                        <ShoppingBag className="w-4 h-4 stroke-[1.5]" />
                      </button>
                    </div>
                  </div>

                  {/* Full View Icon on hover */}
                  <div className="absolute inset-0 bg-black/10 opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-center justify-center pointer-events-none">
                    <div className="p-3 bg-white/90 backdrop-blur-xs rounded-full shadow-md text-[#1B1C1C]">
                      <Eye className="w-5 h-5 stroke-[1.5]" />
                    </div>
                  </div>
                </div>

                {/* Photo Caption & Metadata */}
                <div className="p-3.5 bg-white border-t border-[#F5F3F3]">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <h4 className="font-display text-sm font-semibold text-[#1B1C1C] leading-snug line-clamp-1">
                        {photo.title}
                      </h4>
                      <p className="text-[11px] text-[#545F72] uppercase tracking-wider mt-0.5">
                        {photo.category} • {photo.cameraInfo.time}
                      </p>
                    </div>

                    <span className="text-[11px] font-sans-body text-[#747878] shrink-0 font-medium">
                      45 MP
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Bottom Floating Stats & Batch Action Trigger */}
      <div className="mt-16 p-6 bg-white border border-[#E2E2E2] rounded-xs flex flex-col md:flex-row items-center justify-between gap-6 shadow-xs">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 bg-[#F5F3F3] rounded-xs flex items-center justify-center">
            <Sparkles className="w-6 h-6 text-[#1B1C1C] stroke-[1.5]" />
          </div>
          <div>
            <h4 className="font-display text-lg font-bold text-[#1B1C1C]">
              Seleção &amp; Álbum Fotográfico Físico
            </h4>
            <p className="text-xs text-[#545F72]">
              Você já marcou {favoritesCount} fotos favoritas. Selecione entre
              40 e 60 fotos para a diagramação do álbum encadernado.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 w-full md:w-auto">
          <button
            onClick={handleDownloadBatch}
            className="flex-1 md:flex-none px-5 py-3 bg-white border border-[#1B1C1C] text-[#1B1C1C] hover:bg-[#F5F3F3] text-xs font-medium uppercase tracking-wider flex items-center justify-center gap-2 rounded-xs transition-colors cursor-pointer"
          >
            <Download className="w-4 h-4" />
            Baixar Galeria (ZIP)
          </button>
          <button
            onClick={onOpenAlbumBuilder}
            className="flex-1 md:flex-none px-6 py-3 bg-[#000000] text-white hover:bg-[#2A2A2A] text-xs font-medium uppercase tracking-wider flex items-center justify-center gap-2 rounded-xs transition-colors cursor-pointer"
          >
            Diagramar Álbum
          </button>
        </div>
      </div>
    </div>
  );
};
