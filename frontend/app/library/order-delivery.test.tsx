import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { LibraryOrderCard, type Order } from "./purchase-card";

const order: Order = { id: "order-1", gallery_name: "Evento", parent_gallery_name: "Formatura", gallery_status_label: "Ativa", gallery_removed: false, confirmed_at: null, total_cents: 1200, commercial_state: "purchased", items: [], delivery_album_url: "https://photos.app.goo.gl/Synthetic" };

it("abre álbum seguro e suspende botão depois da correção financeira", () => {
  const { rerender } = render(<LibraryOrderCard order={order} />);
  const link = screen.getByRole("link", { name: "Fotos disponíveis" });
  expect(link.getAttribute("href")).toBe(order.delivery_album_url);
  expect(link.getAttribute("target")).toBe("_blank");
  expect(link.getAttribute("rel")).toBe("noopener noreferrer");
  expect(screen.getByRole("article").id).toBe("order-order-1");
  rerender(<LibraryOrderCard order={{ ...order, commercial_state: "payment_reported" }} />);
  expect(screen.queryByRole("link", { name: "Fotos disponíveis" })).toBeNull();
  expect(screen.getByRole("button", { name: "Fotos indisponíveis" })).toHaveProperty("disabled", true);
  rerender(<LibraryOrderCard order={{ ...order, gallery_removed: true, assets_removed: true }} />);
  expect(screen.getByRole("link", { name: "Fotos disponíveis" })).toBeTruthy();
});

it.each([null, "https://attacker.invalid/album", "javascript:alert(1)", "https://photos.app.goo.gl.attacker.invalid/album"])("sem link válido não oferece destino: %s", (url) => {
  render(<LibraryOrderCard order={{ ...order, delivery_album_url: url }} />);
  expect(screen.queryByRole("link")).toBeNull();
  expect(screen.getByRole("button", { name: "Fotos indisponíveis" })).toHaveProperty("disabled", true);
});
