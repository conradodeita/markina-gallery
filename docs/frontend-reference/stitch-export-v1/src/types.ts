export type PhotoCategory =
  | "cerimonia"
  | "making-of"
  | "casal"
  | "festa"
  | "detalhes"
  | "pre-wedding";

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
  category: PhotoCategory;
  url: string;
  highResUrl: string;
  aspectRatio: "portrait" | "landscape" | "square";
  width: number;
  height: number;
  cameraInfo: CameraInfo;
  isFavorite?: boolean;
  notes?: string;
  featured?: boolean;
}

export interface Gallery {
  id: string;
  title: string;
  coupleNames: string;
  subtitle: string;
  coverImage: string;
  date: string;
  dateRaw: string;
  photographer: string;
  studio: string;
  location: string;
  totalPhotos: number;
  quote: string;
  accessPin: string;
  categories: { id: PhotoCategory | "todas"; label: string; count: number }[];
  photos: Photo[];
}

export type PrintPaperType =
  | "hahnemuhle-rag"
  | "silk-matte"
  | "canvas"
  | "metallic";
export type FrameOption =
  | "none"
  | "oak-wood"
  | "black-minimal"
  | "walnut-wood"
  | "white-gallery";

export interface PrintSize {
  id: string;
  label: string;
  dimensions: string;
  price: number;
  framePrices: Record<FrameOption, number>;
}

export interface CartItem {
  id: string;
  photoId: string;
  photoTitle: string;
  photoUrl: string;
  type: "print" | "framed-print" | "digital-highres" | "album";
  sizeLabel: string;
  paperType?: PrintPaperType;
  paperLabel?: string;
  frame?: FrameOption;
  frameLabel?: string;
  price: number;
  quantity: number;
}

export interface AlbumConfig {
  coverColor: "couro-conhaque" | "linho-areia" | "couro-preto" | "veludo-verde";
  coverText: string;
  embossingColor: "gold" | "silver" | "blind-deboss";
  pageSize: "30x30" | "25x25" | "30x40";
  selectedPhotoIds: string[];
}

export type ActiveTab =
  | "home"
  | "gallery"
  | "cart"
  | "profile"
  | "album-builder";
