import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { PRODUCT_NAME, DEFAULT_WATERMARK_TEXT } from "./product-brand";
import manifest from "./manifest";
import { metadata } from "./layout";
import { ValidationHeader } from "./validation-ui";

it("centraliza nome e preserva identidade técnica e ícones do PWA", () => {
  expect(PRODUCT_NAME).toBe("Pick-your-Pic");
  expect(DEFAULT_WATERMARK_TEXT).toBe("Pick-your-Pic • PRÉVIA");
  expect(metadata.title).toBe(PRODUCT_NAME);
  expect(manifest()).toMatchObject({ name:PRODUCT_NAME, short_name:PRODUCT_NAME, id:"/", start_url:"/", scope:"/" });
  expect(manifest().icons?.map(icon => icon.src)).toEqual([192,512].map(size=>`/api/branding/app-icon?size=${size}`));
  const worker = readFileSync("public/markina-sw.js","utf8");
  expect(worker).toContain(`Sem conexão · ${PRODUCT_NAME}`);
  expect(worker).not.toContain("caches.open");
});

it("renderiza o novo nome em texto de produto", () => {
  render(<ValidationHeader role="Fotógrafo" version="teste" />);
  expect(screen.getByText(`${PRODUCT_NAME} · Homologação`)).toBeTruthy();
});

it("mantém defaults Docker alinhados sem renomear configuração ou projeto", () => {
  for (const file of ["docker-compose.yml", "docker-compose.preview-adjustment.yml"]) {
    const compose = readFileSync(`../docker/${file}`, "utf8");
    expect(compose).toContain(`MEDIA_WATERMARK_TEXT: \u0024{MEDIA_WATERMARK_TEXT:-${DEFAULT_WATERMARK_TEXT}}`);
    expect(compose).not.toContain("MEDIA_WATERMARK_TEXT:-MARKINA");
    expect(compose).toContain("markina-gallery");
  }
});
