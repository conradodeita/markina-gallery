import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import PlatformConsole from "./page";
import { PUSH_LOGOUT_EVENT } from "../../push-device";

vi.mock("./photographer-terms-editor", () => ({ PhotographerTermsEditor: () => null }));

const observed = "2026-11-03T15:00:00Z";
const tenant = { tenant_id: "00000000-0000-4000-8000-000000000100", status: "active", lifecycle: "open", canonical_host: null, canonical_host_status: null, admin_email: "synthetic@example.test" };
const json = (data: unknown, status = 200) => Promise.resolve(new Response(JSON.stringify(data), { status, headers: { "Content-Type": "application/json" } }));
const unknownSources: Array<{ key: string; state: string; availability: string; source: string | null; scope: string;
  observed_at: string | null; connection_updated_at?: string | null; quota_limit: string | null;
  quota_usage: string | null; quota_observed_at: string | null }> = ["backup", "drive", "archive", "restore"].map((key) => ({
  key, state: "unknown", availability: "unknown", source: key === "drive" ? "application_database.google_drive_connection" : null,
  scope: key === "drive" ? "platform_owner" : "platform", observed_at: key === "drive" ? observed : null,
  quota_limit: null, quota_usage: null, quota_observed_at: null,
}));

afterEach(() => {
  cleanup(); vi.unstubAllGlobals();
  Reflect.deleteProperty(window, "gapi");
  Reflect.deleteProperty(window, "google");
  document.getElementById("google-drive-picker-api")?.remove();
});

async function openPickerInConsole() {
  vi.resetModules();
  const Console = (await import("./page")).default;
  let callback: (data: Record<string, unknown>) => void = () => undefined;
  let resolveAccess: (response: Response) => void = () => undefined;
  const dialog = { setVisible: vi.fn() };
  const view = {
    setMimeTypes() { return this; }, setIncludeFolders() { return this; },
    setSelectFolderEnabled() { return this; }, setParent() { return this; },
    setMode() { return this; },
  };
  const builder = {
    addView() { return this; }, setOAuthToken() { return this; },
    setDeveloperKey() { return this; }, setAppId() { return this; },
    setTitle() { return this; }, setLocale() { return this; },
    setMaxItems() { return this; }, setOrigin() { return this; },
    setCallback(value: typeof callback) { callback = value; return this; },
    build() { return dialog; },
  };
  Object.defineProperty(window, "gapi", { configurable: true,
    value: { load: (_name: string, ready: () => void) => ready() } });
  Object.defineProperty(window, "google", { configurable: true, value: { picker: {
    Action: { PICKED: "picked", CANCEL: "cancel", ERROR: "error" },
    Response: { ACTION: "action", DOCUMENTS: "docs" },
    Document: { ID: "id", NAME: "name", MIME_TYPE: "mimeType" },
    ViewId: { DOCS: "docs" }, DocsViewMode: { LIST: "list" },
    DocsView: function () { return view; }, PickerBuilder: function () { return builder; },
  } } });
  const connected = unknownSources.map((source) => source.key === "drive"
    ? { ...source, availability: "authorization_recorded" } : source);
  const fetcher = mockApi(true, connected);
  let capabilityCalls = 0;
  fetcher.mockImplementation((input) => {
    const path = String(input);
    if (path.endsWith("/capabilities")) {
      if (++capabilityCalls === 1) return json({ read_console: true });
      return new Promise<Response>((resolve) => { resolveAccess = resolve; });
    }
    if (path.endsWith("/sources")) return json({ items: connected });
    if (path.endsWith("/picker/session")) return json({
      access_token: "synthetic-short-token", scope: "https://www.googleapis.com/auth/drive.file",
      expires_in: 900, developer_key: `AIza${"x".repeat(35)}`, project_number: "123456789012",
      expected_parent_folder_id: "synthetic-parent",
    });
    return json({}, 403);
  });
  render(<Console />);
  fireEvent.change(await screen.findByLabelText("Senha atual do proprietário"), { target: { value: "synthetic-password" } });
  fireEvent.change(screen.getByLabelText("Código atual do autenticador"), { target: { value: "123456" } });
  fireEvent.click(screen.getByRole("button", { name: "Selecionar pasta global" }));
  await waitFor(() => expect(document.getElementById("google-drive-picker-api")).toBeTruthy());
  fireEvent.load(document.getElementById("google-drive-picker-api")!);
  await waitFor(() => expect(dialog.setVisible).toHaveBeenCalledWith(true));
  return {
    dialog, fetcher,
    fail: () => act(() => callback({ action: "error", error: "synthetic-private-provider-detail" })),
    select: () => act(() => callback({ action: "picked", docs: [{
      id: "synthetic-folder-id", name: "Pick-your-Pic Global", mimeType: "application/vnd.google-apps.folder",
    }] })),
    resolveAccess: async (allowed: boolean, status = 200) => {
      await act(async () => { resolveAccess(new Response(JSON.stringify({ read_console: allowed }), { status })); });
    },
  };
}

