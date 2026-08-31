import React, { useState } from "react";
import { INITIAL_GALLERIES } from "./data/galleriesData";
import { Gallery, Photo, CartItem, ActiveTab } from "./types";
import { Header } from "./components/Header";
import { HeroCover } from "./components/HeroCover";
import { GalleryView } from "./components/GalleryView";
import { PhotoLightbox } from "./components/PhotoLightbox";
import { PrintStoreModal } from "./components/PrintStoreModal";
import { AlbumBuilderModal } from "./components/AlbumBuilderModal";
import { CartDrawer } from "./components/CartDrawer";
import { ClientProfileView } from "./components/ClientProfileView";
import { SlideshowModal } from "./components/SlideshowModal";
import { NavigationDrawer } from "./components/NavigationDrawer";
import { BottomNav } from "./components/BottomNav";

export default function App() {
  const [galleries, setGalleries] = useState<Gallery[]>(INITIAL_GALLERIES);
  const [currentGalleryId, setCurrentGalleryId] = useState<string>(
    INITIAL_GALLERIES[0].id,
  );
  const [activeTab, setActiveTab] = useState<ActiveTab>("home");

  // Modals & Drawers
  const [lightboxPhoto, setLightboxPhoto] = useState<Photo | null>(null);
  const [printPhoto, setPrintPhoto] = useState<Photo | null>(null);
  const [isAlbumBuilderOpen, setIsAlbumBuilderOpen] = useState(false);
  const [isSlideshowOpen, setIsSlideshowOpen] = useState(false);
  const [isCartOpen, setIsCartOpen] = useState(false);
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  // Cart state
  const [cartItems, setCartItems] = useState<CartItem[]>([
    {
      id: "init-01",
      photoId: "mr-001",
      photoTitle: "O Abraço Dourado ao Pôr do Sol",
      photoUrl: INITIAL_GALLERIES[0].coverImage,
      type: "framed-print",
      sizeLabel: "30 x 45 cm (Fine Art Clássico)",
      paperLabel: "Hahnemühle Photo Rag 308g",
      frameLabel: "Carvalho Natural com Paspatur",
      price: 560,
      quantity: 1,
    },
  ]);

  const currentGallery =
    galleries.find((g) => g.id === currentGalleryId) || galleries[0];

  // Favorites handler
  const handleToggleFavorite = (photoId: string) => {
    setGalleries((prevGalleries) =>
      prevGalleries.map((gal) => {
        if (gal.id !== currentGallery.id) return gal;
        return {
          ...gal,
          photos: gal.photos.map((photo) => {
            if (photo.id !== photoId) return photo;
            return {
              ...photo,
              isFavorite: !photo.isFavorite,
            };
          }),
        };
      }),
    );

    // Update lightbox photo state if open
    if (lightboxPhoto && lightboxPhoto.id === photoId) {
      setLightboxPhoto((prev) =>
        prev ? { ...prev, isFavorite: !prev.isFavorite } : null,
      );
    }
  };

  // Cart Handlers
  const handleAddToCart = (item: Omit<CartItem, "id">) => {
    const newItem: CartItem = {
      ...item,
      id: `cart-${Date.now()}-${Math.random().toString(36).substr(2, 4)}`,
    };
    setCartItems((prev) => [newItem, ...prev]);
  };

  const handleUpdateQuantity = (id: string, delta: number) => {
    setCartItems(
      (prev) =>
        prev
          .map((item) => {
            if (item.id === id) {
              const newQ = item.quantity + delta;
              return newQ > 0 ? { ...item, quantity: newQ } : null;
            }
            return item;
          })
          .filter(Boolean) as CartItem[],
    );
  };

  const handleRemoveItem = (id: string) => {
    setCartItems((prev) => prev.filter((item) => item.id !== id));
  };

  const handleClearCart = () => {
    setCartItems([]);
  };

  const favoritesCount = currentGallery.photos.filter(
    (p) => p.isFavorite,
  ).length;
  const cartTotalCount = cartItems.reduce((acc, it) => acc + it.quantity, 0);

  return (
    <div className="min-h-screen bg-[#FBF9F9] text-[#1B1C1C] flex flex-col justify-between selection:bg-[#1A1A1A] selection:text-white">
      {/* Top Header */}
      <Header
        currentGallery={currentGallery}
        galleries={galleries}
        onSelectGallery={(g) => {
          setCurrentGalleryId(g.id);
          setActiveTab("home");
        }}
        cartCount={cartTotalCount}
        favoritesCount={favoritesCount}
        onOpenCart={() => setIsCartOpen(true)}
        onOpenMenu={() => setIsMenuOpen(true)}
        onOpenFavorites={() => {
          setActiveTab("gallery");
        }}
        onOpenAlbumBuilder={() => setIsAlbumBuilderOpen(true)}
        onStartSlideshow={() => setIsSlideshowOpen(true)}
      />

      {/* Main Content by Active Tab */}
      <div className="flex-1">
        {activeTab === "home" && (
          <HeroCover
            gallery={currentGallery}
            onEnterGallery={() => setActiveTab("gallery")}
          />
        )}

        {activeTab === "gallery" && (
          <GalleryView
            gallery={currentGallery}
            onPhotoClick={(photo) => setLightboxPhoto(photo)}
            onToggleFavorite={handleToggleFavorite}
            onOpenPrintModal={(photo) => setPrintPhoto(photo)}
            onStartSlideshow={() => setIsSlideshowOpen(true)}
            onOpenAlbumBuilder={() => setIsAlbumBuilderOpen(true)}
          />
        )}

        {activeTab === "cart" && (
          <div className="pt-24 pb-28 px-4 sm:px-8 max-w-4xl mx-auto">
            <CartDrawer
              items={cartItems}
              onClose={() => setActiveTab("gallery")}
              onUpdateQuantity={handleUpdateQuantity}
              onRemoveItem={handleRemoveItem}
              onClearCart={handleClearCart}
            />
          </div>
        )}

        {activeTab === "profile" && (
          <ClientProfileView
            gallery={currentGallery}
            onEnterGallery={() => setActiveTab("gallery")}
          />
        )}
      </div>

      {/* Bottom Navigation for Mobile */}
      <BottomNav
        activeTab={activeTab}
        onSelectTab={(tab) => {
          if (tab === "cart") {
            setIsCartOpen(true);
          } else {
            setActiveTab(tab);
          }
        }}
        cartCount={cartTotalCount}
      />

      {/* Lightbox Modal */}
      {lightboxPhoto && (
        <PhotoLightbox
          photo={lightboxPhoto}
          photos={currentGallery.photos}
          onClose={() => setLightboxPhoto(null)}
          onSelectPhoto={(p) => setLightboxPhoto(p)}
          onToggleFavorite={handleToggleFavorite}
          onOpenPrintModal={(p) => {
            setPrintPhoto(p);
          }}
        />
      )}

      {/* Print & Frame Store Modal */}
      {printPhoto && (
        <PrintStoreModal
          photo={printPhoto}
          onClose={() => setPrintPhoto(null)}
          onAddToCart={handleAddToCart}
        />
      )}

      {/* Album Builder Modal */}
      {isAlbumBuilderOpen && (
        <AlbumBuilderModal
          gallery={currentGallery}
          onClose={() => setIsAlbumBuilderOpen(false)}
          onAddToCart={handleAddToCart}
        />
      )}

      {/* Slideshow Modal */}
      {isSlideshowOpen && (
        <SlideshowModal
          photos={currentGallery.photos}
          onClose={() => setIsSlideshowOpen(false)}
        />
      )}

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
        favoritesCount={favoritesCount}
        cartCount={cartTotalCount}
      />

      {/* Slide-out Cart Drawer */}
      {isCartOpen && (
        <CartDrawer
          items={cartItems}
          onClose={() => setIsCartOpen(false)}
          onUpdateQuantity={handleUpdateQuantity}
          onRemoveItem={handleRemoveItem}
          onClearCart={handleClearCart}
        />
      )}
    </div>
  );
}
