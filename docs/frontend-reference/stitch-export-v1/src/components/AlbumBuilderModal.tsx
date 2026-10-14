import React, { useState } from "react";
import { Gallery, Photo, AlbumConfig, CartItem } from "../types";
import {
  X,
  Check,
  BookOpen,
  Sparkles,
  Heart,
  Layers,
  SlidersHorizontal,
  ArrowRight,
  ShieldCheck,
} from "lucide-react";
import confetti from "canvas-confetti";

interface AlbumBuilderModalProps {
  gallery: Gallery;
  onClose: () => void;
  onAddToCart: (item: Omit<CartItem, "id">) => void;
}

export const AlbumBuilderModal: React.FC<AlbumBuilderModalProps> = ({
  gallery,
  onClose,
  onAddToCart,
}) => {
  const [selectedPhotoIds, setSelectedPhotoIds] = useState<string[]>(
    gallery.photos.filter((p) => p.isFavorite).map((p) => p.id),
  );

  const [coverMaterial, setCoverMaterial] = useState<
    "couro-conhaque" | "linho-areia" | "couro-preto" | "veludo-verde"
  >("couro-conhaque");
  const [embossingColor, setEmbossingColor] = useState<
    "gold" | "silver" | "blind-deboss"
  >("gold");
  const [pageSize, setPageSize] = useState<"30x30" | "25x25" | "30x40">(
    "30x30",
  );
  const [coverText, setCoverText] = useState("Marina & Ricardo\n15.10.2023");
  const [step, setStep] = useState<"photos" | "cover" | "review">("photos");
  const [submitted, setSubmitted] = useState(false);

  const targetPhotos = 50;
  const progress = Math.min(
    100,
    Math.round((selectedPhotoIds.length / targetPhotos) * 100),
  );

  const togglePhoto = (id: string) => {
    setSelectedPhotoIds((prev) =>
      prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id],
    );
  };

  const coverMaterialDetails = {
    "couro-conhaque": {
      name: "Couro Conhaque Italiano",
      desc: "Couro natural macio com pátina artesanal vintage.",
      bgClass: "bg-[#7C482B] text-amber-100",
    },
    "linho-areia": {
      name: "Linho Puro Areia & Fibras Naturais",
      desc: "Tecido orgânico premium com textura refinada.",
      bgClass: "bg-[#DDD5C7] text-[#2A2621]",
    },
    "couro-preto": {
      name: "Couro Preto Imperial",
      desc: "Acabamento executivo luxuoso com toque aveludado.",
      bgClass: "bg-[#1A1A1A] text-white",
    },
    "veludo-verde": {
      name: "Veludo Verde Botânico",
      desc: "Toque sedoso com profundidade de tom clássico.",
      bgClass: "bg-[#1C352D] text-emerald-100",
    },
  };

  const basePrice =
    pageSize === "30x30" ? 2400 : pageSize === "25x25" ? 1900 : 2900;

  const handleFinish = () => {
    onAddToCart({
      photoId: selectedPhotoIds[0] || gallery.photos[0].id,
      photoTitle: `Álbum Luxo Envernizado (${selectedPhotoIds.length} fotos selecionadas)`,
      photoUrl: gallery.coverImage,
      type: "album",
      sizeLabel: `${pageSize} cm (40 Páginas / 20 Lâminas)`,
      paperLabel: "Papel Fotográfico Silk 800g com Laminação UV",
      frameLabel: `${coverMaterialDetails[coverMaterial].name} • Gravação ${embossingColor}`,
      price: basePrice,
      quantity: 1,
    });

    confetti({
      particleCount: 80,
      spread: 70,
      origin: { y: 0.6 },
    });

    setSubmitted(true);
    setTimeout(() => {
      onClose();
    }, 2000);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-md flex items-center justify-center p-4 sm:p-6 overflow-y-auto">
      <div className="bg-[#FBF9F9] w-full max-w-5xl rounded-xs shadow-2xl overflow-hidden border border-[#E2E2E2] my-auto flex flex-col max-h-[92vh] animate-fade-in-up">
        {/* Modal Header */}
        <div className="p-6 bg-white border-b border-[#E2E2E2] flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-[#F5F3F3] rounded-xs flex items-center justify-center">
              <BookOpen className="w-5 h-5 text-[#1B1C1C] stroke-[1.5]" />
            </div>
            <div>
              <span className="text-[10px] uppercase tracking-widest font-semibold text-[#545F72]">
                Markina Studio Atelier
              </span>
              <h3 className="font-display text-xl sm:text-2xl font-bold text-[#1B1C1C]">
                Curadoria &amp; Diagramação do Álbum de Casamento
              </h3>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-2 text-[#545F72] hover:text-[#1B1C1C] rounded-xs hover:bg-[#EFEAEA] transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Wizard Steps Navigation */}
        <div className="px-6 py-3 bg-[#F5F3F3] border-b border-[#E2E2E2] flex items-center justify-between text-xs">
          <div className="flex items-center gap-4 sm:gap-8">
            <button
              onClick={() => setStep("photos")}
              className={`flex items-center gap-2 font-medium uppercase tracking-wider pb-1 transition-colors ${
                step === "photos"
                  ? "text-[#1B1C1C] border-b-2 border-[#1B1C1C] font-bold"
                  : "text-[#545F72]"
              }`}
            >
              <span className="w-5 h-5 rounded-full bg-[#1B1C1C] text-white text-[10px] flex items-center justify-center">
                1
              </span>
              Seleção de Fotos ({selectedPhotoIds.length})
            </button>

            <button
              onClick={() => setStep("cover")}
              className={`flex items-center gap-2 font-medium uppercase tracking-wider pb-1 transition-colors ${
                step === "cover"
                  ? "text-[#1B1C1C] border-b-2 border-[#1B1C1C] font-bold"
                  : "text-[#545F72]"
              }`}
            >
              <span className="w-5 h-5 rounded-full bg-[#1B1C1C] text-white text-[10px] flex items-center justify-center">
                2
              </span>
              Capa &amp; Gravação
            </button>

            <button
              onClick={() => setStep("review")}
              className={`flex items-center gap-2 font-medium uppercase tracking-wider pb-1 transition-colors ${
                step === "review"
                  ? "text-[#1B1C1C] border-b-2 border-[#1B1C1C] font-bold"
                  : "text-[#545F72]"
              }`}
            >
              <span className="w-5 h-5 rounded-full bg-[#1B1C1C] text-white text-[10px] flex items-center justify-center">
                3
              </span>
              Revisão &amp; Envio
            </button>
          </div>

          <div className="hidden sm:flex items-center gap-2">
            <span className="text-[11px] text-[#747878] font-mono">
              {selectedPhotoIds.length} / {targetPhotos} fotos
            </span>
            <div className="w-24 h-2 bg-[#E2E2E2] rounded-full overflow-hidden">
              <div
                className="h-full bg-[#1B1C1C] transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        </div>

        {/* Modal Body */}
        <div className="flex-1 p-6 sm:p-8 overflow-y-auto bg-[#FBF9F9]">
          {step === "photos" && (
            <div>
              <div className="mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <h4 className="font-display text-xl font-bold text-[#1B1C1C]">
                    Selecione de 40 a 60 fotografias para a narrativa
                  </h4>
                  <p className="text-xs text-[#545F72] mt-1">
                    Clique nas fotos para adicioná-las ou removê-las da
                    diagramação do álbum físico.
                  </p>
                </div>

                <button
                  onClick={() =>
                    setSelectedPhotoIds(
                      gallery.photos
                        .filter((p) => p.isFavorite)
                        .map((p) => p.id),
                    )
                  }
                  className="px-3 py-1.5 bg-white border border-[#C4C7C7] text-xs font-medium uppercase tracking-wider text-[#1B1C1C] rounded-xs hover:border-[#1B1C1C]"
                >
                  Usar Minhas{" "}
                  {gallery.photos.filter((p) => p.isFavorite).length} Favoritas
                </button>
              </div>

              {/* Photo Selector Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
                {gallery.photos.map((photo) => {
                  const isSelected = selectedPhotoIds.includes(photo.id);

                  return (
                    <div
                      key={photo.id}
                      onClick={() => togglePhoto(photo.id)}
                      className={`relative group cursor-pointer border rounded-xs overflow-hidden transition-all ${
                        isSelected
                          ? "border-[#1B1C1C] ring-2 ring-[#1B1C1C]"
                          : "border-[#E2E2E2] hover:border-[#747878]"
                      }`}
                    >
                      <img
                        src={photo.url}
                        alt={photo.title}
                        className="w-full aspect-square object-cover"
                      />

                      {/* Selection Checkbox */}
                      <div
                        className={`absolute top-2 right-2 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                          isSelected
                            ? "bg-[#1B1C1C] text-white shadow-md"
                            : "bg-white/80 text-transparent group-hover:text-gray-400 border border-black/20"
                        }`}
                      >
                        <Check className="w-3.5 h-3.5" />
                      </div>

                      {/* Title overlay */}
                      <div className="p-1.5 bg-white/90 text-[10px] truncate text-[#1B1C1C] font-medium border-t border-gray-100">
                        {photo.title}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {step === "cover" && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              {/* Live Album Cover Mockup */}
              <div className="flex flex-col items-center justify-center p-8 bg-[#ECEAE8] rounded-xs border border-[#E2E2E2]">
                <div
                  className={`w-64 h-64 sm:w-72 sm:h-72 rounded-sm shadow-2xl p-8 flex flex-col justify-center items-center text-center transition-all duration-500 relative border-l-8 border-black/20 ${
                    coverMaterialDetails[coverMaterial].bgClass
                  }`}
                >
                  <div className="border border-current/20 p-6 w-full h-full flex flex-col justify-center items-center">
                    <Sparkles className="w-5 h-5 mb-3 opacity-60" />
                    <pre
                      className={`font-display text-lg sm:text-xl font-bold uppercase tracking-wider whitespace-pre-line leading-relaxed ${
                        embossingColor === "gold"
                          ? "text-[#E5B558] drop-shadow-sm"
                          : embossingColor === "silver"
                            ? "text-[#E0E0E0] drop-shadow-sm"
                            : "opacity-70"
                      }`}
                    >
                      {coverText || "Marina & Ricardo"}
                    </pre>
                  </div>
                </div>

                <p className="text-[11px] text-[#545F72] uppercase tracking-wider mt-4">
                  Visualização da Capa com Gravação em Hot Stamping
                </p>
              </div>

              {/* Cover Options */}
              <div className="space-y-6">
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-[#1B1C1C] mb-2">
                    Material &amp; Revestimento da Capa
                  </label>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                    {(
                      Object.keys(
                        coverMaterialDetails,
                      ) as (keyof typeof coverMaterialDetails)[]
                    ).map((key) => {
                      const mat = coverMaterialDetails[key];
                      const isSelected = coverMaterial === key;

                      return (
                        <button
                          key={key}
                          onClick={() => setCoverMaterial(key)}
                          className={`p-3 text-left border rounded-xs transition-all cursor-pointer ${
                            isSelected
                              ? "border-[#1B1C1C] bg-white ring-1 ring-[#1B1C1C]"
                              : "border-[#E2E2E2] bg-white hover:border-[#747878]"
                          }`}
                        >
                          <p className="text-xs font-bold text-[#1B1C1C]">
                            {mat.name}
                          </p>
                          <p className="text-[10px] text-[#545F72] mt-0.5">
                            {mat.desc}
                          </p>
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-[#1B1C1C] mb-2">
                    Gravação / Hot Stamping
                  </label>
                  <div className="grid grid-cols-3 gap-2">
                    {[
                      { id: "gold", label: "Ouro 24k Reluzente" },
                      { id: "silver", label: "Prata Nobre" },
                      { id: "blind-deboss", label: "Baixo-Relevo Seco" },
                    ].map((emb) => (
                      <button
                        key={emb.id}
                        onClick={() => setEmbossingColor(emb.id as any)}
                        className={`p-2.5 text-center border rounded-xs text-xs font-medium transition-all cursor-pointer ${
                          embossingColor === emb.id
                            ? "border-[#1B1C1C] bg-white ring-1 ring-[#1B1C1C] font-bold text-[#1B1C1C]"
                            : "border-[#E2E2E2] bg-white text-[#545F72]"
                        }`}
                      >
                        {emb.label}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-[#1B1C1C] mb-2">
                    Texto da Capa
                  </label>
                  <textarea
                    rows={2}
                    value={coverText}
                    onChange={(e) => setCoverText(e.target.value)}
                    placeholder="Ex: Marina & Ricardo • 15 de Outubro de 2023"
                    className="w-full p-3 bg-white border border-[#C4C7C7] focus:border-[#1B1C1C] text-xs text-[#1B1C1C] rounded-xs focus:outline-none"
                  />
                </div>
              </div>
            </div>
          )}

          {step === "review" && (
            <div className="max-w-2xl mx-auto bg-white p-8 border border-[#E2E2E2] rounded-xs">
              <div className="text-center mb-8 pb-6 border-b border-[#E2E2E2]">
                <Sparkles className="w-8 h-8 text-[#1B1C1C] mx-auto mb-2 stroke-[1.5]" />
                <h4 className="font-display text-2xl font-bold text-[#1B1C1C]">
                  Resumo do seu Álbum Exclusivo
                </h4>
                <p className="text-xs text-[#545F72] mt-1">
                  Revisão completa antes do envio para o ateliê de encadernação
                  Markina.
                </p>
              </div>

              <div className="space-y-4 text-xs font-sans-body mb-8">
                <div className="flex justify-between py-2 border-b border-gray-100">
                  <span className="text-[#545F72]">
                    Quantidade de Fotografias:
                  </span>
                  <strong className="text-[#1B1C1C]">
                    {selectedPhotoIds.length} fotos selecionadas
                  </strong>
                </div>

                <div className="flex justify-between py-2 border-b border-gray-100">
                  <span className="text-[#545F72]">Formato do Álbum:</span>
                  <strong className="text-[#1B1C1C]">
                    {pageSize} cm Quadrado Panorâmico (Abertura 180° Layflat)
                  </strong>
                </div>

                <div className="flex justify-between py-2 border-b border-gray-100">
                  <span className="text-[#545F72]">Revestimento da Capa:</span>
                  <strong className="text-[#1B1C1C]">
                    {coverMaterialDetails[coverMaterial].name}
                  </strong>
                </div>

                <div className="flex justify-between py-2 border-b border-gray-100">
                  <span className="text-[#545F72]">
                    Acabamento de Gravação:
                  </span>
                  <strong className="text-[#1B1C1C]">
                    Hot Stamping {embossingColor}
                  </strong>
                </div>

                <div className="flex justify-between py-2 border-b border-gray-100">
                  <span className="text-[#545F72]">Papel Interno:</span>
                  <strong className="text-[#1B1C1C]">
                    Fotográfico Silk 800g/m² com Proteção UV
                  </strong>
                </div>

                <div className="flex justify-between py-3 border-t-2 border-[#1B1C1C]">
                  <span className="font-bold text-sm text-[#1B1C1C]">
                    Valor Total do Álbum:
                  </span>
                  <span className="font-display text-xl font-bold text-[#1B1C1C]">
                    R$ {basePrice.toFixed(2).replace(".", ",")}
                  </span>
                </div>
              </div>

              <div className="p-4 bg-[#F5F3F3] rounded-xs flex items-start gap-3 mb-6">
                <ShieldCheck className="w-5 h-5 text-emerald-700 shrink-0 mt-0.5" />
                <p className="text-[11px] text-[#545F72] leading-relaxed">
                  <strong>Garantia Vitalícia:</strong> Nossos álbuns são
                  confeccionados artesanalmente com papéis livres de ácido e
                  encadernação térmica resistente à umidade e ao tempo.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer Controls */}
        <div className="p-6 bg-white border-t border-[#E2E2E2] flex items-center justify-between">
          {step === "photos" ? (
            <button
              onClick={onClose}
              className="px-5 py-2.5 text-xs uppercase tracking-wider font-medium text-[#545F72] hover:text-[#1B1C1C]"
            >
              Cancelar
            </button>
          ) : (
            <button
              onClick={() => setStep(step === "review" ? "cover" : "photos")}
              className="px-5 py-2.5 text-xs uppercase tracking-wider font-medium text-[#545F72] hover:text-[#1B1C1C]"
            >
              ← Voltar
            </button>
          )}

          {step === "photos" && (
            <button
              onClick={() => setStep("cover")}
              disabled={selectedPhotoIds.length === 0}
              className="px-6 py-3 bg-[#1B1C1C] disabled:opacity-40 text-white text-xs font-semibold uppercase tracking-wider rounded-xs flex items-center gap-2 cursor-pointer hover:bg-[#2A2A2A]"
            >
              <span>Personalizar Capa ({selectedPhotoIds.length} fotos)</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          )}

          {step === "cover" && (
            <button
              onClick={() => setStep("review")}
              className="px-6 py-3 bg-[#1B1C1C] text-white text-xs font-semibold uppercase tracking-wider rounded-xs flex items-center gap-2 cursor-pointer hover:bg-[#2A2A2A]"
            >
              <span>Revisar Álbum</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          )}

          {step === "review" && (
            <button
              onClick={handleFinish}
              disabled={submitted}
              className="px-8 py-3.5 bg-[#000000] text-white text-xs font-semibold uppercase tracking-widest rounded-xs flex items-center gap-2 cursor-pointer hover:bg-[#2A2A2A] shadow-md"
            >
              {submitted ? (
                <>
                  <Check className="w-4 h-4 text-emerald-400" />
                  Álbum Adicionado com Sucesso!
                </>
              ) : (
                <>
                  <BookOpen className="w-4 h-4" />
                  Finalizar &amp; Adicionar ao Pedido
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
