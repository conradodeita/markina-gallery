import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { FolderProcessingPanel } from "./folder-processing-panel";

const payload = {
  folder_id: "folder-1", revision: 1, preview_mode: "custom", facial_mode: "on",
  preview_strength: 50, preview_exposure_tenths: 0, effective_preview: { enabled: true },
  facial_available: true, facial_allowed: true, total_photos: 2,
  preview_counts: { queued: 0, processing: 0, ready: 1, failed: 0, cancelled: 0 },
  facial_counts: { queued: 0, processing: 0, completed: 1, failed: 0 }, comparison_photo_id: null,
  facial_progress: { state: "completed", total: 2, waiting_previews: 0, unindexed: 0, detected_faces: 3 },
};
const response = (body: object, status = 200) => Promise.resolve(new Response(JSON.stringify(body), { status }));
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

it.each([50, 75])("salva automaticamente parâmetros próprios com default %i, sem botões manuais", async (strength) => {
  const initial = { ...payload, preview_strength: strength };
  const fetcher = vi.fn((_path: string, init?: RequestInit) => response(init?.method === "PATCH"
    ? { ...initial, revision: 2, ...JSON.parse(String(init.body)) } : initial));
  vi.stubGlobal("fetch", fetcher);
  render(<FolderProcessingPanel folderId="folder-1" folderName="Retratos" />);
  const slider = await screen.findByLabelText("Intensidade do ajuste");
  expect(slider.getAttribute("value")).toBe(String(strength));
  expect(screen.queryByRole("button", { name: /Salvar|Processar/ })).toBeNull();
  expect(screen.queryByRole("combobox")).toBeNull();
  expect(fetcher.mock.calls.every(([, init]) => !init?.method)).toBe(true);
  fireEvent.change(slider, { target: { value: "60" } });
  fireEvent.change(screen.getByLabelText("Exposição do ajuste"), { target: { value: "3" } });
  await waitFor(() => expect(fetcher.mock.calls.filter(([, init]) => init?.method === "PATCH")).toHaveLength(1));
  expect(JSON.parse(String(fetcher.mock.calls.find(([, init]) => init?.method === "PATCH")?.[1]?.body))).toEqual({
    preview_mode: "custom", facial_mode: "on", preview_strength: 60, preview_exposure_tenths: 3,
  });
});

it("serializa alterações durante uma gravação sem perder os últimos valores", async () => {
  let finish: ((value: Response) => void) | undefined;
  let writes = 0;
  const fetcher = vi.fn((_path: string, init?: RequestInit) => {
    if (init?.method === "PATCH") {
      writes++;
      if (writes === 1) return new Promise<Response>((resolve) => { finish = resolve; });
      return response({ ...payload, revision: 3, ...JSON.parse(String(init.body)) });
    }
    return response(payload);
  });
  vi.stubGlobal("fetch", fetcher);
  render(<FolderProcessingPanel folderId="folder-1" folderName="Retratos" />);
  fireEvent.change(await screen.findByLabelText("Intensidade do ajuste"), { target: { value: "60" } });
  await waitFor(() => expect(finish).toBeDefined());
  fireEvent.change(screen.getByLabelText("Intensidade do ajuste"), { target: { value: "65" } });
  fireEvent.change(screen.getByLabelText("Exposição do ajuste"), { target: { value: "4" } });
  expect(writes).toBe(1);
  await act(async () => finish?.(await response({ ...payload, revision: 2, preview_strength: 60 })));
  await waitFor(() => expect(writes).toBe(2));
  expect(screen.getByLabelText("Intensidade do ajuste").getAttribute("value")).toBe("65");
  expect(screen.getByLabelText("Exposição do ajuste").getAttribute("value")).toBe("4");
});

