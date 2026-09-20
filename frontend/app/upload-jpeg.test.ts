import { afterEach, expect, it, vi } from "vitest";
import { webcrypto } from "node:crypto";
import { jpegStorageKey, uploadJpeg } from "./upload-jpeg";

afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers(); });
it("retoma conteúdo idêntico na mesma pasta sem duplicar o ativo", async () => {
  vi.stubGlobal("crypto", webcrypto);
  const file = new File(["synthetic-jpeg"], "foto.jpg");
  Object.defineProperty(file, "arrayBuffer", {value: async () => new TextEncoder().encode("synthetic-jpeg").buffer});
  const first = await jpegStorageKey("gallery", "folder", file);
  expect(await jpegStorageKey("gallery", "folder", file)).toBe(first);
  expect(await jpegStorageKey("gallery", "another-folder", file)).not.toBe(first);
  expect(first).toMatch(/^gallery\/folder\/[a-f0-9]{64}\.jpg$/);
});
it("respeita backpressure e reenvia ao mesmo ativo", async () => {
  vi.useFakeTimers();
  const fetch = vi.fn().mockResolvedValueOnce({ ok:false, status:503, headers:new Headers({ "Retry-After":"2" }) })
    .mockResolvedValueOnce({ ok:true });
  vi.stubGlobal("fetch", fetch);
  const waiting = vi.fn();
  const request = uploadJpeg("/api/source", new File(["jpg"], "photo.jpg"), waiting);
  await vi.advanceTimersByTimeAsync(2000);
  await request;
  expect(waiting).toHaveBeenCalledOnce();
  expect(fetch.mock.calls.map((call) => call[0])).toEqual(["/api/source", "/api/source"]);
});
