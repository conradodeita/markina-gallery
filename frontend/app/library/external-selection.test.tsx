import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { LibraryOrderCard } from "./purchase-card";

it("mostra seleção finalizada e entrega sem valores ou estado de pagamento", () => {
  render(<LibraryOrderCard order={{ id: "external", gallery_name: "Evento", parent_gallery_name: "Evento",
    gallery_status_label: "Ativa", gallery_removed: false, confirmed_at: null,
    commercial_state: "selection_finalized", payment_required: false, total_cents: null,
    delivery_album_url: "https://photos.app.goo.gl/external", items: [] }} />);
  expect(screen.getByText("Seleção finalizada")).toBeTruthy();
  expect(screen.queryByText(/R\$/)).toBeNull();
  expect(screen.queryByText(/Pagamento confirmado|Aguardando pagamento/)).toBeNull();
  expect(screen.getByRole("link", { name: "Fotos disponíveis" }).getAttribute("href")).toBe("https://photos.app.goo.gl/external");
});

it("abre a prévia por item da própria seleção finalizada sem cobrança", () => {
  render(<LibraryOrderCard order={{ id: "finalized", gallery_name: "Ensaio A", parent_gallery_name: "Ensaio A",
    gallery_status_label: "Ativa", gallery_removed: false, confirmed_at: null,
    commercial_state: "selection_finalized", payment_required: false, total_cents: null,
    items: [{ photo_id: "photo-a", name: "A.jpg", preview_url: "/library/purchases/items/item-a/preview",
      delivery_url: null, delivery_reference_available: false }] }} />);
  fireEvent.click(screen.getByRole("button", { name: "Ver fotos (1)" }));
  expect(screen.getByRole("img", { name: "Prévia protegida de A.jpg" }).getAttribute("src"))
    .toBe("/api/library/purchases/items/item-a/preview");
  expect(screen.getByText("Seleção finalizada")).toBeTruthy();
  expect(screen.queryByText(/R\$/)).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Ampliar prévia protegida de A.jpg" }));
  expect(screen.getByRole("img", { name: "Prévia protegida ampliada de A.jpg" }).getAttribute("src"))
    .toBe("/api/library/purchases/items/item-a/preview");
});
