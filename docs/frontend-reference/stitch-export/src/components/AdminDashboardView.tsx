import React, { useState } from "react";
import { Gallery, Order, OrderStatus } from "../types";
import {
  DollarSign,
  ShoppingBag,
  Clock,
  Sparkles,
  CheckCircle2,
  MessageSquare,
  ExternalLink,
  Lock,
  Unlock,
  Plus,
  Edit3,
  Search,
  Filter,
  FileText,
  Check,
  AlertCircle,
  TrendingUp,
  Camera,
  Users,
  Send,
  Eye,
  Sliders,
} from "lucide-react";
import { formatCurrencyBRL } from "../utils/pricing";

interface AdminDashboardViewProps {
  galleries: Gallery[];
  orders: Order[];
  onUpdateOrderStatus: (
    orderId: string,
    status: OrderStatus,
    googlePhotosUrl?: string,
  ) => void;
  onCreateOrUpdateGallery: (gallery: Gallery) => void;
  onExitAdmin: () => void;
}

export const AdminDashboardView: React.FC<AdminDashboardViewProps> = ({
  galleries,
  orders,
  onUpdateOrderStatus,
  onCreateOrUpdateGallery,
  onExitAdmin,
}) => {
  const [activeTab, setActiveTab] = useState<
    "orders" | "galleries" | "pricing" | "customers"
  >("orders");
  const [orderFilterStatus, setOrderFilterStatus] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");

  // Delivery Modal State
  const [deliveringOrder, setDeliveringOrder] = useState<Order | null>(null);
  const [deliveryGooglePhotosUrl, setDeliveryGooglePhotosUrl] = useState("");

  // Gallery Edit Modal State
  const [editingGallery, setEditingGallery] = useState<Gallery | null>(null);
  const [isCreatingGallery, setIsCreatingGallery] = useState(false);

  // Metrics Calculations
  const totalRevenue = orders
    .filter((o) => o.status === "paid_editing" || o.status === "delivered")
    .reduce((acc, o) => acc + o.totalAmount, 0);

  const totalPhotosSold = orders
    .filter((o) => o.status === "paid_editing" || o.status === "delivered")
    .reduce((acc, o) => acc + o.totalPhotos, 0);

  const pendingOrdersCount = orders.filter(
    (o) => o.status === "pending_payment",
  ).length;
  const editingOrdersCount = orders.filter(
    (o) => o.status === "paid_editing",
  ).length;
  const deliveredOrdersCount = orders.filter(
    (o) => o.status === "delivered",
  ).length;

  const averageTicket =
    orders.length > 0 ? totalRevenue / (orders.length || 1) : 0;

  // Filter Orders
  const filteredOrders = orders.filter((order) => {
    if (orderFilterStatus !== "all" && order.status !== orderFilterStatus)
      return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      return (
        order.id.toLowerCase().includes(q) ||
        order.customerName.toLowerCase().includes(q) ||
        order.customerWhatsApp.toLowerCase().includes(q) ||
        order.galleryTitle.toLowerCase().includes(q)
      );
    }
    return true;
  });

  const handleDeliverOrder = (e: React.FormEvent) => {
    e.preventDefault();
    if (!deliveringOrder) return;
    onUpdateOrderStatus(
      deliveringOrder.id,
      "delivered",
      deliveryGooglePhotosUrl ||
        deliveringOrder.googlePhotosUrl ||
        "https://photos.app.goo.gl/markina-entrega-digital",
    );
    setDeliveringOrder(null);
    setDeliveryGooglePhotosUrl("");
  };

  const handleOpenWhatsAppNotify = (order: Order) => {
    let msgText = "";
    if (order.status === "delivered") {
      msgText = `Olá ${order.customerName}! Suas ${order.totalPhotos} fotos digitais tratadas do "${order.galleryTitle}" já foram entregues pelo Markina Studios! Acesse seu álbum no Google Photos: ${order.googlePhotosUrl || "https://photos.app.goo.gl/markina-entrega"}`;
    } else if (order.status === "paid_editing") {
      msgText = `Olá ${order.customerName}! Confirmamos o recebimento do seu PIX no valor de ${formatCurrencyBRL(order.totalAmount)}. Suas fotos já estão em processo de edição/tratamento e logo enviaremos o link final!`;
    } else {
      msgText = `Olá ${order.customerName}! Recebemos seu pedido #${order.id} no Markina Gallery. Chave PIX: pix@markinagallery.com.br (Valor: ${formatCurrencyBRL(order.totalAmount)}).`;
    }

    const cleanPhone = order.customerWhatsApp.replace(/\D/g, "");
    window.open(
      `https://wa.me/${cleanPhone}?text=${encodeURIComponent(msgText)}`,
      "_blank",
    );
  };

  return (
    <div className="min-h-screen bg-[#FBF9F9] pt-24 pb-28 px-4 sm:px-8 md:px-12 max-w-[1400px] mx-auto animate-fade-in-up">
      {/* Admin Header */}
      <div className="bg-white border border-[#E2E2E2] rounded-xs p-6 sm:p-8 mb-8 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6 pb-6 border-b border-[#E2E2E2]">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2.5 py-0.5 bg-[#1B1C1C] text-white text-[10px] font-bold uppercase tracking-widest rounded-xs">
                Painel do Fotógrafo
              </span>
              <span className="text-xs text-[#545F72]">•</span>
              <span className="text-xs text-[#545F72] font-mono">
                Markina Studios MVP
              </span>
            </div>
            <h1 className="font-display text-2xl sm:text-3xl font-bold text-[#1B1C1C]">
              Gestão de Vendas &amp; Galerias
            </h1>
            <p className="text-xs text-[#545F72] mt-0.5">
              Validação manual de PIX, acompanhamento de edição e despacho de
              links Google Photos.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={onExitAdmin}
              className="px-4 py-2 bg-white border border-[#1B1C1C] text-[#1B1C1C] hover:bg-[#F5F3F3] text-xs font-semibold uppercase tracking-wider rounded-xs transition-colors cursor-pointer"
            >
              Voltar à Visão do Cliente
            </button>
          </div>
        </div>

        {/* Global Performance Metrics */}
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 pt-6">
          <div className="p-4 bg-[#F5F3F3] border border-[#E2E2E2] rounded-xs">
            <span className="text-[10px] uppercase tracking-wider text-[#545F72] font-semibold block mb-1">
              Receita Confirmada
            </span>
            <span className="font-display text-xl sm:text-2xl font-bold text-emerald-800">
              {formatCurrencyBRL(totalRevenue)}
            </span>
            <p className="text-[10px] text-emerald-700 mt-1 flex items-center gap-1 font-medium">
              <TrendingUp className="w-3 h-3" />
              PIX Confirmados
            </p>
          </div>

          <div className="p-4 bg-[#F5F3F3] border border-[#E2E2E2] rounded-xs">
            <span className="text-[10px] uppercase tracking-wider text-[#545F72] font-semibold block mb-1">
              Fotos Digitais Vendidas
            </span>
            <span className="font-display text-xl sm:text-2xl font-bold text-[#1B1C1C]">
              {totalPhotosSold} un
            </span>
            <p className="text-[10px] text-[#545F72] mt-1">
              Preço progressivo ativo
            </p>
          </div>

          <div className="p-4 bg-amber-50 border border-amber-200 rounded-xs">
            <span className="text-[10px] uppercase tracking-wider text-amber-900 font-semibold block mb-1">
              Pendentes de PIX
            </span>
            <span className="font-display text-xl sm:text-2xl font-bold text-amber-950">
              {pendingOrdersCount}
            </span>
            <p className="text-[10px] text-amber-800 mt-1">
              Aguardando validação
            </p>
          </div>

          <div className="p-4 bg-blue-50 border border-blue-200 rounded-xs">
            <span className="text-[10px] uppercase tracking-wider text-blue-900 font-semibold block mb-1">
              Em Edição / Tratamento
            </span>
            <span className="font-display text-xl sm:text-2xl font-bold text-blue-950">
              {editingOrdersCount}
            </span>
            <p className="text-[10px] text-blue-800 mt-1">
              Lightroom / Photoshop
            </p>
          </div>

          <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xs">
            <span className="text-[10px] uppercase tracking-wider text-emerald-900 font-semibold block mb-1">
              Entregues Google Photos
            </span>
            <span className="font-display text-xl sm:text-2xl font-bold text-emerald-950">
              {deliveredOrdersCount}
            </span>
            <p className="text-[10px] text-emerald-800 mt-1">Links ativos</p>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-[#E2E2E2] text-xs pt-6">
          <button
            onClick={() => setActiveTab("orders")}
            className={`pb-3 px-4 font-semibold uppercase tracking-wider cursor-pointer transition-colors ${
              activeTab === "orders"
                ? "border-b-2 border-[#1B1C1C] text-[#1B1C1C]"
                : "text-[#545F72] hover:text-[#1B1C1C]"
            }`}
          >
            Gestão de Pedidos ({orders.length})
          </button>

          <button
            onClick={() => setActiveTab("galleries")}
            className={`pb-3 px-4 font-semibold uppercase tracking-wider cursor-pointer transition-colors ${
              activeTab === "galleries"
                ? "border-b-2 border-[#1B1C1C] text-[#1B1C1C]"
                : "text-[#545F72] hover:text-[#1B1C1C]"
            }`}
          >
            Galerias &amp; Eventos ({galleries.length})
          </button>

          <button
            onClick={() => setActiveTab("pricing")}
            className={`pb-3 px-4 font-semibold uppercase tracking-wider cursor-pointer transition-colors ${
              activeTab === "pricing"
                ? "border-b-2 border-[#1B1C1C] text-[#1B1C1C]"
                : "text-[#545F72] hover:text-[#1B1C1C]"
            }`}
          >
            Tabela de Preço Progressivo
          </button>
        </div>
      </div>

      {/* Tab 1: Orders Management */}
      {activeTab === "orders" && (
        <div className="space-y-6">
          {/* Filters Bar */}
          <div className="bg-white border border-[#E2E2E2] rounded-xs p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 shadow-xs">
            <div className="flex items-center gap-1.5 overflow-x-auto w-full sm:w-auto pb-2 sm:pb-0">
              <button
                onClick={() => setOrderFilterStatus("all")}
                className={`px-3 py-1.5 text-xs font-semibold uppercase tracking-wider rounded-xs cursor-pointer ${
                  orderFilterStatus === "all"
                    ? "bg-[#1B1C1C] text-white"
                    : "bg-[#F5F3F3] text-[#545F72] hover:bg-[#EFEAEA]"
                }`}
              >
                Todos ({orders.length})
              </button>

              <button
                onClick={() => setOrderFilterStatus("pending_payment")}
                className={`px-3 py-1.5 text-xs font-semibold uppercase tracking-wider rounded-xs cursor-pointer ${
                  orderFilterStatus === "pending_payment"
                    ? "bg-amber-800 text-white"
                    : "bg-amber-50 text-amber-900 hover:bg-amber-100"
                }`}
              >
                Pendentes PIX ({pendingOrdersCount})
              </button>

              <button
                onClick={() => setOrderFilterStatus("paid_editing")}
                className={`px-3 py-1.5 text-xs font-semibold uppercase tracking-wider rounded-xs cursor-pointer ${
                  orderFilterStatus === "paid_editing"
                    ? "bg-blue-800 text-white"
                    : "bg-blue-50 text-blue-900 hover:bg-blue-100"
                }`}
              >
                Em Edição ({editingOrdersCount})
              </button>

              <button
                onClick={() => setOrderFilterStatus("delivered")}
                className={`px-3 py-1.5 text-xs font-semibold uppercase tracking-wider rounded-xs cursor-pointer ${
                  orderFilterStatus === "delivered"
                    ? "bg-emerald-800 text-white"
                    : "bg-emerald-50 text-emerald-900 hover:bg-emerald-100"
                }`}
              >
                Entregues ({deliveredOrdersCount})
              </button>
            </div>

            {/* Search Input */}
            <div className="relative w-full sm:w-64">
              <Search className="w-3.5 h-3.5 absolute left-3 top-3 text-[#747878]" />
              <input
                type="text"
                placeholder="Buscar cliente, WhatsApp ou #..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-3 py-2 bg-[#FBF9F9] border border-[#E2E2E2] text-xs rounded-xs text-[#1B1C1C] focus:outline-none focus:border-[#1B1C1C]"
              />
            </div>
          </div>

          {/* Orders Table / Cards */}
          <div className="space-y-4">
            {filteredOrders.length === 0 ? (
              <div className="bg-white border border-[#E2E2E2] rounded-xs p-12 text-center text-xs text-[#545F72]">
                Nenhum pedido correspondente ao filtro selecionado.
              </div>
            ) : (
              filteredOrders.map((order) => (
                <div
                  key={order.id}
                  className="bg-white border border-[#E2E2E2] rounded-xs p-5 sm:p-6 shadow-xs space-y-4 hover:border-[#1B1C1C] transition-colors"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#E2E2E2]">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-[#F5F3F3] text-[#1B1C1C] rounded-xs flex items-center justify-center font-mono font-bold text-xs">
                        #{order.id.split("-")[1] || order.id}
                      </div>

                      <div>
                        <div className="flex items-center gap-2">
                          <h4 className="font-display text-base font-bold text-[#1B1C1C]">
                            {order.customerName}
                          </h4>
                          <span className="text-xs text-[#545F72]">•</span>
                          <span className="text-xs text-[#545F72]">
                            {order.createdAt}
                          </span>
                        </div>
                        <p className="text-xs text-[#545F72] flex items-center gap-2">
                          <span>{order.galleryTitle}</span>
                          <span>•</span>
                          <span className="font-mono text-emerald-700 font-semibold">
                            {order.customerWhatsApp}
                          </span>
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      <span className="font-mono text-base font-bold text-emerald-800">
                        {formatCurrencyBRL(order.totalAmount)}
                      </span>

                      {/* Status Badges */}
                      {order.status === "pending_payment" && (
                        <span className="px-2.5 py-1 bg-amber-100 text-amber-950 text-[10px] font-bold uppercase rounded-xs">
                          Pendente PIX
                        </span>
                      )}
                      {order.status === "paid_editing" && (
                        <span className="px-2.5 py-1 bg-blue-100 text-blue-950 text-[10px] font-bold uppercase rounded-xs">
                          Em Edição
                        </span>
                      )}
                      {order.status === "delivered" && (
                        <span className="px-2.5 py-1 bg-emerald-100 text-emerald-950 text-[10px] font-bold uppercase rounded-xs flex items-center gap-1">
                          <CheckCircle2 className="w-3 h-3 text-emerald-700" />
                          Entregue
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Photos Mini Grid */}
                  <div>
                    <div className="flex items-center justify-between text-xs text-[#545F72] mb-2">
                      <span>
                        {order.totalPhotos} fotos compradas (Preço Médio:{" "}
                        <strong>
                          {formatCurrencyBRL(order.effectiveUnitPrice)}/foto
                        </strong>{" "}
                        • Economia:{" "}
                        <strong>{formatCurrencyBRL(order.savings)}</strong>)
                      </span>
                      {order.proofUploaded && (
                        <span className="text-emerald-700 font-medium flex items-center gap-1">
                          <FileText className="w-3.5 h-3.5" />
                          Comprovante Anexado:{" "}
                          {order.proofFileName || "comprovante.pdf"}
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-2 overflow-x-auto pb-2">
                      {order.items.map((it, idx) => (
                        <img
                          key={idx}
                          src={it.photoUrl}
                          alt={it.photoTitle}
                          className="w-14 h-14 rounded-xs object-cover border border-[#E2E2E2] shrink-0"
                          title={it.photoTitle}
                        />
                      ))}
                    </div>
                  </div>

                  {/* Action Buttons for Photographer */}
                  <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-[#E2E2E2]">
                    <div className="flex items-center gap-2 text-xs text-[#545F72]">
                      {order.googlePhotosUrl && (
                        <a
                          href={order.googlePhotosUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-emerald-800 hover:underline flex items-center gap-1 font-medium"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                          Google Photos Ativo
                        </a>
                      )}
                    </div>

                    <div className="flex flex-wrap items-center gap-2">
                      {/* WhatsApp Notify Button */}
                      <button
                        onClick={() => handleOpenWhatsAppNotify(order)}
                        className="px-3 py-1.5 bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-200 text-xs font-semibold rounded-xs flex items-center gap-1.5 cursor-pointer transition-colors"
                      >
                        <MessageSquare className="w-3.5 h-3.5" />
                        <span>Avisar no WhatsApp</span>
                      </button>

                      {/* Transition: Confirm Payment */}
                      {order.status === "pending_payment" && (
                        <button
                          onClick={() =>
                            onUpdateOrderStatus(order.id, "paid_editing")
                          }
                          className="px-3.5 py-1.5 bg-emerald-800 hover:bg-emerald-900 text-white text-xs font-semibold uppercase tracking-wider rounded-xs flex items-center gap-1.5 cursor-pointer transition-colors"
                        >
                          <Check className="w-3.5 h-3.5" />
                          <span>Aprovar PIX &amp; Iniciar Edição</span>
                        </button>
                      )}

                      {/* Transition: Deliver Photos */}
                      {order.status === "paid_editing" && (
                        <button
                          onClick={() => {
                            setDeliveringOrder(order);
                            setDeliveryGooglePhotosUrl(
                              order.googlePhotosUrl || "",
                            );
                          }}
                          className="px-3.5 py-1.5 bg-[#1B1C1C] hover:bg-[#2A2A2A] text-white text-xs font-semibold uppercase tracking-wider rounded-xs flex items-center gap-1.5 cursor-pointer transition-colors shadow-xs"
                        >
                          <Send className="w-3.5 h-3.5" />
                          <span>Concluir Edição &amp; Entregar Link</span>
                        </button>
                      )}

                      {/* Re-deliver or Edit Link */}
                      {order.status === "delivered" && (
                        <button
                          onClick={() => {
                            setDeliveringOrder(order);
                            setDeliveryGooglePhotosUrl(
                              order.googlePhotosUrl || "",
                            );
                          }}
                          className="px-3 py-1.5 border border-[#E2E2E2] hover:border-[#1B1C1C] text-[#545F72] hover:text-[#1B1C1C] text-xs font-medium rounded-xs cursor-pointer transition-colors"
                        >
                          Alterar Link do Google Photos
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Tab 2: Galleries Management */}
      {activeTab === "galleries" && (
        <div className="space-y-6">
          <div className="flex justify-between items-center bg-white border border-[#E2E2E2] rounded-xs p-4">
            <span className="text-xs text-[#545F72]">
              Gerencie suas galerias públicas e privadas, defina PINs e vincule
              álbuns do Google Photos.
            </span>
            <button
              onClick={() => {
                alert(
                  "Para adicionar uma nova galeria, use o editor de galerias do sistema.",
                );
              }}
              className="px-3.5 py-2 bg-[#1B1C1C] text-white text-xs font-semibold uppercase tracking-wider rounded-xs flex items-center gap-1.5 cursor-pointer"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Nova Galeria</span>
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {galleries.map((gallery) => (
              <div
                key={gallery.id}
                className="bg-white border border-[#E2E2E2] rounded-xs overflow-hidden shadow-xs flex flex-col justify-between"
              >
                <div>
                  <div className="relative h-36 bg-[#EFEAEA]">
                    <img
                      src={gallery.coverImage}
                      alt={gallery.title}
                      className="w-full h-full object-cover"
                    />
                    <div className="absolute top-2 left-2">
                      {gallery.type === "private" ? (
                        <span className="px-2 py-0.5 bg-black/80 text-amber-300 text-[10px] font-bold uppercase rounded-xs flex items-center gap-1">
                          <Lock className="w-3 h-3" />
                          Privada (PIN: {gallery.accessPin})
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 bg-emerald-900/80 text-emerald-200 text-[10px] font-bold uppercase rounded-xs flex items-center gap-1">
                          <Unlock className="w-3 h-3" />
                          Pública
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="p-4 space-y-2 text-xs">
                    <h4 className="font-display text-base font-bold text-[#1B1C1C]">
                      {gallery.title}
                    </h4>
                    <p className="text-[#545F72] text-[11px]">
                      {gallery.location}
                    </p>
                    <p className="text-[#545F72] text-[11px]">
                      {gallery.photos.length} fotos cadastradas • Preço base:{" "}
                      <strong>
                        {formatCurrencyBRL(gallery.basePhotoPrice)}/un
                      </strong>
                    </p>

                    <div className="p-2.5 bg-[#F5F3F3] rounded-xs space-y-1 text-[11px] text-[#545F72]">
                      <p className="truncate">
                        <strong>Google Photos:</strong>{" "}
                        {gallery.googlePhotosLink}
                      </p>
                      <p>
                        <strong>Chave PIX:</strong> {gallery.pixKey}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="p-4 pt-0">
                  <button
                    onClick={() => {
                      const newPin = prompt(
                        `Definir novo PIN para ${gallery.title}:`,
                        gallery.accessPin || "2023",
                      );
                      if (newPin) {
                        onCreateOrUpdateGallery({
                          ...gallery,
                          accessPin: newPin,
                        });
                        alert("PIN atualizado com sucesso!");
                      }
                    }}
                    className="w-full py-2 bg-white border border-[#1B1C1C] hover:bg-[#F5F3F3] text-[#1B1C1C] text-xs font-semibold uppercase tracking-wider rounded-xs cursor-pointer"
                  >
                    Editar PIN &amp; Configurações
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 3: Progressive Pricing Table */}
      {activeTab === "pricing" && (
        <div className="bg-white border border-[#E2E2E2] rounded-xs p-6 sm:p-8 space-y-6 shadow-xs">
          <div className="flex items-center gap-3 pb-4 border-b border-[#E2E2E2]">
            <div className="w-10 h-10 bg-emerald-50 text-emerald-800 border border-emerald-200 rounded-full flex items-center justify-center">
              <TrendingUp className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-display text-xl font-bold text-[#1B1C1C]">
                Estrutura de Preço Progressivo
              </h3>
              <p className="text-xs text-[#545F72]">
                Incentivo dinâmico para aumentar o ticket médio e o volume de
                fotos digitais vendidas por cliente.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            <div className="p-4 bg-[#F5F3F3] border border-[#E2E2E2] rounded-xs text-center space-y-2">
              <span className="text-[10px] uppercase font-bold text-[#545F72]">
                Faixa 1 (1 a 4 fotos)
              </span>
              <p className="font-display text-2xl font-bold text-[#1B1C1C]">
                R$ 25,00
              </p>
              <p className="text-[11px] text-[#545F72]">Preço base avulso</p>
            </div>

            <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xs text-center space-y-2">
              <span className="text-[10px] uppercase font-bold text-emerald-800">
                Faixa 2 (5 a 9 fotos)
              </span>
              <p className="font-display text-2xl font-bold text-emerald-950">
                R$ 20,00
              </p>
              <p className="text-[11px] text-emerald-700 font-semibold">
                20% de Desconto
              </p>
            </div>

            <div className="p-4 bg-emerald-100 border border-emerald-300 rounded-xs text-center space-y-2">
              <span className="text-[10px] uppercase font-bold text-emerald-900">
                Faixa 3 (10 a 19 fotos)
              </span>
              <p className="font-display text-2xl font-bold text-emerald-950">
                R$ 16,00
              </p>
              <p className="text-[11px] text-emerald-800 font-semibold">
                36% de Desconto (Mais Popular)
              </p>
            </div>

            <div className="p-4 bg-[#1B1C1C] text-white rounded-xs text-center space-y-2 shadow-md">
              <span className="text-[10px] uppercase font-bold text-emerald-300">
                Faixa 4 (20+ fotos)
              </span>
              <p className="font-display text-2xl font-bold text-white">
                R$ 12,00
              </p>
              <p className="text-[11px] text-emerald-300 font-semibold">
                52% de Desconto (Super Pack)
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Deliver Order Modal */}
      {deliveringOrder && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-[#FBF9F9] border border-[#E2E2E2] rounded-xs w-full max-w-lg shadow-2xl p-6 space-y-5 animate-fade-in-up">
            <div className="flex items-center justify-between pb-3 border-b border-[#E2E2E2]">
              <div>
                <h4 className="font-display text-lg font-bold text-[#1B1C1C]">
                  Concluir Edição &amp; Despachar Link
                </h4>
                <p className="text-xs text-[#545F72]">
                  Pedido #{deliveringOrder.id} • {deliveringOrder.customerName}
                </p>
              </div>
              <button
                onClick={() => setDeliveringOrder(null)}
                className="text-[#545F72] hover:text-[#1B1C1C]"
              >
                <Check className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleDeliverOrder} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-[#1B1C1C] mb-1">
                  Link do Álbum no Google Photos:
                </label>
                <input
                  type="url"
                  required
                  placeholder="https://photos.app.goo.gl/..."
                  value={deliveryGooglePhotosUrl}
                  onChange={(e) => setDeliveryGooglePhotosUrl(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-white border border-[#E2E2E2] text-xs font-mono rounded-xs text-[#1B1C1C] focus:outline-none focus:border-[#1B1C1C]"
                />
                <p className="text-[11px] text-[#545F72] mt-1">
                  O cliente receberá este link com destaque na Área do Cliente
                  VIP e via WhatsApp.
                </p>
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-[#E2E2E2]">
                <button
                  type="button"
                  onClick={() => setDeliveringOrder(null)}
                  className="px-4 py-2 border border-[#E2E2E2] text-[#545F72] text-xs font-semibold uppercase rounded-xs"
                >
                  Cancelar
                </button>

                <button
                  type="submit"
                  className="px-6 py-2 bg-emerald-800 hover:bg-emerald-900 text-white text-xs font-semibold uppercase tracking-wider rounded-xs cursor-pointer"
                >
                  Confirmar Entrega
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
