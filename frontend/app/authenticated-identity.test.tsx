import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AuthenticatedIdentity } from "./authenticated-identity";

afterEach(() => vi.restoreAllMocks());

describe("identidade da sessão autenticada", () => {
  it.each([
    ["admin", "fotografo@markina.test"],
    ["client", "+5511998765432"],
  ] as const)("mostra a identidade retornada pelo servidor para %s", async (role, identity) => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ role, identity }), { status: 200 }),
      ),
    );

    render(<AuthenticatedIdentity />);

    expect(await screen.findByLabelText(`Logado como: ${identity}`)).toBeTruthy();
    expect(screen.getByText(identity)).toBeTruthy();
  });

  it("não exibe identidade se a consulta falhar", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 401 })));

    render(<AuthenticatedIdentity />);

    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(screen.queryByText("Logado como:")).toBeNull();
  });
});
