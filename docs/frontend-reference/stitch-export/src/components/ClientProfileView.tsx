import React, { useState } from "react";
import { Gallery, Order, CustomerUser, Photo } from "../types";
import {
  CheckCircle2,
  Clock,
  Download,
  ExternalLink,
  FileText,
  MessageSquare,
  Phone,
  ShieldCheck,
  Sparkles,
  User,
  QrCode,
  Check,
  FolderCheck,
  LogOut,
  Trash2,
  Lock,
  ArrowRight,
} from "lucide-react";
import { formatCurrencyBRL } from "../utils/pricing";

interface ClientProfileViewProps {
  currentUser: CustomerUser;
  orders: Order[];
  onOpenWhatsAppLogin: () => void;
  onLogoutWhatsApp: () => void;
  onRevokeLgpd: () => void;
  onOpenPixModalForOrder: (order: Order) => void;
  onEnterGallery: () => void;
  currentGallery: Gallery;
}

export const ClientProfileView: React.FC<ClientProfileViewProps> = ({
  currentUser,
  orders,
  onOpenWhatsAppLogin,
  onLogoutWhatsApp,
  onRevokeLgpd,
  onOpenPixModalForOrder,
  onEnterGallery,
  currentGallery,
}) => {
  const [activeTab, setActiveTab] = useState<"orders" | "lgpd" | "help">(
    "orders",
  );
  const [downloadingZipId, setDownloadingZipId] = useState<string | null>(null);

  // Filter orders for this customer (or show all demo orders if logged in Marina)
  const customerOrders = orders;

  const handleDownloadZip = (orderId: string) => {
    setDownloadingZipId(orderId);
    setTimeout(() => {
      setDownloadingZipId(null);
      alert(
        "Download do pacote ZIP em Alta Resolução (45 Megapixels) iniciado!",
      );
    }, 2000);
  };

  return (
    <div className="min-h-screen bg-[#FBF9F9] pt-24 pb-28 px-4 sm:px-8 md:px-12 max-w-[1200px] mx-auto animate-fade-in-up">
      {/* Profile Top Bar */}
      <div className="bg-white border border-[#E2E2E2] rounded-xs p-6 sm:p-8 mb-8 shadow-xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 pb-6 border-b border-[#E2E2E2]">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 bg-[#1B1C1C] text-white rounded-full flex items-center justify-center text-xl font-bold font-display">
              {currentUser.name
                ? currentUser.name.charAt(0).toUpperCase()
                : "M"}
            </div>

            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="px-2.5 py-0.5 bg-emerald-50 text-emerald-800 text-[10px] font-bold uppercase tracking-wider rounded-xs border border-emerald-200">
                  {currentUser.isLoggedIn
                    ? "WhatsApp Conectado"
                    : "Acesso Convidado"}
                </span>
                {currentUser.lgpdConsentFace && (
                  <span className="text-xs text-emerald-700 font-medium flex items-center gap-1">
                    <ShieldCheck className="w-3.5 h-3.5" />
                    Biometria LGPD Ativa
                  </span>
                )}
              </div>

              <h2 className="font-display text-2xl sm:text-3xl font-bold text-[#1B1C1C]">
                {currentUser.name || "Marina Alencar"}
              </h2>
              <p className="text-xs text-[#545F72] mt-0.5 flex items-center gap-2 font-mono">
                <Phone className="w-3.5 h-3.5 text-emerald-600" />
                {currentUser.phone || "+55 (11) 98842-1920"}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {currentUser.isLoggedIn ? (
              <button
                onClick={onLogoutWhatsApp}
                className="px-3.5 py-2 border border-[#E2E2E2] hover:border-red-500 text-[#545F72] hover:text-red-600 text-xs font-semibold uppercase tracking-wider rounded-xs flex items-center gap-1.5 transition-colors cursor-pointer"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span>Trocar Número</span>
              </button>
            ) : (
              <button
                onClick={onOpenWhatsAppLogin}
                className="px-4 py-2 bg-[#1B1C1C] text-white hover:bg-[#2A2A2A] text-xs font-semibold uppercase tracking-wider rounded-xs flex items-center gap-1.5 transition-colors cursor-pointer"
              >
                <MessageSquare className="w-3.5 h-3.5 text-emerald-400" />
                <span>Conectar WhatsApp</span>
              </button>
            )}

            <button
              onClick={onEnterGallery}
              className="px-4 py-2 bg-[#000000] text-white hover:bg-[#2A2A2A] text-xs font-semibold uppercase tracking-wider rounded-xs transition-colors cursor-pointer"
            >
              Abrir Galeria
            </button>
          </div>
        </div>

        {/* Quick Nav Tabs */}
        <div className="flex border-b border-[#E2E2E2] text-xs pt-4">
          <button
            onClick={() => setActiveTab("orders")}
            className={`pb-3 px-4 font-semibold uppercase tracking-wider cursor-pointer transition-colors ${
              activeTab === "orders"
                ? "border-b-2 border-[#1B1C1C] text-[#1B1C1C]"
                : "text-[#545F72] hover:text-[#1B1C1C]"
            }`}
          >
            Meus Pedidos &amp; Downloads ({customerOrders.length})
          </button>

          <button
            onClick={() => setActiveTab("lgpd")}
            className={`pb-3 px-4 font-semibold uppercase tracking-wider cursor-pointer transition-colors ${
              activeTab === "lgpd"
                ? "border-b-2 border-[#1B1C1C] text-[#1B1C1C]"
                : "text-[#545F72] hover:text-[#1B1C1C]"
            }`}
          >
            Privacidade Biometria LGPD
          </button>

          <button
            onClick={() => setActiveTab("help")}
            className={`pb-3 px-4 font-semibold uppercase tracking-wider cursor-pointer transition-colors ${
              activeTab === "help"
                ? "border-b-2 border-[#1B1C1C] text-[#1B1C1C]"
                : "text-[#545F72] hover:text-[#1B1C1C]"
            }`}
          >
            Suporte &amp; Fotógrafo
          </button>
        </div>
      </div>

      {/* Tab: Orders & Downloads */}
      {activeTab === "orders" && (
        <div className="space-y-6">
          {customerOrders.length === 0 ? (
            <div className="bg-white border border-[#E2E2E2] rounded-xs p-12 text-center space-y-4">
              <FolderCheck className="w-12 h-12 text-[#747878] mx-auto" />
              <div>
                <h4 className="font-display text-lg font-bold text-[#1B1C1C]">
                  Nenhum pedido encontrado
                </h4>
                <p className="text-xs text-[#545F72] mt-1">
                  Você ainda não realizou compras digitais neste evento.
                </p>
              </div>
              <button
                onClick={onEnterGallery}
                className="px-5 py-2.5 bg-[#1B1C1C] text-white text-xs font-semibold uppercase tracking-wider rounded-xs cursor-pointer"
              >
                Explorar Galeria &amp; Comprar Fotos
              </button>
            </div>
          ) : (
            customerOrders.map((order) => {
              const isDelivered = order.status === "delivered";
              const isEditing = order.status === "paid_editing";
              const isPending = order.status === "pending_payment";

              return (
                <div
                  key={order.id}
                  className="bg-white border border-[#E2E2E2] rounded-xs p-6 sm:p-8 shadow-xs space-y-6"
                >
                  {/* Order Header Bar */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#E2E2E2]">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-mono text-xs font-bold text-[#1B1C1C]">
                          Pedido #{order.id}
                        </span>
                        <span className="text-xs text-[#545F72]">•</span>
                        <span className="text-xs text-[#545F72]">
                          {order.createdAt}
                        </span>
                      </div>
                      <h3 className="font-display text-xl font-bold text-[#1B1C1C]">
                        {order.galleryTitle}
                      </h3>
                      <p className="text-xs text-[#545F72]">
                        {order.totalPhotos} fotos digitais • Total:{" "}
                        <strong>{formatCurrencyBRL(order.totalAmount)}</strong>
                      </p>
                    </div>

                    {/* Status Badge */}
                    <div>
                      {isDelivered && (
                        <div className="px-3.5 py-1.5 bg-emerald-100 text-emerald-900 border border-emerald-300 rounded-xs text-xs font-bold uppercase tracking-wider flex items-center gap-2">
                          <CheckCircle2 className="w-4 h-4 text-emerald-700" />
                          <span>Entregue • Download Liberado</span>
                        </div>
                      )}

                      {isEditing && (
                        <div className="px-3.5 py-1.5 bg-blue-100 text-blue-900 border border-blue-300 rounded-xs text-xs font-bold uppercase tracking-wider flex items-center gap-2">
                          <Sparkles className="w-4 h-4 text-blue-700 animate-spin" />
                          <span>Pago • Em Edição / Tratamento</span>
                        </div>
                      )}

                      {isPending && (
                        <div className="px-3.5 py-1.5 bg-amber-100 text-amber-950 border border-amber-300 rounded-xs text-xs font-bold uppercase tracking-wider flex items-center gap-2">
                          <Clock className="w-4 h-4 text-amber-700" />
                          <span>Aguardando Pagamento PIX</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Status Pipeline Visualizer */}
                  <div className="p-4 bg-[#F5F3F3] rounded-xs border border-[#E2E2E2]">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-[#545F72] block mb-3">
                      Etapas de Produção &amp; Entrega Digital:
                    </span>

                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                      {/* Step 1 */}
                      <div
                        className={`p-3 rounded-xs border transition-colors ${
                          isDelivered || isEditing
                            ? "bg-emerald-50 border-emerald-300 text-emerald-900 font-semibold"
                            : "bg-amber-50 border-amber-300 text-amber-950 font-bold"
                        }`}
                      >
                        <div className="flex items-center gap-2 mb-1">
                          {isDelivered || isEditing ? (
                            <Check className="w-3.5 h-3.5 text-emerald-600" />
                          ) : (
                            <Clock className="w-3.5 h-3.5 text-amber-700" />
                          )}
                          <span>1. Pagamento PIX</span>
                        </div>
                        <p className="text-[11px] font-normal opacity-90">
                          {isDelivered || isEditing
                            ? `Confirmado em ${order.paidAt || "hoje"}`
                            : "Aguardando validação"}
                        </p>
                      </div>

                      {/* Step 2 */}
                      <div
                        className={`p-3 rounded-xs border transition-colors ${
                          isDelivered
                            ? "bg-emerald-50 border-emerald-300 text-emerald-900 font-semibold"
                            : isEditing
                              ? "bg-blue-50 border-blue-300 text-blue-950 font-bold"
                              : "bg-white border-[#E2E2E2] text-[#747878]"
                        }`}
                      >
                        <div className="flex items-center gap-2 mb-1">
                          {isDelivered ? (
                            <Check className="w-3.5 h-3.5 text-emerald-600" />
                          ) : (
                            <Sparkles className="w-3.5 h-3.5 text-blue-600" />
                          )}
                          <span>2. Tratamento &amp; Export</span>
                        </div>
                        <p className="text-[11px] font-normal opacity-90">
                          {isDelivered
                            ? "Concluído em 45 MP"
                            : isEditing
                              ? "Fotógrafo tratando as fotos"
                              : "Aguardando pagamento"}
                        </p>
                      </div>

                      {/* Step 3 */}
                      <div
                        className={`p-3 rounded-xs border transition-colors ${
                          isDelivered
                            ? "bg-emerald-50 border-emerald-300 text-emerald-900 font-bold"
                            : "bg-white border-[#E2E2E2] text-[#747878]"
                        }`}
                      >
                        <div className="flex items-center gap-2 mb-1">
                          {isDelivered ? (
                            <Check className="w-3.5 h-3.5 text-emerald-600" />
                          ) : (
                            <FolderCheck className="w-3.5 h-3.5 text-[#747878]" />
                          )}
                          <span>3. Entrega Digital</span>
                        </div>
                        <p className="text-[11px] font-normal opacity-90">
                          {isDelivered
                            ? "Google Photos & ZIP Prontos"
                            : "Link gerado após edição"}
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Delivery Actions when Delivered */}
                  {isDelivered && (
                    <div className="p-5 bg-emerald-50/70 border border-emerald-300 rounded-xs space-y-4">
                      <div className="flex items-center gap-2.5 text-emerald-950 font-bold text-sm">
                        <Sparkles className="w-5 h-5 text-emerald-700" />
                        <span>
                          Suas fotos digitais em alta resolução estão prontas!
                        </span>
                      </div>

                      <div className="flex flex-col sm:flex-row gap-3">
                        {/* Google Photos Main Link */}
                        <a
                          href={
                            order.googlePhotosUrl ||
                            currentGallery.googlePhotosLink
                          }
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex-1 py-3.5 px-4 bg-emerald-800 hover:bg-emerald-900 text-white text-xs font-semibold uppercase tracking-wider rounded-xs flex items-center justify-center gap-2 cursor-pointer transition-colors shadow-sm"
                        >
                          <ExternalLink className="w-4 h-4" />
                          <span>Acessar Álbum no Google Photos</span>
                        </a>

                        {/* Direct ZIP Download */}
                        <button
                          onClick={() => handleDownloadZip(order.id)}
                          disabled={downloadingZipId === order.id}
                          className="flex-1 py-3.5 px-4 bg-white border border-emerald-800 text-emerald-950 hover:bg-emerald-100 text-xs font-semibold uppercase tracking-wider rounded-xs flex items-center justify-center gap-2 cursor-pointer transition-colors"
                        >
                          <Download className="w-4 h-4 text-emerald-700" />
                          <span>
                            {downloadingZipId === order.id
                              ? "Baixando ZIP (45 MP)..."
                              : "Baixar Pacote Completo (ZIP)"}
                          </span>
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Pending Action Bar */}
                  {isPending && (
                    <div className="p-4 bg-amber-50 border border-amber-200 rounded-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs">
                      <div>
                        <p className="font-bold text-amber-950">
                          Aguardando confirmação do PIX
                        </p>
                        <p className="text-amber-800 text-[11px]">
                          Efetue a transferência ou anexe o comprovante para
                          início do tratamento.
                        </p>
                      </div>

                      <button
                        onClick={() => onOpenPixModalForOrder(order)}
                        className="px-4 py-2 bg-[#1B1C1C] text-white hover:bg-[#2A2A2A] text-xs font-semibold uppercase tracking-wider rounded-xs flex items-center gap-1.5 cursor-pointer"
                      >
                        <QrCode className="w-3.5 h-3.5" />
                        <span>Abrir QR Code PIX</span>
                      </button>
                    </div>
                  )}

                  {/* Purchased Photos Gallery Grid */}
                  <div>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-[#545F72] block mb-3">
                      Fotos deste Pedido ({order.items.length}):
                    </span>
                    <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 gap-3">
                      {order.items.map((item, idx) => (
                        <div
                          key={idx}
                          className="relative aspect-square bg-[#EFEAEA] rounded-xs overflow-hidden border border-[#E2E2E2] group"
                        >
                          <img
                            src={item.photoUrl}
                            alt={item.photoTitle}
                            className="w-full h-full object-cover"
                          />
                          {isDelivered && (
                            <div className="absolute top-1 right-1 px-1.5 py-0.5 bg-emerald-700 text-white font-mono text-[9px] font-bold rounded-xs">
                              Original
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}

      {/* Tab: LGPD Privacy & Biometrics */}
      {activeTab === "lgpd" && (
        <div className="bg-white border border-[#E2E2E2] rounded-xs p-6 sm:p-8 space-y-6 shadow-xs">
          <div className="flex items-center gap-3 pb-4 border-b border-[#E2E2E2]">
            <div className="w-10 h-10 bg-emerald-50 text-emerald-800 border border-emerald-200 rounded-full flex items-center justify-center">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-display text-xl font-bold text-[#1B1C1C]">
                Gestão de Privacidade &amp; Biometria (LGPD)
              </h3>
              <p className="text-xs text-[#545F72]">
                Conformidade com a Lei Geral de Proteção de Dados (Lei nº
                13.709/2018)
              </p>
            </div>
          </div>

          <div className="space-y-4 text-xs text-[#545F72] leading-relaxed">
            <p>
              O <strong>Markina Gallery</strong> adota rigorosas diretrizes de
              segurança e criptografia de ponta a ponta para proteger os dados
              biométricos de reconhecimento facial e informações cadastrais de
              clientes e convidados.
            </p>

            <div className="p-4 bg-[#F5F3F3] rounded-xs border border-[#E2E2E2] space-y-2">
              <p className="font-bold text-[#1B1C1C]">
                Seus Direitos Garantidos pelo Art. 18 da LGPD:
              </p>
              <ul className="list-disc list-inside space-y-1 text-[11px]">
                <li>
                  Confirmação da existência de tratamento dos seus vetores
                  biométricos;
                </li>
                <li>
                  Anonimização, bloqueio ou eliminação de dados desnecessários
                  ou excessivos;
                </li>
                <li>
                  Revogação do consentimento facial a qualquer momento com
                  exclusão definitiva da selfie de busca;
                </li>
                <li>
                  Acesso irrestrito a todas as fotos digitais adquiridas em seu
                  nome.
                </li>
              </ul>
            </div>

            <div className="pt-4 border-t border-[#E2E2E2] flex items-center justify-between">
              <div>
                <p className="font-bold text-[#1B1C1C]">
                  Revogar Consentimento Biométrico
                </p>
                <p className="text-[11px] text-[#545F72]">
                  Excluir imediatamente sua selfie e limpar filtros de busca
                  facial desta sessão.
                </p>
              </div>

              <button
                onClick={onRevokeLgpd}
                className="px-4 py-2 border border-red-300 text-red-700 hover:bg-red-50 text-xs font-semibold uppercase tracking-wider rounded-xs cursor-pointer transition-colors"
              >
                Excluir Minha Biometria
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Tab: Support & Photographer Contact */}
      {activeTab === "help" && (
        <div className="bg-[#1A1A1A] text-white rounded-xs p-6 sm:p-10 space-y-6">
          <div className="max-w-2xl">
            <span className="text-[10px] uppercase tracking-widest text-gray-400 font-semibold block mb-2">
              Suporte Direto &amp; Estúdio
            </span>
            <h3 className="font-display text-2xl font-bold mb-3">
              Markina Studios Photography
            </h3>
            <p className="text-xs text-gray-300 leading-relaxed mb-6">
              Dúvidas sobre o recebimento do link no Google Photos, comprovantes
              de PIX ou solicitações de edição especial em fotos digitais? Nossa
              equipe está à disposição via WhatsApp VIP.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-4 border-t border-white/10 text-xs">
              <a
                href="https://wa.me/5511988421920"
                target="_blank"
                rel="noopener noreferrer"
                className="p-4 bg-white/10 hover:bg-white/20 rounded-xs flex items-center gap-3 transition-colors"
              >
                <MessageSquare className="w-5 h-5 text-emerald-400" />
                <div>
                  <p className="font-bold">WhatsApp do Fotógrafo</p>
                  <p className="text-[11px] text-gray-300">
                    +55 (11) 98842-1920
                  </p>
                </div>
              </a>

              <div className="p-4 bg-white/10 rounded-xs flex items-center gap-3">
                <Phone className="w-5 h-5 text-gray-400" />
                <div>
                  <p className="font-bold">Chave PIX Oficial</p>
                  <p className="text-[11px] text-gray-300">
                    pix@markinagallery.com.br
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
