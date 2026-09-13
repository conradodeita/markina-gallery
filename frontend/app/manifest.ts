import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    id: "/",
    name: "Markina Gallery",
    short_name: "Markina",
    description: "Suas fotos e a central do fotógrafo.",
    start_url: "/",
    scope: "/",
    display: "standalone",
    background_color: "#f7f5ef",
    theme_color: "#f2c343",
    lang: "pt-BR",
    icons: [192, 512].map((size) => ({
      src: `/app-icons/${size}`, sizes: `${size}x${size}`, type: "image/png", purpose: "any",
    })),
  };
}
