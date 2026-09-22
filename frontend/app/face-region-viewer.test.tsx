import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { FaceRegionViewer } from "./face-region-viewer";
import { GalleryPresentation } from "./gallery-presentation";
import type { FacialSearchResult, FacialSearchStatus } from "./facial-search-client";

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
  it("mostra progresso no stage, sem reaproveitar percentual na admissão e libera rostos ao terminar", async () => {
    response(1);
    const onRegion = vi.fn();
    const result = (status: FacialSearchStatus): FacialSearchResult => ({
      id: "search-1", gallery_id: "gallery", status, reference_deleted: true,
      expires_at: "2026-09-22T00:00:00Z", poll_after_ms: 2000,
      progress: { index: { ready: 2, total: 4 }, comparison: { done: 3, total: 4 } },
      estimate: { remaining_items: 1, seconds: null, confidence: "unavailable" },
    });
    const { rerender } = render(<FaceRegionViewer galleryId="gallery" photo={photo} onRegion={onRegion} busy searchResult={result("searching")} />);
    const face = await screen.findByRole("button", { name: "Procurar pessoa no rosto 1" });
    const bar = () => screen.getByRole("progressbar", { name: "Progresso da busca na foto ampliada" });
    expect(bar().hasAttribute("value")).toBe(false);
    expect(bar().closest(".face-region-stage")).toBeTruthy();
    expect(bar().closest(".face-region-image")).toBeNull();
    fireEvent.click(face);
    expect(onRegion).not.toHaveBeenCalled();
    for (const [status, value] of [["queued", null], ["waiting_index", "50"], ["searching", "75"], ["ranking", null]] as const) {
      rerender(<FaceRegionViewer galleryId="gallery" photo={photo} onRegion={onRegion} searchResult={result(status)} />);
      expect(bar().getAttribute("value")).toBe(value);
      expect((face as HTMLButtonElement).disabled).toBe(true);
    }
    for (const status of ["ready", "failed", "no_candidates", "cancelled", "expired"] as const) {
      rerender(<FaceRegionViewer galleryId="gallery" photo={photo} onRegion={onRegion} searchResult={result(status)} />);
      expect(screen.queryByRole("progressbar")).toBeNull();
      expect((face as HTMLButtonElement).disabled).toBe(false);
    }
  });

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
