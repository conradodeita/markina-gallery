import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { FacialPolicyPanel } from "./facial-policy-panel";

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

const index = { state: "empty", progress: { ready: 0, total: 12 }, queued: 0, processing: 0, failed: 0, unindexed: 12, failures: [], pagination: { page: 1, page_size: 50, total: 0 } };

function response(value: object, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(value), { status }));
}

describe("painel facial administrativo", () => {
  it("explica a indexação automática sem oferecer ativação manual", async () => {
    const fetchMock = vi.fn(() => response(index));
    vi.stubGlobal("fetch", fetchMock);
    render(<FacialPolicyPanel galleryId="gallery-1" />);

    expect(screen.getByText("Consultando reconhecimento facial")).toBeTruthy();
    expect(await screen.findByText("Processamento automático")).toBeTruthy();
    expect(screen.getByText("Não é necessário preparar ou ativar esta galeria.", { exact: false })).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/admin/parent-galleries/gallery-1/facial-index",
      { credentials: "same-origin" },
    );
    expect(screen.queryByRole("button", { name: "Preparar política" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Ativar filtro" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Suspender" })).toBeNull();
  });

  it("mostra progresso automático enquanto há trabalho", async () => {
    const fetchMock = vi.fn(() => response({ ...index, state: "processing", progress: { ready: 7, total: 12 }, processing: 1 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<FacialPolicyPanel galleryId="gallery-1" />);

    expect(await screen.findByText("7 de 12 fotos prontas")).toBeTruthy();
    expect(screen.getByText("1 processando · 0 na fila · 0 falhas")).toBeTruthy();
  });

  it("expõe erro sanitizado e permite retentar somente falhas listadas", async () => {
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/retry") && init?.method === "POST") return response({ retried: 1 });
      return response({ ...index, state: "partial", failed: 1, failures: [{ job_id: "job-1", photo_id: "photo-123456789", category: "processing_unavailable" }] });
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<FacialPolicyPanel galleryId="gallery-1" />);

    expect(await screen.findByText("Falhas técnicas")).toBeTruthy();
    expect(screen.getByText(/processing_unavailable/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Tentar falhas novamente" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/admin/parent-galleries/gallery-1/facial-index/retry",
      expect.objectContaining({ method: "POST", body: JSON.stringify({ job_ids: ["job-1"] }) }),
    ));
  });

  it("mantém o painel fechado quando a leitura inicial falha", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("falha sintética")));
    render(<FacialPolicyPanel galleryId="gallery-1" />);
    expect(await screen.findByText("Reconhecimento facial indisponível")).toBeTruthy();
    expect(screen.getByText("falha sintética")).toBeTruthy();
  });
});
