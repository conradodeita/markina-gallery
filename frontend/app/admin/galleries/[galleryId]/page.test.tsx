import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

const uploadMocks = vi.hoisted(() => ({
  confirmDuplicateJpegs: vi.fn(),
  jpegFingerprint: vi.fn(),
  jpegFingerprintFromStorageKey: vi.fn(),
  jpegStorageKey: vi.fn(),
  uploadJpeg: vi.fn(),
}));

vi.mock("../../../upload-jpeg", () => uploadMocks);
vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement>) => (
    <a href={href} {...props}>{children}</a>
  ),
}));
vi.mock("next/navigation", () => ({
  useParams: () => ({ galleryId: "gallery-1" }),
  useRouter: () => ({ push: vi.fn() }),
}));
vi.mock("../../payments/payment-actions", () => ({ FinancialOrderShortcuts: () => null }));

import GalleryDetailPage from "./page";

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  Object.values(uploadMocks).forEach((mock) => mock.mockReset());
});

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("carteira durante upload em galeria privada", () => {
  it("mostra a reserva e o consumo confirmado pelo servidor para o arquivo enviado", async () => {
    let operationStatus = "reserved";
    let wallet = {
      mode: "finite",
      available_credits: 4,
      reserved_credits: 1,
      pending_operations: 1,
      as_of: "2026-11-01T12:00:00Z",
    };
    const uploadGate: { release?: () => void } = {};
    uploadMocks.confirmDuplicateJpegs.mockImplementation(async (files: File[]) => ({
      items: files,
      skippedCount: 0,
      duplicateIndexes: [],
      confirmed: false,
    }));
    uploadMocks.jpegFingerprint.mockResolvedValue("synthetic-fingerprint");
    uploadMocks.jpegFingerprintFromStorageKey.mockReturnValue(null);
    uploadMocks.jpegStorageKey.mockResolvedValue("synthetic-storage-key");
    uploadMocks.uploadJpeg.mockImplementation(() => new Promise<void>((resolve) => {
      uploadGate.release = resolve;
    }));

    const fetcher = vi.fn((input: string | URL | Request, init?: RequestInit) => {
      const path = String(input);
      if (path === "/api/admin/media-archive/recovery-pricing") {
        return Promise.resolve(jsonResponse({ recovery_fee_credits: 10, configured: true, owner_exempt: false }));
      }
      if (path === "/api/admin/derived-galleries/gallery-1") {
        return Promise.resolve(jsonResponse({
          id: "gallery-1", parent_gallery_id: "parent-1", name: "Galeria privada sintética",
          custom_message: "", selection_expires_at: null, frozen: false, blocked: false,
        }));
      }
      if (path === "/api/admin/derived-galleries/gallery-1/photos") return Promise.resolve(jsonResponse({ photos: [] }));
      if (path === "/api/admin/derived-galleries/gallery-1/folders") {
        return Promise.resolve(jsonResponse({ folders: [{ id: "folder-1", name: "Pasta privada", status: "released", photo_count: 0 }] }));
      }
      if (path === "/api/admin/derived-galleries/gallery-1/members") return Promise.resolve(jsonResponse({ members: [] }));
      if (path === "/api/admin/derived-galleries/gallery-1/facial-index") {
        return Promise.resolve(jsonResponse({ state: "completed", progress: { ready: 0, total: 0 }, queued: 0, processing: 0, failed: 0, coverage: { photos_with_faces: 0, total: 0, percent: 0, detected_faces: 0 } }));
      }
      if (path === "/api/admin/derived-galleries/gallery-1/upload-batches" && init?.method === "POST") {
        return Promise.resolve(jsonResponse({ id: "batch-1", status: "open", count: 1, assets: [] }, 201));
      }
      if (path === "/api/admin/derived-galleries/gallery-1/upload-batches") return Promise.resolve(jsonResponse({ batches: [] }));
      if (path === "/api/admin/photo-folders/folder-1/photos" && init?.method === "POST") {
        return Promise.resolve(jsonResponse({ id: "photo-1", storage_key: "synthetic-storage-key", status: "receiving" }, 201));
      }
      if (path === "/api/admin/photo-folders/folder-1/photos") return Promise.resolve(jsonResponse({ photos: [] }));
      if (path === "/api/admin/credits/wallet") return Promise.resolve(jsonResponse({ wallet, entries: [] }));
      if (path === "/api/admin/photo-assets/photo-1/credit-operation") {
        return Promise.resolve(jsonResponse({ wallet, operation: { status: operationStatus, quantity: 1 } }));
      }
      if (path === "/api/admin/photo-assets/photo-1/source") return Promise.resolve(jsonResponse({ status: "uploaded" }));
      if (path === "/api/admin/derived-galleries/gallery-1/upload-batches/batch-1/close") {
        return Promise.resolve(jsonResponse({ status: "closed" }));
      }
      throw new Error(`Rota inesperada: ${path}`);
    });
    vi.stubGlobal("fetch", fetcher);

    const user = userEvent.setup();
    render(<GalleryDetailPage />);
    const fileInput = await screen.findByLabelText("JPEGs do dispositivo");
    await user.selectOptions(screen.getByLabelText("Pasta"), "folder-1");
    await user.upload(fileInput, new File([new Uint8Array([1, 2, 3])], "foto-sintetica.jpg", { type: "image/jpeg" }));
    const uploadForm = fileInput.closest("form")!;
    fireEvent.submit(uploadForm);
    await waitFor(() => expect(uploadMocks.confirmDuplicateJpegs).toHaveBeenCalled());

    expect(await screen.findByText("1 crédito reservado enquanto o arquivo é recebido.")).toBeTruthy();
    expect(screen.getByText("Reservados").parentElement?.textContent).toContain("1");
    expect(uploadGate.release).toBeTypeOf("function");

    operationStatus = "consumed";
    wallet = {
      mode: "finite",
      available_credits: 3,
      reserved_credits: 0,
      pending_operations: 0,
      as_of: "2026-11-01T12:00:05Z",
    };
    uploadGate.release?.();

    expect(await screen.findByText("1 crédito consumido, confirmado pelo servidor.")).toBeTruthy();
    await waitFor(() => expect(screen.getByText("Créditos disponíveis").parentElement?.textContent).toContain("3"));
  });
});

