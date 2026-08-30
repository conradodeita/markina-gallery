import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const push = vi.fn();
vi.mock("next/link", () => ({ default: ({ children, href, ...props }: { children: React.ReactNode; href: string }) => <a href={href} {...props}>{children}</a> }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }), useParams: () => ({ sourceId: "source-1" }) }));

import NewGalleryPage from "./new/page";
import GalleryEditor from "./sources/[sourceId]/edit/gallery-editor";
import SourceGalleryDetailPage from "./sources/[sourceId]/page";

afterEach(() => {
  vi.restoreAllMocks();
  push.mockReset();
});

const editor = {
  gallery: { id: "source-1", name: "Festa escolar", event_name: "Festa 2026", description: "", active: true, unlisted_link: "/?parent_gallery_id=source-1", cover_photo_id: null, cover_preview_url: null, folder_display_mode: "individual", cover_title_font: "sans-serif", cover_title_color: "#FFFFFF", cover_title_size: 32, cover_title_position: "bottom-left" },
  steps: [
    { id: "ajustes", label: "Ajustes", status: "complete", available: true },
    { id: "vendas", label: "Vendas", status: "unavailable", available: false },
    { id: "detalhes", label: "Detalhes", status: "pending", available: true },
    { id: "imagens", label: "Imagens", status: "pending", available: true },
    { id: "clientes", label: "Clientes", status: "pending", available: true },
  ],
  counts: { folders: 0, registrations: 0, derived_galleries: 0 },
  capabilities: { sales_configuration: false, visual_customization: true, folder_management: true, client_links: true },
  actions: { can_create_folder: true, can_upload: true },
};

function response(value: object, status = 200) {
  return Promise.resolve(new Response(status === 204 ? null : JSON.stringify(value), { status, headers: { "content-type": "application/json" } }));
}

