import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  AuthEntry,
  brazilMobileE164,
  formatBrazilPhone,
} from "./auth-entry";

const fixtureToken = "synthetic-link-with-more-than-32-characters";
beforeEach(() => {
  window.history.replaceState({}, "", `/?access_token=${fixtureToken}`);
});

afterEach(() => {
  vi.restoreAllMocks();
  window.history.replaceState({}, "", "/");
  document.head.querySelectorAll('link[data-branding-test]').forEach((element) => element.remove());
});

describe("entrada com identidade configurável", () => {
  it.each(["/admin/settings", "//external.example.test", "/admin?access_token=synthetic"])("reauth administrativa mantém TOTP e valida retorno %s", async (returnTo) => {
    const navigate = vi.fn();
    const fetchMock = vi.fn((input: string | URL | Request) => {
      const path = String(input);
      if (path === "/api/auth/admin/password") return Promise.resolve(new Response(JSON.stringify({ challenge_id: "synthetic-admin", message: "Informe TOTP" }), { status: 200 }));
      if (path === "/api/auth/admin/totp") return Promise.resolve(new Response(JSON.stringify({ destination: "/admin" }), { status: 200 }));
      return Promise.resolve(path === "/api/auth/destination"
        ? new Response(JSON.stringify({ destination: "/library" }), { status: 200 })
        : new Response(null, { status: 401 }));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<AuthEntry recoveryContext="admin" initialInvitation={{ accessToken: "", returnTo }} navigate={navigate} />);
    expect(screen.getByRole("tab", { name: "Fotógrafo" }).getAttribute("aria-selected")).toBe("true");
    expect(screen.getByRole("status").textContent).toContain("Sua sessão terminou");
    fireEvent.change(screen.getByLabelText("E-mail"), { target: { value: "photographer@example.test" } });
    fireEvent.change(screen.getByLabelText("Senha"), { target: { value: "synthetic-unused-password" } });
    fireEvent.submit(screen.getByLabelText("Senha").closest("form")!);
    await screen.findByLabelText("Código do autenticador");
    expect(navigate).not.toHaveBeenCalled();
    fireEvent.change(screen.getByLabelText("Código do autenticador"), { target: { value: "123456" } });
    fireEvent.submit(screen.getByLabelText("Código do autenticador").closest("form")!);
    await waitFor(() => expect(navigate).toHaveBeenCalledWith(returnTo === "/admin/settings" ? returnTo : "/admin"));
    expect(fetchMock.mock.calls.some(([input]) => String(input).includes("/auth/client/"))).toBe(false);
  });

  it("cliente expirado sem link recebe orientação sem OTP ou escolha de conta por UUID", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 401 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<AuthEntry recoveryContext="client" initialInvitation={{ accessToken: "", returnTo: "/public-galleries/synthetic" }} navigate={vi.fn()} />);
    expect(screen.getByRole("heading", { name: "Abra o link do seu fotógrafo" })).toBeTruthy();
    expect(screen.getByRole("status").textContent).toContain("Reabra o link");
    expect(screen.queryByLabelText("WhatsApp")).toBeNull();
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/auth/destination", expect.anything()));
    expect(fetchMock.mock.calls.some(([input]) => String(input).includes("/auth/client/challenge"))).toBe(false);
  });

  it("orienta usar o link sem pesquisar telefone global e preserva entrada administrativa", async () => {
    window.history.replaceState({}, "", "/");
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 403 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<AuthEntry navigate={vi.fn()} />);
    expect(screen.getByRole("heading", { name: "Abra o link do seu fotógrafo" })).toBeTruthy();
    expect(screen.queryByLabelText("WhatsApp")).toBeNull();
    expect(screen.queryByRole("button", { name: "Receber código" })).toBeNull();
    fireEvent.click(screen.getByRole("tab", { name: "Fotógrafo" }));
    expect(screen.getByLabelText("E-mail")).toBeTruthy();
    expect(screen.getByLabelText("Senha")).toBeTruthy();
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/auth/destination", expect.anything()));
    expect(fetchMock.mock.calls.some(([input]) => String(input).includes("/auth/client/challenge"))).toBe(false);
  });

  it.each(["fotografo-A", "fotografo-B"])("mantém o token de %s na verificação e reenvio", async (owner) => {
    const token = `${owner}-link-with-more-than-32-characters`;
    const navigate = vi.fn();
    const fetchMock = vi.fn((input: string | URL | Request) => {
      const url = String(input);
      if (url.includes("/branding") || url.includes("/auth/destination")) return Promise.resolve(new Response(null, { status: 403 }));
      return Promise.resolve(new Response(JSON.stringify({ challenge_id: "own-challenge", message: "Código solicitado.", destination: "/library" }), { status: 200 }));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<AuthEntry initialInvitation={{ accessToken: token, returnTo: "" }} navigate={navigate} />);
    fireEvent.change(screen.getByLabelText("Nome completo"), { target: { value: "Cliente sintética" } });
    fireEvent.change(screen.getByLabelText("WhatsApp"), { target: { value: "11999990001" } });
    fireEvent.submit(screen.getByRole("button", { name: "Receber código" }).closest("form")!);
    await screen.findByLabelText("Código enviado por WhatsApp");
    fireEvent.click(screen.getByRole("button", { name: "Reenviar código" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/auth/client/resend", expect.objectContaining({ body: JSON.stringify({ challenge_id: "own-challenge", access_token: token }) })));
    await waitFor(() => expect(screen.getByRole("button", { name: "Entrar" }).hasAttribute("disabled")).toBe(false));
    fireEvent.change(screen.getByLabelText("Código enviado por WhatsApp"), { target: { value: "123456" } });
    fireEvent.submit(screen.getByRole("button", { name: "Entrar" }).closest("form")!);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/auth/client/verify", expect.objectContaining({ body: JSON.stringify({ challenge_id: "own-challenge", code: "123456", access_token: token }) })));
    await waitFor(() => expect(navigate).toHaveBeenCalledWith("/library"));
  });

  it("cookie de outro fotógrafo recusado no link não navega para sua biblioteca", async () => {
    const navigate = vi.fn();
    const fetchMock = vi.fn((input: string | URL | Request) => Promise.resolve(
      String(input).includes("/auth/destination") ? new Response(JSON.stringify({ destination: "/library" }), { status: 200 }) : new Response(null, { status: 403 }),
    ));
    vi.stubGlobal("fetch", fetchMock);
    render(<AuthEntry navigate={navigate} />);
    await waitFor(() => expect(fetchMock.mock.calls.some(([input]) => String(input).includes("/public-gallery/access"))).toBe(true));
    expect(screen.getByLabelText("Nome completo")).toBeTruthy();
    expect(navigate).not.toHaveBeenCalled();
  });
  it("mantém os textos de fallback quando a marca não pode ser carregada", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 500 })));
    render(<AuthEntry />);
    expect(screen.getByRole("heading", { name: "Sua galeria, do seu jeito." })).toBeTruthy();
    expect(screen.getByText("Escolha seu tipo de acesso para continuar.")).toBeTruthy();
  });

  it("aplica favicon e ícone do aplicativo retornados pelo servidor", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ login_title: "Entrada", login_intro: "Intro", login_helper: "Ajuda", logo_url: null, favicon_url: "/branding/favicon", app_icon_url: "/branding/app-icon" }), { status: 200 })));
    render(<AuthEntry />);
    await waitFor(() => expect(document.querySelector<HTMLLinkElement>('link[rel="icon"]')?.href).toContain("/api/branding/favicon"));
    expect(document.querySelector<HTMLLinkElement>('link[rel="apple-touch-icon"]')?.href).toContain("/api/branding/app-icon?size=180");
  });

  it("carrega a marca pelo link e conserva seu contexto ao redimensionar o ícone", async () => {
    const fetchMock = vi.fn((input: string | URL | Request) => Promise.resolve(
      String(input).includes("/branding")
        ? new Response(JSON.stringify({ login_title: "Fotógrafo B", logo_url: null,
            app_icon_url: "/branding/app-icon?access_token=syntheticB",
            favicon_url: "/branding/favicon?access_token=syntheticB" }), { status: 200 })
        : new Response(null, { status: 403 }),
    ));
    vi.stubGlobal("fetch", fetchMock);
    const view = render(<AuthEntry initialInvitation={{ accessToken: "syntheticB", returnTo: "" }} />);
    await screen.findByRole("heading", { name: "Fotógrafo B" });
    expect(fetchMock).toHaveBeenCalledWith("/api/branding?access_token=syntheticB", expect.objectContaining({ cache: "no-store" }));
    expect(document.querySelector<HTMLLinkElement>('link[rel="apple-touch-icon"]')?.getAttribute("href"))
      .toBe("/api/branding/app-icon?access_token=syntheticB&size=180");
    view.unmount();
    expect(document.querySelector('link[rel="icon"]')).toBeNull();
    expect(document.querySelector('link[rel="apple-touch-icon"]')).toBeNull();
    expect(window.localStorage.getItem("access_token")).toBeNull();
    expect(window.sessionStorage.getItem("access_token")).toBeNull();
  });

  it("apresenta +55 e envia DDD, nono dígito e celular em E.164", async () => {
    const fetchMock = vi.fn((input: string | URL | Request) =>
      Promise.resolve(
        String(input).includes("/auth/client/challenge")
          ? new Response(
              JSON.stringify({ challenge_id: "challenge-1", message: "Código enviado." }),
              { status: 202 },
            )
          : new Response(JSON.stringify({}), { status: 200 }),
      ),
    );
    vi.stubGlobal("fetch", fetchMock);
    render(<AuthEntry />);

    fireEvent.change(screen.getByLabelText("Nome completo"), {
      target: { value: "Cliente Sintético" },
    });
    const phone = screen.getByLabelText("WhatsApp");
    fireEvent.change(phone, { target: { value: "11987654321" } });
    expect(phone.getAttribute("value")).toBe("(11) 98765-4321");
    expect(phone.getAttribute("pattern")).toBe("\\(\\d{2}\\) 9\\d{4}-\\d{4}");
    expect(screen.getByText("+55")).toBeTruthy();
    fireEvent.submit(screen.getByRole("button", { name: "Receber código" }).closest("form")!);

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/auth/client/challenge",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            full_name: "Cliente Sintético",
            phone: "+5511987654321",
            access_token: fixtureToken,
          }),
        }),
      ),
    );
  });

  it("aceita colagem brasileira completa sem duplicar o +55", () => {
    expect(formatBrazilPhone("+55 (11) 99876-5432")).toBe("(11) 99876-5432");
    expect(brazilMobileE164("+55 (11) 99876-5432")).toBe("+5511998765432");
    expect(brazilMobileE164("(11) 99876-5432")).toBe("+5511998765432");
  });

  it.each(["1187654321", "11887654321"])(
    "não solicita OTP para telefone sem o nono dígito: %s",
    async (invalidPhone) => {
      const fetchMock = vi.fn().mockResolvedValue(
        new Response(JSON.stringify({}), { status: 200 }),
      );
      vi.stubGlobal("fetch", fetchMock);
      render(<AuthEntry />);
      fireEvent.change(screen.getByLabelText("Nome completo"), {
        target: { value: "Cliente Sintético" },
      });
      fireEvent.change(screen.getByLabelText("WhatsApp"), {
        target: { value: invalidPhone },
      });
      fireEvent.submit(screen.getByRole("button", { name: "Receber código" }).closest("form")!);

      expect(
        screen.getByText("Informe DDD e celular com o nono dígito: (11) 99999-9999."),
      ).toBeTruthy();
      expect(fetchMock.mock.calls.some(([input]) => String(input).includes("/auth/client/challenge"))).toBe(false);
    },
  );

  it("limpa o telefone ao trocar o tipo de acesso", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({}), { status: 200 })));
    render(<AuthEntry />);
    fireEvent.change(screen.getByLabelText("WhatsApp"), {
      target: { value: "11987654321" },
    });
    fireEvent.click(screen.getByRole("tab", { name: "Fotógrafo" }));
    fireEvent.click(screen.getByRole("tab", { name: "Cliente" }));
    expect(screen.getByLabelText("WhatsApp").getAttribute("value")).toBe("");
  });

  it("explica a falta de vínculo após OTP válido sem criar um falso erro de código", async () => {
    const denial =
      "Este número ainda não possui acesso. Abra o link compartilhado de uma galeria para se cadastrar.";
    const fetchMock = vi.fn((input: string | URL | Request) => {
      const url = String(input);
      if (url.includes("/branding"))
        return Promise.resolve(new Response(null, { status: 500 }));
      if (url.includes("/challenge"))
        return Promise.resolve(
          new Response(
            JSON.stringify({ challenge_id: "challenge-denied", message: "Código enviado." }),
            { status: 202 },
          ),
        );
      return Promise.resolve(
        new Response(JSON.stringify({ detail: denial }), { status: 403 }),
      );
    });
    const navigate = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    render(<AuthEntry navigate={navigate} />);

    fireEvent.change(screen.getByLabelText("Nome completo"), {
      target: { value: "Pessoa sem convite" },
    });
    fireEvent.change(screen.getByLabelText("WhatsApp"), {
      target: { value: "11987654321" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Receber código" }));
    await screen.findByLabelText("Código enviado por WhatsApp");
    fireEvent.change(screen.getByLabelText("Código enviado por WhatsApp"), {
      target: { value: "123456" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Entrar" }));

    expect(await screen.findByText(denial)).toBeTruthy();
    expect(navigate).not.toHaveBeenCalled();
  });

  it("usa o destino autorizado retornado depois do OTP", async () => {
    const fetchMock = vi.fn((input: string | URL | Request) => {
      const url = String(input);
      if (url.includes("/branding"))
        return Promise.resolve(new Response(null, { status: 500 }));
      if (url.includes("/challenge"))
        return Promise.resolve(
          new Response(
            JSON.stringify({ challenge_id: "challenge-ok", message: "Código enviado." }),
            { status: 202 },
          ),
        );
      return Promise.resolve(
        new Response(JSON.stringify({ destination: "/library?registration=pending" }), {
          status: 200,
        }),
      );
    });
    const navigate = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    render(<AuthEntry navigate={navigate} />);

    fireEvent.change(screen.getByLabelText("Nome completo"), {
      target: { value: "Pessoa convidada" },
    });
    fireEvent.change(screen.getByLabelText("WhatsApp"), {
      target: { value: "11987654321" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Receber código" }));
    await screen.findByLabelText("Código enviado por WhatsApp");
    fireEvent.change(screen.getByLabelText("Código enviado por WhatsApp"), {
      target: { value: "123456" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Entrar" }));

    await waitFor(() =>
      expect(navigate).toHaveBeenCalledWith("/library?registration=pending"),
    );
  });

  it("preserva capability e retorno interno durante o OTP", async () => {
    const galleryId = "0f581c42-08aa-4305-9bfb-55f803d1cfc6";
    window.history.replaceState({}, "", `/?access_token=token-seguro-com-mais-de-32-caracteres&return_to=%2Fpublic-galleries%2F${galleryId}`);
    const fetchMock = vi.fn((input: string | URL | Request) => {
      const url = String(input);
      if (url.includes("/auth/destination")) return Promise.resolve(new Response(null, { status: 401 }));
      if (url.includes("/auth/client/challenge")) return Promise.resolve(new Response(JSON.stringify({ challenge_id: "challenge-link", message: "Código enviado." }), { status: 202 }));
      return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<AuthEntry navigate={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("Nome completo"), { target: { value: "Pessoa convidada" } });
    fireEvent.change(screen.getByLabelText("WhatsApp"), { target: { value: "11987654321" } });
    fireEvent.click(screen.getByRole("button", { name: "Receber código" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/auth/client/challenge",
      expect.objectContaining({ body: JSON.stringify({ full_name: "Pessoa convidada", phone: "+5511987654321", access_token: "token-seguro-com-mais-de-32-caracteres", return_to: `/public-galleries/${galleryId}`, parent_gallery_id: galleryId }) }),
    ));
  });

  it("retorna à galeria contextual após o OTP sem capability", async () => {
    const galleryId = "0f581c42-08aa-4305-9bfb-55f803d1cfc6";
    window.history.replaceState({}, "", `/?reauth=client&return_to=%2Fpublic-galleries%2F${galleryId}`);
    const fetchMock = vi.fn((input: string | URL | Request) => {
      const url = String(input);
      if (url.includes("/auth/destination")) return Promise.resolve(new Response(null, { status: 401 }));
      if (url.includes("/auth/client/challenge")) return Promise.resolve(new Response(JSON.stringify({ challenge_id: "reauth-challenge", message: "Código enviado." }), { status: 202 }));
      if (url.includes("/auth/client/verify")) return Promise.resolve(new Response(JSON.stringify({ destination: `/public-galleries/${galleryId}` }), { status: 200 }));
      return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
    });
    const navigate = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    render(<AuthEntry navigate={navigate} recoveryContext="client" initialInvitation={{ accessToken: "", returnTo: `/public-galleries/${galleryId}` }} />);
    fireEvent.change(screen.getByLabelText("Nome completo"), { target: { value: "Pessoa autorizada" } });
    fireEvent.change(screen.getByLabelText("WhatsApp"), { target: { value: "11987654321" } });
    fireEvent.click(screen.getByRole("button", { name: "Receber código" }));
    await screen.findByLabelText("Código enviado por WhatsApp");
    expect(fetchMock).toHaveBeenCalledWith("/api/auth/client/challenge", expect.objectContaining({
      body: JSON.stringify({ full_name: "Pessoa autorizada", phone: "+5511987654321", return_to: `/public-galleries/${galleryId}`, parent_gallery_id: galleryId }),
    }));
    fireEvent.change(screen.getByLabelText("Código enviado por WhatsApp"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Entrar" }));
    await waitFor(() => expect(navigate).toHaveBeenCalledWith(`/public-galleries/${galleryId}`));
  });

  it("abre a galeria contextual diretamente quando a sessão do cliente ainda é válida", async () => {
    const galleryId = "0f581c42-08aa-4305-9bfb-55f803d1cfc6";
    const fetchMock = vi.fn((input: string | URL | Request) => {
      if (String(input).includes("/auth/destination")) return Promise.resolve(new Response(JSON.stringify({ destination: "/library" }), { status: 200 }));
      return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
    });
    const navigate = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    render(<AuthEntry navigate={navigate} recoveryContext="client" initialInvitation={{ accessToken: "", returnTo: `/public-galleries/${galleryId}` }} />);
    await waitFor(() => expect(navigate).toHaveBeenCalledWith(`/public-galleries/${galleryId}`));
  });

  it("aplica o link automaticamente quando a cliente já está autenticada", async () => {
    window.history.replaceState({}, "", "/?access_token=token-seguro-com-mais-de-32-caracteres");
    const navigate = vi.fn();
    const fetchMock = vi.fn((input: string | URL | Request) => {
      const url = String(input);
      if (url.includes("/auth/destination")) return Promise.resolve(new Response(JSON.stringify({ destination: "/library" }), { status: 200 }));
      if (url.includes("/public-gallery/access")) return Promise.resolve(new Response(JSON.stringify({ destination: "/public-galleries/public-1" }), { status: 200 }));
      return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<AuthEntry navigate={navigate} />);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/public-gallery/access",
      expect.objectContaining({ method: "POST", body: JSON.stringify({ access_token: "token-seguro-com-mais-de-32-caracteres" }) }),
    ));
    expect(navigate).toHaveBeenCalledWith("/public-galleries/public-1");
  });

  it("mantém a mensagem neutra para OTP inválido", async () => {
    const fetchMock = vi.fn((input: string | URL | Request) => {
      const url = String(input);
      if (url.includes("/branding"))
        return Promise.resolve(new Response(null, { status: 500 }));
      if (url.includes("/challenge"))
        return Promise.resolve(
          new Response(
            JSON.stringify({ challenge_id: "challenge-invalid", message: "Código enviado." }),
            { status: 202 },
          ),
        );
      return Promise.resolve(
        new Response(
          JSON.stringify({ detail: "Não foi possível concluir a autenticação." }),
          { status: 401 },
        ),
      );
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<AuthEntry navigate={vi.fn()} />);

    fireEvent.change(screen.getByLabelText("Nome completo"), {
      target: { value: "Pessoa convidada" },
    });
    fireEvent.change(screen.getByLabelText("WhatsApp"), {
      target: { value: "11987654321" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Receber código" }));
    await screen.findByLabelText("Código enviado por WhatsApp");
    fireEvent.change(screen.getByLabelText("Código enviado por WhatsApp"), {
      target: { value: "000000" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Entrar" }));

    expect(
      await screen.findByText(
        "O código expirou ou não pôde ser validado. Solicite outro e tente novamente.",
      ),
    ).toBeTruthy();
  });

  it("oferece recuperação apenas ao fotógrafo e conclui o fluxo neutro", async () => {
    const fetchMock = vi.fn((input: string | URL | Request) => {
      const url = String(input);
      if (url.includes("/branding")) return Promise.resolve(new Response(null, { status: 500 }));
      if (url.endsWith("/recovery/challenge")) {
        return Promise.resolve(new Response(JSON.stringify({ challenge_id: "recovery-1", message: "Se a conta estiver apta, enviaremos as próximas instruções." }), { status: 202 }));
      }
      if (url.endsWith("/recovery/verify")) {
        return Promise.resolve(new Response(JSON.stringify({ message: "Se a conta estiver apta, o link foi enviado ao e-mail cadastrado." }), { status: 202 }));
      }
      return Promise.resolve(new Response(JSON.stringify({ message: "Novo código solicitado." }), { status: 202 }));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<AuthEntry />);

    expect(screen.queryByRole("button", { name: "Esqueci minha senha" })).toBeNull();
    fireEvent.click(screen.getByRole("tab", { name: "Fotógrafo" }));
    fireEvent.click(screen.getByRole("button", { name: "Esqueci minha senha" }));
    fireEvent.change(screen.getByLabelText("E-mail administrativo"), { target: { value: "admin@example.test" } });
    fireEvent.click(screen.getByRole("button", { name: "Receber código" }));

    await screen.findByLabelText("Código de recuperação");
    fireEvent.click(screen.getByRole("button", { name: "Reenviar código" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/auth/admin/recovery/resend", expect.objectContaining({ method: "POST" })));
    fireEvent.change(screen.getByLabelText("Código de recuperação"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Validar código" }));

    expect(await screen.findByRole("heading", { name: "Confira seu e-mail" })).toBeTruthy();
    expect(screen.getByText(/não realiza login automático/i)).toBeTruthy();
  });
});
