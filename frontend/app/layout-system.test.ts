import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

const globals = readFileSync(join(process.cwd(), "app", "globals.css"), "utf8");
const catalog = readFileSync(join(process.cwd(), "app", "admin", "catalog.module.css"), "utf8");
const pricing = readFileSync(join(process.cwd(), "app", "admin", "pricing", "pricing.module.css"), "utf8");
const tokens = readFileSync(join(process.cwd(), "app", "design-tokens.css"), "utf8");
const presentation = readFileSync(join(process.cwd(), "app", "gallery-presentation.tsx"), "utf8");
const publicGallery = readFileSync(join(process.cwd(), "app", "public-galleries", "[galleryId]", "page.tsx"), "utf8");
const tenantAddressNotice = readFileSync(join(process.cwd(), "app", "admin", "tenant-address-notice.module.css"), "utf8");

function declarations(selector: string) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const stylesheet = globals.replace(/\/\*[\s\S]*?\*\//g, "");
  return stylesheet.match(new RegExp(`(?:^|})\\s*${escaped}\\s*\\{([^}]*)\\}`))?.[1] ?? "";
}

function allDeclarations(selector: string) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const stylesheet = globals.replace(/\/\*[\s\S]*?\*\//g, "");
  return [...stylesheet.matchAll(new RegExp(`(?:^|})\\s*${escaped}\\s*\\{([^}]*)\\}`, "g"))]
    .map((match) => match[1])
    .join("\n");
}

describe("sistema global de layout fluido", () => {
  it("define um gutter adaptativo compartilhado", () => {
    expect(tokens).toMatch(/--mk-page-gutter:\s*clamp\(/);
  });

  it("mantém compacto no mobile o aviso de escolha do link da marca", () => {
    const mobile = tenantAddressNotice.match(/@media\s*\(max-width:\s*600px\)\s*\{([\s\S]*?)\n\}/)?.[1] ?? "";
    expect(mobile).toMatch(/\.notice p\s*\{[^}]*flex:\s*0 1 auto/);
  });

  it.each([".admin-shell", ".admin-content", ".client-content"])(
    "mantém %s full-width sem container central estreito",
    (selector) => {
      const rule = declarations(selector);
      expect(rule).toMatch(/width:\s*100%/);
      expect(rule).toMatch(/max-width:\s*none/);
      expect(rule).toContain("padding-inline:var(--mk-page-gutter)");
      expect(rule).not.toMatch(/840px|960px|1180px/);
    },
  );

  it.each([".admin-topbar", ".client-topbar"])(
    "alinha %s pelo gutter, sem cálculo de container central",
    (selector) => {
      const rule = declarations(selector);
      expect(rule).toContain("padding-inline:var(--mk-page-gutter)");
      expect(rule).not.toContain("calc((100vw -");
    },
  );

  it("não reintroduz centralização estreita no shell administrativo aninhado", () => {
    const rule = declarations(".admin-frame .admin-content > .admin-shell");
    expect(rule.trim()).not.toBe("");
    expect(rule).not.toMatch(/max-width:\s*\d+px/);
    expect(rule).not.toMatch(/margin-inline:\s*auto/);
  });

  it("usa a viewport na autenticação sem alargar o formulário", () => {
    expect(declarations(".auth-shell")).toMatch(/width:\s*100%/);
    expect(declarations(".auth-card")).toMatch(/width:\s*min\(100%,\s*440px\)/);
  });

  it("remove os limites estruturais locais inventariados", () => {
    const contract = globals.split("/* Contrato estrutural full-width")[1] ?? "";
    for (const selector of [
      ".gallery-editor-shell",
      ".gallery-preview-page",
      ".client-checkout-review",
      ".private-gallery-detail",
      ".admin-notifications-page",
    ]) {
      expect(contract, selector).toContain(selector);
    }
    expect(contract).toContain(".admin-shell:has(.photo-card-grid)");
    expect(contract).toMatch(/width:100%;\s*max-width:none;/);
  });

  it("não mantém limites estruturais antigos nos wrappers das rotas", () => {
    for (const selector of [
      ".public-gallery-shell",
      ".selection-summary--floating",
      ".gallery-editor-shell",
      ".gallery-preview-page",
      ".client-checkout-review",
      ".private-gallery-detail",
      ".admin-notifications-page",
    ]) {
      const rules = allDeclarations(selector);
      expect(rules, selector).not.toMatch(/max-width:\s*\d+px/);
      expect(rules, selector).not.toMatch(/width:\s*min\([^;]*\d+px/);
      expect(rules, selector).not.toMatch(/margin:\s*\d+px\s+auto\b/);
    }
  });

  it("mantém cards e mídias contidos nas seções fluidas", () => {
    expect(globals).toContain(":where(main,section,article,aside,header,footer,div,form,fieldset) { min-width:0; }");
    expect(globals).toContain("img,video,canvas,svg { max-width:100%; }");
  });

  it("adapta grids compartilhados à largura disponível", () => {
    const presentationRules = [...globals.matchAll(/\.gallery-presentation-grid\s*\{([^}]*)\}/g)].map((match) => match[1]);
    expect(presentationRules.some((rule) => rule.includes("repeat(auto-fit,minmax(240px,1fr))"))).toBe(true);
    expect(globals).toContain(".public-photo-grid { grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); }");
  });

  it("mantém catálogos administrativos fluidos e empilha as linhas de clientes em telas estreitas", () => {
    expect(catalog).toMatch(/\.catalog\s*\{[^}]*min-width:\s*0/);
    expect(catalog).toMatch(/\.directoryTable\s*\{[^}]*width:\s*100%/);
    expect(catalog).toMatch(/@media\s*\(max-width:[^)]+\)\s*\{[^]*\.directoryTable tbody tr\s*\{[^}]*display:\s*grid/);
  });

  it("empilha catálogo e editor de preços quando as duas colunas deixam de caber", () => {
    expect(pricing).toMatch(/\.workspace\s*\{[^}]*grid-template-columns:\s*minmax\(0, 1fr\) minmax\(0, 1\.1fr\)/);
    expect(pricing).toMatch(/@media\s*\(max-width:\s*65rem\)\s*\{\s*\.workspace\s*\{[^}]*grid-template-columns:\s*minmax\(0, 1fr\)/);
  });

  it("mantém duas colunas efetivas na grade fotográfica da cliente no mobile", () => {
    const mobileBlocks = [...globals.matchAll(/@media \(max-width:\s*560px\)\s*\{([\s\S]*?)\n\}/g)].map((match) => match[1]);
    expect(mobileBlocks.some((block) => /\.gallery-presentation-grid\s*\{[^}]*grid-template-columns:\s*repeat\(2,minmax\(0,1fr\)\)/.test(block))).toBe(true);
    expect(mobileBlocks.some((block) => /\.gallery-presentation-grid\s*\{[^}]*grid-template-columns:\s*1fr/.test(block))).toBe(false);
    expect(mobileBlocks.some((block) => /\.gallery-presentation-photo\s*\{[^}]*grid-column:\s*span 1/.test(block))).toBe(true);
  });

  it("reutiliza a mesma grade na Coleção e nos resultados faciais", () => {
    expect(publicGallery).toContain("<GalleryPresentation");
    expect(presentation.match(/className="gallery-presentation-grid"/g)).toHaveLength(2);
    expect(presentation).toContain("featuredGroups");
  });
});
