import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { FolderProcessingPanel } from "./folder-processing-panel";

const payload = {
  folder_id: "folder-1", folder_name: "Pasta restrita", preview_mode: "inherit", facial_mode: "inherit",
  preview_strength: 50, preview_exposure_tenths: 0,
  effective_preview: { mode: "inherit", enabled: true, strength: 40, exposure_tenths: 3 },
  facial_available: true, facial_allowed: true, total_photos: 2,
  preview_counts: { queued: 0, processing: 0, ready: 1, failed: 0, cancelled: 0 },
  facial_counts: { queued: 0, processing: 0, completed: 1, failed: 0 }, comparison_photo_id: null,
};
const response = (body: object) => Promise.resolve(new Response(JSON.stringify(body), { status: 200 }));
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

it("carrega apenas ao abrir, mostra escopo compartilhado e salva exposição própria sem somar", async () => {
  const fetcher = vi.fn((path: string, init?: RequestInit) =>
    response(init?.method === "PATCH"
      ? { ...payload, ...JSON.parse(String(init.body)), effective_preview: {
        mode: "custom", enabled: true, strength: 60, exposure_tenths: 5,
      } } : payload));
  vi.stubGlobal("fetch", fetcher);
  render(<FolderProcessingPanel folderId="folder-1" folderName="Pasta restrita" shared />);
  expect(fetcher).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: /Processamento da pasta/ }));
  expect(await screen.findByText(/todas as clientes atribuídas/)).toBeTruthy();
  fireEvent.change(screen.getAllByLabelText("Comportamento da pasta")[1], { target: { value: "custom" } });
  fireEvent.change(screen.getByLabelText(/Intensidade/), { target: { value: "60" } });
  fireEvent.change(screen.getByLabelText(/Exposição/), { target: { value: "5" } });
  fireEvent.click(screen.getByRole("button", { name: "Salvar configuração" }));
  await waitFor(() => expect(fetcher.mock.calls.some(([, init]) => init?.method === "PATCH")).toBe(true));
  const patch = fetcher.mock.calls.find(([, init]) => init?.method === "PATCH");
  expect(JSON.parse(String(patch?.[1]?.body)).preview_exposure_tenths).toBe(5);
  expect(screen.getByText(/Configuração salva/)).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: /Processamento da pasta/ }));
  expect(screen.queryByText(/todas as clientes atribuídas/)).toBeNull();
});

it("encerra a consulta e o polling ao recolher, sem gravar configuração", async () => {
  const fetcher = vi.fn((_path: string, _init?: RequestInit) => response({ ...payload,
    preview_counts: { ...payload.preview_counts, queued: 1 } }));
  const clear = vi.spyOn(window, "clearInterval");
  vi.stubGlobal("fetch", fetcher);
  render(<FolderProcessingPanel folderId="folder-1" folderName="Pasta restrita" />);
  const toggle = screen.getByRole("button", { name: /Processamento da pasta/ });
  fireEvent.click(toggle);
  await screen.findByText(/1 pronta/);
  await waitFor(() => expect(screen.getByRole("button", { name: /Processamento da pasta/ }).getAttribute("aria-expanded")).toBe("true"));
  const signal = fetcher.mock.calls[0][1]?.signal;
  fireEvent.click(toggle);
  expect(signal?.aborted).toBe(true);
  expect(clear).toHaveBeenCalled();
  expect(fetcher.mock.calls.every(([, init]) => !init || !init.method || init.method === "GET")).toBe(true);
});

it("mostra erro de leitura e permite tentar novamente", async () => {
  const fetcher = vi.fn()
    .mockResolvedValueOnce(new Response(JSON.stringify({ detail: "Falha temporária" }), { status: 503 }))
    .mockImplementation(() => response(payload));
  vi.stubGlobal("fetch", fetcher);
  render(<FolderProcessingPanel folderId="folder-1" folderName="Pasta restrita" />);
  fireEvent.click(screen.getByRole("button", { name: /Processamento da pasta/ }));
  expect(await screen.findByRole("alert")).toHaveProperty("textContent", "Falha temporária");
  fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
  expect(await screen.findByRole("button", { name: "Salvar configuração" })).toBeTruthy();
  expect(fetcher).toHaveBeenCalledTimes(2);
});

it("mantém IDs distintos e lê a mesma configuração em duas vistas da pasta", async () => {
  const fetcher = vi.fn((_path: string) => response(payload));
  vi.stubGlobal("fetch", fetcher);
  render(<><FolderProcessingPanel folderId="folder-1" folderName="Pasta restrita" />
    <FolderProcessingPanel folderId="folder-1" folderName="Pasta restrita" shared /></>);
  expect(fetcher).not.toHaveBeenCalled();
  const toggles = screen.getAllByRole("button", { name: /Processamento da pasta/ });
  toggles[0].focus();
  await userEvent.keyboard("{Enter}");
  fireEvent.click(toggles[1]);
  await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2));
  expect(fetcher.mock.calls.every(([path]) => String(path).endsWith("folder-1/processing"))).toBe(true);
  const selects = screen.getAllByRole("combobox");
  expect(selects).toHaveLength(4);
  expect(new Set(selects.map((select) => select.id)).size).toBe(4);
  expect(screen.getByText(/todas as clientes atribuídas/)).toBeTruthy();
});
