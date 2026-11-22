import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { GoogleDriveConnectForm, isAllowedGoogleAuthorizationUrl } from "./google-drive-connect";

afterEach(() => vi.unstubAllGlobals());

const authorizationUrl = "https://accounts.google.com/o/oauth2/v2/auth?client_id=synthetic-client&redirect_uri=https%3A%2F%2Fmarkina.pickyourpic.com.br%2Fapi%2Fadmin%2Fplatform%2Fdrive%2Foauth%2Fcallback&response_type=code&scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fdrive.file&code_challenge_method=S256&state=synthetic-state&code_challenge=synthetic-challenge";

it("envia reautenticação uma vez, limpa os campos e só redireciona ao consentimento drive.file", async () => {
  const fetcher = vi.fn(() => Promise.resolve(new Response(JSON.stringify({ authorization_url: authorizationUrl }), { status: 200 })));
  const navigate = vi.fn();
  vi.stubGlobal("fetch", fetcher);
  render(<GoogleDriveConnectForm navigate={navigate} />);
  fireEvent.change(screen.getByLabelText("Senha atual do proprietário"), { target: { value: "synthetic-password" } });
  fireEvent.change(screen.getByLabelText("Código atual do autenticador"), { target: { value: "123456" } });
  fireEvent.click(screen.getByRole("button", { name: "Continuar para o Google" }));

  await waitFor(() => expect(navigate).toHaveBeenCalledWith(authorizationUrl));
  expect(fetcher).toHaveBeenCalledWith("/api/admin/platform/drive/connect/start", expect.objectContaining({
    method: "POST", credentials: "same-origin", cache: "no-store", redirect: "error",
    body: JSON.stringify({ current_password: "synthetic-password", totp_code: "123456" }),
  }));
  expect((screen.getByLabelText("Senha atual do proprietário") as HTMLInputElement).value).toBe("");
  expect((screen.getByLabelText("Código atual do autenticador") as HTMLInputElement).value).toBe("");
});

it("recusa redirecionamento para host, caminho ou escopo diferente", () => {
  expect(isAllowedGoogleAuthorizationUrl(authorizationUrl)).toBe(true);
  expect(isAllowedGoogleAuthorizationUrl("https://attacker.invalid/o/oauth2/v2/auth?scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fdrive.file")).toBe(false);
  expect(isAllowedGoogleAuthorizationUrl("https://accounts.google.com.evil.invalid/o/oauth2/v2/auth?scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fdrive.file")).toBe(false);
  expect(isAllowedGoogleAuthorizationUrl("https://accounts.google.com/o/oauth2/v2/auth?scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fdrive")).toBe(false);
  expect(isAllowedGoogleAuthorizationUrl(authorizationUrl + "&scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fdrive.file")).toBe(false);
  expect(isAllowedGoogleAuthorizationUrl("javascript:alert(1)")).toBe(false);
});
