import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { PhotographerTermsEditor } from "./photographer-terms-editor";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe("editor de Termos do proprietário", () => {
  it("salva rascunho sem publicar e exige confirmação mais reautenticação para publicar", async () => {
    let revision: string | null = null;
    let published = false;
    const template = "{{provider_legal_name}} {{provider_contact_email}} {{photographer_name}} {{photographer_verified_email}}";
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path.endsWith("/draft") && init?.method === "PUT") {
        const payload = JSON.parse(String(init.body));
        revision = "revision-2";
        return new Response(JSON.stringify({ ...payload, revision, updated_at: "2026-11-07T12:00:00Z" }));
      }
      if (path.endsWith("/draft")) return new Response(JSON.stringify({
        revision, template_text: template, provider_legal_name: "", provider_contact_email: "owner@example.test", updated_at: null,
      }));
      if (path.endsWith("/versions")) return new Response(JSON.stringify({ items: published ? [{
        version: "v1", template_sha256: "a".repeat(64), published_at: "2026-11-07T12:00:00Z",
        provider_legal_name: "Provedor sintético", provider_contact_email: "owner@example.test",
      }] : [] }));
      if (path.endsWith("/publish")) {
        published = true;
        return new Response(JSON.stringify({ version: "v1", template_sha256: "a".repeat(64), already_current: false }));
      }
      return new Response("{}", { status: 404 });
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<PhotographerTermsEditor />);
    fireEvent.change(await screen.findByLabelText("Nome legal do provedor"), { target: { value: "Provedor sintético" } });
    fireEvent.click(screen.getByRole("button", { name: "Salvar rascunho" }));
    expect(await screen.findByText("Rascunho salvo. A versão publicada continua inalterada.")).toBeTruthy();
    expect(screen.getByText("Nenhuma versão publicada.")).toBeTruthy();
    const draftCall = fetchMock.mock.calls.find(([path, init]) => String(path).endsWith("/draft") && init?.method === "PUT");
    expect(JSON.parse(String(draftCall?.[1]?.body))).toEqual({
      revision: null, template_text: template,
      provider_legal_name: "Provedor sintético", provider_contact_email: "owner@example.test",
    });

    fireEvent.click(screen.getByLabelText("Confirmo que revisei este rascunho e quero publicá-lo para novos aceites."));
    fireEvent.change(screen.getByLabelText("Senha atual do proprietário"), { target: { value: "synthetic-password" } });
    fireEvent.change(screen.getByLabelText("Código do autenticador"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Publicar nova versão" }));
    expect(await screen.findByText("Versão v1 publicada.")).toBeTruthy();
    const publishCall = fetchMock.mock.calls.find(([path]) => String(path).endsWith("/publish"));
    expect(JSON.parse(String(publishCall?.[1]?.body))).toMatchObject({
      expected_revision: "revision-2", confirm_publication: true,
      current_password: "synthetic-password", totp_code: "123456",
    });
    await waitFor(() => expect(screen.getByText(/v1 ·/)).toBeTruthy());
    expect(screen.queryByText("synthetic-password")).toBeNull();
    expect(screen.queryByText("123456")).toBeNull();
  });
});
