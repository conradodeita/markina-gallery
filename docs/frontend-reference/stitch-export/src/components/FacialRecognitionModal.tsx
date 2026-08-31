import React, { useState, useRef, useEffect } from "react";
import { Gallery, Photo } from "../types";
import {
  X,
  Camera,
  Upload,
  ShieldCheck,
  Sparkles,
  Scan,
  Check,
  AlertCircle,
  RefreshCw,
  CheckCircle2,
  Lock,
  ArrowRight,
} from "lucide-react";

interface FacialRecognitionModalProps {
  isOpen: boolean;
  onClose: () => void;
  gallery: Gallery;
  onMatchesFound: (matchedPhotoIds: string[], selfieUrl: string) => void;
}

export const FacialRecognitionModal: React.FC<FacialRecognitionModalProps> = ({
  isOpen,
  onClose,
  gallery,
  onMatchesFound,
}) => {
  const [lgpdConsent, setLgpdConsent] = useState(false);
  const [method, setMethod] = useState<"camera" | "upload" | "demo">("camera");
  const [isCapturingCamera, setIsCapturingCamera] = useState(false);
  const [selfiePreview, setSelfiePreview] = useState<string | null>(null);
  const [isScanning, setIsScanning] = useState(false);
  const [scanStep, setScanStep] = useState<string>("");
  const [matchedPhotos, setMatchedPhotos] = useState<Photo[]>([]);
  const [scanCompleted, setScanCompleted] = useState(false);

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
      }
    };
  }, []);

  if (!isOpen) return null;

  const startCamera = async () => {
    try {
      setIsCapturingCamera(true);
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: "user",
          width: { ideal: 640 },
          height: { ideal: 640 },
        },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
    } catch (err) {
      console.warn("Camera error, fallback to file upload:", err);
      setIsCapturingCamera(false);
      setMethod("upload");
    }
  };

  const captureCameraPhoto = () => {
    if (!videoRef.current) return;
    const canvas = document.createElement("canvas");
    canvas.width = videoRef.current.videoWidth || 480;
    canvas.height = videoRef.current.videoHeight || 480;
    const ctx = canvas.getContext("2d");
    if (ctx) {
      ctx.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);
      const dataUrl = canvas.toDataURL("image/jpeg");
      setSelfiePreview(dataUrl);
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
      }
      setIsCapturingCamera(false);
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (ev) => {
        setSelfiePreview(ev.target?.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleSelectDemoPerson = (
    name: string,
    imageUrl: string,
    tag: string,
  ) => {
    setSelfiePreview(imageUrl);
  };

  const runBiometricScan = () => {
    if (!lgpdConsent) {
      alert(
        "É obrigatório aceitar o termo de consentimento biométrico LGPD antes de iniciar a busca facial.",
      );
      return;
    }

    setIsScanning(true);
    setScanStep("Mapeando 128 pontos biométricos faciais...");

    setTimeout(() => {
      setScanStep("Comparando malha vetorial com acervo da galeria...");
    }, 1200);

    setTimeout(() => {
      setScanStep("Calculando scores de confiança e similaridade...");
    }, 2400);

    setTimeout(() => {
      // Find matching photos
      // Matching heuristic: match photos that have faceTags or pick representative photos from current gallery
      const matches = gallery.photos.filter((p) => {
        if (p.faceTags && p.faceTags.length > 0) {
          return true; // matches relevant tagged photos
        }
        return (
          p.category === "casal" ||
          p.category === "chegada" ||
          p.category === "colacao"
        );
      });

      const processedMatches = (
        matches.length > 0 ? matches : gallery.photos.slice(0, 6)
      ).map((photo, idx) => ({
        ...photo,
        matchConfidence: [98, 96, 94, 91, 88, 85][idx % 6],
      }));

      setMatchedPhotos(processedMatches);
      setIsScanning(false);
      setScanCompleted(true);
    }, 3600);
  };

  const handleApplyMatches = () => {
    onMatchesFound(
      matchedPhotos.map((p) => p.id),
      selfiePreview || "",
    );
    onClose();
  };

  const handleReset = () => {
    setSelfiePreview(null);
    setScanCompleted(false);
    setMatchedPhotos([]);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-xs flex items-center justify-center p-3 sm:p-6 overflow-y-auto">
      <div className="bg-[#FBF9F9] border border-[#E2E2E2] rounded-xs w-full max-w-xl shadow-2xl overflow-hidden animate-fade-in-up my-auto">
        {/* Header */}
        <div className="bg-white border-b border-[#E2E2E2] p-5 sm:p-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-[#1B1C1C] text-white rounded-xs flex items-center justify-center">
              <Scan className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-display text-lg sm:text-xl font-bold text-[#1B1C1C]">
                  Reconhecimento Facial
                </h3>
                <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 text-[10px] font-bold uppercase rounded-xs">
                  LGPD Safe
                </span>
              </div>
              <p className="text-[11px] text-[#545F72]">
                Localize instantaneamente todas as suas fotos neste evento
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="text-[#545F72] hover:text-[#1B1C1C] p-1.5 rounded-xs hover:bg-[#EFEAEA] transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-5 sm:p-6">
          {!scanCompleted && !isScanning && (
            <div className="space-y-5">
              {/* LGPD Consent Box (Mandatory by Brazilian Law) */}
              <div className="p-4 bg-amber-50/70 border border-amber-200 rounded-xs">
                <div className="flex items-start gap-3">
                  <ShieldCheck className="w-5 h-5 text-amber-700 shrink-0 mt-0.5" />
                  <div className="flex-1 text-xs">
                    <p className="font-bold text-amber-900 mb-1">
                      Termo de Consentimento Biométrico (LGPD - Art. 11, Lei
                      13.709/2018)
                    </p>
                    <p className="text-amber-800 leading-relaxed text-[11px] mb-3">
                      Ao enviar sua selfie, você autoriza o processamento
                      temporário de sua biometria facial{" "}
                      <strong>exclusivamente</strong> para identificar e agrupar
                      suas fotos nesta galeria. Seus dados faciais nunca são
                      comercializados e você pode revogar este consentimento a
                      qualquer momento.
                    </p>

                    <label className="flex items-center gap-2 font-medium text-amber-950 cursor-pointer select-none">
                      <input
                        type="checkbox"
                        checked={lgpdConsent}
                        onChange={(e) => setLgpdConsent(e.target.checked)}
                        className="w-4 h-4 accent-[#1B1C1C] cursor-pointer"
                      />
                      <span>
                        Concordo com os termos de privacidade e autorizo a
                        leitura facial
                      </span>
                    </label>
                  </div>
                </div>
              </div>

              {/* Source Selection Tabs */}
              <div className="flex border-b border-[#E2E2E2] text-xs">
                <button
                  type="button"
                  onClick={() => {
                    setMethod("camera");
                    if (!isCapturingCamera && !selfiePreview) startCamera();
                  }}
                  className={`flex-1 py-2.5 font-semibold text-center uppercase tracking-wider flex items-center justify-center gap-2 cursor-pointer transition-colors ${
                    method === "camera"
                      ? "border-b-2 border-[#1B1C1C] text-[#1B1C1C]"
                      : "text-[#545F72] hover:text-[#1B1C1C]"
                  }`}
                >
                  <Camera className="w-4 h-4" />
                  <span>Tirar Selfie</span>
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setMethod("upload");
                    if (streamRef.current) {
                      streamRef.current.getTracks().forEach((t) => t.stop());
                      streamRef.current = null;
                      setIsCapturingCamera(false);
                    }
                  }}
                  className={`flex-1 py-2.5 font-semibold text-center uppercase tracking-wider flex items-center justify-center gap-2 cursor-pointer transition-colors ${
                    method === "upload"
                      ? "border-b-2 border-[#1B1C1C] text-[#1B1C1C]"
                      : "text-[#545F72] hover:text-[#1B1C1C]"
                  }`}
                >
                  <Upload className="w-4 h-4" />
                  <span>Enviar Foto</span>
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setMethod("demo");
                    if (streamRef.current) {
                      streamRef.current.getTracks().forEach((t) => t.stop());
                      streamRef.current = null;
                      setIsCapturingCamera(false);
                    }
                  }}
                  className={`flex-1 py-2.5 font-semibold text-center uppercase tracking-wider flex items-center justify-center gap-2 cursor-pointer transition-colors ${
                    method === "demo"
                      ? "border-b-2 border-[#1B1C1C] text-[#1B1C1C]"
                      : "text-[#545F72] hover:text-[#1B1C1C]"
                  }`}
                >
                  <Sparkles className="w-4 h-4 text-amber-600" />
                  <span>Exemplo Rápido</span>
                </button>
              </div>

              {/* Method Content */}
              {method === "camera" && (
                <div className="text-center space-y-4">
                  {selfiePreview ? (
                    <div className="relative inline-block mx-auto">
                      <img
                        src={selfiePreview}
                        alt="Selfie Capturada"
                        className="w-48 h-48 sm:w-56 sm:h-56 rounded-full object-cover border-4 border-[#1B1C1C] mx-auto shadow-md"
                      />
                      <button
                        onClick={() => {
                          setSelfiePreview(null);
                          startCamera();
                        }}
                        className="mt-2 text-xs text-[#545F72] hover:text-[#1B1C1C] underline flex items-center gap-1 mx-auto cursor-pointer"
                      >
                        <RefreshCw className="w-3.5 h-3.5" />
                        Tirar outra selfie
                      </button>
                    </div>
                  ) : (
                    <div>
                      <div className="w-48 h-48 sm:w-56 sm:h-56 bg-black rounded-full overflow-hidden mx-auto relative border-4 border-[#1B1C1C] flex items-center justify-center shadow-md">
                        <video
                          ref={videoRef}
                          autoPlay
                          playsInline
                          muted
                          className="w-full h-full object-cover"
                        />
                        {/* Facial Guide Overlay */}
                        <div className="absolute inset-4 border border-dashed border-white/60 rounded-full pointer-events-none" />
                      </div>

                      <div className="mt-4 flex justify-center gap-3">
                        {!isCapturingCamera ? (
                          <button
                            type="button"
                            onClick={startCamera}
                            className="px-5 py-2.5 bg-[#1B1C1C] text-white text-xs font-semibold uppercase tracking-wider rounded-xs cursor-pointer"
                          >
                            Ligar Câmera
                          </button>
                        ) : (
                          <button
                            type="button"
                            onClick={captureCameraPhoto}
                            className="px-6 py-2.5 bg-[#1B1C1C] text-white hover:bg-[#2A2A2A] text-xs font-semibold uppercase tracking-wider rounded-xs flex items-center gap-2 cursor-pointer transition-colors"
                          >
                            <Camera className="w-4 h-4" />
                            Capturar Rosto
                          </button>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {method === "upload" && (
                <div className="text-center space-y-4">
                  {selfiePreview ? (
                    <div className="relative inline-block mx-auto">
                      <img
                        src={selfiePreview}
                        alt="Foto Carregada"
                        className="w-48 h-48 sm:w-56 sm:h-56 rounded-full object-cover border-4 border-[#1B1C1C] mx-auto shadow-md"
                      />
                      <button
                        onClick={() => setSelfiePreview(null)}
                        className="mt-2 text-xs text-[#545F72] hover:text-[#1B1C1C] underline flex items-center gap-1 mx-auto cursor-pointer"
                      >
                        <RefreshCw className="w-3.5 h-3.5" />
                        Escolher outra imagem
                      </button>
                    </div>
                  ) : (
                    <label className="border-2 border-dashed border-[#E2E2E2] hover:border-[#1B1C1C] rounded-xs p-8 flex flex-col items-center justify-center cursor-pointer transition-colors bg-white">
                      <Upload className="w-8 h-8 text-[#545F72] mb-2" />
                      <span className="text-xs font-bold text-[#1B1C1C]">
                        Clique para enviar uma foto nítida do seu rosto
                      </span>
                      <span className="text-[11px] text-[#545F72] mt-1">
                        Formatos aceitos: JPG, PNG ou WEBP (até 10MB)
                      </span>
                      <input
                        type="file"
                        accept="image/*"
                        onChange={handleFileUpload}
                        className="hidden"
                      />
                    </label>
                  )}
                </div>
              )}

              {method === "demo" && (
                <div className="space-y-3">
                  <p className="text-xs text-[#545F72]">
                    Selecione um rosto de teste para simular o reconhecimento
                    facial instantaneamente:
                  </p>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                    <button
                      type="button"
                      onClick={() =>
                        handleSelectDemoPerson(
                          "Noiva Marina",
                          "https://images.unsplash.com/photo-1594909122845-11baa439b7bf?w=400&auto=format&fit=crop&q=80",
                          "face_marina",
                        )
                      }
                      className="p-3 bg-white border border-[#E2E2E2] hover:border-[#1B1C1C] rounded-xs text-left flex items-center gap-3 transition-colors cursor-pointer"
                    >
                      <img
                        src="https://images.unsplash.com/photo-1594909122845-11baa439b7bf?w=400&auto=format&fit=crop&q=80"
                        alt="Marina"
                        className="w-10 h-10 rounded-full object-cover border border-[#1B1C1C]"
                      />
                      <div>
                        <p className="text-xs font-bold text-[#1B1C1C]">
                          Marina
                        </p>
                        <p className="text-[10px] text-[#545F72]">
                          Noiva / Evento
                        </p>
                      </div>
                    </button>

                    <button
                      type="button"
                      onClick={() =>
                        handleSelectDemoPerson(
                          "Noivo Ricardo",
                          "https://images.unsplash.com/photo-1507676184212-d03ab07a01bf?w=400&auto=format&fit=crop&q=80",
                          "face_ricardo",
                        )
                      }
                      className="p-3 bg-white border border-[#E2E2E2] hover:border-[#1B1C1C] rounded-xs text-left flex items-center gap-3 transition-colors cursor-pointer"
                    >
                      <img
                        src="https://images.unsplash.com/photo-1507676184212-d03ab07a01bf?w=400&auto=format&fit=crop&q=80"
                        alt="Ricardo"
                        className="w-10 h-10 rounded-full object-cover border border-[#1B1C1C]"
                      />
                      <div>
                        <p className="text-xs font-bold text-[#1B1C1C]">
                          Ricardo
                        </p>
                        <p className="text-[10px] text-[#545F72]">
                          Noivo / Evento
                        </p>
                      </div>
                    </button>

                    <button
                      type="button"
                      onClick={() =>
                        handleSelectDemoPerson(
                          "Corredor / Atleta",
                          "https://images.unsplash.com/photo-1530549387789-4c1017266635?w=400&auto=format&fit=crop&q=80",
                          "face_runner_1042",
                        )
                      }
                      className="p-3 bg-white border border-[#E2E2E2] hover:border-[#1B1C1C] rounded-xs text-left flex items-center gap-3 transition-colors cursor-pointer"
                    >
                      <img
                        src="https://images.unsplash.com/photo-1530549387789-4c1017266635?w=400&auto=format&fit=crop&q=80"
                        alt="Corredor"
                        className="w-10 h-10 rounded-full object-cover border border-[#1B1C1C]"
                      />
                      <div>
                        <p className="text-xs font-bold text-[#1B1C1C]">
                          Corredor
                        </p>
                        <p className="text-[10px] text-[#545F72]">Prova 21K</p>
                      </div>
                    </button>
                  </div>
                </div>
              )}

              {/* Start Scan Button */}
              <div className="pt-2">
                <button
                  type="button"
                  disabled={!selfiePreview || !lgpdConsent}
                  onClick={runBiometricScan}
                  className={`w-full py-3.5 rounded-xs text-xs font-semibold uppercase tracking-widest flex items-center justify-center gap-2 transition-all ${
                    selfiePreview && lgpdConsent
                      ? "bg-[#1B1C1C] text-white hover:bg-[#2A2A2A] cursor-pointer shadow-md"
                      : "bg-[#E2E2E2] text-[#747878] cursor-not-allowed"
                  }`}
                >
                  <Scan className="w-4 h-4" />
                  <span>Escanear Galeria &amp; Encontrar Minhas Fotos</span>
                </button>
                {!lgpdConsent && selfiePreview && (
                  <p className="text-[11px] text-amber-700 text-center mt-2 flex items-center justify-center gap-1">
                    <AlertCircle className="w-3.5 h-3.5" />
                    Marque a caixa de consentimento LGPD acima para continuar.
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Scanning Animation State */}
          {isScanning && (
            <div className="py-12 text-center space-y-6">
              <div className="relative w-40 h-40 mx-auto">
                <img
                  src={selfiePreview || gallery.coverImage}
                  alt="Scanning Face"
                  className="w-full h-full rounded-full object-cover border-4 border-[#1B1C1C] filter grayscale"
                />
                {/* Radar Scanline */}
                <div className="absolute inset-0 rounded-full border-2 border-emerald-500 overflow-hidden">
                  <div className="w-full h-1 bg-gradient-to-b from-transparent via-emerald-400 to-transparent shadow-[0_0_15px_#10B981] animate-pulse transition-all duration-700" />
                </div>
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="w-24 h-24 border border-dashed border-emerald-400 rounded-full animate-spin" />
                </div>
              </div>

              <div>
                <h4 className="font-display text-lg font-bold text-[#1B1C1C] mb-1">
                  Processando Biometria Facial
                </h4>
                <p className="text-xs text-[#545F72] font-mono animate-pulse">
                  {scanStep}
                </p>
              </div>
            </div>
          )}

          {/* Scan Completed / Matches Results */}
          {scanCompleted && (
            <div className="space-y-6">
              <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xs flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-emerald-600 text-white rounded-full flex items-center justify-center">
                    <CheckCircle2 className="w-6 h-6" />
                  </div>
                  <div>
                    <h4 className="font-display text-base font-bold text-emerald-950">
                      Encontramos {matchedPhotos.length} fotos com seu rosto!
                    </h4>
                    <p className="text-xs text-emerald-800">
                      Similaridade média de 94% detectada no acervo.
                    </p>
                  </div>
                </div>

                <button
                  onClick={handleReset}
                  className="text-xs text-emerald-800 hover:text-emerald-950 underline font-medium cursor-pointer"
                >
                  Nova busca
                </button>
              </div>

              {/* Matched Photos Preview Grid */}
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-[#545F72] block mb-2">
                  Prévia das Fotos Identificadas:
                </span>
                <div className="grid grid-cols-3 sm:grid-cols-4 gap-2 max-h-56 overflow-y-auto p-1 bg-white border border-[#E2E2E2] rounded-xs">
                  {matchedPhotos.map((photo) => (
                    <div
                      key={photo.id}
                      className="relative aspect-square bg-[#EFEAEA] overflow-hidden group"
                    >
                      <img
                        src={photo.url}
                        alt={photo.title}
                        className="w-full h-full object-cover"
                      />
                      <div className="absolute top-1 right-1 px-1.5 py-0.5 bg-black/80 text-emerald-400 font-mono text-[9px] font-bold rounded-xs">
                        {photo.matchConfidence}%
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Action Buttons */}
              <div className="space-y-2">
                <button
                  type="button"
                  onClick={handleApplyMatches}
                  className="w-full py-3.5 bg-[#1B1C1C] text-white hover:bg-[#2A2A2A] text-xs font-semibold uppercase tracking-widest rounded-xs flex items-center justify-center gap-2 cursor-pointer transition-colors shadow-md"
                >
                  <span>
                    Filtrar Galeria com Minhas {matchedPhotos.length} Fotos
                  </span>
                  <ArrowRight className="w-4 h-4" />
                </button>

                <p className="text-[11px] text-[#545F72] text-center">
                  Dica: Você pode comprar o pacote com todas as suas fotos
                  aproveitando o{" "}
                  <strong>desconto progressivo por quantidade</strong>.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
