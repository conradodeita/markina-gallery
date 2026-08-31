import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
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
  gallery: { id: "source-1", name: "Festa escolar", event_name: "Festa 2026", description: "", active: true, access_mode: "invite_only", unlisted_link: null, public_link: { status: "active", capability_id: "capability-1", expires_at: null, secret_available: false }, cover_photo_id: null, cover_preview_url: null, folder_display_mode: "individual", cover_title_font: "sans-serif", cover_title_color: "#FFFFFF", cover_title_size: 32, cover_title_position: "bottom-left" },
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

  it("salva o modo de acesso explicitamente sem inferência do frontend", async () => {
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (init?.method === "PATCH") return response({});
      return path.endsWith("/editor") ? response(editor) : response({});
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<GalleryEditor sourceId="source-1" step="ajustes" />);
    const accessMode = await screen.findByRole("combobox", { name: /Modo de acesso/ });
    fireEvent.change(accessMode, { target: { value: "standard" } });
    fireEvent.click(screen.getByRole("button", { name: "Salvar ajustes" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/admin/parent-galleries/source-1/settings",
      expect.objectContaining({ method: "PATCH", body: expect.stringContaining('"access_mode":"standard"') }),
    ));
    expect(screen.getByRole("option", { name: /Coletivo protegido/ })).toBeTruthy();
  });

  it("informa indisponibilidade quando o contrato do editor falha", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "Sessão expirada" }), { status: 401, headers: { "content-type": "application/json" } })));
    render(<GalleryEditor sourceId="source-1" step="ajustes" />);
    expect((await screen.findByRole("alert")).textContent).toContain("Galeria indisponível");
  });

  it("não oferece novo vínculo para cliente já associada à galeria", async () => {
    const linkedClient = { client_id: "client-1", name: "Ana Cliente", phone: "+5511999999999", registration_status: "active", derived_gallery_id: "derived-1", available_count: 1, selected_count: 0, purchased_count: 0, gallery_status: "no_selection" };
    vi.stubGlobal("fetch", vi.fn((path: string) => {
      if (path.endsWith("/editor")) return response(editor);
      if (path.includes("/parent-galleries/source-1/clients")) return response({ clients: [linkedClient] });
      return response({ clients: [{ id: "client-1", name: "Ana Cliente", phone: "+5511999999999" }] });
    }));
    render(<GalleryEditor sourceId="source-1" step="clientes" />);
    expect(await screen.findByText("Ana Cliente")).toBeTruthy();
    expect(screen.queryByRole("button", { name: /Vincular/ })).toBeNull();
    const card = screen.getByRole("article", { name: "Cliente Ana Cliente" });
    expect(within(card).getByText("Sem seleção")).toBeTruthy();
    expect(within(card).getByText("Disponíveis")).toBeTruthy();
    expect(within(card).getByText("Selecionadas")).toBeTruthy();
    expect(within(card).getByText("Compradas")).toBeTruthy();
    const galleryLink = within(card).getByRole("link", { name: "Ana Cliente" });
    galleryLink.focus();
    expect(document.activeElement).toBe(galleryLink);
  });

  it("apresenta estados por texto, contraste semântico e cartões responsivos", async () => {
    const statuses = [
      ["pending_registration", "Cadastro pendente", "warning"],
      ["no_selection", "Sem seleção", "warning"],
      ["blocked", "Galeria bloqueada", "dark"],
      ["expired", "Galeria expirada", "warning"],
      ["active", "Galeria ativa", "success"],
    ] as const;
    const linkedClients = statuses.map(([gallery_status], index) => ({
      client_id: `client-${index}`,
      name: `Cliente ${index}`,
      phone: `+551199999990${index}`,
      registration_status: gallery_status === "pending_registration" ? "pending" : "active",
      derived_gallery_id: `derived-${index}`,
      available_count: index + 1,
      selected_count: index,
      purchased_count: Math.max(0, index - 1),
      gallery_status,
    }));
    vi.stubGlobal("fetch", vi.fn((path: string) => {
      if (path.endsWith("/editor")) return response(editor);
      if (path.includes("/parent-galleries/source-1/clients")) return response({ clients: linkedClients });
      return response({ clients: [] });
    }));
    render(<GalleryEditor sourceId="source-1" step="clientes" />);
    await screen.findByRole("article", { name: "Cliente Cliente 0" });
    statuses.forEach(([, label, tone], index) => {
      const card = screen.getByRole("article", { name: `Cliente Cliente ${index}` });
      expect(card.className).toContain(`gallery-linked-client--${statuses[index][0]}`);
      expect(within(card).getByText(label).className).toContain(`mk-badge--${tone}`);
    });
  });

  it("desvincula a cliente preservando cadastro e compra informados pelo backend", async () => {
    const linkedClient = { client_id: "client-1", name: "Ana Cliente", phone: "+5511999999999", registration_status: "active", derived_gallery_id: "derived-1", available_count: 2, selected_count: 1, purchased_count: 1, gallery_status: "active" };
    const queued = { operation_id: "unlink-1", status: "queued", status_url: "/admin/gallery-lifecycle-operations/unlink-1", last_error: null, progress: { label: "Na fila", percent: 0, failed_step: null }, actions: { can_cancel: true, can_retry: false, should_poll: true, poll_after_ms: 1 } };
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/editor")) return response(editor);
      if (path.includes("/clients/client-1/unlink-inventory")) return response({ operation_type: "unlink_client", target: { parent_gallery_id: "source-1", parent_gallery_name: "Festa escolar", client_id: "client-1", client_name: "Ana Cliente" }, inventory: { remove: { private_galleries: 1, available_references: 2, selections: 1 }, preserve: { clients: 1, orders: 1, order_items: 1 } }, consequences: { gallery_relationship_removed: true, private_gallery_removed: true, client_preserved: true, commercial_history_preserved: true, other_gallery_relationships_preserved: true, restoration_available_after_start: false } });
      if (path === "/api/admin/parent-galleries/source-1/clients/client-1" && init?.method === "DELETE") return response(queued, 202);
      if (path === "/api/admin/gallery-lifecycle-operations/unlink-1") return response({ ...queued, status: "completed", progress: { label: "Concluída", percent: 100, failed_step: null }, actions: { can_cancel: false, can_retry: false, should_poll: false, poll_after_ms: null } });
      if (path.includes("/parent-galleries/source-1/clients")) return response({ clients: [linkedClient] });
      return response({ clients: [] });
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<GalleryEditor sourceId="source-1" step="clientes" />);
    fireEvent.click(await screen.findByRole("button", { name: "Desvincular cliente" }));
    expect(await screen.findByRole("dialog", { name: "Desvincular Ana Cliente?" })).toBeTruthy();
    expect(screen.getByText((_, element) => element?.tagName === "SPAN" && element.textContent?.trim() === "1 pedidos preservados")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Confirmar desvinculação" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/admin/parent-galleries/source-1/clients/client-1",
      expect.objectContaining({ method: "DELETE", headers: { "Idempotency-Key": expect.any(String) } }),
    ));
    expect(await screen.findByText(/Cadastro e histórico foram preservados/)).toBeTruthy();
  });

  it("expõe bloqueio financeiro e falha do backend sem remover o cartão", async () => {
    const linkedClient = { client_id: "client-1", name: "Cliente Pendente", phone: "+5511999999999", registration_status: "active", derived_gallery_id: "derived-1", available_count: 1, selected_count: 1, purchased_count: 0, gallery_status: "active" };
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/editor")) return response(editor);
      if (path.includes("/clients/client-1/unlink-inventory")) return response({ operation_type: "unlink_client", target: { parent_gallery_id: "source-1", parent_gallery_name: "Festa escolar", client_id: "client-1", client_name: "Cliente Pendente" }, inventory: { remove: { private_galleries: 1, available_references: 1, selections: 1 }, preserve: { clients: 1, orders: 1, orders_by_status: { pending: 1, confirmed: 0, cancelled: 0 } } }, consequences: { gallery_relationship_removed: true, private_gallery_removed: true, client_preserved: true, commercial_history_preserved: true, other_gallery_relationships_preserved: true, restoration_available_after_start: false } });
      if (path === "/api/admin/parent-galleries/source-1/clients/client-1" && init?.method === "DELETE") return response({ detail: "Pagamento comunicado aguarda revisão administrativa." }, 409);
      if (path.includes("/parent-galleries/source-1/clients")) return response({ clients: [linkedClient] });
      return response({ clients: [] });
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<GalleryEditor sourceId="source-1" step="clientes" />);
    fireEvent.click(await screen.findByRole("button", { name: "Desvincular cliente" }));
    expect(await screen.findByText(/Pedidos pendentes serão avaliados/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Confirmar desvinculação" }));
    expect(await screen.findByText("Pagamento comunicado aguarda revisão administrativa.")).toBeTruthy();
    expect(screen.getByRole("article", { name: "Cliente Cliente Pendente" })).toBeTruthy();
  });

  it("cria galeria privada administrativa com fotos disponíveis e zero seleção inferida", async () => {
    const linkedClient = { client_id: "client-1", name: "Cliente Administrativa", phone: "+5511999999999", registration_status: "active", derived_gallery_id: null, available_count: 0, selected_count: 0, purchased_count: 0, gallery_status: "no_selection" };
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/editor")) return response(editor);
      if (path.endsWith("/available-photos")) return response({ photos: [{ id: "photo-1", name: "Foto 1", folder_name: "Lote liberado", preview_url: "/preview" }] });
      if (path.includes("/parent-galleries/source-1/clients")) return response({ clients: [linkedClient] });
      if (path === "/api/admin/derived-galleries" && init?.method === "POST") return response({ id: "private-1", selected_count: 0 }, 201);
      return response({ clients: [] });
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<GalleryEditor sourceId="source-1" step="clientes" />);
    fireEvent.click(await screen.findByRole("button", { name: "Disponibilizar fotos" }));
    expect(await screen.findByRole("dialog", { name: "Fotos para Cliente Administrativa" })).toBeTruthy();
    expect((screen.getByRole("button", { name: "Criar ou atualizar galeria privada" }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(screen.getByRole("button", { name: "Criar ou atualizar galeria privada" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/admin/derived-galleries",
      expect.objectContaining({ method: "POST", body: JSON.stringify({ parent_gallery_id: "source-1", client_id: "client-1", name: "Festa escolar · Cliente Administrativa", photo_ids: ["photo-1"] }) }),
    ));
    expect(await screen.findByText(/sem seleção automática/)).toBeTruthy();
  });

  it("separa vinculados, busca e novo cadastro em blocos responsivos", async () => {
    vi.stubGlobal("fetch", vi.fn((path: string) => {
      if (path.endsWith("/editor")) return response(editor);
      if (path.includes("/parent-galleries/source-1/clients")) return response({ clients: [] });
      return response({ clients: [{ id: "client-2", name: "Beatriz Cliente", phone: "+5511888888888" }] });
    }));
    render(<GalleryEditor sourceId="source-1" step="clientes" />);
    expect(await screen.findByRole("region", { name: "Clientes vinculadas" })).toBeTruthy();
    expect(screen.getByRole("region", { name: "Vincular cliente" })).toBeTruthy();
    expect(screen.getByRole("region", { name: "Cadastrar e vincular" })).toBeTruthy();
    expect(screen.getByRole("button", { name: /Beatriz Cliente.*Vincular/ })).toBeTruthy();
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

  it("renderiza o resumo com capa clicável, estado do link e exclusão contextual", async () => {
    const fetchMock = vi.fn((path: string) => path.endsWith("/folders")
      ? response({ folders: [{ id: "folder-1", name: "Lote inicial", status: "preparing", photo_count: 2 }] })
      : response({ name: "Evento completo", event_name: "Festa 2026", active: true, unlisted_link: null, public_link_status: "active", cover_preview_url: "/admin/photo-assets/photo-1/watermarked-preview", counts: { folders: 1, photos: 2, clients: 0 }, clients: [] }));
    vi.stubGlobal("fetch", fetchMock);
    render(<SourceGalleryDetailPage />);
    expect(await screen.findByRole("heading", { name: "Evento completo" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Capa protegida da galeria" }).getAttribute("href")).toBe("/admin/galleries/sources/source-1/preview");
    expect(screen.getByText("ativo")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Excluir Galeria pública" })).toBeTruthy();
  });

  it("confirma uma vez com inventário e acompanha a exclusão até o sucesso", async () => {
    const queuedOperation = {
      operation_id: "operation-1",
      status: "queued",
      status_url: "/admin/gallery-lifecycle-operations/operation-1",
      last_error: null,
      progress: { label: "Na fila", percent: 0, failed_step: null },
      actions: { can_cancel: true, can_retry: false, should_poll: true, poll_after_ms: 1 },
    };
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/folders")) return response({ folders: [] });
      if (path.endsWith("/summary")) return response({ name: "Evento completo", event_name: "Festa", active: true, unlisted_link: null, public_link_status: "active", cover_preview_url: null, counts: { folders: 1, photos: 2, clients: 1 }, clients: [] });
      if (path.endsWith("/deletion-inventory")) return response({ operation_type: "delete_parent_gallery", target: { id: "source-1", name: "Evento completo" }, inventory: { remove: { folders: 1, photos: 1 }, preserve: { clients: 1, private_galleries: 1 } }, consequences: { private_galleries_preserved: true, private_referenced_photos_preserved: true, clients_preserved: true, commercial_history_preserved: true, restoration_available_after_start: false } });
      if (path === "/api/admin/parent-galleries/source-1" && init?.method === "DELETE") return response(queuedOperation, 202);
      if (path === "/api/admin/gallery-lifecycle-operations/operation-1") return response({ ...queuedOperation, status: "completed", progress: { label: "Concluída", percent: 100, failed_step: null }, actions: { can_cancel: false, can_retry: false, should_poll: false, poll_after_ms: null } });
      return response({});
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<SourceGalleryDetailPage />);
    const deleteButton = await screen.findByRole("button", { name: "Excluir Galeria pública" });
    fireEvent.click(deleteButton);
    fireEvent.click(deleteButton);
    expect(await screen.findByRole("dialog", { name: "Excluir “Evento completo”?" })).toBeTruthy();
    expect(fetchMock.mock.calls.filter(([path]) => String(path).endsWith("/deletion-inventory"))).toHaveLength(1);
    expect(screen.getByText("Será removido")).toBeTruthy();
    expect(screen.getByText("Será preservado")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Excluir Evento completo" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/admin/parent-galleries/source-1",
      expect.objectContaining({ method: "DELETE", headers: { "Idempotency-Key": expect.any(String) } }),
    ));
    expect(await screen.findByRole("heading", { name: "Concluída" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Voltar para galerias" })).toBeTruthy();
  });

  it("permite cancelar antes da remoção física e expõe retomada após falha", async () => {
    const failedOperation = {
      operation_id: "operation-2",
      status: "failed",
      status_url: "/admin/gallery-lifecycle-operations/operation-2",
      last_error: "Falha interna na etapa removing_storage.",
      progress: { label: "Falhou", percent: 25, failed_step: "removing_storage" },
      actions: { can_cancel: false, can_retry: true, should_poll: false, poll_after_ms: null },
    };
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/folders")) return response({ folders: [] });
      if (path.endsWith("/summary")) return response({ name: "Evento falho", event_name: "Festa", active: true, unlisted_link: null, public_link_status: "active", cover_preview_url: null, counts: { folders: 0, photos: 0, clients: 0 }, clients: [] });
      if (path.endsWith("/deletion-inventory")) return response({ operation_type: "delete_parent_gallery", target: { id: "source-1", name: "Evento falho" }, inventory: { remove: {}, preserve: {} }, consequences: { private_galleries_preserved: true, private_referenced_photos_preserved: true, clients_preserved: true, commercial_history_preserved: true, restoration_available_after_start: false } });
      if (path === "/api/admin/parent-galleries/source-1" && init?.method === "DELETE") return response(failedOperation, 202);
      if (path.endsWith("/operation-2/retry") && init?.method === "POST") return response({ ...failedOperation, status: "queued", last_error: null, progress: { label: "Na fila", percent: 25, failed_step: null }, actions: { can_cancel: true, can_retry: false, should_poll: false, poll_after_ms: null } });
      if (path.endsWith("/operation-2/cancel") && init?.method === "POST") return response({ ...failedOperation, status: "cancelled", last_error: null, progress: { label: "Cancelada", percent: 100, failed_step: null }, actions: { can_cancel: false, can_retry: false, should_poll: false, poll_after_ms: null } });
      return response({});
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<SourceGalleryDetailPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Excluir Galeria pública" }));
    fireEvent.click(await screen.findByRole("button", { name: "Excluir Evento falho" }));
    expect(await screen.findByRole("button", { name: "Retomar operação" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Retomar operação" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/admin/gallery-lifecycle-operations/operation-2/retry",
      expect.objectContaining({ method: "POST" }),
    ));
    expect(await screen.findByRole("heading", { name: "Na fila" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Cancelar antes da remoção física" }));
    expect(await screen.findByRole("heading", { name: "Cancelada" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Fechar acompanhamento" })).toBeTruthy();
  });
});
