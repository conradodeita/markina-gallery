import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { OrderPhotos } from "./order-photos";

const folders = [{ id: "folder", name: "Pasta", items: [1, 2].map((id) => ({
  id: String(id), photo_id: `photo-${id}`, name: `foto-${id}.jpg`, unit_price_cents: 700,
  thumbnail_url: `/admin/orders/order/items/${id}/preview?size=thumbnail`,
  preview_url: `/admin/orders/order/items/${id}/preview?size=preview`,
})) }];
beforeEach(() => {
  HTMLDialogElement.prototype.showModal = vi.fn(function (this: HTMLDialogElement) { this.open = true; });
  HTMLDialogElement.prototype.close = vi.fn(function (this: HTMLDialogElement) { this.open = false; });
});
afterEach(() => { vi.restoreAllMocks(); document.body.style.overflow = ""; });

it("usa miniaturas lazy e abre só uma ampliação em modal com foco/scroll restaurados", () => {
  render(<OrderPhotos folders={folders} />);
  const images = document.querySelectorAll("img");
  expect(images).toHaveLength(2);
  expect(images[0].getAttribute("loading")).toBe("lazy");
  expect(images[0].getAttribute("src")).toContain("size=thumbnail");
  const trigger = screen.getByRole("button", { name: "Ampliar foto-1.jpg" });
  trigger.focus(); fireEvent.click(trigger);
  const dialog = screen.getByRole("dialog", { name: "Fotografias do pedido" });
  expect(dialog.parentElement).toBe(document.body);
  expect(HTMLDialogElement.prototype.showModal).toHaveBeenCalledOnce();
  expect(document.activeElement).toBe(within(dialog).getByRole("button", { name: "Fechar fotografia" }));
  expect(document.body.style.overflow).toBe("hidden");
  fireEvent.keyDown(document.activeElement!, { key: "Tab", shiftKey: true });
  expect(document.activeElement).toBe(within(dialog).getByRole("button", { name: "Próxima" }));
  fireEvent.keyDown(document.activeElement!, { key: "Tab" });
  expect(document.activeElement).toBe(within(dialog).getByRole("button", { name: "Fechar fotografia" }));
  expect(dialog.querySelectorAll("img")).toHaveLength(1);
  expect(dialog.querySelector("img")?.getAttribute("src")).toContain("/items/1/preview?size=preview");
  fireEvent.keyDown(dialog, { key: "ArrowRight" });
  expect(dialog.querySelector("img")?.getAttribute("src")).toContain("/items/2/preview?size=preview");
  fireEvent.keyDown(dialog, { key: "ArrowLeft" });
  expect(dialog.querySelector("img")?.getAttribute("src")).toContain("/items/1/preview?size=preview");
  fireEvent(dialog, new Event("cancel", { bubbles: false, cancelable: true })); // Escape gera cancel.
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(document.activeElement).toBe(trigger);
  expect(document.body.style.overflow).toBe("");
});

it("fecha por botão/backdrop e mantém placeholder quando a imagem falha", () => {
  render(<OrderPhotos folders={folders} />);
  fireEvent.click(screen.getByRole("button", { name: "Ampliar foto-1.jpg" }));
  let dialog = screen.getByRole("dialog");
  fireEvent.error(dialog.querySelector("img")!);
  expect(within(dialog).getByText("Prévia indisponível.")).toBeTruthy();
  fireEvent.click(within(dialog).getByRole("button", { name: "Fechar fotografia" }));
  expect(screen.queryByRole("dialog")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Ampliar foto-2.jpg" }));
  dialog = screen.getByRole("dialog");
  fireEvent.click(within(dialog).getByText("foto-2.jpg"));
  expect(screen.getByRole("dialog")).toBeTruthy();
  fireEvent.click(dialog);
  expect(screen.queryByRole("dialog")).toBeNull();
});
