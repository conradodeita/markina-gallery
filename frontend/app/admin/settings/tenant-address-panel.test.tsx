import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ADDRESS_CHANGED, ADDRESS_ENDPOINT } from "../tenant-address";
import { TenantAddressNotice } from "../tenant-address-notice";
import { TenantAddressPanel } from "./tenant-address-panel";

const route = vi.hoisted(() => ({ pathname: "/admin" }));
vi.mock("next/navigation", () => ({ usePathname: () => route.pathname }));

const initial = { base_domain: "pickyourpic.com.br", hostname: null, state: "unselected",
  choice_complete: false, suggested_prefix: "fotografa-local", public_url: null };
const reserved = { ...initial, hostname: "minha-marca.pickyourpic.com.br", state: "reserved",
  choice_complete: true, suggested_prefix: null };
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });

afterEach(() => { cleanup(); vi.unstubAllGlobals(); route.pathname = "/admin"; });

describe("escolha inicial do endereço", () => {
  it("mostra prévia, reserva somente no PUT e confirma escolha sem anunciar link pronto", async () => {
    let chosen = false;
    const fetchMock = vi.fn((_path: string, init?: RequestInit) => {
      if (init?.method === "PUT") { chosen = true; return Promise.resolve(json(reserved)); }
      return Promise.resolve(json(chosen ? reserved : initial));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<TenantAddressPanel />);
    const input = await screen.findByLabelText("Nome para o link da marca");
    expect((input as HTMLInputElement).value).toBe("fotografa-local");
    expect(fetchMock.mock.calls.every(([, options]) => options?.method !== "PUT")).toBe(true);
    fireEvent.change(input, { target: { value: "Minha-Marca" } });
    expect(screen.getByText("minha-marca.pickyourpic.com.br").closest("a")).toBeNull();
    fireEvent.submit(input.closest("form")!);
    await screen.findByText("Escolha concluída");
    expect(screen.getByText("Escolha concluída").closest("summary")?.textContent).toContain("✓");
    expect(screen.getByText("Preparação do link: pendente")).toBeTruthy();
    expect(screen.queryByRole("link", { name: "Acessar meu espaço" })).toBeNull();
    expect(fetchMock).toHaveBeenCalledWith(ADDRESS_ENDPOINT, expect.objectContaining({
      method: "PUT", credentials: "same-origin", body: JSON.stringify({ prefix: "minha-marca" }),
    }));
  });

  it("preserva a entrada após conflito e falha de rede, permitindo repetir sem falso sucesso", async () => {
    let attempts = 0;
    vi.stubGlobal("fetch", vi.fn((_path, init?: RequestInit) => {
      if (init?.method !== "PUT") return Promise.resolve(json(attempts === 3 ? reserved : initial));
      attempts++;
      if (attempts === 1) return Promise.resolve(json({}, 409));
      if (attempts === 2) return Promise.reject(new Error("network"));
      return Promise.resolve(json(reserved));
    }));
    render(<TenantAddressPanel />);
    const input = await screen.findByLabelText("Nome para o link da marca");
    fireEvent.change(input, { target: { value: "minha-marca" } });
    fireEvent.submit(input.closest("form")!);
    await screen.findByText("Este nome de link não está disponível. Escolha outro nome.");
    expect((input as HTMLInputElement).value).toBe("minha-marca");
    expect(screen.queryByText("Escolha concluída")).toBeNull();
    fireEvent.submit(input.closest("form")!);
    await screen.findByText("Não foi possível confirmar a reserva do link. Tente novamente com o mesmo nome.");
    expect((input as HTMLInputElement).value).toBe("minha-marca");
    fireEvent.submit(input.closest("form")!);
    await screen.findByText("Escolha concluída");
  });

  it("trata resposta inválida como indisponibilidade e oferece nova consulta", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(json({ choice_complete: true }))
      .mockResolvedValueOnce(json(initial)));
    render(<TenantAddressPanel />);
    await screen.findByRole("alert");
    expect(screen.queryByText("Escolha concluída")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
    expect(await screen.findByLabelText("Nome para o link da marca")).toBeTruthy();
  });

  it.each([403, 404])("não apresenta seleção a proprietário/legado inelegível (%s)", async (status) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(json({}, status)));
    const { container } = render(<TenantAddressPanel />);
    await waitFor(() => expect(container.querySelector("#tenant-address")).toBeNull());
  });

  it("só oferece abrir endereço quando o servidor informa prontidão", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(json({ ...reserved, state: "ready",
      public_url: "https://minha-marca.pickyourpic.com.br" })));
    render(<TenantAddressPanel />);
    await screen.findByText("Escolha concluída");
    fireEvent.click(screen.getByText("Link da sua marca").closest("summary")!);
    expect(screen.getByRole("link", { name: "Acessar meu espaço" }).getAttribute("href"))
      .toBe("https://minha-marca.pickyourpic.com.br");
    expect(screen.queryByText("Preparação do link: pendente")).toBeNull();
  });
});

describe("aviso no primeiro acesso", () => {
  it("leva a Configurações e desaparece quando a escolha é confirmada", async () => {
    let chosen = false;
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(json(chosen ? reserved : initial))));
    render(<TenantAddressNotice />);
    const notice = await screen.findByLabelText("Link da sua marca");
    expect(notice.textContent).toContain("Esse será o endereço na web que seus clientes usarão para acessar seu espaço.");
    expect(notice.className).not.toBe("");
    expect((await screen.findByRole("link", { name: "Escolher link da minha marca" })).getAttribute("href"))
      .toBe("/admin/settings#tenant-address");
    chosen = true;
    act(() => window.dispatchEvent(new Event(ADDRESS_CHANGED)));
    await waitFor(() => expect(screen.queryByRole("link", { name: "Escolher link da minha marca" })).toBeNull());
  });

  it("evita aviso duplicado em Configurações e não consulta quando desabilitado", () => {
    route.pathname = "/admin/settings";
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const { container } = render(<TenantAddressNotice />);
    expect(container.innerHTML).toBe("");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("não exibe convite de escolha para proprietário ou legado", async () => {
    const fetchMock = vi.fn().mockResolvedValue(json({}, 403));
    vi.stubGlobal("fetch", fetchMock);
    const { container } = render(<TenantAddressNotice />);
    await act(async () => {});
    expect(container.innerHTML).toBe("");
  });
});
