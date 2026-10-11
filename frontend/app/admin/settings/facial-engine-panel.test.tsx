import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import FacialEnginePanel from "./facial-engine-panel";

const experiment = {
  enabled: false,
  mode: "shadow",
  model_id: "google/embeddinggemma-2",
  model_revision: "revision",
  worker_ready: true,
  worker_last_seen_at: null,
  indexed_faces: 0,
  jobs: { queued: 0, completed: 0 },
  serving_engine: "opencv-yunet-sface",
  backfill_enabled: false,
};

afterEach(() => vi.restoreAllMocks());

describe("seletor global do motor facial", () => {
  it("oculta controles para contas sem autorização global", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 403 })));
    const { container } = render(<FacialEnginePanel />);
    await waitFor(() => expect(container.firstChild).toBeNull());
  });

  it("alterna para Gemma e oferece retorno a SFace", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify(experiment), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ ...experiment, enabled: true }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<FacialEnginePanel />);

    expect(await screen.findByText(/O limiar de busca Gemma ainda não foi calibrado/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Usar Gemma" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/admin/facial-engine-experiment",
      expect.objectContaining({ method: "PATCH", body: JSON.stringify({ enabled: true }) }),
    ));
    expect(await screen.findByRole("button", { name: "Usar SFace" })).toBeTruthy();
  });

  it("impede ativação quando o worker ainda não está pronto", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ...experiment, worker_ready: false }), { status: 200 }),
    ));
    render(<FacialEnginePanel />);
    expect((await screen.findByRole("button", { name: "Usar Gemma" }) as HTMLButtonElement).disabled).toBe(true);
  });
});
