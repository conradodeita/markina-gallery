import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { FaceRegionViewer } from "./face-region-viewer";
import { GalleryPresentation } from "./gallery-presentation";

const photo = { id: "photo", name: "Grupo", previewUrl: "/api/preview", width: 1000, height: 600 };
beforeEach(() => {
  vi.stubGlobal("ResizeObserver", class { observe() {} disconnect() {} });
  vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockReturnValue(1000);
  vi.spyOn(HTMLElement.prototype, "clientHeight", "get").mockReturnValue(600);
});
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

function response(count: number, threshold = 4) {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({ auto_threshold: threshold,
    regions: Array.from({ length: count }, (_, i) => ({ id: `region-${i}`, x: .1 + i*.1, y: .2, width: .05, height: .08 })) }) }));
}

describe("regiões persistidas", () => {
  it("mostra poucas regiões e envia somente o UUID escolhido", async () => {
    response(2);
    const onRegion = vi.fn();
    render(<FaceRegionViewer galleryId="gallery" photo={photo} onRegion={onRegion} />);
    const face = await screen.findByRole("button", { name: "Procurar pessoa no rosto 1" });
    fireEvent.click(face);
    expect(onRegion).toHaveBeenCalledWith("region-0");
    expect(fetch).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByLabelText("Aumentar zoom"));
    expect(screen.getByText("150%")).toBeTruthy();
  });
  it("abre grupos sem retângulos e exige ativação explícita", async () => {
    response(8);
    render(<FaceRegionViewer galleryId="gallery" photo={photo} onRegion={vi.fn()} />);
    const enable = await screen.findByRole("button", { name: "Encontrar uma pessoa nesta foto" });
    expect(screen.queryByRole("button", { name: /Procurar pessoa no rosto/ })).toBeNull();
    fireEvent.click(enable);
    expect(screen.getAllByRole("button", { name: /Procurar pessoa no rosto/ })).toHaveLength(8);
  });
  it("mantém a ação comercial fora da superfície fotográfica", async () => {
    render(<GalleryPresentation galleryName="Galeria" folders={[{ id:"folder", name:"Fotos", photos:[photo] }]}
      renderPhotoMarkers={() => <button>Selecionar foto</button>} />);
    fireEvent.click(screen.getByRole("button", { name:"Ampliar prévia protegida de Grupo" }));
    await waitFor(() => expect(document.querySelector(".gallery-presentation-dialog-selection button")).toBeTruthy());
    expect(document.querySelector(".gallery-presentation-dialog-media button")).toBeNull();
  });
});
