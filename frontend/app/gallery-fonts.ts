const galleryFontFamilies: Record<string, string> = {
  "system-sans": "var(--font-system-sans)",
  montserrat: "var(--font-montserrat)",
  "system-serif": "var(--font-system-serif)",
  "playfair-display": "var(--font-playfair-display)",
  "handwritten-caveat": "var(--font-caveat)",
  "handwritten-dancing-script": "var(--font-dancing-script)",
};

const legacyGalleryFonts: Record<string, string> = {
  "sans-serif": "system-sans",
  DejaVuSans: "system-sans",
  serif: "system-serif",
  DejaVuSerif: "system-serif",
  monospace: "system-sans",
};

export function galleryFontFamily(token: string | null | undefined) {
  const normalized = token && galleryFontFamilies[token] ? token : legacyGalleryFonts[token ?? ""] ?? "system-sans";
  return galleryFontFamilies[normalized];
}
