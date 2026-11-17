import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { MediaArchiveNoticeCenter, type MediaArchiveNotice } from "./media-archive-notice-center";

const notice: MediaArchiveNotice = {
  id: "notice-one",
  notice_type: "window_7_days",
  title: "Uma pasta poderá ser arquivada em 7 dias",
  body: "A janela normal de reabertura termina em 7 dias.",
  cycle_id: "cycle-one",
  folder_id: "folder-one",
  parent_gallery_id: "gallery-one",
  deadline_at: "2026-12-01T12:00:00Z",
  created_at: "2026-11-24T12:00:00Z",
  read_at: null,
  superseded_at: null,
};

afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

it("carrega a caixa e marca o aviso tenant-scoped como lido", async () => {
  const fetch = vi.fn()
    .mockResolvedValueOnce(new Response(JSON.stringify({ items: [notice], unread_count: 1 })))
    .mockResolvedValueOnce(new Response(JSON.stringify({ id: notice.id, read_at: "2026-11-24T13:00:00Z" })));
  vi.stubGlobal("fetch", fetch);
  render(<MediaArchiveNoticeCenter />);

  fireEvent.click(screen.getByRole("button", { name: "Ver avisos" }));
  expect(await screen.findByText(notice.title)).toBeTruthy();
  expect(screen.getByText("1 não lido(s)")).toBeTruthy();
  expect(screen.getByRole("link", { name: "Abrir galeria" }).getAttribute("href")).toBe("/admin/galleries/sources/gallery-one");
  fireEvent.click(screen.getByRole("button", { name: "Marcar como lido" }));
  expect(await screen.findByText("Lido")).toBeTruthy();
  expect(screen.queryByText("1 não lido(s)")).toBeNull();
  expect(fetch).toHaveBeenNthCalledWith(1, "/api/admin/media-archive/notices?limit=50", expect.objectContaining({ cache: "no-store" }));
  expect(fetch).toHaveBeenNthCalledWith(2, "/api/admin/media-archive/notices/notice-one/read", expect.objectContaining({ method: "POST" }));
});

it("sinaliza prazo superado sem reapresentá-lo como prazo atual", async () => {
  const oldNotice = {
    ...notice,
    superseded_at: "2026-11-25T12:00:00Z",
  };
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(
    new Response(JSON.stringify({ items: [oldNotice], unread_count: 0 })),
  ));
  render(<MediaArchiveNoticeCenter />);
  fireEvent.click(screen.getByRole("button", { name: "Ver avisos" }));

  expect(await screen.findByText("Prazo alterado")).toBeTruthy();
  expect(screen.getByText("A reabertura mais recente alterou a data deste aviso.")).toBeTruthy();
  expect(screen.queryByText(/Elegível para arquivo após/)).toBeNull();
});

it("permite repetir a consulta após erro de rede", async () => {
  const fetch = vi.fn()
    .mockRejectedValueOnce(new Error("offline"))
    .mockResolvedValueOnce(new Response(JSON.stringify({ items: [], unread_count: 0 })));
  vi.stubGlobal("fetch", fetch);
  render(<MediaArchiveNoticeCenter />);
  fireEvent.click(screen.getByRole("button", { name: "Ver avisos" }));
  expect(await screen.findByRole("alert")).toHaveProperty("textContent", "offline");
  fireEvent.click(screen.getByRole("button", { name: "Ver avisos" }));
  expect(await screen.findByText("Nenhum aviso de arquivo frio")).toBeTruthy();
});
