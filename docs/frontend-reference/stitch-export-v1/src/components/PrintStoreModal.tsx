import React, { useState } from "react";
import {
  Photo,
  PrintSize,
  PrintPaperType,
  FrameOption,
  CartItem,
} from "../types";
import { PRINT_SIZES } from "../data/galleriesData";
import {
  X,
  Check,
  ShoppingBag,
  Sparkles,
  Image as ImageIcon,
  Home,
  Eye,
} from "lucide-react";

interface PrintStoreModalProps {
  photo: Photo;
  onClose: () => void;
  onAddToCart: (item: Omit<CartItem, "id">) => void;
}

export const PrintStoreModal: React.FC<PrintStoreModalProps> = ({
  photo,
  onClose,
  onAddToCart,
}) => {
  const [selectedSize, setSelectedSize] = useState<PrintSize>(PRINT_SIZES[1]); // 30x45 default
  const [selectedPaper, setSelectedPaper] =
    useState<PrintPaperType>("hahnemuhle-rag");
  const [selectedFrame, setSelectedFrame] = useState<FrameOption>("oak-wood");
  const [quantity, setQuantity] = useState(1);
  const [activePreviewRoom, setActivePreviewRoom] = useState<
    "living" | "minimal" | "close-up"
  >("living");
  const [addedNotice, setAddedNotice] = useState(false);

  const paperNames: Record<
    PrintPaperType,
    { title: string; desc: string; extra: number }
  > = {
    "hahnemuhle-rag": {
      title: "Hahnemühle Photo Rag 308g",
      desc: "100% Algodão, padrão museu com longevidade de 100+ anos.",
      extra: 60,
    },
    "silk-matte": {
      title: "Papel Fotográfico Silk Fosco",
      desc: "Toque aveludado, antirreflexo com pretos profundos.",
      extra: 0,
    },
    canvas: {
      title: "Canvas Algodão Fine Art 380g",
      desc: "Textura de tela artística esticada em chassi de madeira nobre.",
      extra: 90,
    },
    metallic: {
      title: "Papel Metálico Pearl 260g",
      desc: "Brilho acetinado com profundidade e cores vibrantes.",
      extra: 40,
    },
  };

  const frameNames: Record<
    FrameOption,
    { title: string; desc: string; borderClass: string }
  > = {
    none: {
      title: "Sem Moldura (Apenas Impressão)",
      desc: "Enviado em tubo rígido protegido com papel vegetal neutro.",
      borderClass: "border-0",
    },
    "oak-wood": {
      title: "Carvalho Natural com Paspatur",
      desc: "Madeira maciça clara certificada e paspatur livre de ácido.",
      borderClass: "border-[12px] border-[#c2a47e] shadow-xl",
    },
    "black-minimal": {
      title: "Preto Minimalista com Paspatur",
      desc: "Madeira laqueada preta fosca com vidro museológico.",
      borderClass: "border-[12px] border-[#1a1a1a] shadow-xl",
    },
    "walnut-wood": {
      title: "Nogueira Nobre com Paspatur",
      desc: "Tons escuros e sofisticados em madeira de lei reflorestada.",
      borderClass: "border-[12px] border-[#533827] shadow-xl",
    },
    "white-gallery": {
      title: "Branco Galeria com Paspatur",
      desc: "Acabamento contemporâneo para ambientes limpos e claros.",
      borderClass: "border-[12px] border-[#f0f0f0] shadow-xl",
    },
  };

  // Calculate item unit price
  const basePrice = selectedSize.price;
  const framePrice = selectedSize.framePrices[selectedFrame] || 0;
  const paperExtra = paperNames[selectedPaper].extra;
  const unitPrice = basePrice + framePrice + paperExtra;
  const totalPrice = unitPrice * quantity;

  const handleAdd = () => {
    onAddToCart({
      photoId: photo.id,
      photoTitle: photo.title,
      photoUrl: photo.url,
      type: selectedFrame === "none" ? "print" : "framed-print",
      sizeLabel: selectedSize.label,
      paperType: selectedPaper,
      paperLabel: paperNames[selectedPaper].title,
      frame: selectedFrame,
      frameLabel: frameNames[selectedFrame].title,
      price: unitPrice,
      quantity: quantity,
    });

    setAddedNotice(true);
    setTimeout(() => {
      onClose();
    }, 1200);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 sm:p-6 overflow-y-auto">
      <div className="bg-[#FBF9F9] w-full max-w-5xl rounded-xs shadow-2xl overflow-hidden border border-[#E2E2E2] my-auto flex flex-col md:flex-row max-h-[90vh] animate-fade-in-up">
        {/* Left: Interactive Mockup Wall Visualizer */}
        <div className="w-full md:w-1/2 bg-[#ECEAE8] p-6 flex flex-col justify-between relative border-b md:border-b-0 md:border-r border-[#E2E2E2]">
          {/* Room switcher pills */}
          <div className="flex items-center justify-between mb-4 z-10">
            <span className="text-[11px] uppercase tracking-widest font-semibold text-[#545F72] flex items-center gap-1.5">
              <Eye className="w-3.5 h-3.5" />
              Simulação de Ambiente
            </span>

            <div className="flex items-center gap-1 bg-white/80 p-1 rounded-xs border border-[#C4C7C7]">
              <button
                onClick={() => setActivePreviewRoom("living")}
                className={`px-2 py-1 text-[10px] uppercase tracking-wider font-medium rounded-xs transition-colors ${
                  activePreviewRoom === "living"
                    ? "bg-[#1B1C1C] text-white"
                    : "text-[#545F72] hover:text-[#1B1C1C]"
                }`}
              >
                Sala
              </button>
              <button
                onClick={() => setActivePreviewRoom("minimal")}
                className={`px-2 py-1 text-[10px] uppercase tracking-wider font-medium rounded-xs transition-colors ${
                  activePreviewRoom === "minimal"
                    ? "bg-[#1B1C1C] text-white"
                    : "text-[#545F72] hover:text-[#1B1C1C]"
                }`}
              >
                Galeria
              </button>
              <button
                onClick={() => setActivePreviewRoom("close-up")}
                className={`px-2 py-1 text-[10px] uppercase tracking-wider font-medium rounded-xs transition-colors ${
                  activePreviewRoom === "close-up"
                    ? "bg-[#1B1C1C] text-white"
                    : "text-[#545F72] hover:text-[#1B1C1C]"
                }`}
              >
                Detalhe
              </button>
            </div>
          </div>

          {/* Simulated Living Room Environment */}
          <div className="flex-1 flex items-center justify-center py-6 relative overflow-hidden min-h-[300px]">
            {/* Background Texture / Wall */}
            <div className="absolute inset-0 bg-[#E8E6E3] flex flex-col justify-between pointer-events-none">
              <div className="w-full h-full bg-[radial-gradient(#d3cfc8_1px,transparent_1px)] [background-size:16px_16px] opacity-40" />
            </div>

            {/* Framed Artwork Element */}
            <div className="relative z-10 max-w-[260px] sm:max-w-[320px] transition-all duration-500">
              <div
                className={`bg-white p-3 sm:p-4 transition-all duration-300 ${
                  frameNames[selectedFrame].borderClass
                }`}
              >
                <img
                  src={photo.url}
                  alt={photo.title}
                  className="w-full object-cover max-h-[260px] shadow-inner"
                  style={{
                    aspectRatio:
                      photo.aspectRatio === "portrait"
                        ? "3/4"
                        : photo.aspectRatio === "square"
                          ? "1/1"
                          : "4/3",
                  }}
                />
              </div>

              {/* Dimensions tag */}
              <div className="text-center mt-3">
                <span className="text-[10px] uppercase tracking-widest font-mono text-[#545F72] bg-white/90 px-2 py-0.5 rounded-xs border border-[#C4C7C7]">
                  {selectedSize.dimensions} •{" "}
                  {selectedFrame !== "none" ? "Com Paspatur" : "Impressão Solo"}
                </span>
              </div>
            </div>

            {/* Furniture Mockup for Living Room */}
            {activePreviewRoom === "living" && (
              <div className="absolute bottom-0 w-full h-12 bg-[#3C322C] border-t-4 border-[#2A231F] rounded-t-xs shadow-md opacity-80 pointer-events-none flex items-center justify-center">
                <div className="w-48 h-2 bg-[#5A4B42] rounded-full" />
              </div>
            )}
          </div>

          {/* Authenticity Certificate Note */}
          <div className="bg-white/80 p-3 border border-[#E2E2E2] rounded-xs flex items-center gap-3">
            <Sparkles className="w-4 h-4 text-[#1B1C1C] shrink-0" />
            <p className="text-[11px] text-[#545F72] leading-tight">
              Acompanha{" "}
              <strong className="text-[#1B1C1C]">
                Certificado de Autenticidade
              </strong>{" "}
              numerado e assinado por Markina Studios com selo de garantia
              museológica.
            </p>
          </div>
        </div>

        {/* Right: Configuration & Purchase */}
        <div className="w-full md:w-1/2 p-6 sm:p-8 flex flex-col justify-between overflow-y-auto bg-[#FBF9F9]">
          <div>
            {/* Header */}
            <div className="flex items-start justify-between pb-4 border-b border-[#E2E2E2] mb-6">
              <div>
                <span className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#545F72]">
                  Fine Art Print Studio
                </span>
                <h3 className="font-display text-2xl font-bold text-[#1B1C1C]">
                  {photo.title}
                </h3>
              </div>
              <button
                onClick={onClose}
                className="p-1.5 text-[#545F72] hover:text-[#1B1C1C] rounded-xs hover:bg-[#EFEAEA] transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Step 1: Choose Size */}
            <div className="mb-6">
              <label className="block text-xs font-semibold uppercase tracking-wider text-[#1B1C1C] mb-2.5">
                1. Dimensão da Impressão
              </label>
              <div className="grid grid-cols-2 gap-2">
                {PRINT_SIZES.map((size) => (
                  <button
                    key={size.id}
                    onClick={() => setSelectedSize(size)}
                    className={`p-2.5 text-left border rounded-xs transition-all cursor-pointer ${
                      selectedSize.id === size.id
                        ? "border-[#1B1C1C] bg-white ring-1 ring-[#1B1C1C]"
                        : "border-[#E2E2E2] bg-white hover:border-[#747878]"
                    }`}
                  >
                    <p className="text-xs font-semibold text-[#1B1C1C]">
                      {size.label}
                    </p>
                    <p className="text-[11px] text-[#545F72] mt-0.5">
                      a partir de{" "}
                      <strong className="text-[#1B1C1C]">
                        R$ {size.price},00
                      </strong>
                    </p>
                  </button>
                ))}
              </div>
            </div>

            {/* Step 2: Choose Frame / Finishing */}
            <div className="mb-6">
              <label className="block text-xs font-semibold uppercase tracking-wider text-[#1B1C1C] mb-2.5">
                2. Moldura &amp; Acabamento
              </label>
              <div className="space-y-2">
                {(Object.keys(frameNames) as FrameOption[]).map((frameKey) => {
                  const frame = frameNames[frameKey];
                  const priceAdd = selectedSize.framePrices[frameKey] || 0;
                  const isSelected = selectedFrame === frameKey;

                  return (
                    <div
                      key={frameKey}
                      onClick={() => setSelectedFrame(frameKey)}
                      className={`p-3 border rounded-xs flex items-center justify-between cursor-pointer transition-all ${
                        isSelected
                          ? "border-[#1B1C1C] bg-white ring-1 ring-[#1B1C1C]"
                          : "border-[#E2E2E2] bg-white hover:border-[#747878]"
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <div
                          className={`w-4 h-4 rounded-full border flex items-center justify-center ${
                            isSelected
                              ? "border-[#1B1C1C] bg-[#1B1C1C]"
                              : "border-[#C4C7C7]"
                          }`}
                        >
                          {isSelected && (
                            <div className="w-1.5 h-1.5 bg-white rounded-full" />
                          )}
                        </div>
                        <div>
                          <p className="text-xs font-medium text-[#1B1C1C]">
                            {frame.title}
                          </p>
                          <p className="text-[11px] text-[#545F72]">
                            {frame.desc}
                          </p>
                        </div>
                      </div>

                      <span className="text-xs font-semibold text-[#1B1C1C] shrink-0 font-sans-body">
                        {priceAdd === 0 ? "+ R$ 0,00" : `+ R$ ${priceAdd},00`}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Step 3: Choose Paper */}
            <div className="mb-6">
              <label className="block text-xs font-semibold uppercase tracking-wider text-[#1B1C1C] mb-2.5">
                3. Substrato / Papel Fine Art
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {(Object.keys(paperNames) as PrintPaperType[]).map(
                  (paperKey) => {
                    const paper = paperNames[paperKey];
                    const isSelected = selectedPaper === paperKey;

                    return (
                      <button
                        key={paperKey}
                        onClick={() => setSelectedPaper(paperKey)}
                        className={`p-2.5 text-left border rounded-xs transition-all cursor-pointer ${
                          isSelected
                            ? "border-[#1B1C1C] bg-white ring-1 ring-[#1B1C1C]"
                            : "border-[#E2E2E2] bg-white hover:border-[#747878]"
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-semibold text-[#1B1C1C]">
                            {paper.title}
                          </span>
                          {paper.extra > 0 && (
                            <span className="text-[10px] font-mono text-[#545F72]">
                              +R${paper.extra}
                            </span>
                          )}
                        </div>
                        <p className="text-[10px] text-[#545F72] mt-1 leading-tight">
                          {paper.desc}
                        </p>
                      </button>
                    );
                  },
                )}
              </div>
            </div>
          </div>

          {/* Quantity & Order Summary Footer */}
          <div className="pt-5 border-t border-[#E2E2E2]">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <span className="text-xs uppercase tracking-wider text-[#545F72] font-medium">
                  Qtd:
                </span>
                <div className="flex items-center border border-[#C4C7C7] rounded-xs bg-white">
                  <button
                    onClick={() => setQuantity((q) => Math.max(1, q - 1))}
                    className="px-2.5 py-1 text-xs text-[#1B1C1C] hover:bg-[#F5F3F3]"
                  >
                    -
                  </button>
                  <span className="px-2.5 py-1 text-xs font-bold text-[#1B1C1C]">
                    {quantity}
                  </span>
                  <button
                    onClick={() => setQuantity((q) => q + 1)}
                    className="px-2.5 py-1 text-xs text-[#1B1C1C] hover:bg-[#F5F3F3]"
                  >
                    +
                  </button>
                </div>
              </div>

              <div className="text-right">
                <span className="text-[10px] uppercase tracking-widest text-[#747878] block">
                  Total da Peça
                </span>
                <span className="font-display text-2xl font-bold text-[#1B1C1C]">
                  R$ {totalPrice.toFixed(2).replace(".", ",")}
                </span>
              </div>
            </div>

            {addedNotice ? (
              <div className="w-full py-4 bg-emerald-700 text-white flex items-center justify-center gap-2 text-xs font-semibold uppercase tracking-wider rounded-xs animate-fade-in-up">
                <Check className="w-4 h-4" />
                Adicionado ao Carrinho com Sucesso!
              </div>
            ) : (
              <button
                onClick={handleAdd}
                className="w-full py-4 bg-[#000000] text-white hover:bg-[#2A2A2A] active:scale-[0.99] transition-all flex items-center justify-center gap-2 text-xs font-semibold uppercase tracking-widest rounded-xs cursor-pointer shadow-md"
              >
                <ShoppingBag className="w-4 h-4" />
                Adicionar ao Carrinho • R${" "}
                {totalPrice.toFixed(2).replace(".", ",")}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
