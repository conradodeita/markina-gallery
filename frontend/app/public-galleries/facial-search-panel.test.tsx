import { readFileSync } from "node:fs";
import { join } from "node:path";

import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { FacialSearchResult } from "../facial-search-client";
import { FacialSearchPanel } from "./facial-search-panel";

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
  window.sessionStorage.clear();
  window.localStorage.clear();
});

function response(value: object, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(value), { status }));
}

const queued: FacialSearchResult = {
  id: "request-1",
  gallery_id: "gallery-1",
  status: "queued",
  progress: {
    index: { ready: 2, total: 2 },
    comparison: { done: 0, total: 2 },
  },
  reference_deleted: false,
  expires_at: "2099-01-01T00:00:00Z",
  poll_after_ms: 1000,
  estimate: { remaining_items: 2, seconds: null, confidence: "unavailable" },
};

function Harness() {
  const [result, setResult] = useState<FacialSearchResult | null>(queued);
  return (
    <>
      <FacialSearchPanel galleryId="gallery-1" result={result} onResult={setResult} />
      <output data-testid="search-state">{result?.status ?? "none"}</output>
    </>
  );
}

function EmptyHarness() {
  const [result, setResult] = useState<FacialSearchResult | null>(null);
  return (
    <>
      <FacialSearchPanel galleryId="gallery-1" result={result} onResult={setResult} />
      <output data-testid="search-state">{result?.status ?? "none"}</output>
    </>
  );
}

describe("polling da busca facial", () => {
  it("aumenta o intervalo sem progresso e para ao expirar", async () => {
    vi.useFakeTimers();
    let reads = 0;
    vi.stubGlobal("fetch", vi.fn((path: string) => {
      if (path.endsWith("/facial-search")) {
        return response({
          state: "consent_required",
          manual_selection_available: true,
          minor_search_available: false,
          consent_version: "consent-v1",
        });
      }
      if (path.endsWith("/latest")) return response({ detail: "not found" }, 404);
      reads += 1;
      if (reads === 1) return response(queued);
      return response({ ...queued, status: "expired", poll_after_ms: null });
    }));
    render(<Harness />);
    await act(async () => { await Promise.resolve(); });

    expect(screen.getByText(/2 itens restantes/)).toBeTruthy();
    await act(async () => { await vi.advanceTimersByTimeAsync(1000); });
    expect(reads).toBe(1);
    await act(async () => { await vi.advanceTimersByTimeAsync(1499); });
    expect(reads).toBe(1);
    await act(async () => { await vi.advanceTimersByTimeAsync(1); });
    expect(reads).toBe(2);
    expect(screen.getByTestId("search-state").textContent).toBe("expired");
    await act(async () => { await vi.advanceTimersByTimeAsync(30_000); });
    expect(reads).toBe(2);
  });

  it("encerra polling e remove retomada quando a consulta foi revogada", async () => {
    vi.useFakeTimers();
    window.sessionStorage.setItem("markina:facial-search:gallery-1", "request-1");
    let reads = 0;
    vi.stubGlobal("fetch", vi.fn((path: string) => {
      if (path.endsWith("/facial-search")) {
        return response({
          state: "consent_required",
          manual_selection_available: true,
          minor_search_available: false,
          consent_version: "consent-v1",
        });
      }
      reads += 1;
      return response({ detail: "Consulta facial indisponível." }, 404);
    }));
    render(<Harness />);
    await act(async () => { await Promise.resolve(); });
    await act(async () => { await vi.advanceTimersByTimeAsync(1000); });

    expect(screen.getByTestId("search-state").textContent).toBe("none");
    expect(window.sessionStorage.getItem("markina:facial-search:gallery-1")).toBeNull();
    await act(async () => { await vi.advanceTimersByTimeAsync(30_000); });
    expect(reads).toBeLessThanOrEqual(2);
  });
});

