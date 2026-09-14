import { PRODUCT_NAME } from "./product-brand";
import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    id: "/",
    name: PRODUCT_NAME,
    short_name: PRODUCT_NAME,
    description: "Suas fotos e a central do fotógrafo.",
    start_url: "/",
    scope: "/",
    display: "standalone",
    background_color: "#f3f4f5",
    theme_color: "#f2c343",
    lang: "pt-BR",
    icons: [192, 512].map((size) => ({
      src: `/api/branding/app-icon?size=${size}`, sizes: `${size}x${size}`, type: "image/png", purpose: "any",
    })),
  };
}
