import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import CreditHistory, { type HistoryPage } from "./credit-history";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

const asOf = "2026-11-01T21:00:00+00:00";
const folder = {
  id: "folder:one", type: "folder_upload", delta: -36, photo_count: 36,
  folder_id: "11111111-1111-4111-8111-111111111111", description: "Ensaio de teste",
  gallery_name: "Galeria sintética", source_reference: "11111111-1111-4111-8111-111111111111",
  created_at: "2026-11-01T20:00:00+00:00", first_at: "2026-10-31T18:00:00+00:00",
  last_at: "2026-11-01T20:00:00+00:00",
};
const purchase = {
  id: "purchase-one", type: "purchase", delta: 50, photo_count: 0, folder_id: null,
  description: "Compra de teste", source_reference: "purchase-reference", created_at: asOf,
};
const initialPage: HistoryPage = { items: [folder, purchase], has_more: false, as_of: asOf };
function json(body: unknown, status = 200) { return new Response(JSON.stringify(body), { status }); }

describe("histórico resumido por pasta", () => {
  it.each(["/api/admin/credits/history", "/api/admin/platform/credit-tenants/T/history"])("mostra somente resumos e metadados em %s", (endpoint) => {
    const fetcher = vi.fn();
    vi.stubGlobal("fetch", fetcher);
    render(<CreditHistory endpoint={endpoint} initialPage={initialPage} />);
    expect(screen.getByText("36 fotos cobradas")).toBeTruthy();
    expect(screen.getByText("-36")).toBeTruthy();
    expect(screen.getByText("Galeria sintética")).toBeTruthy();
    expect(screen.getByText(/Referência da pasta: 11111111/)).toBeTruthy();
    expect(screen.getByText(/Último envio:/)).toBeTruthy();
    expect(screen.getByText("Compra de teste")).toBeTruthy();
    expect(screen.queryByRole("button", { name: /detalhes/i })).toBeNull();
    expect(screen.queryByText(/Referência da operação:/)).toBeNull();
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("pagina resumos com o mesmo snapshot e conserva os totais da pasta", async () => {
    const fetcher = vi.fn<(input: string | URL | Request) => Promise<Response>>(() => Promise.resolve(json({
      items: [folder, { ...purchase, id: "purchase-two", description: "Outra compra" }],
      has_more: false, as_of: asOf,
    })));
    vi.stubGlobal("fetch", fetcher);
    render(<CreditHistory endpoint="/api/admin/credits/history" initialPage={{ ...initialPage, has_more: true }} />);
    fireEvent.click(screen.getByRole("button", { name: "Carregar mais movimentações" }));
    expect(await screen.findByText("Outra compra")).toBeTruthy();
    expect(screen.getAllByText("36 fotos cobradas")).toHaveLength(1);
    expect(screen.getByText("3 resumos exibidos")).toBeTruthy();
    const request = new URL(String(fetcher.mock.calls[0][0]), "http://localhost");
    expect(request.searchParams.get("offset")).toBe("2");
    expect(request.searchParams.get("as_of")).toBe(asOf);
  });

  it("representa 2.000 fotos como uma linha de pasta sem buscar operações individuais", () => {
    const fetcher = vi.fn();
    vi.stubGlobal("fetch", fetcher);
    render(<CreditHistory endpoint="/api/admin/credits/history" initialPage={{
      items: [{ ...folder, photo_count: 2000, delta: -2000 }], has_more: false, as_of: asOf,
    }} />);
    expect(screen.getByText("2.000 fotos cobradas")).toBeTruthy();
    expect(screen.getByText("-2.000")).toBeTruthy();
    expect(screen.getAllByRole("listitem")).toHaveLength(1);
    expect(screen.queryByRole("button")).toBeNull();
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("identifica a pasta recuperada no débito do arquivo frio", () => {
    vi.stubGlobal("fetch", vi.fn());
    render(<CreditHistory endpoint="/api/admin/credits/history" initialPage={{
      items: [{
        ...purchase, id: "recovery-one", type: "archive_recovery", delta: -3,
        description: "Recuperação de arquivo frio", related_folder_name: "Ensaio arquivado",
        folder_id: "folder-archive-one",
      }], has_more: false,
    }} />);
    expect(screen.getByText("Recuperação · Ensaio arquivado")).toBeTruthy();
    expect(screen.getByText("Recuperação de arquivo frio ·")).toBeTruthy();
    expect(screen.getByText("-3")).toBeTruthy();
  });

  it("ignora resposta atrasada ao trocar a carteira selecionada", async () => {
    let finish!: (value: Response) => void;
    vi.stubGlobal("fetch", vi.fn(() => new Promise<Response>((resolve) => { finish = resolve; })));
    const { rerender } = render(<CreditHistory endpoint="/api/admin/platform/credit-tenants/A/history" />);
    expect(screen.getByText("Consultando movimentações")).toBeTruthy();
    rerender(<CreditHistory endpoint="/api/admin/platform/credit-tenants/B/history" initialPage={{
      items: [{ ...purchase, description: "Conta B" }], has_more: false, as_of: asOf,
    }} />);
    await act(async () => { finish(json(initialPage)); });
    expect(screen.getByText("Conta B")).toBeTruthy();
    expect(screen.queryByText("36 fotos cobradas")).toBeNull();
  });

  it("distingue erro de leitura, lista vazia e origem antiga não identificável", async () => {
    vi.stubGlobal("fetch", vi.fn<(input: string | URL | Request) => Promise<Response>>(() => Promise.resolve(json({ detail: "error" }, 503))));
    const { rerender } = render(<CreditHistory endpoint="/api/admin/credits/history" />);
    expect(await screen.findByText("Histórico indisponível")).toBeTruthy();
    expect(screen.queryByText("Nenhuma movimentação")).toBeNull();
    rerender(<CreditHistory endpoint="/api/admin/credits/history" refreshKey="empty" initialPage={{ items: [], has_more: false }} />);
    expect(screen.getByText("Nenhuma movimentação")).toBeTruthy();
    rerender(<CreditHistory endpoint="/api/admin/credits/history" refreshKey="legacy" initialPage={{
      items: [1, 2].map((id) => ({ ...purchase, id: `legacy-${id}`, type: "upload_consumption", delta: -1,
        source_reference: `hidden-operation-${id}`, description: "JPEG de conteúdo armazenado", folder_unidentified: true })), has_more: false,
    }} />);
    expect(screen.getAllByText("Consumos anteriores preservados")).toHaveLength(1);
    expect(screen.queryByText(/hidden-operation/)).toBeNull();
    expect(screen.queryByText("JPEG de conteúdo armazenado")).toBeNull();
    expect(screen.queryByText("Nenhuma movimentação")).toBeNull();
    expect(screen.queryByRole("button", { name: "Ver detalhes" })).toBeNull();
  });

  it("conserva os resumos quando a próxima página falha e permite nova tentativa", async () => {
    const fetcher = vi.fn()
      .mockResolvedValueOnce(json({}, 503))
      .mockResolvedValueOnce(json({ items: [{ ...purchase, id: "another", description: "Outra compra" }], has_more: false, as_of: asOf }));
    vi.stubGlobal("fetch", fetcher);
    render(<CreditHistory endpoint="/api/admin/credits/history" initialPage={{ ...initialPage, has_more: true }} />);
    fireEvent.click(screen.getByRole("button", { name: "Carregar mais movimentações" }));
    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(screen.getByText("36 fotos cobradas")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Carregar mais movimentações" }));
    expect(await screen.findByText("Outra compra")).toBeTruthy();
    await waitFor(() => expect(screen.queryByRole("alert")).toBeNull());
  });
});
