import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { GalleryPresentation } from "./gallery-presentation";

const folders = [
  { id: "opening", name: "Abertura", photos: [
    { id: "landscape", name: "Horizontal.jpg", previewUrl: "/horizontal.jpg", width: 1600, height: 900 },
    { id: "portrait", name: "Vertical.jpg", previewUrl: "/vertical.jpg", width: 800, height: 1200 },
  ] },
  { id: "closing", name: "Encerramento", photos: [
    { id: "fallback", name: "Sem dimensões.jpg", previewUrl: "/fallback.jpg" },
  ] },
];

describe("apresentação editorial compartilhada", () => {
  it("mantém ordem DOM, proporção e todas as pastas no modo sequencial", () => {
    render(<GalleryPresentation galleryName="Evento" folders={folders} folderDisplayMode="sequential" />);
    expect(screen.getByRole("heading", { name: "Abertura" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Encerramento" })).toBeTruthy();
    expect(screen.queryByRole("navigation", { name: "Pastas da galeria" })).toBeNull();

    const images = screen.getAllByRole("img").filter((image) => image.getAttribute("alt")?.startsWith("Prévia protegida de"));
    expect(images.map((image) => image.getAttribute("alt"))).toEqual([
      "Prévia protegida de Horizontal.jpg",
      "Prévia protegida de Vertical.jpg",
      "Prévia protegida de Sem dimensões.jpg",
    ]);
    expect(images[0].closest("article")?.getAttribute("style")).toContain("--photo-aspect: 1600 / 900");
    expect(images[0].closest("article")?.getAttribute("style")).toContain("--photo-span: 2");
    expect(images[2].closest("article")?.getAttribute("style")).toContain("--photo-aspect: 4 / 3");
  });

  it("troca uma coleção por vez no modo individual", () => {
    render(<GalleryPresentation galleryName="Evento" folders={folders} folderDisplayMode="individual" />);
    expect(screen.getByRole("img", { name: "Prévia protegida de Horizontal.jpg" })).toBeTruthy();
    expect(screen.queryByRole("img", { name: "Prévia protegida de Sem dimensões.jpg" })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: /Encerramento/ }));
    expect(screen.getByRole("img", { name: "Prévia protegida de Sem dimensões.jpg" })).toBeTruthy();
    expect(screen.queryByRole("img", { name: "Prévia protegida de Horizontal.jpg" })).toBeNull();
  });

  it("separa ampliar dos marcadores da cliente e não cria ações no modo fotógrafo", () => {
    const onSelect = vi.fn();
    const { rerender } = render(<GalleryPresentation galleryName="Evento" folders={folders.slice(0, 1)} renderPhotoMarkers={(photo) => <button onClick={() => onSelect(photo.id)}>Selecionar {photo.name}</button>} />);
    fireEvent.click(screen.getByRole("button", { name: "Selecionar Horizontal.jpg" }));
    expect(onSelect).toHaveBeenCalledWith("landscape");
    fireEvent.click(screen.getByRole("button", { name: "Ampliar prévia protegida de Horizontal.jpg" }));
    expect(screen.getByRole("dialog", { name: "Prévia ampliada de Horizontal.jpg" })).toBeTruthy();
    fireEvent.keyDown(screen.getByRole("dialog"), { key: "ArrowRight" });
    expect(screen.getByRole("dialog", { name: "Prévia ampliada de Vertical.jpg" })).toBeTruthy();
    fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });
    expect(screen.queryByRole("dialog")).toBeNull();

    rerender(<GalleryPresentation galleryName="Evento" folders={folders.slice(0, 1)} modeLabel={<strong>Modo fotógrafo</strong>} />);
    expect(screen.queryByRole("button", { name: /Selecionar Horizontal/ })).toBeNull();
  });

  it("explica a limitação de screenshot e bloqueia cópia direta", () => {
    render(<GalleryPresentation galleryName="Evento" folders={folders.slice(0, 1)} />);
    fireEvent.keyUp(window, { key: "PrintScreen" });
    expect(screen.getByText(/não consegue impedir screenshots/)).toBeTruthy();
    fireEvent.contextMenu(screen.getByRole("button", { name: "Ampliar prévia protegida de Horizontal.jpg" }));
    expect(screen.getByText(/menu de contexto/)).toBeTruthy();
  });
});
