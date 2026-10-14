import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PurchasePreview, purchasePreviewUrl } from "./purchase-preview";

describe("prévia protegida de compra", () => {
  it.each(["/library/purchases/items/item-1/preview", "/library/history/items/item-1/preview", "/gallery/gallery-1/photos/photo-1/preview", "/public-galleries/gallery-1/photos/photo-1/preview"])("encaminha %s uma única vez à API", (path) => {
    expect(purchasePreviewUrl(path)).toBe(`/api${path}`);
    expect(purchasePreviewUrl(`/api${path}`)).toBe(`/api${path}`);
  });
  it.each([null, "", "https://outside.test/preview", "//outside.test/preview", "/admin/photos/a/preview", "/gallery/a/photos/b/original", "/public-galleries/a/photos/b/original", "/api/api/gallery/a/photos/b/preview", "/api/api/public-galleries/a/photos/b/preview", "/gallery/../photos/a/preview", "/public-galleries/../photos/a/preview", "/gallery/a/photos/b/preview?redirect=outside", "/public-galleries/a/photos/b/preview?redirect=outside", "/public-galleries/a/photos/b/preview#fragment"])("recusa alternativa indevida %s", (path) => {
    expect(purchasePreviewUrl(path)).toBeNull();
  });
  it("trata mídia ausente, falha e nova URL sem trocar para original", () => {
    const { rerender } = render(<PurchasePreview path={null} name="A.jpg" />);
    expect(screen.getByRole("status").textContent).toBe("Prévia indisponível");
    rerender(<PurchasePreview path="/library/history/items/a/preview" name="A.jpg" />);
    fireEvent.error(screen.getByRole("img"));
    expect(screen.queryByRole("img")).toBeNull();
    expect(screen.getByRole("status")).toBeTruthy();
    rerender(<PurchasePreview path="/library/history/items/b/preview" name="B.jpg" />);
    expect(screen.getByRole("img").getAttribute("src")).toBe("/api/library/history/items/b/preview");
  });
  it("renderiza a prévia protegida da galeria canônica no carrinho", () => {
    render(<PurchasePreview path="/public-galleries/gallery-1/photos/photo-1/preview" name="Ensaio.jpg" />);
    expect(screen.getByRole("img").getAttribute("src")).toBe("/api/public-galleries/gallery-1/photos/photo-1/preview");
  });
  it.each([
    "/library/purchases/items/a/original",
    "/library/purchases/items/../preview",
    "/library/purchases/items/a/preview?redirect=outside",
    "/library/purchases/items/a/preview#fragment",
    "/api/api/library/purchases/items/a/preview",
    "https://outside.test/library/purchases/items/a/preview",
    "//outside.test/library/purchases/items/a/preview",
  ])("recusa alternativa comercial indevida %s", (path) => {
    expect(purchasePreviewUrl(path)).toBeNull();
  });
});
