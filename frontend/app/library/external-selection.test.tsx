import { render, screen } from "@testing-library/react";
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
