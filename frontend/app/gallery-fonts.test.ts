import { describe, expect, it } from "vitest";

import { galleryFontFamily } from "./gallery-fonts";

describe("registro local de fontes da galeria", () => {
  it("resolve as oito opções controladas, incluindo três manuscritas", () => {
    const tokens = [
      "system-sans",
      "montserrat",
      "system-rounded",
      "system-serif",
      "playfair-display",
      "handwritten-caveat",
      "handwritten-dancing-script",
      "handwritten-personal",
    ];
    expect(new Set(tokens.map(galleryFontFamily))).toHaveLength(8);
    expect(tokens.filter((token) => token.startsWith("handwritten-"))).toHaveLength(3);
  });

  it("usa fallback seguro para token arbitrário sem aceitar CSS remoto", () => {
    expect(galleryFontFamily("url(https://example.test/font.woff2)")).toBe("var(--font-system-sans)");
  });
});
