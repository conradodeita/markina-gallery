import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { PhotographerTermsHistory } from "./photographer-terms-history";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe("histórico owner-only dos aceites dos Termos", () => {
  it("mostra protocolo integral, identidade, hash e instante do tenant consultado", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ items: [{
      id: "acceptance-1", version: "v2", text: "Texto integral do aceite", sha256: "a".repeat(64),
      provider_identity: "Provedor sintético", photographer_identity: "Fotógrafa sintética",
      accepted_at: "2026-11-07T12:00:00Z", environment: "production",
    }] })));
    vi.stubGlobal("fetch", fetchMock);
    render(<PhotographerTermsHistory tenantId="tenant-synthetic" />);
    fireEvent.click(await screen.findByText(/v2 ·/));
    expect(await screen.findByText("Texto integral do aceite")).toBeTruthy();
    expect(screen.getByText(/Provedor: Provedor sintético/)).toBeTruthy();
    expect(screen.getByText((_, element) => element?.tagName === "P" && element.textContent?.includes("Fotógrafa sintética") === true)).toBeTruthy();
    expect(screen.getByText(new RegExp("a".repeat(64)))).toBeTruthy();
    expect(fetchMock.mock.calls[0][0]).toBe("/api/admin/platform/terms/acceptances/tenant-synthetic");
  });
});
