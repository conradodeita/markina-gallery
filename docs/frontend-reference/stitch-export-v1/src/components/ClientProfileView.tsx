import React, { useState } from "react";
import { Gallery } from "../types";
import {
  ShieldCheck,
  Key,
  Download,
  FileText,
  Mail,
  Phone,
  MapPin,
  Calendar,
  CheckCircle2,
  Award,
  Sparkles,
  ExternalLink,
  Copy,
  Check,
} from "lucide-react";

interface ClientProfileViewProps {
  gallery: Gallery;
  onEnterGallery: () => void;
}

export const ClientProfileView: React.FC<ClientProfileViewProps> = ({
  gallery,
  onEnterGallery,
}) => {
  const [copiedPin, setCopiedPin] = useState(false);
  const [downloadStarted, setDownloadStarted] = useState(false);

  const handleCopyPin = () => {
    navigator.clipboard.writeText(gallery.accessPin);
    setCopiedPin(true);
    setTimeout(() => setCopiedPin(false), 2000);
  };

  const handleDownloadAll = () => {
    setDownloadStarted(true);
    setTimeout(() => {
      setDownloadStarted(false);
    }, 4000);
  };

  return (
    <div className="min-h-screen bg-[#FBF9F9] pt-24 pb-28 px-4 sm:px-8 md:px-16 max-w-[1200px] mx-auto animate-fade-in-up">
      {/* Profile Header */}
      <div className="bg-white border border-[#E2E2E2] rounded-xs p-6 sm:p-10 mb-8 shadow-xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 pb-8 border-b border-[#E2E2E2]">
          <div className="flex items-center gap-5">
            <img
              src={gallery.coverImage}
              alt={gallery.coupleNames}
              className="w-20 h-20 sm:w-24 sm:h-24 rounded-full object-cover border-2 border-[#1B1C1C]"
            />
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="px-2.5 py-0.5 bg-[#E9E8E7] text-[#1B1C1C] text-[10px] font-bold uppercase tracking-wider rounded-xs">
                  Área do Cliente VIP
                </span>
                <span className="text-xs text-emerald-700 font-medium flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Galeria Entregue
                </span>
              </div>
              <h2 className="font-display text-2xl sm:text-4xl font-bold text-[#1B1C1C]">
                {gallery.coupleNames}
              </h2>
              <p className="text-xs text-[#545F72] mt-0.5 flex items-center gap-2">
                <MapPin className="w-3.5 h-3.5" />
                {gallery.location}
              </p>
            </div>
          </div>

          <button
            onClick={onEnterGallery}
            className="px-6 py-3 bg-[#000000] text-white hover:bg-[#2A2A2A] text-xs font-semibold uppercase tracking-widest rounded-xs transition-colors cursor-pointer self-start md:self-auto"
          >
            Abrir Galeria
          </button>
        </div>

        {/* Security & Access Key */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-6">
          <div className="p-4 bg-[#F5F3F3] rounded-xs border border-[#E2E2E2]">
            <span className="text-[10px] uppercase tracking-wider text-[#545F72] font-semibold block mb-1">
              PIN de Acesso Privado
            </span>
            <div className="flex items-center justify-between">
              <span className="font-mono text-xl font-bold text-[#1B1C1C] tracking-widest">
                {gallery.accessPin}
              </span>
              <button
                onClick={handleCopyPin}
                className="text-xs text-[#545F72] hover:text-[#1B1C1C] flex items-center gap-1 cursor-pointer"
              >
                {copiedPin ? (
                  <Check className="w-3.5 h-3.5 text-emerald-600" />
                ) : (
                  <Copy className="w-3.5 h-3.5" />
                )}
                {copiedPin ? "Copiado" : "Copiar"}
              </button>
            </div>
          </div>

          <div className="p-4 bg-[#F5F3F3] rounded-xs border border-[#E2E2E2]">
            <span className="text-[10px] uppercase tracking-wider text-[#545F72] font-semibold block mb-1">
              Data do Evento
            </span>
            <p className="text-sm font-semibold text-[#1B1C1C] flex items-center gap-1.5 mt-1">
              <Calendar className="w-4 h-4 text-[#545F72]" />
              {gallery.date}
            </p>
          </div>

          <div className="p-4 bg-[#F5F3F3] rounded-xs border border-[#E2E2E2]">
            <span className="text-[10px] uppercase tracking-wider text-[#545F72] font-semibold block mb-1">
              Acervo Digital
            </span>
            <p className="text-sm font-semibold text-[#1B1C1C] flex items-center gap-1.5 mt-1">
              <Sparkles className="w-4 h-4 text-[#545F72]" />
              {gallery.totalPhotos} Fotos em Alta Resolução
            </p>
          </div>
        </div>
      </div>

      {/* Main Grid: Downloads & License */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
        {/* High Res Download Card */}
        <div className="bg-white border border-[#E2E2E2] rounded-xs p-6 sm:p-8 flex flex-col justify-between shadow-xs">
          <div>
            <div className="w-12 h-12 bg-[#F5F3F3] rounded-xs flex items-center justify-center mb-4">
              <Download className="w-6 h-6 text-[#1B1C1C] stroke-[1.5]" />
            </div>
            <h3 className="font-display text-xl font-bold text-[#1B1C1C] mb-2">
              Download Completo em Alta Resolução (Original)
            </h3>
            <p className="text-xs text-[#545F72] leading-relaxed mb-6">
              Arquivo mestre comprimido (ZIP) com todas as 120 fotos em
              resolução total (45 Megapixels, perfil de cor Adobe RGB / sRGB
              pronto para impressões em grandes formatos).
            </p>

            <ul className="space-y-2 text-xs text-[#545F72] mb-6">
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                <span>Arquivos sem marcas d'água</span>
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                <span>Otimizado para exibição em telas 4K / 8K</span>
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                <span>Backup garantido em nuvem por 5 anos</span>
              </li>
            </ul>
          </div>

          <div>
            {downloadStarted ? (
              <div className="w-full py-3.5 bg-emerald-700 text-white text-xs font-semibold uppercase tracking-wider rounded-xs flex items-center justify-center gap-2">
                <Check className="w-4 h-4" />
                Download Iniciado (2.4 GB)
              </div>
            ) : (
              <button
                onClick={handleDownloadAll}
                className="w-full py-3.5 bg-[#000000] text-white hover:bg-[#2A2A2A] text-xs font-semibold uppercase tracking-widest rounded-xs flex items-center justify-center gap-2 cursor-pointer transition-colors"
              >
                <Download className="w-4 h-4" />
                Baixar Pacote Completo (ZIP)
              </button>
            )}
          </div>
        </div>

        {/* License & Certificate Card */}
        <div className="bg-white border border-[#E2E2E2] rounded-xs p-6 sm:p-8 flex flex-col justify-between shadow-xs">
          <div>
            <div className="w-12 h-12 bg-[#F5F3F3] rounded-xs flex items-center justify-center mb-4">
              <Award className="w-6 h-6 text-[#1B1C1C] stroke-[1.5]" />
            </div>
            <h3 className="font-display text-xl font-bold text-[#1B1C1C] mb-2">
              Termo de Licença &amp; Direitos de Uso
            </h3>
            <p className="text-xs text-[#545F72] leading-relaxed mb-6">
              Este certificado concede a <strong>Marina &amp; Ricardo</strong> o
              direito irrestrito, pessoal e não-comercial para reprodução,
              impressão, publicação em redes sociais e confecção de álbuns
              físicos.
            </p>

            <div className="p-4 bg-[#F5F3F3] rounded-xs border border-[#E2E2E2] space-y-1.5 text-xs text-[#545F72] mb-6">
              <p>
                <strong>Licenciante:</strong> Markina Studios Fotografia LTDA
              </p>
              <p>
                <strong>Número de Registro:</strong> MK-2023-VILABISUTTI-991
              </p>
              <p>
                <strong>Data de Emissão:</strong> 15 de Outubro de 2023
              </p>
            </div>
          </div>

          <button
            onClick={() =>
              alert(
                "Download do Certificado de Autenticidade e Licença PDF gerado!",
              )
            }
            className="w-full py-3.5 bg-white border border-[#1B1C1C] text-[#1B1C1C] hover:bg-[#F5F3F3] text-xs font-semibold uppercase tracking-widest rounded-xs flex items-center justify-center gap-2 cursor-pointer transition-colors"
          >
            <FileText className="w-4 h-4" />
            Baixar Certificado em PDF
          </button>
        </div>
      </div>

      {/* Photographer Contact & Notes */}
      <div className="bg-[#1A1A1A] text-white rounded-xs p-6 sm:p-10">
        <div className="max-w-2xl">
          <span className="text-[10px] uppercase tracking-widest text-gray-400 font-semibold block mb-2">
            Mensagem do Fotógrafo
          </span>
          <h3 className="font-display text-2xl font-bold mb-4">
            "Foi uma honra eternizar o amor de vocês."
          </h3>
          <p className="text-xs text-gray-300 leading-relaxed italic mb-8">
            "Queridos Marina e Ricardo, cada momento da Fazenda Vila Rica foi
            repleto de luz natural e emoção genuína. Esperamos que essas imagens
            os façam reviver esse dia inesquecível para todo o sempre."
            <br />
            <strong className="not-italic text-white mt-2 block">
              — Markina &amp; Equipe
            </strong>
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-6 border-t border-white/10 text-xs">
            <div className="flex items-center gap-3">
              <Mail className="w-4 h-4 text-gray-400" />
              <span>contato@markinagallery.com.br</span>
            </div>
            <div className="flex items-center gap-3">
              <Phone className="w-4 h-4 text-gray-400" />
              <span>+55 (11) 98842-1920 (WhatsApp VIP)</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