it("renomeia pasta exclusiva existente da Galeria privada legada", async () => {
  let folderName = "Pasta privada";
  const fetcher = vi.fn((input: string | URL | Request, init?: RequestInit) => {
    const path = String(input);
    if (path === "/api/admin/media-archive/recovery-pricing") {
      return Promise.resolve(jsonResponse({ recovery_fee_credits: 10, configured: true, owner_exempt: false }));
    }
    if (path === "/api/admin/derived-galleries/gallery-1") return Promise.resolve(jsonResponse({
      id: "gallery-1", parent_gallery_id: "parent-1", name: "Galeria privada sintética",
      custom_message: "", selection_expires_at: null, frozen: false, blocked: false,
    }));
    if (path === "/api/admin/derived-galleries/gallery-1/photos") return Promise.resolve(jsonResponse({ photos: [] }));
    if (path === "/api/admin/derived-galleries/gallery-1/folders") return Promise.resolve(jsonResponse({ folders: [{
      id: "folder-1", name: folderName, status: "released", photo_count: 0,
    }] }));
    if (path === "/api/admin/derived-galleries/gallery-1/members") return Promise.resolve(jsonResponse({ members: [] }));
    if (path === "/api/admin/derived-galleries/gallery-1/facial-index") return Promise.resolve(jsonResponse({
      state: "completed", progress: { ready: 0, total: 0 }, queued: 0, processing: 0, failed: 0,
      coverage: { photos_with_faces: 0, total: 0, percent: 0, detected_faces: 0 },
    }));
    if (path === "/api/admin/derived-galleries/gallery-1/upload-batches") return Promise.resolve(jsonResponse({ batches: [] }));
    if (path === "/api/admin/photo-folders/folder-1" && init?.method === "PATCH") {
      folderName = JSON.parse(String(init.body)).name;
      return Promise.resolve(jsonResponse({ id: "folder-1", name: folderName }));
    }
    throw new Error(`Rota inesperada: ${path}`);
  });
  vi.stubGlobal("fetch", fetcher);
  vi.spyOn(window, "prompt").mockReturnValue("  Coleção privada atualizada  ");
  render(<GalleryDetailPage />);

  fireEvent.click(await screen.findByRole("button", { name: "Renomear pasta" }));

  expect(await screen.findByText("Nome da pasta atualizado.")).toBeTruthy();
  expect(fetcher).toHaveBeenCalledWith("/api/admin/photo-folders/folder-1", expect.objectContaining({
    method: "PATCH", body: JSON.stringify({ name: "Coleção privada atualizada" }),
  }));
  await waitFor(() => expect(screen.getAllByText("Coleção privada atualizada").length).toBeGreaterThan(0));
});
