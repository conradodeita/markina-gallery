import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const push = vi.fn();
vi.mock("next/link", () => ({ default: ({ children, href, ...props }: { children: React.ReactNode; href: string }) => <a href={href} {...props}>{children}</a> }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }), useParams: () => ({ sourceId: "source-1" }) }));

import NewGalleryPage from "./new/page";
import GalleryEditor from "./sources/[sourceId]/edit/gallery-editor";
import SourceGalleryDetailPage from "./sources/[sourceId]/page";

const validPix = "0002015204000053039865802BR5907MARKINA6009SAO PAULO6304BE17";

afterEach(() => {
  vi.restoreAllMocks();
  push.mockReset();
});

const editor = {
  gallery: { id: "source-1", name: "Festa escolar", event_name: "Festa 2026", description: "", active: true, access_mode: "invite_only", unlisted_link: null, public_link: { status: "active", capability_id: "capability-1", expires_at: null, secret_available: false }, cover_photo_id: null, cover_preview_url: null, folder_display_mode: "individual", cover_title_font: "system-sans", cover_title_color: "#FFFFFF", cover_title_size: 32, cover_title_position: "bottom-left" },
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
    const fetchMock = vi.fn((path: string, init?: RequestInit) => path.endsWith("/editor") ? response(editor) : path.endsWith("/publish-ready") && init?.method === "POST" ? response({ published_count: 0, pending_count: 0, failed_count: 0, available_count: 0, folders: [] }) : response({ folders: [], clients: [] }));
    vi.stubGlobal("fetch", fetchMock);
    render(<GalleryEditor sourceId="source-1" step="imagens" />);
    await screen.findByRole("heading", { name: "Imagens e pastas" });
    expect(screen.getByRole("link", { name: "← Voltar" }).getAttribute("href")).toBe("/admin/galleries/sources/source-1/edit/detalhes");
    fireEvent.click(screen.getByRole("button", { name: "Salvar e avançar →" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/admin/parent-galleries/source-1/publish-ready",
      expect.objectContaining({ method: "POST" }),
    ));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/admin/galleries/sources/source-1/edit/clientes"));
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
    fireEvent.click(screen.getByRole("button", { name: "Salvar e avançar →" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/admin/parent-galleries/source-1/settings",
      expect.objectContaining({ method: "PATCH", body: expect.stringContaining('"access_mode":"standard"') }),
    ));
    expect(screen.getByRole("option", { name: /Coletivo protegido/ })).toBeTruthy();
    const accessHints = screen.getByRole("region", { name: "Como funcionam os modos de acesso" });
    expect(within(accessHints).getByText("Padrão")).toBeTruthy();
    expect(within(accessHints).getByText("Somente convite individual")).toBeTruthy();
    expect(within(accessHints).getByText("Coletivo protegido")).toBeTruthy();
    expect(within(accessHints).getByText(/não ativa reconhecimento facial/i)).toBeTruthy();
    expect(push).toHaveBeenCalledWith("/admin/galleries/sources/source-1/edit/vendas");
  });

  it("protege troca direta e retorno quando há alterações não salvas", async () => {
    vi.stubGlobal("fetch", vi.fn((path: string) => path.endsWith("/editor") ? response(editor) : response({})));
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
    render(<GalleryEditor sourceId="source-1" step="ajustes" />);

    fireEvent.change(await screen.findByLabelText("Título da galeria"), { target: { value: "Título alterado" } });
    expect(fireEvent.click(screen.getByRole("link", { name: /Detalhes/ }))).toBe(false);
    expect(confirm).toHaveBeenCalledWith("Descartar as alterações ainda não salvas desta etapa?");
    confirm.mockReturnValue(true);
    expect(fireEvent.click(screen.getByRole("link", { name: "← Galerias" }))).toBe(true);
  });

  it("ignora clique repetido enquanto Salvar e avançar está pendente", async () => {
    let finishSave!: (value: Response) => void;
    const pendingSave = new Promise<Response>((resolve) => { finishSave = resolve; });
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/editor")) return response(editor);
      if (init?.method === "PATCH") return pendingSave;
      return response({});
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<GalleryEditor sourceId="source-1" step="ajustes" />);

    const save = await screen.findByRole("button", { name: "Salvar e avançar →" });
    fireEvent.click(save);
    const pendingButton = screen.getByRole("button", { name: "Salvando…" });
    fireEvent.click(pendingButton);
    expect(fetchMock.mock.calls.filter(([, init]) => init?.method === "PATCH")).toHaveLength(1);
    finishSave(new Response(JSON.stringify({ id: "source-1" }), { status: 200 }));
    await waitFor(() => expect(push).toHaveBeenCalledTimes(1));
  });

  it("informa indisponibilidade quando o contrato do editor falha", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "Sessão expirada" }), { status: 401, headers: { "content-type": "application/json" } })));
    render(<GalleryEditor sourceId="source-1" step="ajustes" />);
    expect((await screen.findByRole("alert")).textContent).toContain("Galeria indisponível");
  });

  it("mantém cliente vinculada no cadastro existente sem oferecer vínculo duplicado", async () => {
    const linkedClient = { client_id: "client-1", name: "Ana Cliente", phone: "+5511999999999", registration_status: "active", derived_gallery_id: "derived-1", available_count: 1, selected_count: 0, purchased_count: 3, gallery_status: "no_selection", commercial_status: "paid" };
    vi.stubGlobal("fetch", vi.fn((path: string) => {
      if (path.endsWith("/editor")) return response(editor);
      if (path.includes("/parent-galleries/source-1/clients")) return response({ clients: [linkedClient] });
      return response({ clients: [{ id: "client-1", name: "Ana Cliente", phone: "+5511999999999" }] });
    }));
    render(<GalleryEditor sourceId="source-1" step="clientes" />);
    expect((await screen.findAllByText("Ana Cliente")).length).toBeGreaterThan(1);
    expect(screen.queryByRole("button", { name: /Vincular/ })).toBeNull();
    expect(screen.getByText("Já vinculada")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Editar cadastro de Ana Cliente" })).toBeTruthy();
    const card = screen.getByRole("article", { name: "Cliente Ana Cliente" });
    expect(within(card).getByText("Sem seleção")).toBeTruthy();
    expect(within(card).getByText("Disponíveis")).toBeTruthy();
    expect(within(card).getByText("Selecionadas")).toBeTruthy();
    expect(within(card).getByText("Compradas")).toBeTruthy();
    expect(within(card).getByText("Pago")).toBeTruthy();
    expect(within(card).getByText("Sem seleção")).toBeTruthy();
    const galleryLink = within(card).getByRole("link", { name: "Ana Cliente" });
    galleryLink.focus();
    expect(document.activeElement).toBe(galleryLink);
  });

  it("edita o nome da mesma cliente e recarrega a lista", async () => {
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/editor")) return response(editor);
      if (path.includes("/parent-galleries/source-1/clients")) return response({ clients: [] });
      if (path === "/api/admin/clients/client-2" && init?.method === "PATCH") {
        return response({ id: "client-2", name: "Beatriz Corrigida", phone: "+5511888888888" });
      }
      if (path.startsWith("/api/admin/clients")) return response({ clients: [{ id: "client-2", name: "Beatriz Cliente", phone: "+5511888888888" }] });
      return response({ photos: [] });
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<GalleryEditor sourceId="source-1" step="clientes" />);

    fireEvent.click(await screen.findByRole("button", { name: "Editar cadastro de Beatriz Cliente" }));
    const dialog = screen.getByRole("dialog", { name: "Editar Beatriz Cliente" });
    fireEvent.change(within(dialog).getByLabelText("Nome completo"), { target: { value: "Beatriz Corrigida" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Salvar cadastro" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/admin/clients/client-2",
      expect.objectContaining({ method: "PATCH", body: JSON.stringify({ full_name: "Beatriz Corrigida" }) }),
    ));
    expect(await screen.findByText("Cadastro da cliente atualizado sem alterar seus vínculos ou histórico.")).toBeTruthy();
  });

  it("comprova por OTP o novo WhatsApp antes de trocar o telefone", async () => {
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/editor")) return response(editor);
      if (path.includes("/parent-galleries/source-1/clients")) return response({ clients: [] });
      if (path === "/api/auth/client/challenge" && init?.method === "POST") return response({ challenge_id: "challenge-phone", message: "Código enviado." }, 202);
      if (path === "/api/admin/clients/client-2/phone" && init?.method === "POST") return response({ id: "client-2" });
      if (path.startsWith("/api/admin/clients")) return response({ clients: [{ id: "client-2", name: "Beatriz Cliente", phone: "+5511888888888" }] });
      return response({ photos: [] });
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<GalleryEditor sourceId="source-1" step="clientes" />);

    fireEvent.click(await screen.findByRole("button", { name: "Editar cadastro de Beatriz Cliente" }));
    const dialog = screen.getByRole("dialog", { name: "Editar Beatriz Cliente" });
    fireEvent.change(within(dialog).getByLabelText("Número do WhatsApp"), { target: { value: "+55 11 97777-6666" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Enviar código" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/auth/client/challenge",
      expect.objectContaining({ method: "POST", body: JSON.stringify({ full_name: "Beatriz Cliente", phone: "+55 11 97777-6666" }) }),
    ));
    fireEvent.change(await within(dialog).findByLabelText("Código enviado ao novo WhatsApp"), { target: { value: "123456" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Salvar cadastro" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/admin/clients/client-2/phone",
      expect.objectContaining({ method: "POST", body: JSON.stringify({ phone_e164: "+55 11 97777-6666", challenge_id: "challenge-phone", code: "123456" }) }),
    ));
  });

  it("bloqueia exclusão de cliente com histórico e orienta a edição", async () => {
    vi.stubGlobal("fetch", vi.fn((path: string) => {
      if (path.endsWith("/editor")) return response(editor);
      if (path.includes("/parent-galleries/source-1/clients")) return response({ clients: [] });
      if (path.endsWith("/clients/client-2/deletion-inventory")) return response({ client_id: "client-2", blockers: { orders: 1 }, blocking: { orders: 1 }, can_delete: false, removable: { client: 1, phone_records: 1 } });
      if (path.startsWith("/api/admin/clients")) return response({ clients: [{ id: "client-2", name: "Beatriz Cliente", phone: "+5511888888888" }] });
      return response({ photos: [] });
    }));
    render(<GalleryEditor sourceId="source-1" step="clientes" />);

    fireEvent.click(await screen.findByRole("button", { name: "Editar cadastro de Beatriz Cliente" }));
    fireEvent.click(screen.getByRole("button", { name: "Verificar exclusão" }));
    expect(await screen.findByText("Exclusão bloqueada")).toBeTruthy();
    expect(screen.getByText("1 pedidos")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Excluir cadastro definitivamente" })).toBeNull();
  });

  it("apresenta estados por texto, contraste semântico e cartões responsivos", async () => {
    const statuses = [
      ["pending_registration", "Aguardando primeiro acesso", "warning"],
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
    const unlinkProgress = await screen.findByRole("region", { name: "Desvinculação de Ana Cliente" });
    await waitFor(() => expect(within(unlinkProgress).getByText(/Cadastro e histórico foram preservados/)).toBeTruthy());
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
    expect(await screen.findByText(/pagamento informado e ainda em análise impede a desvinculação/i)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Confirmar desvinculação" }));
    const dialog = await screen.findByRole("dialog", { name: "Desvincular Cliente Pendente?" });
    expect(await within(dialog).findByRole("alert")).toHaveProperty("textContent", "Pagamento comunicado aguarda revisão administrativa.");
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
    fireEvent.click(await screen.findByRole("button", { name: "Montar galeria privada" }));
    expect(await screen.findByRole("dialog", { name: "Galeria privada de Cliente Administrativa" })).toBeTruthy();
    expect((screen.getByRole("button", { name: "Criar ou atualizar galeria privada" }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(screen.getByRole("button", { name: "Criar ou atualizar galeria privada" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/admin/derived-galleries",
      expect.objectContaining({ method: "POST", body: JSON.stringify({ parent_gallery_id: "source-1", client_id: "client-1", name: "Festa escolar · Cliente Administrativa", photo_ids: ["photo-1"] }) }),
    ));
    expect(await screen.findByText(/sem seleção automática/)).toBeTruthy();
  });

  it("explica por que a galeria privada não pode ser montada sem publicação", async () => {
    const linkedClient = { client_id: "client-1", name: "Cliente Sem Fotos", phone: "+5511999999999", registration_status: "active", derived_gallery_id: null, available_count: 0, selected_count: 0, purchased_count: 0, gallery_status: "no_selection" };
    vi.stubGlobal("fetch", vi.fn((path: string) => {
      if (path.endsWith("/editor")) return response(editor);
      if (path.endsWith("/available-photos")) return response({ photos: [] });
      if (path.includes("/parent-galleries/source-1/clients")) return response({ clients: [linkedClient] });
      return response({ clients: [] });
    }));
    render(<GalleryEditor sourceId="source-1" step="clientes" />);
    fireEvent.click(await screen.findByRole("button", { name: "Montar galeria privada" }));
    const dialog = await screen.findByRole("dialog", { name: "Galeria privada de Cliente Sem Fotos" });
    expect(within(dialog).getByText("Nenhuma foto publicada")).toBeTruthy();
    expect(within(dialog).getByRole("link", { name: "Ir para Imagens" }).getAttribute("href")).toBe("/admin/galleries/sources/source-1/edit/imagens");
  });

  it("mantém no modal o erro ao disponibilizar fotos", async () => {
    const linkedClient = { client_id: "client-1", name: "Cliente Bloqueada", phone: "+5511999999999", registration_status: "active", derived_gallery_id: null, available_count: 0, selected_count: 0, purchased_count: 0, gallery_status: "no_selection" };
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/editor")) return response(editor);
      if (path.endsWith("/available-photos")) return response({ photos: [{ id: "photo-1", name: "Foto 1", folder_name: "Publicadas", preview_url: "/preview" }] });
      if (path.includes("/parent-galleries/source-1/clients")) return response({ clients: [linkedClient] });
      if (path === "/api/admin/derived-galleries" && init?.method === "POST") return response({ detail: "A cliente já possui uma galeria privada nesta Galeria pública." }, 409);
      return response({ clients: [] });
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<GalleryEditor sourceId="source-1" step="clientes" />);
    fireEvent.click(await screen.findByRole("button", { name: "Montar galeria privada" }));
    fireEvent.click(await screen.findByRole("checkbox"));
    fireEvent.click(screen.getByRole("button", { name: "Criar ou atualizar galeria privada" }));
    const dialog = await screen.findByRole("dialog", { name: "Galeria privada de Cliente Bloqueada" });
    expect(await within(dialog).findByRole("alert")).toHaveProperty("textContent", "A cliente já possui uma galeria privada nesta Galeria pública.");
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
    expect(screen.getByRole("button", { name: "Vincular Beatriz Cliente" })).toBeTruthy();
    expect(screen.getByText("Nenhuma galeria privada criada")).toBeTruthy();
  });

  it("mostra, copia e regenera links estáveis e gerencia membros da privada", async () => {
    const linkedClient = { client_id: "client-1", name: "Ana Cliente", phone: "+5511999999999", registration_status: "active", membership_status: "active", derived_gallery_id: "derived-1", available_count: 2, selected_count: 1, purchased_count: 0, gallery_status: "active" };
    const member = { membership_id: "membership-1", client_id: "client-1", client_name: "Ana Cliente", phone_e164: "+5511999999999", status: "active", selected_count: 1, purchased_count: 0, order_count: 0, confirmed_total_cents: 0, payment_status: "none" };
    const clipboardWrite = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText: clipboardWrite } });
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/editor")) return response(editor);
      if (path.endsWith("/parent-galleries/source-1/clients")) return response({ clients: [linkedClient] });
      if (path.endsWith("/available-photos")) return response({ photos: [] });
      if (path === "/api/admin/clients") return response({ clients: [] });
      if (path.endsWith("/public-link/rotate") && init?.method === "POST") return response({ status: "active", capability_id: "public-2", expires_at: null, secret_available: true, link: "https://example.test/a/public-new" });
      if (path.endsWith("/public-link")) return response({ status: "active", capability_id: "public-1", expires_at: null, secret_available: true, link: "https://example.test/a/public" });
      if (path.endsWith("/derived-galleries/derived-1/link")) return response({ status: "active", capability_id: "private-1", expires_at: null, secret_available: true, link: "https://example.test/a/private" });
      if (path.endsWith("/members/client-1/block") && init?.method === "POST") return response({ ...member, status: "blocked" });
      if (path.endsWith("/derived-galleries/derived-1/members")) return response({ members: [member] });
      return response({});
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<GalleryEditor sourceId="source-1" step="clientes" />);

    const publicInput = await screen.findByLabelText("Link da Galeria pública") as HTMLInputElement;
    expect(publicInput.value).toBe("https://example.test/a/public");
    expect(await screen.findByLabelText("Link privado de Ana Cliente")).toHaveProperty("value", "https://example.test/a/private");
    expect(screen.getByText("Ana Cliente", { selector: ".private-member-row strong" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Copiar link" }));
    await waitFor(() => expect(clipboardWrite).toHaveBeenCalledWith("https://example.test/a/public"));
    fireEvent.click(screen.getByRole("button", { name: "Regenerar link" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/admin/parent-galleries/source-1/public-link/rotate",
      expect.objectContaining({ method: "POST", body: "{}" }),
    ));
    expect((screen.getByLabelText("Link da Galeria pública") as HTMLInputElement).value).toBe("https://example.test/a/public-new");
    fireEvent.click(screen.getByRole("button", { name: "Bloquear" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/admin/derived-galleries/derived-1/members/client-1/block",
      expect.objectContaining({ method: "POST" }),
    ));
  });

  it("preserva a etapa e mostra conflito ao adicionar cliente já vinculada a outra privada", async () => {
    const linkedClient = { client_id: "client-1", name: "Ana Cliente", phone: "+5511999999999", registration_status: "active", membership_status: "active", derived_gallery_id: "derived-1", available_count: 1, selected_count: 0, purchased_count: 0, gallery_status: "no_selection" };
    const member = { membership_id: "membership-1", client_id: "client-1", client_name: "Ana Cliente", phone_e164: "+5511999999999", status: "active", selected_count: 0, purchased_count: 0, order_count: 0, confirmed_total_cents: 0, payment_status: "none" };
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/editor")) return response(editor);
      if (path.endsWith("/parent-galleries/source-1/clients")) return response({ clients: [linkedClient] });
      if (path.endsWith("/available-photos")) return response({ photos: [] });
      if (path === "/api/admin/clients") return response({ clients: [{ id: "client-2", name: "Beatriz Cliente", phone: "+5511888888888" }] });
      if (path.endsWith("/public-link")) return response({ status: "unavailable", capability_id: null, expires_at: null, secret_available: false, link: null });
      if (path.endsWith("/derived-galleries/derived-1/link")) return response({ status: "unavailable", capability_id: null, expires_at: null, secret_available: false, link: null });
      if (path.endsWith("/derived-galleries/derived-1/members") && init?.method === "POST") return response({ detail: "A cliente já pertence a outra galeria privada desta origem." }, 409);
      if (path.endsWith("/derived-galleries/derived-1/members")) return response({ members: [member] });
      return response({});
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<GalleryEditor sourceId="source-1" step="clientes" />);

    fireEvent.change(await screen.findByLabelText("Adicionar cliente à galeria de Ana Cliente"), { target: { value: "client-2" } });
    fireEvent.click(screen.getByRole("button", { name: "Adicionar membro" }));
    expect(await screen.findByText("A cliente já pertence a outra galeria privada desta origem.")).toBeTruthy();
    expect(screen.getByRole("article", { name: "Galeria privada Ana Cliente" })).toBeTruthy();
  });

  it("expõe carregamento e erro isolado da galeria privada", async () => {
    const linkedClient = { client_id: "client-1", name: "Ana Cliente", phone: "+5511999999999", registration_status: "active", membership_status: "active", derived_gallery_id: "derived-1", available_count: 1, selected_count: 0, purchased_count: 0, gallery_status: "no_selection" };
    let finishPrivateLink!: (value: Response) => void;
    const pendingPrivateLink = new Promise<Response>((resolve) => { finishPrivateLink = resolve; });
    vi.stubGlobal("fetch", vi.fn((path: string) => {
      if (path.endsWith("/editor")) return response(editor);
      if (path.endsWith("/parent-galleries/source-1/clients")) return response({ clients: [linkedClient] });
      if (path.endsWith("/available-photos")) return response({ photos: [] });
      if (path === "/api/admin/clients") return response({ clients: [] });
      if (path.endsWith("/public-link")) return response({ status: "unavailable", capability_id: null, expires_at: null, secret_available: false, link: null });
      if (path.endsWith("/derived-galleries/derived-1/link")) return pendingPrivateLink;
      if (path.endsWith("/derived-galleries/derived-1/members")) return response({ members: [] });
      return response({});
    }));
    render(<GalleryEditor sourceId="source-1" step="clientes" />);

    expect(await screen.findByText("Carregando acesso")).toBeTruthy();
    finishPrivateLink(new Response(JSON.stringify({ detail: "Falha ao consultar link privado." }), { status: 500, headers: { "content-type": "application/json" } }));
    expect(await screen.findByText("Acesso indisponível")).toBeTruthy();
    expect(screen.getByText("Falha ao consultar link privado.")).toBeTruthy();
  });

  it("mostra capacidade comercial indisponível sem inventar configuração", async () => {
    vi.stubGlobal("fetch", vi.fn((path: string) => path.endsWith("/editor") ? response(editor) : response({ available: false, reason: "Configuração comercial será liberada em uma mudança própria.", capabilities: [] })));
    render(<GalleryEditor sourceId="source-1" step="vendas" />);
    expect(await screen.findByText("Configuração comercial indisponível")).toBeTruthy();
    expect(screen.getByText(/liberada em uma mudança própria/i)).toBeTruthy();
    expect(screen.queryByLabelText(/preço/i)).toBeNull();
  });

  it("edita e persiste todos os controles da etapa Vendas na Galeria pública", async () => {
    const sales = {
      available: true,
      capabilities: ["pricing_tiers", "pix", "sales_message", "interactions", "selection_deadline"],
      pricing_mode: "fixed",
      fixed_unit_price_cents: 700,
      progressive_pricing_preset_id: null,
      pricing_snapshot: { mode: "fixed", unit_price_cents: 700 },
      pricing_review_required: false,
      tiers: [{ minimum_quantity: 1, maximum_quantity: null, unit_price_cents: 700 }],
      pix: { copy_paste: null, qr_code_payload: null, qr_png_data_url: "data:image/png;base64,cXI=", review_required: false, instructions: null },
      sales_message: "Escolha suas fotos",
      selection_duration_days: 14,
      favorites_enabled: true,
      comments_enabled: false,
    };
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/editor")) return response(editor);
      if (path.endsWith("/sales") && init?.method === "PUT") return response({ ...sales, ...JSON.parse(String(init.body)) });
      return response(sales);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<GalleryEditor sourceId="source-1" step="vendas" />);

    await screen.findByRole("heading", { name: "Vendas" });
    expect(screen.getByLabelText("Valor unitário da foto")).toHaveProperty("value", expect.stringMatching(/7,00/));
    fireEvent.change(screen.getByLabelText("Valor unitário da foto"), { target: { value: "700000" } });
    expect(screen.getByLabelText("Valor unitário da foto")).toHaveProperty("value", expect.stringMatching(/7\.000,00/));
    expect(screen.queryByLabelText("Payload do QR Code")).toBeNull();
    expect(screen.getByAltText("QR Code PIX gerado a partir da configuração salva")).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Chave PIX ou copia e cola"), { target: { value: validPix } });
    fireEvent.change(screen.getByLabelText("Mensagem comercial"), { target: { value: "Mensagem atualizada" } });
    fireEvent.change(screen.getByLabelText("Prazo padrão de seleção (dias)"), { target: { value: "21" } });
    fireEvent.click(screen.getByLabelText("Permitir comentários"));
    fireEvent.click(screen.getByRole("button", { name: "Salvar e avançar →" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/admin/parent-galleries/source-1/sales",
      expect.objectContaining({
        method: "PUT",
        body: expect.stringContaining(`"copy_paste":"${validPix}"`),
      }),
    ));
    const saveCall = fetchMock.mock.calls.find(([path, init]) => path.endsWith("/sales") && init?.method === "PUT");
    expect(JSON.parse(String(saveCall?.[1]?.body))).toMatchObject({
      pricing_mode: "fixed",
      fixed_unit_price_cents: 700000,
      sales_message: "Mensagem atualizada",
      selection_duration_days: 21,
      comments_enabled: true,
    });
    expect(JSON.parse(String(saveCall?.[1]?.body)).pix).toEqual({ copy_paste: validPix, receiver_name: null, receiver_city: null, instructions: null });
  });

  it("aceita chave PIX simples com os dados necessários para gerar o QR", async () => {
    const sales = { available: true, capabilities: [], pricing_mode: "fixed", fixed_unit_price_cents: 700, progressive_pricing_preset_id: null, pricing_snapshot: { mode: "fixed" }, pricing_review_required: false, tiers: [{ minimum_quantity: 1, maximum_quantity: null, unit_price_cents: 700 }], pix: { copy_paste: null, qr_code_payload: null, qr_png_data_url: null, review_required: false, instructions: null }, sales_message: "", selection_duration_days: 14, favorites_enabled: true, comments_enabled: false };
    const fetchMock = vi.fn((path: string, init?: RequestInit) => path.endsWith("/editor") ? response(editor) : init?.method === "PUT" ? response({ ...sales, pix: { ...sales.pix, copy_paste: "fotografo@example.com", input_type: "email", receiver_name: "MARKINA", receiver_city: "SAO PAULO" } }) : response(sales));
    vi.stubGlobal("fetch", fetchMock);
    render(<GalleryEditor sourceId="source-1" step="vendas" />);
    expect(await screen.findByText(/Aceita CPF, telefone brasileiro, e-mail/i)).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Chave PIX ou copia e cola"), { target: { value: "fotografo@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: "Salvar e avançar →" }));
    expect(await screen.findByRole("alert")).toHaveProperty("textContent", "Para gerar o QR a partir de uma chave, informe o nome e a cidade do recebedor.");
    fireEvent.change(screen.getByLabelText("Nome do recebedor"), { target: { value: "Markina" } });
    fireEvent.change(screen.getByLabelText("Cidade do recebedor"), { target: { value: "São Paulo" } });
    fireEvent.click(screen.getByRole("button", { name: "Salvar e avançar →" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/admin/parent-galleries/source-1/sales",
      expect.objectContaining({
        method: "PUT",
        body: expect.stringContaining('"receiver_name":"Markina","receiver_city":"São Paulo"'),
      }),
    ));
    expect(push).toHaveBeenCalledWith("/admin/galleries/sources/source-1/edit/detalhes");
  });

  it("preserva os dados editados e mostra o erro retornado ao falhar Vendas", async () => {
    const sales = { available: true, capabilities: [], pricing_mode: "fixed", fixed_unit_price_cents: 700, progressive_pricing_preset_id: null, pricing_snapshot: { mode: "fixed" }, pricing_review_required: false, tiers: [{ minimum_quantity: 1, maximum_quantity: null, unit_price_cents: 700 }], pix: { copy_paste: null, qr_code_payload: null, qr_png_data_url: null, review_required: false, instructions: null }, sales_message: "Original", selection_duration_days: 14, favorites_enabled: true, comments_enabled: false };
    vi.stubGlobal("fetch", vi.fn((path: string, init?: RequestInit) => path.endsWith("/editor") ? response(editor) : init?.method === "PUT" ? response({ detail: "As faixas devem ser contíguas." }, 422) : response(sales)));
    render(<GalleryEditor sourceId="source-1" step="vendas" />);
    const message = await screen.findByLabelText("Mensagem comercial") as HTMLTextAreaElement;
    fireEvent.change(message, { target: { value: "Não perder" } });
    fireEvent.click(screen.getByRole("button", { name: "Salvar e avançar →" }));
    expect(await screen.findByText("As faixas devem ser contíguas.")).toBeTruthy();
    expect(message.value).toBe("Não perder");
    expect(push).not.toHaveBeenCalled();
  });

  it("exige escolha e confirmação explícitas para converter preço legado", async () => {
    const sales = { available: true, capabilities: [], pricing_mode: "legacy_volume", fixed_unit_price_cents: null, progressive_pricing_preset_id: null, pricing_snapshot: { mode: "legacy_volume" }, pricing_review_required: true, tiers: [{ minimum_quantity: 1, maximum_quantity: 10, unit_price_cents: 700 }, { minimum_quantity: 11, maximum_quantity: null, unit_price_cents: 500 }], pix: { copy_paste: null, qr_code_payload: null, qr_png_data_url: null, review_required: false, instructions: null }, sales_message: "", selection_duration_days: 14, favorites_enabled: true, comments_enabled: false };
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/editor")) return response(editor);
      if (path.endsWith("/pricing-presets")) return response({ presets: [] });
      if (init?.method === "PUT") return response({ ...sales, ...JSON.parse(String(init.body)), pricing_review_required: false });
      return response(sales);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<GalleryEditor sourceId="source-1" step="vendas" />);
    expect((await screen.findByRole("alert")).textContent).toMatch(/precisa de revisão/i);
    fireEvent.click(screen.getByRole("button", { name: "Salvar e avançar →" }));
    expect(await screen.findByText(/Escolha preço fixo ou uma tabela progressiva/)).toBeTruthy();
    expect(fetchMock.mock.calls.some(([, init]) => init?.method === "PUT")).toBe(false);
    fireEvent.click(screen.getByLabelText("Preço fixo por foto"));
    fireEvent.change(screen.getByLabelText("Valor unitário da foto"), { target: { value: "R$ 7,00" } });
    fireEvent.click(screen.getByLabelText(/Confirmo a substituição/));
    fireEvent.click(screen.getByRole("button", { name: "Salvar e avançar →" }));
    await waitFor(() => expect(fetchMock.mock.calls.some(([, init]) => init?.method === "PUT")).toBe(true));
    const saveCall = fetchMock.mock.calls.find(([, init]) => init?.method === "PUT");
    expect(JSON.parse(String(saveCall?.[1]?.body))).toMatchObject({ pricing_mode: "fixed", fixed_unit_price_cents: 700, confirm_legacy_conversion: true });
  });

  it("seleciona tabela global e simula parcelas e economia no backend", async () => {
    const sales = { available: true, capabilities: [], pricing_mode: "progressive", fixed_unit_price_cents: null, progressive_pricing_preset_id: "preset-1", pricing_snapshot: { mode: "progressive" }, pricing_review_required: false, tiers: [{ minimum_quantity: 1, maximum_quantity: 30, unit_price_cents: 700 }, { minimum_quantity: 31, maximum_quantity: null, unit_price_cents: 600 }], pix: { copy_paste: null, qr_code_payload: null, qr_png_data_url: null, review_required: false, instructions: null }, sales_message: "", selection_duration_days: 14, favorites_enabled: true, comments_enabled: false };
    const fetchMock = vi.fn((path: string) => {
      if (path.endsWith("/editor")) return response(editor);
      if (path.endsWith("/pricing-presets")) return response({ presets: [{ id: "preset-1", code: "01", name: "Escolar", label: "01 — Escolar", version: 1, active: true, tiers: sales.tiers }] });
      if (path.includes("/pricing-presets/preset-1/quote")) return response({ quantity: 60, parcels: [{ minimum_quantity: 1, maximum_quantity: 30, quantity: 30, unit_price_cents: 700, subtotal_cents: 21000 }, { minimum_quantity: 31, maximum_quantity: null, quantity: 30, unit_price_cents: 600, subtotal_cents: 18000 }], base_total_cents: 42000, savings_cents: 3000, total_cents: 39000 });
      return response(sales);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<GalleryEditor sourceId="source-1" step="vendas" />);

    expect(await screen.findByRole("option", { name: "01 — Escolar" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Simular valor" }));
    expect(await screen.findByText(/60 fotos.*R\$\s*390,00/)).toBeTruthy();
    expect(screen.getByText(/Economia de R\$\s*30,00/)).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledWith("/api/admin/pricing-presets/preset-1/quote?quantity=60", expect.anything());
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
    const details = { available: true, capabilities: ["cover", "title"], font_options: [{ token: "system-sans", label: "Sistema", category: "sans", css_family: "var(--font-system-sans)" }], cover_options: [], settings: { cover_photo_id: null, cover_preview_url: null, cover_title_font: "system-sans", cover_title_color: "#FFFFFF", cover_title_size: 32, cover_title_position: "bottom-left" } };
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (init?.method === "PATCH") return response({});
      return path.endsWith("/editor") ? response(editor) : response(details);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<GalleryEditor sourceId="source-1" step="detalhes" />);
    expect(await screen.findByRole("heading", { name: "Detalhes e apresentação" })).toBeTruthy();
    expect(screen.getByLabelText("Tipografia do título")).toBeInstanceOf(HTMLSelectElement);
    expect(screen.queryByLabelText("Tipografia da marca-d’água")).toBeNull();
    expect(screen.getByText(/marca-d’água continua global/i)).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Tamanho do título"), { target: { value: "40" } });
    fireEvent.click(screen.getByRole("button", { name: "Salvar e avançar →" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/admin/parent-galleries/source-1/settings",
      expect.objectContaining({ method: "PATCH", body: expect.stringContaining('"cover_title_size":40') }),
    ));
    expect(screen.getByRole("link", { name: /Ajustes/ }).getAttribute("href")).toBe("/admin/galleries/sources/source-1/edit/ajustes");
    expect(screen.getByRole("link", { name: /Clientes/ }).getAttribute("href")).toBe("/admin/galleries/sources/source-1/edit/clientes");
  });

  it("mantém a etapa Detalhes focada em capa e título, sem Organização ou proteção local", async () => {
    const details = { available: true, capabilities: ["cover", "title"], font_options: [{ token: "handwritten-caveat", label: "Caveat", category: "handwritten", css_family: "var(--font-handwritten-caveat)" }], cover_options: [], settings: { cover_photo_id: null, cover_preview_url: null, cover_title_font: "handwritten-caveat", cover_title_color: "#FFFFFF", cover_title_size: 32, cover_title_position: "bottom-left" } };
    vi.stubGlobal("fetch", vi.fn((path: string) => path.endsWith("/editor") ? response(editor) : response(details)));
    render(<GalleryEditor sourceId="source-1" step="detalhes" />);
    await screen.findByRole("heading", { name: "Detalhes e apresentação" });
    expect(screen.getByRole("group", { name: "Capa e título" })).toBeTruthy();
    expect(screen.queryByRole("group", { name: "Organização" })).toBeNull();
    expect(screen.queryByRole("group", { name: "Marca-d’água" })).toBeNull();
    expect(screen.getByText(/Envie uma capa para visualizar o título/)).toBeTruthy();
    expect(screen.getByRole("option", { name: /Caveat.*Manuscrita/ })).toBeTruthy();
    expect(screen.queryByLabelText(/css/i)).toBeNull();
  });

  it("escolhe uma capa pronta e atualiza a prévia de título de forma reativa", async () => {
    const details = { available: true, capabilities: ["cover", "title"], font_options: [{ token: "system-sans", label: "Sistema", category: "sans", css_family: "var(--font-system-sans)" }, { token: "handwritten-caveat", label: "Caveat", category: "handwritten", css_family: "var(--font-handwritten-caveat)" }], cover_options: [{ id: "cover-1", name: "CAPA.jpg", source: "cover_assets", status: "ready", preview_url: "/admin/photo-assets/cover-1/watermarked-preview", width: 1600, height: 1067 }], settings: { cover_photo_id: "cover-1", cover_preview_url: "/admin/photo-assets/cover-1/watermarked-preview", cover_title_font: "system-sans", cover_title_color: "#FFFFFF", cover_title_size: 32, cover_title_position: "bottom-left" } };
    const fetchMock = vi.fn((path: string, init?: RequestInit) => path.endsWith("/editor") ? response(editor) : path.endsWith("/cover") && init?.method === "PUT" ? response({ photo_id: "cover-1" }) : response(details));
    vi.stubGlobal("fetch", fetchMock);
    render(<GalleryEditor sourceId="source-1" step="detalhes" />);

    const coverButton = (await screen.findByText("CAPA.jpg")).closest("button") as HTMLButtonElement;
    coverButton.focus();
    expect(document.activeElement).toBe(coverButton);
    fireEvent.click(coverButton);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/admin/parent-galleries/source-1/cover",
      expect.objectContaining({ method: "PUT", body: JSON.stringify({ photo_id: "cover-1" }) }),
    ));
    fireEvent.change(screen.getByLabelText("Tipografia do título"), { target: { value: "handwritten-caveat" } });
    fireEvent.change(screen.getByLabelText("Cor do título"), { target: { value: "#112233" } });
    const previewTitle = screen.getByText("Festa escolar", { selector: ".gallery-customization-preview-image strong" });
    expect(previewTitle.getAttribute("style")).toContain("--font-handwritten-caveat");
    expect(previewTitle.getAttribute("style")).toContain("rgb(17, 34, 51)");
    expect(screen.getByAltText("Prévia protegida da capa da galeria")).toBeTruthy();
  });

  it("envia uma capa dedicada pelo pipeline e mantém o editor utilizável em falha", async () => {
    let uploadFails = true;
    const details = { available: true, capabilities: ["cover", "title"], font_options: [], cover_options: [], settings: { cover_photo_id: null, cover_preview_url: null, cover_title_font: "system-sans", cover_title_color: "#FFFFFF", cover_title_size: 32, cover_title_position: "bottom-left" } };
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/editor")) return response(editor);
      if (path.endsWith("/cover-photos") && init?.method === "POST") return uploadFails ? response({ detail: "JPEG excede o limite permitido." }, 413) : response({ upload_url: "/admin/photo-assets/cover-2/source" }, 201);
      if (path.endsWith("/source") && init?.method === "PUT") return response({ status: "processing" }, 202);
      return response(details);
    });
    vi.stubGlobal("fetch", fetchMock);
    const { container } = render(<GalleryEditor sourceId="source-1" step="detalhes" />);
    await screen.findByRole("heading", { name: "Detalhes e apresentação" });
    const input = container.querySelector('input[type="file"][accept="image/jpeg"]') as HTMLInputElement;
    const file = new File(["jpeg"], "capa.jpg", { type: "image/jpeg" });

    fireEvent.change(input, { target: { files: [file] } });
    expect(await screen.findByText("JPEG excede o limite permitido.")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Enviar imagem de capa" })).toBeTruthy();

    uploadFails = false;
    fireEvent.change(input, { target: { files: [file] } });
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/admin/photo-assets/cover-2/source",
      expect.objectContaining({ method: "PUT", body: file }),
    ));
    expect(await screen.findByText(/Capa enviada para processamento/)).toBeTruthy();
  });

  it("mantém Imagens focada em pastas e upload", async () => {
    const fetchMock = vi.fn((path: string) => path.endsWith("/editor") ? response(editor) : path.endsWith("/folders") ? response({ folders: [] }) : response({ clients: [] }));
    vi.stubGlobal("fetch", fetchMock);
    render(<GalleryEditor sourceId="source-1" step="imagens" />);
    await screen.findByRole("heading", { name: "Imagens e pastas" });
    expect(screen.queryByRole("group", { name: "Capa e título" })).toBeNull();
    expect(screen.getByRole("group", { name: "Organização das pastas" })).toBeTruthy();
    expect(screen.getByLabelText("Nome da nova pasta")).toBeTruthy();
    expect(fetchMock.mock.calls.some(([path]) => String(path).includes("/clients"))).toBe(false);
  });

  it("salva Organização na etapa Imagens e representa os dois modos na prévia", async () => {
    let mode = "individual";
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/editor")) return response({ ...editor, gallery: { ...editor.gallery, folder_display_mode: mode } });
      if (path.endsWith("/settings") && init?.method === "PATCH") {
        mode = JSON.parse(String(init.body)).folder_display_mode;
        return response({ folder_display_mode: mode });
      }
      return response({ folders: [] });
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<GalleryEditor sourceId="source-1" step="imagens" />);

    expect(await screen.findByLabelText("Prévia com pastas lado a lado")).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Exibição das pastas"), { target: { value: "sequential" } });
    expect(await screen.findByLabelText("Prévia em sequência cronológica")).toBeTruthy();
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/admin/parent-galleries/source-1/settings",
      expect.objectContaining({ method: "PATCH", body: JSON.stringify({ folder_display_mode: "sequential" }) }),
    ));
  });

  it("distingue estados e publica somente a rodada pronta sem consultar clientes", async () => {
    const folder = { id: "folder-1", name: "Rodada incremental", status: "released", position: 0, photo_count: 4, preview_url: "/admin/photo-assets/photo-ready/watermarked-preview", released_at: "2026-09-01T00:00:00Z", publication_counts: { published: 1, ready_to_publish: 1, processing: 1, failed: 1 } };
    const photos = [
      { id: "photo-published", name: "PUBLICADA.jpg", preview_url: "/p1", status: "completed", publication_state: "published", error: null, can_delete: true, is_cover: false },
      { id: "photo-ready", name: "PRONTA.jpg", preview_url: "/p2", status: "completed", publication_state: "ready_to_publish", error: null, can_delete: true, is_cover: false },
      { id: "photo-processing", name: "PROCESSANDO.jpg", preview_url: null, status: "processing", publication_state: "processing", error: null, can_delete: true, is_cover: false },
      { id: "photo-failed", name: "FALHA.jpg", preview_url: null, status: "failed", publication_state: "failed", error: "Falha sanitizada", can_delete: true, is_cover: false },
    ];
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/editor")) return response(editor);
      if (path.endsWith("/folders")) return response({ folders: [folder] });
      if (path.endsWith("/photos")) return response({ photos });
      if (path.endsWith("/publish") && init?.method === "POST") return response({ published_count: 1, pending_count: 1, failed_count: 1 });
      return response({});
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<GalleryEditor sourceId="source-1" step="imagens" />);

    const folderCard = (await screen.findByText("Rodada incremental")).closest("article") as HTMLElement;
    expect(folderCard.className).toContain("has-failures");
    expect(within(folderCard).getByText("1 publicadas")).toBeTruthy();
    expect(within(folderCard).getByText("1 prontas")).toBeTruthy();
    expect(within(folderCard).getByText("1 processando")).toBeTruthy();
    expect(within(folderCard).getByText("1 falhas")).toBeTruthy();
    fireEvent.click(within(folderCard).getByRole("button"));
    expect(await screen.findByText("Pronta para publicar")).toBeTruthy();
    expect(screen.getByText("Falha sanitizada")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Publicar novas fotos prontas" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/admin/photo-folders/folder-1/publish",
      expect.objectContaining({ method: "POST", body: "{}" }),
    ));
    expect(await screen.findByText(/1 foto\(s\) publicada\(s\)/)).toBeTruthy();
    expect(fetchMock.mock.calls.some(([path]) => String(path).includes("/clients"))).toBe(false);
  });

  it("publica a rodada pronta ao salvar Imagens e não avança com processamento ou falha", async () => {
    const folder = { id: "folder-1", name: "Rodada", status: "preparing", position: 0, photo_count: 3, preview_url: null, released_at: null, publication_counts: { published: 0, ready_to_publish: 1, processing: 1, failed: 1 } };
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/editor")) return response(editor);
      if (path.endsWith("/folders")) return response({ folders: [folder] });
      if (path.endsWith("/publish-ready") && init?.method === "POST") return response({ published_count: 1, pending_count: 1, failed_count: 1, available_count: 1, folders: [] });
      return response({});
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<GalleryEditor sourceId="source-1" step="imagens" />);

    fireEvent.click(await screen.findByRole("button", { name: "Salvar e avançar →" }));
    expect(await screen.findByText(/Ainda há 1 em processamento e 1 com falha/)).toBeTruthy();
    expect(push).not.toHaveBeenCalled();
  });

  it("abre somente uma pasta válida recebida pelo resumo", async () => {
    const folder = { id: "folder-valid", name: "Pasta válida", status: "released", position: 0, photo_count: 0, preview_url: null, released_at: null, publication_counts: { published: 0, ready_to_publish: 0, processing: 0, failed: 0 } };
    const fetchMock = vi.fn((path: string) => path.endsWith("/editor") ? response(editor) : path.endsWith("/folders") ? response({ folders: [folder] }) : path.includes("folder-valid/photos") ? response({ photos: [] }) : response({ detail: "não deveria consultar" }, 500));
    vi.stubGlobal("fetch", fetchMock);
    const { unmount } = render(<GalleryEditor sourceId="source-1" step="imagens" initialFolderId="folder-manipulated" />);
    await screen.findByText("Pasta válida");
    expect(fetchMock.mock.calls.some(([path]) => String(path).includes("folder-manipulated/photos"))).toBe(false);
    unmount();

    render(<GalleryEditor sourceId="source-1" step="imagens" initialFolderId="folder-valid" />);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/admin/photo-folders/folder-valid/photos", expect.anything()));
    expect(await screen.findByRole("heading", { name: "Pasta válida" })).toBeTruthy();
  });

  it("renderiza o resumo com capa clicável, estado do link e exclusão contextual", async () => {
    const fetchMock = vi.fn((path: string) => path.endsWith("/folders")
      ? response({ folders: [{ id: "folder-1", name: "Lote inicial", status: "preparing", photo_count: 2, preview_url: "/admin/photo-assets/photo-1/watermarked-preview" }] })
      : response({ name: "Evento completo", event_name: "Festa 2026", active: true, unlisted_link: null, public_link_status: "active", cover_preview_url: "/admin/photo-assets/photo-1/watermarked-preview", counts: { folders: 1, photos: 2, clients: 1 }, clients: [{ client_id: "client-1", name: "Ana Resumo", phone: "+5511999990000", registration_status: "active", derived_gallery_id: "private-1", available_count: 4, selected_count: 2, purchased_count: 1, gallery_status: "active", commercial_status: "awaiting_payment" }] }));
    vi.stubGlobal("fetch", fetchMock);
    render(<SourceGalleryDetailPage />);
    expect(await screen.findByRole("heading", { name: "Evento completo" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Capa protegida da galeria" }).getAttribute("href")).toBe("/admin/galleries/sources/source-1/preview");
    expect(screen.getByText("ativo")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Abrir pasta Lote inicial" }).getAttribute("href")).toBe("/admin/galleries/sources/source-1/edit/imagens?folder=folder-1");
    expect(screen.getByRole("article", { name: "Cliente Ana Resumo" })).toBeTruthy();
    expect(screen.getByText("Aguardando pagamento")).toBeTruthy();
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

  it("mostra dentro da confirmação quando o backend impede excluir a Galeria pública", async () => {
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/folders")) return response({ folders: [] });
      if (path.endsWith("/summary")) return response({ name: "Evento protegido", event_name: "Festa", active: true, unlisted_link: null, public_link_status: "active", cover_preview_url: null, counts: { folders: 0, photos: 0, clients: 0 }, clients: [] });
      if (path.endsWith("/deletion-inventory")) return response({ operation_type: "delete_parent_gallery", target: { id: "source-1", name: "Evento protegido" }, inventory: { remove: {}, preserve: { orders: 1 } }, consequences: { private_galleries_preserved: true, private_referenced_photos_preserved: true, clients_preserved: true, commercial_history_preserved: true, restoration_available_after_start: false } });
      if (path === "/api/admin/parent-galleries/source-1" && init?.method === "DELETE") return response({ detail: "Pagamento comunicado aguarda revisão administrativa." }, 409);
      return response({});
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<SourceGalleryDetailPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Excluir Galeria pública" }));
    fireEvent.click(await screen.findByRole("button", { name: "Excluir Evento protegido" }));
    const dialog = await screen.findByRole("dialog", { name: "Excluir “Evento protegido”?" });
    expect(await within(dialog).findByRole("alert")).toHaveProperty("textContent", "Pagamento comunicado aguarda revisão administrativa.");
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