function mockApi(readConsole = true, sources = unknownSources) {
  const fetcher = vi.fn<(input: RequestInfo | URL, init?: RequestInit) => Promise<Response>>((input) => {
    const path = String(input);
    if (path.endsWith("/capabilities")) return json({ read_console: readConsole });
    if (path.endsWith("/sources")) return json({ items: sources });
    if (path.includes("/tenants?")) return json({ items: [tenant], has_more: false, observed_at: observed });
    return json({ tenant_id: tenant.tenant_id, status: "active", lifecycle: "open", canonical_host: null, canonical_host_status: null, gallery_count: 2, photo_count: 7, observed_at: observed });
  });
  vi.stubGlobal("fetch", fetcher);
  return fetcher;
}

describe("console privado da plataforma", () => {
  it.each(["antes", "durante"])("preserva a pasta recebida %s da revalidação de foco positiva", async (timing) => {
    const picker = await openPickerInConsole();
    if (timing === "antes") picker.select();
    fireEvent(window, new Event("focus"));
    expect(screen.getByText("Verificando acesso")).toBeTruthy();
    const gate = screen.getByRole("region", { name: "Destino global de backup", hidden: true }).closest("[hidden]");
    expect(gate?.hasAttribute("inert")).toBe(true);
    if (timing === "durante") picker.select();
    expect(screen.queryByRole("button", { name: "Autorizar esta pasta" })).toBeNull();
    await picker.resolveAccess(true);
    expect(await screen.findByText(/Pasta selecionada:/)).toBeTruthy();
    expect((screen.getByRole("button", { name: "Autorizar esta pasta" }) as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByLabelText("Senha atual do proprietário") as HTMLInputElement).value).toBe("");
    expect((screen.getByLabelText("Novo código do autenticador") as HTMLInputElement).value).toBe("");
    expect(picker.fetcher.mock.calls.filter(([path]) => String(path).endsWith("/capabilities"))).toHaveLength(2);
    expect(picker.fetcher.mock.calls.filter(([path]) => String(path).endsWith("/sources"))).toHaveLength(1);
    expect(picker.fetcher.mock.calls.some(([path]) => String(path).endsWith("/picker/authorize"))).toBe(false);
    expect(document.body.textContent).not.toContain("synthetic-short-token");
  });

  it("preserva o erro sanitizado do Picker durante a revalidação positiva", async () => {
    const picker = await openPickerInConsole();
    fireEvent(window, new Event("focus"));
    picker.fail();
    expect(screen.queryByRole("alert")).toBeNull();
    await picker.resolveAccess(true);
    expect((await screen.findByRole("alert")).textContent).toContain("O Google Drive não conseguiu concluir a seleção.");
    expect(document.body.textContent).not.toContain("synthetic-private-provider-detail");
    expect(screen.queryByText(/Pasta selecionada:/)).toBeNull();
    expect(picker.fetcher.mock.calls.some(([path]) => String(path).endsWith("/picker/authorize"))).toBe(false);
  });

  it.each(["recusa", "falha", "logout"])("descarta o Picker em %s e ignora callback e resposta tardios", async (result) => {
    const picker = await openPickerInConsole();
    fireEvent(window, new Event("focus"));
    if (result === "logout") {
      fireEvent(window, new Event(PUSH_LOGOUT_EVENT));
    } else {
      await picker.resolveAccess(false, result === "falha" ? 503 : 200);
    }
    expect(await screen.findByText("Console indisponível")).toBeTruthy();
    expect(picker.dialog.setVisible).toHaveBeenLastCalledWith(false);
    picker.select();
    if (result === "logout") await picker.resolveAccess(true);
    expect(screen.queryByRole("region", { name: "Destino global de backup" })).toBeNull();
    expect(screen.queryByText(/Pasta selecionada:/)).toBeNull();
    expect(picker.fetcher.mock.calls.some(([path]) => String(path).endsWith("/picker/authorize"))).toBe(false);
  });

  it("nega a área sem consultar diretório ou fontes quando não há propriedade", async () => {
    const fetcher = mockApi(false);
    render(<PlatformConsole />);
    expect(await screen.findByText("Console indisponível")).toBeTruthy();
    expect(screen.queryByLabelText("Senha atual do proprietário")).toBeNull();
    expect(fetcher.mock.calls.map(([path]) => String(path))).toEqual(["/api/admin/platform/console/capabilities"]);
  });

  it("inicia limpo, consulta explicitamente e apresenta somente o resumo selecionado", async () => {
    const fetcher = mockApi();
    render(<PlatformConsole />);
    await screen.findByRole("heading", { name: "Fotógrafos" });
    expect(fetcher.mock.calls.some(([path]) => String(path).includes("/tenants"))).toBe(false);
    fireEvent.change(screen.getByLabelText("Organização"), { target: { value: "all" } });
    fireEvent.click(screen.getByRole("button", { name: "Pesquisar" }));
    await screen.findByText(tenant.admin_email);
    expect(await screen.findByLabelText("Senha atual do proprietário")).toBeTruthy();
    expect(fetcher.mock.calls.some(([path]) => String(path).includes("mode=all"))).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: `Consultar ${tenant.admin_email}` }));
    expect(await screen.findByText("Galerias: 2 · Fotografias: 7")).toBeTruthy();
    expect(await screen.findByText(/Sem registro de conexão; quota desconhecida/)).toBeTruthy();
    expect(screen.getByText(/Registro consultado em/)).toBeTruthy();
    expect(screen.getByText(/Backup, arquivo e restauração: sem fonte integrada; estado desconhecido/)).toBeTruthy();
    expect(screen.queryByText(/backup saudável/i)).toBeNull();
  });

  it("distingue autorização Drive persistida de saúde atual e apresenta a última quota salva", async () => {
    const connectedSources = unknownSources.map((source) => source.key === "drive" ? {
      ...source, state: "connected", availability: "authorization_recorded", connection_updated_at: observed,
      quota_limit: "109951162777600", quota_usage: "54975581388800", quota_observed_at: observed,
    } : source);
    const fetcher = mockApi(true, connectedSources);
    render(<PlatformConsole />);
    expect(await screen.findByText("Autorização registrada")).toBeTruthy();
    expect(screen.getByRole("region", { name: "Destino global de backup" })).toBeTruthy();
    expect((screen.getByRole("button", { name: "Selecionar pasta global" }) as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByLabelText("Senha atual do proprietário")).toBeTruthy();
    expect(fetcher.mock.calls.some(([path]) => String(path).includes("/picker/"))).toBe(false);
    expect(screen.getByText(/A disponibilidade atual do Drive não foi verificada/)).toBeTruthy();
    expect(screen.getByText(/50 TiB usados de 100 TiB/)).toBeTruthy();
    expect(screen.queryByText(/Drive saudável|Drive disponível/i)).toBeNull();
  });

  it("só libera hostname reservado após hash, confirmação e reautenticação", async () => {
    const reservedDetail = { ...tenant, canonical_host: "synthetic.pickyourpic.com.br", canonical_host_status: "reserved",
      gallery_count: 2, photo_count: 7, observed_at: observed };
    let currentDetail = reservedDetail;
    let activationInit: RequestInit | undefined;
    const fetcher = mockApi();
    fetcher.mockImplementation((input, init) => {
      const path = String(input);
      if (path.endsWith(`/tenants/${tenant.tenant_id}/hostname/activate`)) {
        activationInit = init;
        currentDetail = { ...reservedDetail, canonical_host_status: "ready" };
        return json({ tenant_id: tenant.tenant_id, canonical_host: currentDetail.canonical_host,
          canonical_host_status: "ready", replayed: false });
      }
      if (path.endsWith(`/tenants/${tenant.tenant_id}`)) return json(currentDetail);
      if (path.endsWith("/capabilities")) return json({ read_console: true });
      if (path.endsWith("/sources")) return json({ items: unknownSources });
      if (path.includes("/tenants?")) return json({ items: [tenant], has_more: false, observed_at: observed });
      return json({});
    });
    render(<PlatformConsole />);
    await screen.findByRole("heading", { name: "Fotógrafos" });
    fireEvent.change(screen.getByLabelText("Organização"), { target: { value: "all" } });
    fireEvent.click(screen.getByRole("button", { name: "Pesquisar" }));
    await screen.findByText(tenant.admin_email);
    fireEvent.click(screen.getByRole("button", { name: `Consultar ${tenant.admin_email}` }));
    expect(await screen.findByText("Status do endereço: Reservado; aguardando liberação")).toBeTruthy();
    const submit = screen.getByRole("button", { name: "Confirmar liberação do endereço" }) as HTMLButtonElement;
    expect(submit.disabled).toBe(true);
    const hash = "a".repeat(64);
    fireEvent.change(screen.getByLabelText("SHA-256 do relatório operacional"), { target: { value: hash.toUpperCase() } });
    fireEvent.click(screen.getByLabelText("Confirmo que revisei o relatório para este endereço"));
    fireEvent.change(screen.getByLabelText("Senha do proprietário para esta liberação"), { target: { value: "synthetic-password" } });
    fireEvent.change(screen.getByLabelText("Código do autenticador para esta liberação"), { target: { value: "123456" } });
    expect(submit.disabled).toBe(false);
    fireEvent.click(submit);
    await screen.findByText("Status do endereço: Pronto para uso");
    expect(activationInit?.method).toBe("POST");
    expect(JSON.parse(String(activationInit?.body))).toMatchObject({
      expected_hostname: "synthetic.pickyourpic.com.br", expected_status: "reserved",
      evidence_sha256: hash, confirm_readiness: true, current_password: "synthetic-password", totp_code: "123456",
    });
  });

  it("limpa a atestação e as credenciais ao consultar outro fotógrafo", async () => {
    const first = { ...tenant, photographer_name: "Fotógrafa A", canonical_host: "first.pickyourpic.com.br",
      canonical_host_status: "reserved", gallery_count: 1, photo_count: 2, observed_at: observed };
      const second = { ...first, tenant_id: "00000000-0000-4000-8000-000000000101", photographer_name: "Fotógrafa B",
      admin_email: "second@example.test", canonical_host: "second.pickyourpic.com.br" };
    const fetcher = mockApi();
    fetcher.mockImplementation((input) => {
      const path = String(input);
      if (path.endsWith("/capabilities")) return json({ read_console: true });
      if (path.endsWith("/sources")) return json({ items: unknownSources });
      if (path.includes("/tenants?")) return json({ items: [first, second], has_more: false, observed_at: observed });
      return json(path.endsWith(second.tenant_id) ? second : first);
    });
    render(<PlatformConsole />);
    await screen.findByRole("heading", { name: "Fotógrafos" });
    fireEvent.change(screen.getByLabelText("Organização"), { target: { value: "all" } });
    fireEvent.click(screen.getByRole("button", { name: "Pesquisar" }));
    await screen.findByRole("button", { name: `Consultar ${first.admin_email}` });
    fireEvent.click(screen.getByRole("button", { name: `Consultar ${first.admin_email}` }));
    await screen.findByText(`Endereço do fotógrafo: ${first.canonical_host}`);
    fireEvent.change(screen.getByLabelText("SHA-256 do relatório operacional"), { target: { value: "a".repeat(64) } });
    fireEvent.click(screen.getByLabelText("Confirmo que revisei o relatório para este endereço"));
    fireEvent.change(screen.getByLabelText("Senha do proprietário para esta liberação"), { target: { value: "synthetic" } });
    fireEvent.change(screen.getByLabelText("Código do autenticador para esta liberação"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: `Consultar ${second.admin_email}` }));
    await screen.findByText(`Endereço do fotógrafo: ${second.canonical_host}`);
    expect((screen.getByLabelText("SHA-256 do relatório operacional") as HTMLInputElement).value).toBe("");
    expect((screen.getByLabelText("Confirmo que revisei o relatório para este endereço") as HTMLInputElement).checked).toBe(false);
    expect((screen.getByLabelText("Senha do proprietário para esta liberação") as HTMLInputElement).value).toBe("");
    expect((screen.getByLabelText("Código do autenticador para esta liberação") as HTMLInputElement).value).toBe("");
    expect((screen.getByRole("button", { name: "Confirmar liberação do endereço" }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("remove os dados quando uma consulta perde autorização", async () => {
    const fetcher = mockApi();
    render(<PlatformConsole />);
    await screen.findByRole("heading", { name: "Fotógrafos" });
    fireEvent.change(screen.getByLabelText("Nome ou e-mail do fotógrafo"), { target: { value: "synthetic" } });
    fireEvent.click(screen.getByRole("button", { name: "Pesquisar" }));
    await screen.findByText(tenant.admin_email);
    fetcher.mockImplementation((input) => String(input).includes("/tenants/") ? json({ detail: "Acesso não autorizado." }, 403) : json({ read_console: true }));
    fireEvent.click(screen.getByRole("button", { name: `Consultar ${tenant.admin_email}` }));
    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(screen.queryByText(tenant.admin_email)).toBeNull();
  });

  it("revalida ao retornar à janela e descarta uma resposta antiga em voo", async () => {
    const fetcher = mockApi();
    let resolveOld: (response: Response) => void = () => undefined;
    fetcher.mockImplementation((input) => {
      const path = String(input);
      if (path.includes("/tenants?")) return new Promise<Response>((resolve) => { resolveOld = resolve; });
      if (path.endsWith("/sources")) return json({ items: [] });
      return json({ read_console: true });
    });
    render(<PlatformConsole />);
    await screen.findByRole("heading", { name: "Fotógrafos" });
    fireEvent.change(screen.getByLabelText("Organização"), { target: { value: "all" } });
    fireEvent.click(screen.getByRole("button", { name: "Pesquisar" }));
    fetcher.mockImplementation(() => json({ read_console: false }));
    fireEvent(window, new Event("focus"));
    await screen.findByText("Console indisponível");
    await act(async () => { resolveOld(new Response(JSON.stringify({ items: [tenant], has_more: false, observed_at: observed }))); });
    await waitFor(() => expect(screen.queryByText(tenant.admin_email)).toBeNull());
  });
});
