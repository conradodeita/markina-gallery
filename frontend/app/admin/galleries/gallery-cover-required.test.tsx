import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));
vi.mock("./preview-adjustment-panel", () => ({ default: () => null }));
import GalleryEditor from "./sources/[sourceId]/edit/gallery-editor";

afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); push.mockReset(); });

function editor(status: string) {
  return {
    gallery: { id: "source-1", name: "Galeria", active: true, access_mode: "invite_only", cover_photo_id: status === "missing" ? null : "cover-1", cover_preview_url: null, folder_display_mode: "individual", cover_title_font: "system-sans", cover_title_color: "#FFFFFF", cover_title_size: 32, cover_title_position: "bottom-left" },
    cover_readiness: { status, message: `Estado da capa: ${status}` },
    steps: ["ajustes", "vendas", "detalhes", "imagens", "clientes"].map((id) => ({ id, label: id, available: true, status: "pending" })),
    counts: { folders: 0, registrations: 0, derived_galleries: 0 },
    capabilities: { sales_configuration: true, visual_customization: true, folder_management: true, client_links: true },
    actions: { can_upload: true, can_create_folder: true, can_complete: status === "ready" },
  };
}
function details(status: string) {
  return {
    available: true, capabilities: ["cover", "title"], cover_readiness: editor(status).cover_readiness,
    font_options: [{ token: "system-sans", label: "Sistema", category: "sans" }],
    settings: editor(status).gallery,
    cover_options: status === "missing" ? [] : [{ id: "cover-1", name: "Capa.jpg", status, preview_url: status === "ready" ? "/admin/photo-assets/cover-1/preview" : null }],
  };
}
function response(data: object, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(data), { status }));
}

it.each(["missing", "processing", "failed"])("Detalhes não salva capa %s, mas permite enviá-la", async (status) => {
  const fetcher = vi.fn((path: string) => response(path.endsWith("/editor") ? editor(status) : details(status)));
  vi.stubGlobal("fetch", fetcher);
  render(<GalleryEditor sourceId="source-1" step="detalhes" />);
  await screen.findByRole("heading", { name: "Detalhes e apresentação" });
  expect(screen.getByRole("button", { name: "Salvar e avançar →" })).toHaveProperty("disabled", true);
  expect(screen.getByText(`Estado da capa: ${status}`)).toBeTruthy();
  expect(screen.getByRole("button", { name: /imagem de capa/ })).toHaveProperty("disabled", false);
  fireEvent.submit(screen.getByLabelText("Tamanho do título").closest("form")!);
  expect(fetcher.mock.calls.every((call) => !String(call[0]).endsWith("/settings"))).toBe(true);
  expect(push).not.toHaveBeenCalled();
});

it("capa pronta permite salvar Detalhes e avançar", async () => {
  const fetcher = vi.fn((path: string) => response(path.endsWith("/editor") ? editor("ready") : details("ready")));
  vi.stubGlobal("fetch", fetcher);
  render(<GalleryEditor sourceId="source-1" step="detalhes" />);
  await screen.findByRole("heading", { name: "Detalhes e apresentação" });
  expect(screen.getByRole("button", { name: "Salvar e avançar →" })).toHaveProperty("disabled", false);
  fireEvent.click(screen.getByRole("button", { name: "Salvar e avançar →" }));
  await waitFor(() => expect(push).toHaveBeenCalledWith("/admin/galleries/sources/source-1/edit/imagens"));
  expect(fetcher).toHaveBeenCalledWith("/api/admin/parent-galleries/source-1/settings", expect.objectContaining({ method: "PATCH" }));
});

it.each(["missing", "processing", "failed", "ready", "error"])("Concluir revalida a API atual: %s", async (latest) => {
  let reads = 0;
  const fetcher = vi.fn((path: string) => {
    if (path.endsWith("/editor")) {
      reads++;
      return reads === 1 ? response(editor("ready")) : latest === "error" ? response({ detail: "Consulta indisponível" }, 503) : response(editor(latest));
    }
    return response({ clients: [], status: "active", secret_available: false });
  });
  vi.stubGlobal("fetch", fetcher);
  render(<GalleryEditor sourceId="source-1" step="clientes" />);
  fireEvent.click(await screen.findByRole("button", { name: "Concluir" }));
  await waitFor(() => expect(reads).toBe(2));
  if (latest === "ready") {
    await waitFor(() => expect(push).toHaveBeenCalledWith("/admin/galleries/sources/source-1"));
  } else {
    expect(await screen.findByText(latest === "error" ? "Consulta indisponível" : `Estado da capa: ${latest}`)).toBeTruthy();
    expect(push).not.toHaveBeenCalled();
  }
});
