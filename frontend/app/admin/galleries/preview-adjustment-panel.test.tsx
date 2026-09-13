import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import PreviewAdjustmentPanel from "./preview-adjustment-panel";

afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

it("permite desligar e informa retorno às prévias convencionais", async () => {
  const fetchMock = vi.fn(async (url: string, init?: RequestInit) => new Response(JSON.stringify(
    url.endsWith("/configuration") ? {
      enabled: init?.method === "PATCH" ? false : true, strength: 50, generation: 2, exposure_tenths: 0,
    } : { counts: {}, photos: [], next_cursor: null },
  ), { status: 200 }));
  vi.stubGlobal("fetch", fetchMock);
  render(<PreviewAdjustmentPanel galleryId="gallery" />);
  const checkbox = await screen.findByLabelText("Melhorar prévias automaticamente");
  expect((checkbox as HTMLInputElement).checked).toBe(true);
  fireEvent.click(checkbox);
  fireEvent.click(screen.getByRole("button", { name: "Salvar ajuste de prévias" }));
  await screen.findByText("Desligado. As próximas visualizações usam as prévias convencionais.");
  expect(fetchMock).toHaveBeenCalledWith("/api/admin/preview-adjustment/galleries/gallery/configuration", expect.objectContaining({
    method: "PATCH", body: JSON.stringify({ enabled: false, strength: 50, exposure_tenths: 0 }),
  }));
});

it("agenda páginas sem duplicar a operação e oferece antes/depois", async () => {
  let enqueues = 0;
  const fetchMock = vi.fn(async (url: string) => {
    let payload: unknown = { enabled: true, strength: 50, generation: 3, exposure_tenths: 0 };
    if (url.includes("/enqueue")) {
      enqueues += 1;
      payload = { queued: 1, next_cursor: enqueues === 1 ? "cursor" : null };
    } else if (!url.endsWith("/configuration")) {
      payload = { counts: { ready: 1, queued: 0, processing: 0, failed: 0, cancelled: 0 },
        photos: [{ id: "photo", filename: "foto.jpg" }], next_cursor: null };
    }
    return new Response(JSON.stringify(payload), { status: 200 });
  });
  vi.stubGlobal("fetch", fetchMock);
  render(<PreviewAdjustmentPanel galleryId="gallery" />);
  await screen.findByLabelText("Melhorar prévias automaticamente");
  fireEvent.click(screen.getByRole("button", { name: "Processar galeria / tentar falhas" }));
  await waitFor(() => expect(enqueues).toBe(2));
  await screen.findByRole("option", { name: "foto.jpg" });
  fireEvent.change(screen.getByLabelText("Comparar foto"), { target: { value: "photo" } });
  expect(screen.getByAltText("Prévia convencional protegida").getAttribute("src")).toContain("/photo/before");
  expect(screen.getByAltText("Prévia ajustada protegida").getAttribute("src")).toContain("/photo/after");
});

it("mostra erro de configuração sem permitir ativação falsa", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => new Response(null, { status: 503 })));
  render(<PreviewAdjustmentPanel galleryId="gallery" />);
  await screen.findByText("Ajuste de prévias indisponível.");
  expect(screen.queryByRole("button", { name: "Salvar ajuste de prévias" })).toBeNull();
});

it("exige salvar a exposição da galeria antes de reprocessar", async () => {
  const fetchMock = vi.fn(async (url: string, init?: RequestInit) => new Response(JSON.stringify(
    url.endsWith("/configuration") ? {
      enabled: true, strength: 50, generation: 3, exposure_tenths: init?.method === "PATCH" ? 12 : 0,
    } : { counts: {}, photos: [], next_cursor: null },
  ), { status: 200 }));
  vi.stubGlobal("fetch", fetchMock);
  render(<PreviewAdjustmentPanel galleryId="only-this-gallery" />);
  const slider = await screen.findByLabelText(/Exposição:/);
  fireEvent.change(slider, { target: { value: "12" } });
  const process = screen.getByRole("button", { name: "Processar galeria / tentar falhas" }) as HTMLButtonElement;
  expect(process.disabled).toBe(true);
  fireEvent.click(screen.getByRole("button", { name: "Salvar ajuste de prévias" }));
  await waitFor(() => expect(process.disabled).toBe(false));
  expect(fetchMock).toHaveBeenCalledWith("/api/admin/preview-adjustment/galleries/only-this-gallery/configuration", expect.objectContaining({
    method: "PATCH", body: JSON.stringify({ enabled: true, strength: 50, exposure_tenths: 12 }),
  }));
  expect(screen.queryByLabelText("Galeria para avaliação")).toBeNull();
});