it("aplica a última alteração à pasta anterior ao trocar e mantém a nova independente", async () => {
  const fetcher = vi.fn((path: string, init?: RequestInit) => response({ ...payload,
    folder_id: path.includes("folder-2") ? "folder-2" : "folder-1",
    preview_strength: path.includes("folder-2") ? 75 : init?.method === "PATCH" ? 60 : 50,
  }));
  vi.stubGlobal("fetch", fetcher);
  const view = render(<FolderProcessingPanel key="folder-1" folderId="folder-1" folderName="Pública" />);
  fireEvent.change(await screen.findByLabelText("Intensidade do ajuste"), { target: { value: "60" } });
  view.rerender(<FolderProcessingPanel key="folder-2" folderId="folder-2" folderName="Privada" />);
  await waitFor(() => expect(screen.getByLabelText("Intensidade do ajuste").getAttribute("value")).toBe("75"));
  const patches = fetcher.mock.calls.filter(([, init]) => init?.method === "PATCH");
  expect(patches).toHaveLength(1);
  expect(patches[0][0]).toBe("/api/admin/photo-folders/folder-1/processing");
});

it("mantém os dados durante falha de gravação e permite tentar novamente", async () => {
  let fail = true;
  vi.stubGlobal("fetch", vi.fn((_path: string, init?: RequestInit) => init?.method === "PATCH" && fail
    ? response({ detail: "Falha temporária" }, 503) : response(payload)));
  render(<FolderProcessingPanel folderId="folder-1" folderName="Retratos" />);
  fireEvent.change(await screen.findByLabelText("Intensidade do ajuste"), { target: { value: "60" } });
  await screen.findByText("Falha temporária");
  expect(screen.getByLabelText("Intensidade do ajuste").getAttribute("value")).toBe("50");
  fail = false;
  fireEvent.change(screen.getByLabelText("Exposição do ajuste"), { target: { value: "2" } });
  await screen.findByText(/Ajuste atualizado/);
});

it("retenta reconhecimento paginado somente na pasta, mantendo o gate", async () => {
  const fetcher = vi.fn((path: string, init?: RequestInit) => response(init?.method === "POST"
    ? { next_cursor: path.includes("after=") ? null : "next-photo" }
    : { ...payload, facial_counts: { ...payload.facial_counts, failed: 1 } }));
  vi.stubGlobal("fetch", fetcher);
  render(<FolderProcessingPanel folderId="folder-1" folderName="Retratos" />);
  fireEvent.click(await screen.findByRole("button", { name: "Refazer reconhecimento" }));
  await screen.findByText(/Retentativa do reconhecimento iniciada/);
  expect(fetcher.mock.calls.filter(([, init]) => init?.method === "POST").map(([path]) => path)).toEqual([
    "/api/admin/photo-folders/folder-1/processing/facial/reprocess",
    "/api/admin/photo-folders/folder-1/processing/facial/reprocess?after=next-photo",
  ]);
});

it("amplia ambas as versões protegidas e devolve o foco", async () => {
  vi.stubGlobal("fetch", vi.fn(() => response({ ...payload, comparison_photo_id: "photo-1" })));
  render(<FolderProcessingPanel folderId="folder-1" folderName="Retratos" />);
  fireEvent.click(await screen.findByText("Comparar prévias"));
  fireEvent.change(screen.getByLabelText("Comparar foto"), { target: { value: "photo-1" } });
  for (const [label, path] of [["convencional", "before"], ["ajustada", "after"]]) {
    const trigger = screen.getByRole("button", { name: `Ampliar versão ${label}` });
    fireEvent.click(trigger);
    expect(screen.getByRole("dialog").querySelector("img")?.getAttribute("src")).toBe(`/api/admin/preview-adjustment/photos/photo-1/${path}`);
    fireEvent.click(screen.getByRole("button", { name: "Fechar" }));
    expect(document.activeElement).toBe(trigger);
  }
});

it("recupera falha de leitura sem enfileirar trabalho", async () => {
  const fetcher = vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({ detail: "Falha temporária" }), { status: 503 }))
    .mockImplementation(() => response(payload));
  vi.stubGlobal("fetch", fetcher);
  render(<FolderProcessingPanel folderId="folder-1" folderName="Retratos" />);
  await screen.findByText("Falha temporária");
  fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
  await screen.findByLabelText("Intensidade do ajuste");
  expect(fetcher.mock.calls.every(([, init]) => !init?.method)).toBe(true);
});
