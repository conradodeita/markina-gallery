import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import PlatformConsole from "./page";

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
});

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
    expect(screen.getByText(/Estado do arquivo de mídia e da restauração indisponível/)).toBeTruthy();
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
    expect(screen.queryByRole("button", { name: "Selecionar pasta global" })).toBeNull();
    expect(fetcher.mock.calls.some(([path]) => String(path).includes("/picker/"))).toBe(false);
    expect(screen.getByText(/A disponibilidade atual do Drive não foi verificada/)).toBeTruthy();
    expect(screen.getByText(/50 TiB usados de 100 TiB/)).toBeTruthy();
    expect(screen.queryByText(/Drive saudável|Drive disponível/i)).toBeNull();
  });

  it("apresenta evidência local de uma cópia validada sem afirmar disponibilidade do destino", async () => {
    const backupSources = unknownSources.map((source) => source.key === "backup" ? {
      ...source, state: "current", availability: "current",
      source: "application_database.global_postgresql_backup_run", scope: "platform_owner",
      observed_at: observed, latest_run_status: "validated", latest_attempt_day: "2026-11-03",
      last_validated_day: "2026-11-03", last_validated_at: observed,
      snapshot_id: "a".repeat(32), dump_size_bytes: 4096, duration_ms: 1500,
    } : source);
    mockApi(true, backupSources);
    render(<PlatformConsole />);

    expect(await screen.findByText("Cópia global validada hoje")).toBeTruthy();
    expect(screen.getByText(/Último recibo validado: 2026-11-03/)).toBeTruthy();
    expect(screen.getByText(/Snapshot a{12}/)).toBeTruthy();
    expect(screen.getByText(/esta leitura não consulta a disponibilidade atual do destino remoto/i)).toBeTruthy();
  });

  it("mostra uma cópia anterior como desatualizada e mantém visível a última falha", async () => {
    const backupSources = unknownSources.map((source) => source.key === "backup" ? {
      ...source, state: "stale", availability: "stale",
      source: "application_database.global_postgresql_backup_run", scope: "platform_owner",
      observed_at: observed, latest_run_status: "failed", latest_attempt_day: "2026-11-04",
      last_validated_day: "2026-11-03", last_validated_at: observed,
      snapshot_id: "b".repeat(32), dump_size_bytes: 2048, duration_ms: 4000,
    } : source);
    mockApi(true, backupSources);
    render(<PlatformConsole />);

    expect(await screen.findByText("A última cópia validada está desatualizada")).toBeTruthy();
    expect(screen.getByText(/Estado da tentativa mais recente: falha · 2026-11-04/)).toBeTruthy();
  });

  it("mantém desconhecido quando não existe recibo local validado", async () => {
    const backupSources = unknownSources.map((source) => source.key === "backup" ? {
      ...source, state: "unknown", availability: "unknown", scope: "platform_owner",
      latest_run_status: "unknown", latest_attempt_day: "2026-11-05",
    } : source);
    const fetcher = mockApi(true, backupSources);
    render(<PlatformConsole />);

    expect(await screen.findByText("Estado desconhecido; nenhuma cópia validada foi confirmada")).toBeTruthy();
    expect(screen.queryByText(/Último recibo validado/)).toBeNull();
    expect(screen.queryByText(/Snapshot/)).toBeNull();
    expect(fetcher.mock.calls.some(([path]) => /restic|rclone|backup-run/i.test(String(path)))).toBe(false);
  });

  it("mostra backup indisponível sem expor detalhes de erro", async () => {
    const backupSources = unknownSources.map((source) => source.key === "backup" ? {
      ...source, state: "unavailable", availability: "unavailable", scope: "platform_owner",
      latest_run_status: "unknown", error_code: "synthetic_database_credential_detail",
    } : source);
    mockApi(true, backupSources);
    render(<PlatformConsole />);

    expect(await screen.findByText("Estado do backup indisponível")).toBeTruthy();
    expect(screen.queryByText(/synthetic_database_credential_detail/)).toBeNull();
    expect(screen.queryByText(/Último recibo validado/)).toBeNull();
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
