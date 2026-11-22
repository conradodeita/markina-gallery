import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { FolderDeadlineFields } from "./folder-deadline-fields";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

function pricing(payload: unknown) {
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify(payload), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  })));
}

describe("aviso de prazo e recuperação da pasta", () => {
  it("mostra a taxa configurada dinamicamente e explica quando ela é debitada", async () => {
    const fetcher = vi.fn(async () => new Response(JSON.stringify({
      recovery_fee_credits: 7,
      configured: true,
      owner_exempt: false,
    }), { status: 200, headers: { "Content-Type": "application/json" } }));
    vi.stubGlobal("fetch", fetcher);

    render(<FolderDeadlineFields startsAt="release" />);

    expect(await screen.findByText(/7 créditos por pasta e ciclo/)).toBeTruthy();
    expect(screen.getByText(/débito ocorre após a recuperação completa e verificada/)).toBeTruthy();
    expect(screen.getByText("A contagem começa quando as fotos da pasta forem liberadas. Após a expiração, a pasta pode ir para o arquivo frio depois de 30 dias.")).toBeTruthy();
    const daysInput = screen.getByLabelText("Dias de acesso da pasta");
    expect(daysInput.getAttribute("inputmode")).toBe("numeric");
    expect(daysInput.parentElement?.textContent).toContain("dias");
    expect(fetcher).toHaveBeenCalledWith("/api/admin/media-archive/recovery-pricing", expect.objectContaining({
      cache: "no-store",
      credentials: "same-origin",
    }));
  });

  it("mostra isenção na conta do proprietário e não exibe uma taxa", async () => {
    pricing({ recovery_fee_credits: 7, configured: true, owner_exempt: true });

    render(<FolderDeadlineFields startsAt="release" initialDays={30} />);

    expect(await screen.findByText(/7 créditos por pasta e ciclo/)).toBeTruthy();
    expect(screen.getByText(/Taxa de referência:/)).toBeTruthy();
    expect(screen.getByText(/Na sua conta, a recuperação não debita créditos/)).toBeTruthy();
  });

  it("não revela a configuração administrativa ausente", async () => {
    pricing({ recovery_fee_credits: null, configured: false, owner_exempt: false });

    render(<FolderDeadlineFields startsAt="release" />);

    expect(await screen.findByText("A contagem começa quando as fotos da pasta forem liberadas. Após a expiração, a pasta pode ir para o arquivo frio depois de 30 dias.")).toBeTruthy();
    expect(screen.queryByText(/novos pedidos pagos ficam indisponíveis/)).toBeNull();
  });

  it.each(["release", "save"] as const)("não repete aviso ou consulta preço em pasta existente (%s)", (startsAt) => {
    const fetcher = vi.fn();
    vi.stubGlobal("fetch", fetcher);
    render(<FolderDeadlineFields mode="existing" startsAt={startsAt} initialDays={14} />);
    expect(screen.getByLabelText("Dias de acesso da pasta")).toHaveProperty("value", "14");
    expect(screen.queryByText(/arquivo frio/)).toBeNull();
    expect(fetcher).not.toHaveBeenCalled();
    expect(Boolean(screen.queryByText("A contagem começa hoje, quando você salvar este prazo."))).toBe(startsAt === "save");
  });
});