describe("jornada mobile e privacidade da referência", () => {
  it("oferece fototeca e câmera separadas, envia JPEG e persiste somente o identificador opaco", async () => {
    const created = { ...queued, id: "opaque-request-2" };
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/facial-search")) {
        return response({
          state: "consent_required",
          manual_selection_available: true,
          minor_search_available: false,
          consent_version: "consent-v1",
          legal_notice_version: "notice-v1",
          max_reference_bytes: 31_457_280,
          reference_retention_seconds: 900,
          candidate_retention_seconds: 86_400,
        });
      }
      if (path.endsWith("/latest")) return response({ detail: "not found" }, 404);
      if (path.endsWith("/facial-searches") && init?.method === "POST") return response(created, 202);
      return response({ detail: "not found" }, 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<EmptyHarness />);

    fireEvent.click(await screen.findByRole("button", { name: "Enviar foto para procurar" }));
    expect(screen.getByRole("heading", { name: "Busca facial nesta galeria" })).toBeTruthy();
    expect(screen.getByText(/Não há cadastro biométrico permanente/)).toBeTruthy();
    expect(screen.getByText(/no máximo, em 15 minutos/)).toBeTruthy();
    expect(screen.getByText(/Os resultados expiram em até 24 horas/)).toBeTruthy();
    expect(screen.getByText(/não confirmam identidade/)).toBeTruthy();
    expect(screen.getByText(/semelhante a foto de documento/)).toBeTruthy();
    expect(screen.getByText(/Não fotografe nem envie documento de identidade/)).toBeTruthy();
    const libraryInput = screen.getByLabelText("Escolher foto JPEG da galeria do celular") as HTMLInputElement;
    const cameraInput = screen.getByLabelText("Tirar foto JPEG com a câmera") as HTMLInputElement;
    expect(libraryInput.accept).toBe("image/jpeg");
    expect(libraryInput.getAttribute("capture")).toBeNull();
    expect(libraryInput.hidden).toBe(true);
    expect(cameraInput.accept).toBe("image/jpeg");
    expect(cameraInput.getAttribute("capture")).toBe("user");
    expect(cameraInput.hidden).toBe(true);
    const libraryClick = vi.spyOn(libraryInput, "click");
    const cameraClick = vi.spyOn(cameraInput, "click");
    fireEvent.click(screen.getByRole("button", { name: "Escolher foto do celular" }));
    fireEvent.click(screen.getByRole("button", { name: "Usar câmera" }));
    expect(libraryClick).toHaveBeenCalledOnce();
    expect(cameraClick).toHaveBeenCalledOnce();
    const submitButton = screen.getByRole("button", { name: "Autorizar e procurar fotos" }) as HTMLButtonElement;
    expect(submitButton.disabled).toBe(true);
    const reference = new File(["private-reference-bytes"], "referencia.jpg", { type: "image/jpeg" });
    Object.defineProperty(reference, "size", { value: 31_457_280 });
    fireEvent.change(libraryInput, { target: { files: [reference] } });
    expect(screen.getByText("Foto selecionada e pronta para envio.")).toBeTruthy();
    fireEvent.click(screen.getByRole("radio", { name: "Pessoa adulta" }));
    fireEvent.click(screen.getByRole("checkbox", { name: /Autorizo, de forma livre, informada e específica/ }));
    expect(submitButton.disabled).toBe(false);
    fireEvent.submit(submitButton.closest("form")!);

    await waitFor(() => expect(screen.getByTestId("search-state").textContent).toBe("queued"));
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/public-galleries/gallery-1/facial-searches",
      expect.objectContaining({ method: "POST", body: reference }),
    );
    expect(window.sessionStorage.length).toBe(1);
    expect(window.sessionStorage.getItem("markina:facial-search:gallery-1")).toBe("opaque-request-2");
    expect(window.localStorage.length).toBe(0);
    expect(JSON.stringify({ ...window.sessionStorage })).not.toContain("private-reference-bytes");
    expect(document.querySelector("img[src^='data:'], img[src^='blob:']")).toBeNull();
  });

  it("rejeita JPEG acima de 30 MB antes do upload e mantém o erro visível no diálogo", async () => {
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      void init;
      if (path.endsWith("/facial-search")) return response({
        state: "consent_required",
        manual_selection_available: true,
        minor_search_available: false,
        consent_version: "consent-v1",
        max_reference_bytes: 31_457_280,
      });
      return response({ detail: "not found" }, 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<EmptyHarness />);

    fireEvent.click(await screen.findByRole("button", { name: "Enviar foto para procurar" }));
    const reference = new File(["jpeg"], "grande.jpg", { type: "image/jpeg" });
    Object.defineProperty(reference, "size", { value: 31_457_281 });
    fireEvent.change(screen.getByLabelText("Escolher foto JPEG da galeria do celular"), {
      target: { files: [reference] },
    });

    expect(screen.getByRole("alert").textContent).toBe("Escolha uma foto JPEG de até 30 MB.");
    expect(screen.queryByText("Foto selecionada e pronta para envio.")).toBeNull();
    expect((screen.getByRole("button", { name: "Autorizar e procurar fotos" }) as HTMLButtonElement).disabled).toBe(true);
    expect(fetchMock.mock.calls.some(([, init]) => init?.method === "POST")).toBe(false);
  });

  it("exige representação e consentimento específicos antes de enviar referência infantil", async () => {
    const created = { ...queued, id: "minor-request" };
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/facial-search")) return response({
        state: "consent_required",
        manual_selection_available: true,
        minor_search_available: true,
        minor_representation_reference: "opaque-representation",
        consent_version: "consent-v2",
        legal_notice_version: "notice-v2",
      });
      if (path.endsWith("/latest")) return response({ detail: "not found" }, 404);
      if (path.endsWith("/facial-searches") && init?.method === "POST") return response(created, 202);
      return response({ detail: "not found" }, 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<EmptyHarness />);

    fireEvent.click(await screen.findByRole("button", { name: "Enviar foto para procurar" }));
    const reference = new File(["minor-reference"], "referencia.jpg", { type: "image/jpeg" });
    fireEvent.change(screen.getByLabelText("Escolher foto JPEG da galeria do celular"), { target: { files: [reference] } });
    fireEvent.click(screen.getByRole("radio", { name: "Criança ou adolescente" }));

    const submitButton = screen.getByRole("button", { name: "Autorizar e procurar fotos" }) as HTMLButtonElement;
    const guardian = screen.getByRole("checkbox", { name: /Declaro que sou pai, mãe ou responsável legal/ });
    const consent = screen.getByRole("checkbox", { name: /Autorizo, de forma livre, informada e específica/ });
    expect((guardian as HTMLInputElement).checked).toBe(false);
    expect((consent as HTMLInputElement).checked).toBe(false);
    expect(submitButton.disabled).toBe(true);

    fireEvent.click(consent);
    expect(submitButton.disabled).toBe(true);
    fireEvent.click(guardian);
    expect(submitButton.disabled).toBe(false);
    fireEvent.submit(submitButton.closest("form")!);

    await waitFor(() => expect(screen.getByTestId("search-state").textContent).toBe("queued"));
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/public-galleries/gallery-1/facial-searches",
      expect.objectContaining({
        method: "POST",
        body: reference,
        headers: expect.objectContaining({
          "x-facial-consent-version": "consent-v2",
          "x-facial-subject-declaration": "minor",
          "x-facial-representation-reference": "opaque-representation",
        }),
      }),
    );
  });

  it("mantém o diálogo rolável e alcançável na viewport mobile", () => {
    const css = readFileSync(join(process.cwd(), "app", "globals.css"), "utf8");
    const dialogRule = css.match(/\.facial-consent-dialog\s*\{[^}]+\}/)?.[0] ?? "";
    const mobileRule = Array.from(css.matchAll(/@media \(max-width:700px\)\s*\{[^\n]+/g))
      .find(([rule]) => rule.includes(".facial-consent-dialog"))?.[0] ?? "";
    expect(dialogRule).toMatch(/max-height:calc\(100dvh\s*-\s*32px\)/);
    expect(dialogRule).toMatch(/overflow-y:auto/);
    expect(dialogRule).toMatch(/overscroll-behavior:contain/);
    expect(mobileRule).toMatch(/width:calc\(100vw\s*-\s*16px\)/);
    expect(mobileRule).toMatch(/max-height:calc\(100dvh\s*-\s*8px\)/);
    expect(mobileRule).toMatch(/\.facial-consent-actions\s*\{[^}]*position:static/);
    expect(mobileRule).toMatch(/\.facial-consent-actions\s*\{[^}]*grid-template-columns:1fr/);
  });

  it.each([
    ["no_face", "Nenhum rosto foi detectado", "Tente uma foto frontal, bem iluminada e com o rosto inteiro."],
    ["multiple_faces", "A foto enviada contém mais de um rosto", "Recorte a imagem para manter somente a pessoa procurada."],
    ["low_quality", "A foto não tem qualidade suficiente", "Envie outra foto com mais nitidez e melhor iluminação."],
  ] as const)("mostra mensagem sanitizada para %s sem renderizar a referência", async (status, title, guidance) => {
    const terminal = { ...queued, status, reference_deleted: true, poll_after_ms: null };
    window.sessionStorage.setItem("markina:facial-search:gallery-1", terminal.id);
    vi.stubGlobal("fetch", vi.fn((path: string) => {
      if (path.endsWith("/facial-search")) return response({ state: "consent_required", manual_selection_available: true, minor_search_available: false, consent_version: "consent-v1" });
      return response(terminal);
    }));
    render(<Harness />);

    expect(await screen.findByText(title)).toBeTruthy();
    expect(screen.getByText(guidance)).toBeTruthy();
    expect(screen.getByText("Foto de referência eliminada")).toBeTruthy();
    expect(document.querySelector("img[src^='data:'], img[src^='blob:']")).toBeNull();
    expect(document.body.textContent).not.toContain("private-reference-bytes");
  });

  it("cancela no backend, encerra o progresso e remove a retomada local", async () => {
    window.sessionStorage.setItem("markina:facial-search:gallery-1", queued.id);
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/facial-search")) return response({ state: "consent_required", manual_selection_available: true, minor_search_available: false, consent_version: "consent-v1" });
      if (init?.method === "DELETE") return response({ ...queued, status: "cancelled", reference_deleted: true });
      return response(queued);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<Harness />);

    fireEvent.click(await screen.findByRole("button", { name: "Cancelar busca" }));
    await waitFor(() => expect(screen.getByTestId("search-state").textContent).toBe("none"));
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/public-galleries/gallery-1/facial-searches/request-1",
      expect.objectContaining({ method: "DELETE", credentials: "same-origin" }),
    );
    expect(window.sessionStorage.getItem("markina:facial-search:gallery-1")).toBeNull();
    expect(screen.queryByRole("progressbar", { name: "Progresso da busca facial" })).toBeNull();
  });
});
