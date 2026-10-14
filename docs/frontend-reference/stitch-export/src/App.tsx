import React, { useState } from "react";
import { INITIAL_GALLERIES, INITIAL_ORDERS } from "./data/galleriesData";
import {
  Gallery,
  Photo,
  Order,
  OrderStatus,
  CustomerUser,
  ActiveTab,
} from "./types";
import { Header } from "./components/Header";
import { HeroCover } from "./components/HeroCover";
import { GalleryView } from "./components/GalleryView";
import { PhotoLightbox } from "./components/PhotoLightbox";
import { CartDrawer } from "./components/CartDrawer";
import { PixCheckoutModal } from "./components/PixCheckoutModal";
import { ClientProfileView } from "./components/ClientProfileView";
import { AdminDashboardView } from "./components/AdminDashboardView";
import { FacialRecognitionModal } from "./components/FacialRecognitionModal";
import { GalleryCatalogModal } from "./components/GalleryCatalogModal";
import { WhatsAppAuthModal } from "./components/WhatsAppAuthModal";
import { SlideshowModal } from "./components/SlideshowModal";
import { NavigationDrawer } from "./components/NavigationDrawer";
import { BottomNav } from "./components/BottomNav";
import { calculateProgressivePrice, formatCurrencyBRL } from "./utils/pricing";