describe("editor administrativo de galeria", () => {
  it("mantém a sequência de cinco etapas e cria pasta somente na galeria atual", async () => {
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (init?.method === "POST") return response({ id: "folder-1", status: "preparing", position: 0 }, 201);
      if (path.endsWith("/editor")) return response(editor);
      if (path.endsWith("/folders")) return response({ folders: [] });
      return response({ clients: [] });
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<GalleryEditor sourceId="source-1" step="imagens" />);
    expect(await screen.findByRole("heading", { name: "Imagens e pastas" })).toBeTruthy();
    expect(screen.getAllByRole("link", { name: /Ajustes|Vendas|Detalhes|Imagens|Clientes/ })).toHaveLength(5);
    expect(screen.getByRole("link", { name: /Imagens/ }).getAttribute("aria-current")).toBe("step");
    fireEvent.change(screen.getByLabelText("Nome da nova pasta"), { target: { value: "Apresentação" } });
    fireEvent.click(screen.getByRole("button", { name: "Criar pasta" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/admin/parent-galleries/source-1/folders",
      expect.objectContaining({ method: "POST" }),
    ));
    expect(fetchMock).not.toHaveBeenCalledWith("/api/admin/photo-folders", expect.anything());
  });

  it("oferece retorno e avanço dentro do contexto da mesma galeria", async () => {
    vi.stubGlobal("fetch", vi.fn((path: string) => path.endsWith("/editor") ? response(editor) : response({ folders: [], clients: [] })));
    render(<GalleryEditor sourceId="source-1" step="imagens" />);
    await screen.findByRole("heading", { name: "Imagens e pastas" });
    expect(screen.getByRole("link", { name: "← Voltar" }).getAttribute("href")).toBe("/admin/galleries/sources/source-1/edit/detalhes");
    expect(screen.getByRole("link", { name: "Avançar →" }).getAttribute("href")).toBe("/admin/galleries/sources/source-1/edit/clientes");
  });

  it("informa indisponibilidade quando o contrato do editor falha", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "Sessão expirada" }), { status: 401, headers: { "content-type": "application/json" } })));
    render(<GalleryEditor sourceId="source-1" step="ajustes" />);
    expect((await screen.findByRole("alert")).textContent).toContain("Galeria indisponível");
  });

  it("não oferece novo vínculo para responsável já associado à galeria", async () => {
    const linkedClient = { client_id: "client-1", name: "Ana Responsável", phone: "+5511999999999", registration_status: "active", derived_gallery_id: "derived-1" };
    vi.stubGlobal("fetch", vi.fn((path: string) => {
      if (path.endsWith("/editor")) return response(editor);
      if (path.includes("/parent-galleries/source-1/clients")) return response({ clients: [linkedClient] });
      return response({ clients: [{ id: "client-1", name: "Ana Responsável", phone: "+5511999999999" }] });
    }));
    render(<GalleryEditor sourceId="source-1" step="clientes" />);
    expect(await screen.findByText("Ana Responsável")).toBeTruthy();
    expect(screen.queryByRole("button", { name: /Vincular/ })).toBeNull();
  });

  it("separa vinculados, busca e novo cadastro em blocos responsivos", async () => {
    vi.stubGlobal("fetch", vi.fn((path: string) => {
      if (path.endsWith("/editor")) return response(editor);
      if (path.includes("/parent-galleries/source-1/clients")) return response({ clients: [] });
      return response({ clients: [{ id: "client-2", name: "Beatriz Responsável", phone: "+5511888888888" }] });
    }));
    render(<GalleryEditor sourceId="source-1" step="clientes" />);
    expect(await screen.findByRole("region", { name: "Responsáveis vinculados" })).toBeTruthy();
    expect(screen.getByRole("region", { name: "Vincular responsável" })).toBeTruthy();
    expect(screen.getByRole("region", { name: "Cadastrar e vincular" })).toBeTruthy();
    expect(screen.getByRole("button", { name: /Beatriz Responsável.*Vincular/ })).toBeTruthy();
  });

  it("mostra capacidade comercial indisponível sem inventar configuração", async () => {
    vi.stubGlobal("fetch", vi.fn((path: string) => path.endsWith("/editor") ? response(editor) : response({ available: false, reason: "Configuração comercial será liberada em uma mudança própria.", capabilities: [] })));
    render(<GalleryEditor sourceId="source-1" step="vendas" />);
    expect(await screen.findByText("Configuração ainda indisponível")).toBeTruthy();
    expect(screen.getByText(/não cria valores ou opções locais/i)).toBeTruthy();
    expect(screen.queryByLabelText(/preço/i)).toBeNull();
  });

  it("cria a galeria antes de navegar para o editor", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ id: "source-new" }), { status: 201 })));
    render(<NewGalleryPage />);
    fireEvent.change(screen.getByLabelText("Título da galeria"), { target: { value: "Nova galeria" } });
    fireEvent.click(screen.getByRole("button", { name: "Criar e continuar" }));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/admin/galleries/sources/source-new/edit/ajustes"));
  });

  it("abre a prévia protegida em modal e envia a escolha de capa ao backend", async () => {
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/editor")) return response(editor);
      if (path.endsWith("/folders")) return response({ folders: [{ id: "folder-1", name: "Apresentação", status: "preparing", position: 0, photo_count: 1, preview_url: "/admin/photo-assets/photo-1/watermarked-preview", released_at: null }] });
      if (path.endsWith("/clients")) return response({ clients: [] });
      if (path.endsWith("/photos")) return response({ photos: [{ id: "photo-1", name: "FOTO_001.jpg", preview_url: "/admin/photo-assets/photo-1/watermarked-preview", status: "completed", error: null, can_delete: true, is_cover: false }] });
      if (path.endsWith("/cover") && init?.method === "PUT") return response({ photo_id: "photo-1", preview_url: "/admin/photo-assets/photo-1/watermarked-preview" });
      return response({});
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<GalleryEditor sourceId="source-1" step="imagens" />);
    fireEvent.click(await screen.findByRole("button", { name: /Apresentação/ }));
    const expand = await screen.findByRole("button", { name: "Ampliar FOTO_001.jpg" });
    fireEvent.click(expand);
    const dialog = await screen.findByRole("dialog", { name: "Prévia ampliada de FOTO_001.jpg" });
    expect(dialog).toBeTruthy();
    fireEvent.keyDown(dialog, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    fireEvent.click(screen.getByRole("button", { name: "Usar como capa" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/admin/parent-galleries/source-1/cover",
      expect.objectContaining({ method: "PUT" }),
    ));
  });

  it("confirma a exclusão no contexto da pasta, sem criar dados no navegador", async () => {
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/editor")) return response(editor);
      if (path.endsWith("/folders")) return response({ folders: [{ id: "folder-1", name: "Apresentação", status: "preparing", position: 0, photo_count: 1, preview_url: null, released_at: null }] });
      if (path.endsWith("/clients")) return response({ clients: [] });
      if (path.endsWith("/photos") && !init?.method) return response({ photos: [{ id: "photo-1", name: "FOTO_001.jpg", preview_url: "/admin/photo-assets/photo-1/watermarked-preview", status: "completed", error: null, can_delete: true, is_cover: false }] });
      if (path.endsWith("/photos/photo-1") && init?.method === "DELETE") return response({}, 204);
      return response({});
    });
    vi.stubGlobal("fetch", fetchMock);
    vi.stubGlobal("confirm", vi.fn(() => true));
    render(<GalleryEditor sourceId="source-1" step="imagens" />);
    fireEvent.click(await screen.findByRole("button", { name: /Apresentação/ }));
    fireEvent.click(await screen.findByRole("button", { name: "Excluir" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/admin/photo-folders/folder-1/photos/photo-1",
      expect.objectContaining({ method: "DELETE" }),
    ));
  });

  it("mantém controles de apresentação próprios e direciona a proteção global", async () => {
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (init?.method === "PATCH") return response({});
      return path.endsWith("/editor") ? response(editor) : response({ available: true, capabilities: ["cover", "title", "folder_organization"] });
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<GalleryEditor sourceId="source-1" step="detalhes" />);
    expect(await screen.findByRole("heading", { name: "Detalhes e apresentação" })).toBeTruthy();
    expect(screen.getByLabelText("Tipografia do título")).toBeInstanceOf(HTMLSelectElement);
    expect(screen.queryByLabelText("Tipografia da marca-d’água")).toBeNull();
    expect(screen.getByText(/marca-d’água continua global/i)).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Tamanho do título"), { target: { value: "40" } });
    fireEvent.click(screen.getByRole("button", { name: "Salvar detalhes" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/admin/parent-galleries/source-1/settings",
      expect.objectContaining({ method: "PATCH", body: expect.stringContaining('"cover_title_size":40') }),
    ));
    expect(screen.getByRole("link", { name: /Ajustes/ }).getAttribute("href")).toBe("/admin/galleries/sources/source-1/edit/ajustes");
    expect(screen.getByRole("link", { name: /Clientes/ }).getAttribute("href")).toBe("/admin/galleries/sources/source-1/edit/clientes");
  });

  it("organiza a apresentação por galeria sem controles locais de proteção", async () => {
    vi.stubGlobal("fetch", vi.fn((path: string) => path.endsWith("/editor") ? response(editor) : response({ available: true, capabilities: ["cover", "title", "folder_organization"] })));
    render(<GalleryEditor sourceId="source-1" step="detalhes" />);
    await screen.findByRole("heading", { name: "Detalhes e apresentação" });
    expect(screen.getByRole("group", { name: "Capa e título" })).toBeTruthy();
    expect(screen.getByRole("group", { name: "Organização" })).toBeTruthy();
    expect(screen.queryByRole("group", { name: "Marca-d’água" })).toBeNull();
    expect(screen.getByText(/Prévia disponível após definir uma capa/)).toBeTruthy();
    expect(screen.queryByLabelText(/css/i)).toBeNull();
  });

  it("mantém Imagens focada em pastas e upload", async () => {
    vi.stubGlobal("fetch", vi.fn((path: string) => path.endsWith("/editor") ? response(editor) : path.endsWith("/folders") ? response({ folders: [] }) : response({ clients: [] })));
    render(<GalleryEditor sourceId="source-1" step="imagens" />);
    await screen.findByRole("heading", { name: "Imagens e pastas" });
    expect(screen.queryByRole("group", { name: "Capa e título" })).toBeNull();
    expect(screen.getByLabelText("Nome da nova pasta")).toBeTruthy();
  });

  it("renderiza o resumo com capa clicável, link e exclusão contextual", async () => {
    const fetchMock = vi.fn((path: string) => path.endsWith("/folders")
      ? response({ folders: [{ id: "folder-1", name: "Lote inicial", status: "preparing", photo_count: 2 }] })
      : response({ name: "Evento completo", event_name: "Festa 2026", active: true, unlisted_link: "https://local.test/?parent_gallery_id=source-1", cover_preview_url: "/admin/photo-assets/photo-1/watermarked-preview", counts: { folders: 1, photos: 2, clients: 0 }, clients: [] }));
    vi.stubGlobal("fetch", fetchMock);
    render(<SourceGalleryDetailPage />);
    expect(await screen.findByRole("heading", { name: "Evento completo" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Capa protegida da galeria" }).getAttribute("href")).toBe("/admin/galleries/sources/source-1/preview");
    expect(screen.getByDisplayValue("https://local.test/?parent_gallery_id=source-1")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Copiar link" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Excluir galeria vazia" })).toBeTruthy();
  });
});
