export type GalleryType = "private" | "public";

export type OrderStatus = "pending_payment" | "paid_editing" | "delivered";

export interface CameraInfo {
  camera: string;
  lens: string;
  focalLength: string;
  aperture: string;
  shutterSpeed: string;
  iso: string;
  time: string;
}

export interface Photo {
  id: string;
  title: string;
  category: string;
  url: string;
  highResUrl: string;
  aspectRatio: "portrait" | "landscape" | "square";
  width: number;
  height: number;
  cameraInfo: CameraInfo;
  isFavorite?: boolean;
  notes?: string;
  featured?: boolean;
  faceTags?: string[]; // Face identifier tokens for recognition matching
  matchConfidence?: number; // Calculated dynamic match percentage e.g. 96%
}

export interface PricingTier {
  id: string;
  minQty: number;
  maxQty: number | null; // null represents unbounded e.g. 20+
  unitPrice: number; // in BRL (R$)
  discountPercent: number;
  label: string;
  badge?: string;
}

export interface Gallery {
  id: string;
  title: string;
  coupleOrEventName: string;
  subtitle: string;
  coverImage: string;
  date: string;
  dateRaw: string;
  photographer: string;
  studio: string;
  location: string;
  type: GalleryType;
  accessPin?: string;
  totalPhotos: number;
  quote: string;
  googlePhotosLink: string;
  googleDriveLink?: string;
  pixKey: string;
  pixKeyType: string;
  basePhotoPrice: number; // Base single photo price
  fullGalleryPrice: number; // Complete gallery bundle package price
  categories: { id: string; label: string; count: number }[];
  photos: Photo[];
}

export interface CartPhotoItem {
  id: string;
  photoId: string;
  photoTitle: string;
  photoUrl: string;
  category: string;
  galleryId: string;
  galleryTitle: string;
}

export interface CustomerUser {
  phone: string;
  name: string;
  isLoggedIn: boolean;
  lgpdConsentFace: boolean;
  selfieUrl?: string;
  matchedFaceToken?: string;
}

export interface OrderItem {
  photoId: string;
  photoTitle: string;
  photoUrl: string;
  unitPrice: number;
}

export interface Order {
  id: string;
  createdAt: string;
  galleryId: string;
  galleryTitle: string;
  customerName: string;
  customerWhatsApp: string;
  customerEmail?: string;
  items: OrderItem[];
  totalPhotos: number;
  totalAmount: number;
  originalAmount: number;
  savings: number;
  effectiveUnitPrice: number;
  isFullGalleryBundle?: boolean;
  pixCode: string;
  pixQrCodeUrl: string;
  status: OrderStatus;
  paidAt?: string;
  deliveredAt?: string;
  googlePhotosUrl?: string;
  zipDownloadUrl?: string;
  proofUploaded?: boolean;
  proofFileName?: string;
  photographerNotes?: string;
}

export type ActiveTab = "home" | "gallery" | "cart" | "profile" | "admin";
