import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

const { push } = vi.hoisted(() => ({ push: vi.fn() }));

vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));
vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => <a href={href}>{children}</a>,
}));

import NewGalleryPage from "./page";

afterEach(() => {
  vi.unstubAllGlobals();
  push.mockReset();
});

it("envia os campos opcionais vazios como null e abre Ajustes com um único cadastro", async () => {
  let finish: (response: Response) => void = () => {};
  const fetchMock = vi.fn(() => new Promise<Response>((resolve) => { finish = resolve; }));
  vi.stubGlobal("fetch", fetchMock);
  render(<NewGalleryPage />);

  const input = screen.getByRole("textbox", { name: "Título da galeria" }) as HTMLInputElement;
  expect(input.required).toBe(true);
  fireEvent.change(input, { target: { value: "Galeria sintética" } });
  const form = screen.getByRole("form", { name: "Dados da nova galeria" });
  fireEvent.submit(form);
  fireEvent.submit(form);

  expect(screen.getByRole("button", { name: "Criando…" })).toHaveProperty("disabled", true);
  expect(fetchMock).toHaveBeenCalledOnce();
  expect(fetchMock).toHaveBeenCalledWith("/api/admin/parent-galleries", expect.objectContaining({
    method: "POST",
    credentials: "same-origin",
    body: JSON.stringify({ name: "Galeria sintética", event_name: null, description: null }),
  }));
  finish(new Response(JSON.stringify({ id: "gallery-synthetic" }), { status: 201 }));
  await waitFor(() => expect(push).toHaveBeenCalledWith("/admin/galleries/sources/gallery-synthetic/edit/ajustes"));
});

it("preserva os campos ao rejeitar a criação e distingue resultado incerto", async () => {
  const fetchMock = vi.fn()
    .mockResolvedValueOnce(new Response(null, { status: 422 }))
    .mockResolvedValueOnce(new Response(JSON.stringify({}), { status: 201 }));
  vi.stubGlobal("fetch", fetchMock);
  render(<NewGalleryPage />);

  const input = screen.getByRole("textbox", { name: "Título da galeria" });
  fireEvent.change(input, { target: { value: "Galeria mantida" } });
  const create = screen.getByRole("button", { name: "Criar e continuar" });
  fireEvent.click(create);
  expect((await screen.findByRole("alert")).textContent).toContain("Revise os dados");
  expect(input).toHaveProperty("value", "Galeria mantida");
  fireEvent.click(create);
  await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("Confira a lista de galerias"));
  expect(input).toHaveProperty("value", "Galeria mantida");
  expect(push).not.toHaveBeenCalled();
});

it("cancela a espera ao sair e descarta redirecionamento de uma resposta tardia", async () => {
  let finish: (response: Response) => void = () => {};
  const fetchMock = vi.fn<(path: string, init: RequestInit) => Promise<Response>>(
    () => new Promise<Response>((resolve) => { finish = resolve; }),
  );
  vi.stubGlobal("fetch", fetchMock);
  const { unmount } = render(<NewGalleryPage />);
  fireEvent.change(screen.getByRole("textbox", { name: "Título da galeria" }), { target: { value: "Galeria sintética" } });
  fireEvent.click(screen.getByRole("button", { name: "Criar e continuar" }));
  const signal = fetchMock.mock.calls[0][1].signal;
  unmount();
  finish(new Response(JSON.stringify({ id: "gallery-synthetic" }), { status: 201 }));
  expect(signal?.aborted).toBe(true);
  await Promise.resolve();
  expect(push).not.toHaveBeenCalled();
});
