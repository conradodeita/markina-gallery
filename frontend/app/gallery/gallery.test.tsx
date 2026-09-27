import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

const replace = vi.fn();
vi.mock("next/navigation", () => ({
  useParams: () => ({ galleryId: "legacy-1" }),
  useRouter: () => ({ replace }),
}));

import LegacyGalleryRedirect from "./[galleryId]/page";

afterEach(() => {
  vi.unstubAllGlobals();
  replace.mockReset();
});

it("redireciona um link legado autorizado para a coleção canônica", async () => {
  const fetchMock = vi.fn().mockResolvedValue(new Response(
    JSON.stringify({ status: "authorized", redirect_url: "/public-galleries/public-1" }),
    { status: 200 },
  ));
  vi.stubGlobal("fetch", fetchMock);
  render(<LegacyGalleryRedirect />);
  await waitFor(() => expect(replace).toHaveBeenCalledWith("/public-galleries/public-1"));
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/gallery/legacy-1",
    expect.objectContaining({ credentials: "same-origin" }),
  );
});

it("redireciona o histórico legado para Compras quando não há galeria ativa", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(
    JSON.stringify({ status: "authorized", redirect_url: "/library/purchases" }),
    { status: 200 },
  )));
  render(<LegacyGalleryRedirect />);
  await waitFor(() => expect(replace).toHaveBeenCalledWith("/library/purchases"));
});

it("não redireciona acesso negado e mostra saídas seguras", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 403 })));
  render(<LegacyGalleryRedirect />);
  expect(await screen.findByText("Galeria indisponível")).toBeTruthy();
  expect(replace).not.toHaveBeenCalled();
  expect(screen.getByRole("link", { name: "Ver coleção" }).getAttribute("href")).toBe("/library");
  expect(screen.getByRole("link", { name: "Ver compras" }).getAttribute("href")).toBe("/library/purchases");
});
