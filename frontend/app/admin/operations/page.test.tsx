import { describe, expect, it, vi } from "vitest";

const navigation = vi.hoisted(() => ({
  redirect: vi.fn((destination: string) => {
    throw new Error(`REDIRECT:${destination}`);
  }),
}));

vi.mock("next/navigation", () => ({ redirect: navigation.redirect }));

import LegacyOperationsPage from "./page";

describe("rota legada de Operação", () => {
  it("redireciona para Galerias quando não há contexto", async () => {
    await expect(
      LegacyOperationsPage({ searchParams: Promise.resolve({}) }),
    ).rejects.toThrow("REDIRECT:/admin/galleries");
  });

  it("preserva a galeria ao redirecionar uma URL contextual", async () => {
    await expect(
      LegacyOperationsPage({
        searchParams: Promise.resolve({ parent_gallery_id: "source-1" }),
      }),
    ).rejects.toThrow(
      "REDIRECT:/admin/galleries/sources/source-1/edit/imagens",
    );
  });
});