export default function App() {
  // Main Data States
  const [galleries, setGalleries] = useState<Gallery[]>(INITIAL_GALLERIES);
  const [currentGalleryId, setCurrentGalleryId] = useState<string>(
    INITIAL_GALLERIES[0].id,
  );
  const [orders, setOrders] = useState<Order[]>(INITIAL_ORDERS);
  const [activeTab, setActiveTab] = useState<ActiveTab>("home");

  // Customer User (WhatsApp Auth)
  const [currentUser, setCurrentUser] = useState<CustomerUser>({
    phone: "(11) 98842-1920",
    name: "Marina Alencar",
    isLoggedIn: true,
    lgpdConsentFace: false,
  });

  // Digital Photos Cart State
  const [cartPhotoIds, setCartPhotoIds] = useState<string[]>([
    "mr-001",
    "mr-002",
    "mr-003",
  ]);

  // Biometric Facial Recognition State
  const [matchedPhotoIds, setMatchedPhotoIds] = useState<string[]>([]);
  const [selfieUrl, setSelfieUrl] = useState<string | null>(null);

  // Modals & UI Viewers
  const [lightboxPhoto, setLightboxPhoto] = useState<Photo | null>(null);
  const [activePixOrder, setActivePixOrder] = useState<Order | null>(null);
  const [isCartOpen, setIsCartOpen] = useState(false);
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isSlideshowOpen, setIsSlideshowOpen] = useState(false);
  const [isFacialRecognitionOpen, setIsFacialRecognitionOpen] = useState(false);
  const [isCatalogModalOpen, setIsCatalogModalOpen] = useState(false);
  const [isWhatsAppModalOpen, setIsWhatsAppModalOpen] = useState(false);

  const currentGallery =
    galleries.find((g) => g.id === currentGalleryId) || galleries[0];

  // Cart photos resolved from IDs
  const cartPhotos = currentGallery.photos.filter((p) =>
    cartPhotoIds.includes(p.id),
  );

  // Toggle favorite photo
  const handleToggleFavorite = (photoId: string) => {
    setGalleries((prevGalleries) =>
      prevGalleries.map((gal) => {
        if (gal.id !== currentGallery.id) return gal;
        return {
          ...gal,
          photos: gal.photos.map((p) => {
            if (p.id !== photoId) return p;
            return {
              ...p,
              isFavorite: !p.isFavorite,
            };
          }),
        };
      }),
    );

    if (lightboxPhoto && lightboxPhoto.id === photoId) {
      setLightboxPhoto((prev) =>
        prev ? { ...prev, isFavorite: !prev.isFavorite } : null,
      );
    }
  };

  // Cart Handlers
  const handleToggleCartPhoto = (photo: Photo) => {
    setCartPhotoIds((prev) =>
      prev.includes(photo.id)
        ? prev.filter((id) => id !== photo.id)
        : [...prev, photo.id],
    );
  };

  const handleRemoveCartPhoto = (photoId: string) => {
    setCartPhotoIds((prev) => prev.filter((id) => id !== photoId));
  };

  const handleClearCart = () => {
    setCartPhotoIds([]);
  };

  const handleAddMultipleToCart = (photosToAdd: Photo[]) => {
    const idsToAdd = photosToAdd.map((p) => p.id);
    setCartPhotoIds((prev) => Array.from(new Set([...prev, ...idsToAdd])));
    setIsCartOpen(true);
  };

  const handleSelectAllGalleryPhotos = () => {
    const allIds = currentGallery.photos.map((p) => p.id);
    setCartPhotoIds(allIds);
  };

  // Checkout Handler: creates real Order with PIX QR
  const handleProceedToCheckout = (
    customerName: string,
    customerPhone: string,
  ) => {
    const progressive = calculateProgressivePrice(
      cartPhotos.length,
      undefined,
      currentGallery.basePhotoPrice,
    );

    const newOrderId = `MK-${Date.now().toString().slice(-4)}`;
    const newOrder: Order = {
      id: newOrderId,
      customerName,
      customerWhatsApp: customerPhone,
      galleryId: currentGallery.id,
      galleryTitle: currentGallery.title,
      items: cartPhotos.map((p) => ({
        photoId: p.id,
        photoTitle: p.title,
        photoUrl: p.url,
        highResUrl: p.highResUrl,
        unitPrice: progressive.unitPrice,
      })),
      totalPhotos: cartPhotos.length,
      effectiveUnitPrice: progressive.unitPrice,
      originalAmount: progressive.originalAmount,
      totalAmount: progressive.totalAmount,
      savings: progressive.savings,
      status: "pending_payment",
      pixCode: `00020126580014br.gov.bcb.pix0136pix@markinagallery.com.br520400005303986540${progressive.totalAmount.toFixed(2)}5802BR5920Markina Studios6009Sao Paulo62070503***6304${Math.random().toString(36).substr(2, 4).toUpperCase()}`,
      pixQrCodeUrl: `https://api.qrserver.com/v1/create-qr-code/?size=240x240&data=PIX_MARKINA_${newOrderId}_VALOR_${progressive.totalAmount}`,
      createdAt: new Date().toLocaleDateString("pt-BR"),
      googlePhotosUrl: currentGallery.googlePhotosLink,
    };

    setOrders((prev) => [newOrder, ...prev]);
    setCurrentUser((prev) => ({
      ...prev,
      name: customerName,
      phone: customerPhone,
      isLoggedIn: true,
    }));

    setIsCartOpen(false);
    setActivePixOrder(newOrder);
  };

  // Confirm payment transition
  const handleConfirmOrderPayment = (orderId: string, proofName?: string) => {
    setOrders((prev) =>
      prev.map((ord) => {
        if (ord.id !== orderId) return ord;
        return {
          ...ord,
          status: "paid_editing",
          paidAt: new Date().toLocaleDateString("pt-BR"),
          proofUploaded: true,
          proofFileName: proofName || "comprovante_pix.pdf",
        };
      }),
    );
  };

  // Admin status transition
  const handleUpdateOrderStatus = (
    orderId: string,
    status: OrderStatus,
    googlePhotosUrl?: string,
  ) => {
    setOrders((prev) =>
      prev.map((ord) => {
        if (ord.id !== orderId) return ord;
        return {
          ...ord,
          status,
          ...(status === "delivered"
            ? { deliveredAt: new Date().toLocaleDateString("pt-BR") }
            : {}),
          ...(googlePhotosUrl ? { googlePhotosUrl } : {}),
        };
      }),
    );
  };

  // Facial Recognition Matches
  const handleMatchesFound = (matchedIds: string[], selfie: string) => {
    setMatchedPhotoIds(matchedIds);
    setSelfieUrl(selfie);
    setCurrentUser((prev) => ({
      ...prev,
      lgpdConsentFace: true,
      selfieUrl: selfie,
    }));
    setActiveTab("gallery");
  };

  const handleRevokeLgpd = () => {
    setMatchedPhotoIds([]);
    setSelfieUrl(null);
    setCurrentUser((prev) => ({
      ...prev,
      lgpdConsentFace: false,
      selfieUrl: undefined,
    }));
    alert("Consentimento biométrico revogado e selfie eliminada com sucesso!");
  };

  const handleLoginWhatsApp = (
    name: string,
    phone: string,
    consent: boolean,
  ) => {
    setCurrentUser({
      name,
      phone,
      isLoggedIn: true,
      lgpdConsentFace: consent,
    });
  };

  const favoritesCount = currentGallery.photos.filter(
    (p) => p.isFavorite,
  ).length;

  return (
    <div className="min-h-screen bg-[#FBF9F9] text-[#1B1C1C] flex flex-col justify-between selection:bg-[#1A1A1A] selection:text-white">
      {/* Top Header */}
      <Header
        currentGallery={currentGallery}
        galleries={galleries}
        onOpenCatalog={() => setIsCatalogModalOpen(true)}
        cartCount={cartPhotoIds.length}
        favoritesCount={favoritesCount}
        onOpenCart={() => setIsCartOpen(true)}
        onOpenMenu={() => setIsMenuOpen(true)}
        onOpenFavorites={() => setActiveTab("gallery")}
        onOpenFacialRecognition={() => setIsFacialRecognitionOpen(true)}
        onOpenWhatsAppAuth={() => setIsWhatsAppModalOpen(true)}
        onOpenProfile={() => setActiveTab("profile")}
        onOpenAdmin={() => setActiveTab("admin")}
        currentUser={currentUser}
      />

      {/* Main Content Router */}
      <div className="flex-1">
        {activeTab === "home" && (
          <HeroCover
            gallery={currentGallery}
            onEnterGallery={() => setActiveTab("gallery")}
            onOpenFacialRecognition={() => setIsFacialRecognitionOpen(true)}
          />
        )}

        {activeTab === "gallery" && (
          <GalleryView
            gallery={currentGallery}
            onPhotoClick={(photo) => setLightboxPhoto(photo)}
            onToggleFavorite={handleToggleFavorite}
            cartPhotoIds={cartPhotoIds}
            onToggleCartPhoto={handleToggleCartPhoto}
            onAddMultipleToCart={handleAddMultipleToCart}
            onOpenFacialRecognition={() => setIsFacialRecognitionOpen(true)}
            matchedPhotoIds={matchedPhotoIds}
            selfieUrl={selfieUrl}
            onClearFaceFilter={() => setMatchedPhotoIds([])}
            onStartSlideshow={() => setIsSlideshowOpen(true)}
            onOpenCart={() => setIsCartOpen(true)}
          />
        )}

        {activeTab === "cart" && (
          <div className="pt-24 pb-28 px-4 sm:px-8 max-w-4xl mx-auto">
            <CartDrawer
              isOpen={true}
              onClose={() => setActiveTab("gallery")}
              gallery={currentGallery}
              cartPhotos={cartPhotos}
              onRemovePhoto={handleRemoveCartPhoto}
              onClearCart={handleClearCart}
              currentUser={currentUser}
              onProceedToCheckout={handleProceedToCheckout}
              onSelectAllGalleryPhotos={handleSelectAllGalleryPhotos}
            />
          </div>
        )}

        {activeTab === "profile" && (
          <ClientProfileView
            currentUser={currentUser}
            orders={orders}
            onOpenWhatsAppLogin={() => setIsWhatsAppModalOpen(true)}
            onLogoutWhatsApp={() =>
              setCurrentUser({
                name: "",
                phone: "",
                isLoggedIn: false,
                lgpdConsentFace: false,
              })
            }
            onRevokeLgpd={handleRevokeLgpd}
            onOpenPixModalForOrder={(ord) => setActivePixOrder(ord)}
            onEnterGallery={() => setActiveTab("gallery")}
            currentGallery={currentGallery}
          />
        )}

        {activeTab === "admin" && (
          <AdminDashboardView
            galleries={galleries}
            orders={orders}
            onUpdateOrderStatus={handleUpdateOrderStatus}
            onCreateOrUpdateGallery={(updatedGal) => {
              setGalleries((prev) =>
                prev.map((g) => (g.id === updatedGal.id ? updatedGal : g)),
              );
            }}
            onExitAdmin={() => setActiveTab("gallery")}
          />
        )}
      </div>

      {/* Mobile Bottom Navigation */}
      <BottomNav
        activeTab={activeTab}
        onSelectTab={(tab) => {
          if (tab === "cart") {
            setIsCartOpen(true);
          } else {
            setActiveTab(tab);
          }
        }}
        cartCount={cartPhotoIds.length}
        onOpenFacialRecognition={() => setIsFacialRecognitionOpen(true)}
      />

      {/* Lightbox Modal */}
      {lightboxPhoto && (
        <PhotoLightbox
          photo={lightboxPhoto}
          photos={currentGallery.photos}
          onClose={() => setLightboxPhoto(null)}
          onSelectPhoto={(p) => setLightboxPhoto(p)}
          onToggleFavorite={handleToggleFavorite}
          isCarted={cartPhotoIds.includes(lightboxPhoto.id)}
          onToggleCart={() => handleToggleCartPhoto(lightboxPhoto)}
          unitPrice={
            calculateProgressivePrice(
              cartPhotoIds.length || 1,
              undefined,
              currentGallery.basePhotoPrice,
            ).unitPrice
          }
        />
      )}

      {/* Facial Recognition Biometric Modal (LGPD Compliant) */}
      <FacialRecognitionModal
        isOpen={isFacialRecognitionOpen}
        onClose={() => setIsFacialRecognitionOpen(false)}
        gallery={currentGallery}
        onMatchesFound={handleMatchesFound}
      />

      {/* Gallery Catalog & PIN Unlock Modal */}
      <GalleryCatalogModal
        isOpen={isCatalogModalOpen}
        onClose={() => setIsCatalogModalOpen(false)}
        galleries={galleries}
        currentGalleryId={currentGallery.id}
        onSelectGallery={(g) => {
          setCurrentGalleryId(g.id);
          setActiveTab("home");
        }}
      />

      {/* WhatsApp Auth Modal */}
      <WhatsAppAuthModal
        isOpen={isWhatsAppModalOpen}
        onClose={() => setIsWhatsAppModalOpen(false)}
        onLogin={handleLoginWhatsApp}
        initialPhone={currentUser.phone}
        initialName={currentUser.name}
      />

      {/* PIX Checkout & Simulation Modal */}
      {activePixOrder && (
        <PixCheckoutModal
          order={activePixOrder}
          onClose={() => setActivePixOrder(null)}
          onConfirmOrderPayment={handleConfirmOrderPayment}
          onViewOrderStatus={() => {
            setActivePixOrder(null);
            setActiveTab("profile");
          }}
        />
      )}

      {/* Slideshow Presentation Modal */}
      <SlideshowModal
        isOpen={isSlideshowOpen}
        photos={currentGallery.photos}
        onClose={() => setIsSlideshowOpen(false)}
      />

      {/* Lateral Menu Drawer */}
      <NavigationDrawer
        isOpen={isMenuOpen}
        onClose={() => setIsMenuOpen(false)}
        galleries={galleries}
        currentGallery={currentGallery}
        onSelectGallery={(g) => {
          setCurrentGalleryId(g.id);
          setActiveTab("home");
        }}
        onNavigateTab={(tab) => setActiveTab(tab)}
        onOpenCatalog={() => setIsCatalogModalOpen(true)}
        onOpenFacialRecognition={() => setIsFacialRecognitionOpen(true)}
        onOpenWhatsAppAuth={() => setIsWhatsAppModalOpen(true)}
        onOpenAdmin={() => setActiveTab("admin")}
        cartCount={cartPhotoIds.length}
        currentUser={currentUser}
      />

      {/* Cart Drawer */}
      <CartDrawer
        isOpen={isCartOpen}
        onClose={() => setIsCartOpen(false)}
        gallery={currentGallery}
        cartPhotos={cartPhotos}
        onRemovePhoto={handleRemoveCartPhoto}
        onClearCart={handleClearCart}
        currentUser={currentUser}
        onProceedToCheckout={handleProceedToCheckout}
        onSelectAllGalleryPhotos={handleSelectAllGalleryPhotos}
      />
    </div>
  );
}
