import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

const globals = readFileSync(join(process.cwd(), "app", "globals.css"), "utf8");
const tokens = readFileSync(join(process.cwd(), "app", "design-tokens.css"), "utf8");

function declarations(selector: string) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return globals.match(new RegExp(`${escaped}\\s*\\{([^}]*)\\}`))?.[1] ?? "";
}

describe("sistema global de layout fluido", () => {
  it("define um gutter adaptativo compartilhado", () => {
    expect(tokens).toMatch(/--mk-page-gutter:\s*clamp\(/);
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

  it("usa a viewport na autenticação sem alargar o formulário", () => {
    expect(declarations(".auth-shell")).toMatch(/width:\s*100%/);
    expect(declarations(".auth-card")).toMatch(/width:\s*min\(100%,\s*440px\)/);
  });

  it("remove os limites estruturais locais inventariados", () => {
    const contract = globals.split("/* Contrato estrutural full-width")[1] ?? "";
    for (const selector of [
      ".gallery-editor-shell",
      ".gallery-preview-page",
      ".pricing-presets-page",
      ".client-directory-shell",
      ".client-checkout-review",
      ".private-gallery-detail",
      ".admin-notifications-page",
    ]) {
      expect(contract, selector).toContain(selector);
    }
    expect(contract).toContain(".admin-shell:has(.photo-card-grid)");
    expect(contract).toMatch(/width:100%;\s*max-width:none;/);
  });

  it("mantém cards e mídias contidos nas seções fluidas", () => {
    expect(globals).toContain(":where(main,section,article,aside,header,footer,div,form,fieldset) { min-width:0; }");
    expect(globals).toContain("img,video,canvas,svg { max-width:100%; }");
  });

  it("adapta grids compartilhados à largura disponível", () => {
    expect(globals).toContain(".client-directory-grid { grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); }");
    const presentationRules = [...globals.matchAll(/\.gallery-presentation-grid\s*\{([^}]*)\}/g)].map((match) => match[1]);
    expect(presentationRules.some((rule) => rule.includes("repeat(auto-fit,minmax(240px,1fr))"))).toBe(true);
    expect(globals).toContain(".public-photo-grid { grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); }");
  });
});
