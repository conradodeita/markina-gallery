import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  AuthEntry,
  brazilMobileE164,
  formatBrazilPhone,
} from "./auth-entry";

afterEach(() => {
  vi.restoreAllMocks();
  document.head.querySelectorAll('link[data-branding-test]').forEach((element) => element.remove());
});

describe("entrada com identidade configurável", () => {
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
    expect(document.querySelector<HTMLLinkElement>('link[rel="apple-touch-icon"]')?.href).toContain("/api/branding/app-icon");
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
      expect(fetchMock).toHaveBeenCalledTimes(1);
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
});
