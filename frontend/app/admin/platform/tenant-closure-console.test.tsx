import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { TenantClosureConsole } from "./tenant-closure-console";

const tenantId = "00000000-0000-4000-8000-000000000100";
const closed = {
  tenant_id: tenantId,
  lifecycle: "closed",
  availability: "suspended",
  history_state: "available",
  closed_at: "2024-02-29T11:30:00+00:00",
  days_closed: 3649,
  review_at: "2034-02-28T11:30:00+00:00",
  review_due: false,
  reopen_blocker: null,
  previous_cycle: { closed_at: "2010-01-01T09:00:00+00:00", reopened_at: "2010-02-01T09:00:00+00:00" },
  batches: [] as Array<{ batch_id: string; state: string; duration_days: number; created_at: string; operations: Array<{ status: string }> }>,
  media_deletion: {
    eligible: false,
    blocker: "review_not_due",
    confirmation_phrase: "EXCLUIR MÍDIA PERMANENTEMENTE",
    review_due: false,
    batch: null,
    observed_at: "2034-02-28T11:29:00+00:00",
  },
  observed_at: "2034-02-28T11:29:00+00:00",
};
const json = (data: unknown, status = 200) => Promise.resolve(new Response(JSON.stringify(data), {
  status, headers: { "Content-Type": "application/json" },
}));

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe("console de encerramento da conta", () => {
  it("reduz o perfil somente após revisão, frase e reautenticação", async () => {
    let state = { ...closed, profile_retention: { state: "retained", eligible: true, blocker: null,
      confirmation_phrase: "REMOVER CPF E ENDEREÇO", reduced_at: null as string | null } };
    let submitted: Record<string, unknown> | null = null;
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input).endsWith("/profile-reduction")) {
        submitted = JSON.parse(String(init?.body));
        state = { ...state, profile_retention: { ...state.profile_retention, state: "reduced", eligible: false,
          reduced_at: "2034-02-28T11:30:00+00:00" } };
        return json({ state: "reduced", replayed: false });
      }
      return json(state);
    }));
    render(<TenantClosureConsole tenantId={tenantId} onUpdated={vi.fn()} />);
    const action = await screen.findByRole("button", { name: "Remover CPF e endereço do perfil" });
    expect(action).toHaveProperty("disabled", true);
    fireEvent.click(screen.getByLabelText(/Confirmei que não há disputa/));
    fireEvent.change(screen.getByLabelText("Digite REMOVER CPF E ENDEREÇO"), { target: { value: "REMOVER CPF E ENDEREÇO" } });
    fireEvent.change(screen.getByLabelText("Senha para reduzir o cadastro"), { target: { value: "SyntheticOwnerPassword!2026" } });
    fireEvent.change(screen.getByLabelText("Código do autenticador para reduzir o cadastro"), { target: { value: "123456" } });
    fireEvent.click(action);
    expect(await screen.findByText(/CPF e endereço não estão armazenados no perfil/)).toBeTruthy();
    expect(submitted).toMatchObject({ confirm_review: true, confirm_phrase: "REMOVER CPF E ENDEREÇO",
      current_password: "SyntheticOwnerPassword!2026", totp_code: "123456" });
    expect(screen.queryByText("SyntheticOwnerPassword!2026")).toBeNull();
    expect(screen.queryByRole("button", { name: "Remover CPF e endereço do perfil" })).toBeNull();
  });

  it("mostra falha de conexão em português sem revelar o erro de transporte", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new TypeError("synthetic internal transport detail"))));
    render(<TenantClosureConsole tenantId={tenantId} onUpdated={vi.fn()} />);
    expect(await screen.findByRole("alert")).toHaveProperty("textContent", expect.stringContaining("Confira sua conexão"));
    expect(screen.queryByText(/synthetic internal transport detail/)).toBeNull();
    expect(screen.queryByRole("button", { name: "Solicitar recuperação" })).toBeNull();
  });

  it.each([
    { ...closed, media_deletion: undefined },
    { ...closed, tenant_id: "00000000-0000-4000-8000-000000000999" },
  ])("oculta ações se a resposta está incompleta ou pertence a outra conta", async (response) => {
    vi.stubGlobal("fetch", vi.fn(() => json(response)));
    render(<TenantClosureConsole tenantId={tenantId} onUpdated={vi.fn()} />);
    expect(await screen.findByRole("alert")).toHaveProperty("textContent", expect.stringContaining("não pôde ser confirmado"));
    expect(screen.queryByRole("button", { name: "Solicitar recuperação" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Confirmar reabertura" })).toBeNull();
    expect(screen.queryByText("Há 3649 dias completos")).toBeNull();
  });

  it("mostra ciclo, contador e revisão em UTC sem dados do CPF", async () => {
    vi.stubGlobal("fetch", vi.fn(() => json(closed)));
    render(<TenantClosureConsole tenantId={tenantId} onUpdated={vi.fn()} />);
    expect(await screen.findByText("Há 3649 dias completos")).toBeTruthy();
    expect(screen.getByText(/28 de fev\. de 2034, 11:30 UTC/)).toBeTruthy();
    expect(screen.getByText(/Último ciclo/)).toBeTruthy();
    expect(screen.queryByText(/cpf|fingerprint|hmac/i)).toBeNull();
    expect(screen.queryByText(/identity_confirmation_required|restoration_pending/)).toBeNull();
  });

  it("envia recuperação autenticada, lista o lote e mantém separada a reabertura", async () => {
    let current = closed;
    let submitted: Record<string, unknown> | null = null;
    const fetcher = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path.endsWith("/closure/recovery-batches")) {
        submitted = JSON.parse(String(init?.body)) as Record<string, unknown>;
        current = { ...closed, batches: [{ batch_id: "batch-1", state: "processing", duration_days: 30,
          created_at: "2034-02-28T11:30:00+00:00", operations: [{ status: "queued" }, { status: "completed" }] }] };
        return json({ batch_id: "batch-1", state: "processing" }, 202);
      }
      return json(current);
    });
    vi.stubGlobal("fetch", fetcher);
    render(<TenantClosureConsole tenantId={tenantId} onUpdated={vi.fn()} />);

    fireEvent.change(await screen.findByLabelText("Prazo de acesso após a recuperação"), { target: { value: "30" } });
    fireEvent.click(screen.getByLabelText(/Entendo que a recuperação/));
    fireEvent.change(screen.getByLabelText("Senha para solicitar recuperação"), { target: { value: "SyntheticOwnerPassword!2026" } });
    fireEvent.change(screen.getByLabelText("Código do autenticador para solicitar recuperação"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Solicitar recuperação" }));

    expect(await screen.findByText("Em andamento")).toBeTruthy();
    expect(screen.getByText(/Prazo escolhido: 30 dias/)).toBeTruthy();
    expect(submitted).toMatchObject({ duration_days: 30, current_password: "SyntheticOwnerPassword!2026", totp_code: "123456" });
    expect(screen.queryByText("SyntheticOwnerPassword!2026")).toBeNull();
    expect(screen.queryByText("123456")).toBeNull();
    expect(screen.getByRole("button", { name: "Confirmar reabertura" })).toBeTruthy();
    const reopenCall = fetcher.mock.calls.find(([path]) => String(path).endsWith("/closure/reopen"));
    expect(reopenCall).toBeUndefined();
  });

  it("exige o fluxo de identidade depois do décimo aniversário e não oferece reabertura", async () => {
    vi.stubGlobal("fetch", vi.fn(() => json({ ...closed, review_due: true, reopen_blocker: "identity_confirmation_required" })));
    render(<TenantClosureConsole tenantId={tenantId} onUpdated={vi.fn()} />);
    expect(await screen.findByText(/revisão manual de dez anos está pendente/i)).toBeTruthy();
    expect(screen.getByText(/Conclua o atendimento em Recuperar acesso do fotógrafo/i)).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Confirmar reabertura" })).toBeNull();
  });

  it("reabre somente após confirmação e reautenticação em ação separada", async () => {
    let lifecycle = "closed";
    let reopenBody: Record<string, unknown> | null = null;
    const onUpdated = vi.fn();
    const fetcher = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path.endsWith("/closure/reopen")) {
        reopenBody = JSON.parse(String(init?.body)) as Record<string, unknown>;
        lifecycle = "open";
        return json({ lifecycle, availability: "suspended" });
      }
      return json({ ...closed, lifecycle, reopen_blocker: lifecycle === "closed" ? null : "not_closed" });
    });
    vi.stubGlobal("fetch", fetcher);
    render(<TenantClosureConsole tenantId={tenantId} onUpdated={onUpdated} />);

    fireEvent.click(await screen.findByLabelText(/Confirmo que a mídia foi recuperada/));
    fireEvent.change(screen.getByLabelText("Senha para reabrir a conta"), { target: { value: "SyntheticOwnerPassword!2026" } });
    fireEvent.change(screen.getByLabelText("Código do autenticador para reabrir a conta"), { target: { value: "654321" } });
    fireEvent.click(screen.getByRole("button", { name: "Confirmar reabertura" }));

    expect(await screen.findByText("Aberta")).toBeTruthy();
    expect(screen.getByText("Disponibilidade").parentElement?.textContent).toContain("Suspensa");
    expect(reopenBody).toMatchObject({ current_password: "SyntheticOwnerPassword!2026", totp_code: "654321" });
    expect(onUpdated).toHaveBeenCalledOnce();
    expect(fetcher.mock.calls.some(([path]) => String(path).endsWith("/closure/recovery-batches"))).toBe(false);
    expect(screen.queryByText("SyntheticOwnerPassword!2026")).toBeNull();
    expect(screen.queryByText("654321")).toBeNull();
  });

  it("explica o bloqueio da exclusão permanente sem expor nomes internos", async () => {
    vi.stubGlobal("fetch", vi.fn(() => json(closed)));
    render(<TenantClosureConsole tenantId={tenantId} onUpdated={vi.fn()} />);
    expect(await screen.findByText("O prazo de dez anos ainda não foi atingido.")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Excluir mídia fria" })).toBeNull();
    expect(screen.queryByText(/remote_delete|fingerprint|EXCLUIR MÍDIA PERMANENTEMENTE/)).toBeNull();
  });

  it("registra pedido de exclusão apenas com frase, confirmação e reautenticação", async () => {
    const eligible = {
      ...closed,
      media_deletion: { ...closed.media_deletion, eligible: true, blocker: null, review_due: true },
    };
    let current: unknown = eligible;
    let submitted: Record<string, unknown> | null = null;
    const fetcher = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path.endsWith("/closure/media-deletion")) {
        submitted = JSON.parse(String(init?.body)) as Record<string, unknown>;
        const queued = {
          ...eligible,
          media_deletion: {
            ...eligible.media_deletion,
            eligible: false,
            blocker: "deletion_already_requested",
            batch: {
              batch_id: "batch-deletion-1", state: "queued", object_count: 4,
              verified_deleted_object_count: 0, cycle_count: 2, retry_available: false,
              operations: [{ status: "queued", error_code: null }],
            },
          },
        };
        current = queued;
        return json(queued.media_deletion, 202);
      }
      return json(current);
    });
    vi.stubGlobal("fetch", fetcher);
    render(<TenantClosureConsole tenantId={tenantId} onUpdated={vi.fn()} />);

    fireEvent.click(await screen.findByLabelText(/Confirmo que entendo que a exclusão é permanente/));
    fireEvent.change(screen.getByLabelText(/Digite exatamente:/), { target: { value: "EXCLUIR MÍDIA PERMANENTEMENTE" } });
    fireEvent.change(screen.getByLabelText("Senha do proprietário"), { target: { value: "SyntheticOwnerPassword!2026" } });
    fireEvent.change(screen.getByLabelText("Código do autenticador"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Excluir mídia fria" }));

    expect(await screen.findByText(/Pedido registrado/)).toBeTruthy();
    expect(await screen.findByText("Na fila")).toBeTruthy();
    expect(submitted).toMatchObject({
      confirm_phrase: "EXCLUIR MÍDIA PERMANENTEMENTE",
      current_password: "SyntheticOwnerPassword!2026",
      totp_code: "123456",
    });
    expect(screen.getByText("Pastas").parentElement?.textContent).toContain("2");
    expect(screen.queryByText("SyntheticOwnerPassword!2026")).toBeNull();
    expect(screen.queryByText("123456")).toBeNull();
    expect(screen.queryByText(/batch-deletion-1/)).toBeNull();
  });

  it("permite retry reautenticado e mostra erro técnico em linguagem segura", async () => {
    const pending = {
      ...closed,
      reopen_blocker: "media_deletion_pending",
      media_deletion: {
        ...closed.media_deletion,
        blocker: "deletion_already_requested",
        batch: {
          batch_id: "private-batch-id", state: "attention_required", object_count: 2,
          verified_deleted_object_count: 1, cycle_count: 1, retry_available: true,
          operations: [{ status: "failed", error_code: "remote_delete_not_verified" }],
        },
      },
    };
    let current = pending;
    let submitted: Record<string, unknown> | null = null;
    const fetcher = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path.endsWith("/closure/media-deletion/retry")) {
        submitted = JSON.parse(String(init?.body)) as Record<string, unknown>;
        current = {
          ...pending,
          media_deletion: {
            ...pending.media_deletion,
            batch: { ...pending.media_deletion.batch, state: "queued", retry_available: false },
          },
        };
        return json(current.media_deletion, 202);
      }
      return json(current);
    });
    vi.stubGlobal("fetch", fetcher);
    render(<TenantClosureConsole tenantId={tenantId} onUpdated={vi.fn()} />);

    expect(await screen.findByText("Um arquivo ainda apareceu após a tentativa de remoção.")).toBeTruthy();
    fireEvent.click(screen.getByLabelText(/Revisei o estado parcial/));
    fireEvent.change(screen.getByLabelText(/Digite exatamente:/), { target: { value: "EXCLUIR MÍDIA PERMANENTEMENTE" } });
    fireEvent.change(screen.getByLabelText("Senha do proprietário"), { target: { value: "SyntheticOwnerPassword!2026" } });
    fireEvent.change(screen.getByLabelText("Código do autenticador"), { target: { value: "654321" } });
    fireEvent.click(screen.getByRole("button", { name: "Retomar exclusão" }));

    expect(await screen.findByText(/Nova tentativa registrada/)).toBeTruthy();
    expect(submitted).toMatchObject({
      confirm_phrase: "EXCLUIR MÍDIA PERMANENTEMENTE",
      current_password: "SyntheticOwnerPassword!2026",
      totp_code: "654321",
    });
    expect(fetcher.mock.calls.some(([path]) => String(path).endsWith("/closure/reopen"))).toBe(false);
    expect(screen.queryByText("private-batch-id")).toBeNull();
  });
});
