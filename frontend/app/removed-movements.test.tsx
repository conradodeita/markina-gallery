import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { RemovedMovements } from "./removed-movements";
import { LibraryOrderCard } from "./library/purchase-card";

it("mostra seleção como referência textual sem criar compra nem imagem", () => {
  const { container } = render(<RemovedMovements admin items={[{
    id: "movement", kind: "selected", client_name: "Cliente teste", gallery_name: "Galeria 01",
    parent_gallery_name: "Evento", folder_name: "Pasta", filename: "IMG_1234.jpg",
    occurred_at: "2026-09-20T12:00:00Z", removed_at: "2026-09-21T12:00:00Z",
  }]} />);
  expect(screen.getByText("IMG_1234.jpg")).toBeTruthy();
  expect(screen.getByText(/Selecionada, sem compra/)).toBeTruthy();
  expect(container.querySelectorAll("img,a")).toHaveLength(0);
});

it("preserva nome e estado financeiro sem oferecer ampliar imagem removida", () => {
  render(<LibraryOrderCard order={{ id: "order", gallery_name: "Removida", parent_gallery_name: "Evento",
    gallery_removed: true, assets_removed: true, gallery_status_label: "Galeria removida",
    confirmed_at: null, commercial_state: "payment_reported", total_cents: 700,
    items: [{ photo_id: "photo", name: "IMG_5678.jpg", preview_url: null, delivery_url: null,
      delivery_reference_available: false }] }} />);
  expect(screen.getByText("Pagamento informado")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Ver fotos (1)" }));
  expect(screen.getByText("IMG_5678.jpg")).toBeTruthy();
  expect(screen.queryByRole("button", { name: /Ampliar/ })).toBeNull();
});
