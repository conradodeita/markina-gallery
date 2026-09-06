import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { FacialPolicyPanel } from "./facial-policy-panel";

afterEach(() => vi.restoreAllMocks());

const policy = {
  status: "disabled",
  ready_for_activation: false,
  missing_requirements: ["policy", "kill_switch"],
  legal_notice_version: "notice-v1",
  legal_basis_reference: "legitimate-purpose-v1",
  retention_policy_version: "retention-v1",
  minor_policy_version: "minor-disabled-v1",
  model_version: "model-v1",
  quality_version: "quality-v1",
  calibration_version: "calibration-v1",
  similarity_threshold_milli: 750,
  index_generation: 0,
  activated_at: null,
  suspended_at: null,
};

const index = { state: "empty", progress: { ready: 0, total: 12 }, queued: 0, processing: 0, failed: 0, unindexed: 12, failures: [], pagination: { page: 1, page_size: 50, total: 0 } };

function response(value: object, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(value), { status }));
}

describe("painel facial administrativo", () => {
  it("explica defaults desligados e prepara a política sem ativação implícita", async () => {
    let currentPolicy = policy;
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (init?.method === "PUT") {
        currentPolicy = { ...policy, status: "pending", missing_requirements: ["kill_switch"] };
        return response(currentPolicy);
      }
      if (path.endsWith("/facial-index")) return response(index);
      return response(currentPolicy);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<FacialPolicyPanel galleryId="gallery-1" />);

    expect(screen.getByText("Consultando reconhecimento facial")).toBeTruthy();
    expect(await screen.findByText("Ativação ainda bloqueada")).toBeTruthy();
    expect(screen.getByText("recurso desligado no ambiente")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Preparar política" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/admin/parent-galleries/gallery-1/facial-policy",
      expect.objectContaining({ method: "PUT" }),
    ));
    expect(screen.queryByRole("button", { name: "Ativar filtro" })).toBeTruthy();
  });

  it("mostra progresso e permite suspensão por teclado", async () => {
    const active = { ...policy, status: "active", ready_for_activation: true, missing_requirements: [] };
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/suspend") && init?.method === "POST") return response({ ...active, status: "suspended" });
      if (path.endsWith("/facial-index")) return response({ ...index, state: "processing", progress: { ready: 7, total: 12 }, processing: 1 });
      return response(active);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<FacialPolicyPanel galleryId="gallery-1" />);

    expect(await screen.findByText("7 de 12 fotos prontas")).toBeTruthy();
    const suspend = screen.getByRole("button", { name: "Suspender" });
    suspend.focus();
    fireEvent.keyDown(suspend, { key: "Enter" });
    fireEvent.click(suspend);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/admin/parent-galleries/gallery-1/facial-policy/suspend",
      expect.objectContaining({ method: "POST" }),
    ));
  });

  it("expõe erro sanitizado e permite retentar somente falhas listadas", async () => {
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/retry") && init?.method === "POST") return response({ retried: 1 });
      if (path.endsWith("/facial-index")) return response({ ...index, state: "partial", failed: 1, failures: [{ job_id: "job-1", photo_id: "photo-123456789", category: "processing_unavailable" }] });
      return response({ ...policy, status: "pending", missing_requirements: ["kill_switch"] });
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
    expect(screen.queryByRole("button", { name: "Ativar filtro" })).toBeNull();
  });
});
