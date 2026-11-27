import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { OwnerMediaArchiveRecoveries, type OwnerRecovery } from "./owner-media-archive-recoveries";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

const failedRecovery: OwnerRecovery = {
  operation_id: "33333333-3333-4333-8333-333333333333",
  cycle_id: "11111111-1111-4111-8111-111111111111",
  folder_id: "22222222-2222-4222-8222-222222222222",
  folder_name: "Ensaio arquivado",
  status: "failed",
  stage: "downloading",
  duration_days: 14,
  fee_credits: 3,
  owner_exempt: false,
  requester_type: "tenant",
  retry_of_operation_id: null,
  last_error_code: "archive_read_failed",
  last_error: "Falha comprovada na operação; mídia preservada.",
  created_at: "2026-11-09T12:00:00Z",
  updated_at: "2026-11-09T12:05:00Z",
  completed_at: null,
};

describe("retry de arquivo frio no console do proprietário", () => {
  it("exibe erro sanitizado e exige senha mais TOTP para iniciar retry vinculado à falha", async () => {
    const fetcher = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) =>
      new Response(JSON.stringify({ operation_id: "retry-operation", status: "queued" }), {
        status: 202, headers: { "Content-Type": "application/json" },
      }));
    vi.stubGlobal("fetch", fetcher);
    vi.stubGlobal("crypto", { randomUUID: () => "synthetic-owner-retry" });
    const updated = vi.fn();
    render(<OwnerMediaArchiveRecoveries tenantId="tenant-one" items={[failedRecovery]} onUpdated={updated} />);

    expect(screen.getByText(/archive_read_failed/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
    fireEvent.change(screen.getByRole("combobox", { name: "Operação com falha" }), {
      target: { value: failedRecovery.operation_id },
    });
    expect(screen.getByText("Prazo do pedido original: 14 dias.")).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Senha atual do proprietário"), { target: { value: "synthetic-password" } });
    fireEvent.change(screen.getByLabelText("Código do autenticador"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Confirmar retry" }));

    expect(await screen.findByRole("status")).toBeTruthy();
    const [path, init] = fetcher.mock.calls[0];
    expect(String(path)).toContain("/credit-tenants/tenant-one/media-archive/recoveries/" + failedRecovery.operation_id + "/retry");
    expect(JSON.parse(String(init?.body))).toMatchObject({
      duration_days: 14,
      idempotency_key: "archive-retry-synthetic-owner-retry",
      current_password: "synthetic-password",
      totp_code: "123456",
    });
    expect(updated).toHaveBeenCalledOnce();
  });
});
