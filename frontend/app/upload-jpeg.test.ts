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

it("informa bytes enviados e preserva a mesma URL após 503", async () => {
  vi.useFakeTimers();
  const statuses = [503, 202];
  const paths: string[] = [];
  class FakeXHR {
    status = statuses.shift() ?? 500;
    responseText = "{}";
    onload: (() => void) | null = null;
    onerror: (() => void) | null = null;
    progress: ((event: ProgressEvent) => void) | null = null;
    upload = { addEventListener: (_name: string, handler: (event: ProgressEvent) => void) => { this.progress = handler; } };
    open(_method: string, path: string) { paths.push(path); }
    setRequestHeader() {}
    getResponseHeader() { return this.status === 503 ? "1" : null; }
    send(file: File) {
      this.progress?.({ lengthComputable: true, loaded: file.size, total: file.size } as ProgressEvent);
      this.onload?.();
    }
  }
  vi.stubGlobal("XMLHttpRequest", FakeXHR);
  const waiting = vi.fn();
  const progress = vi.fn();
  const request = uploadJpeg("/api/source", new File(["jpeg"], "foto.jpg"), waiting, progress);
  await vi.advanceTimersByTimeAsync(1000);
  await request;
  expect(paths).toEqual(["/api/source", "/api/source"]);
  expect(waiting).toHaveBeenCalledOnce();
  expect(progress).toHaveBeenCalledWith(4, 4);
});

it("propaga erro de upload medido sem declarar sucesso", async () => {
  class FakeXHR {
    status = 500;
    responseText = '{"detail":"Falha sintética"}';
    onload: (() => void) | null = null;
    upload = { addEventListener: () => {} };
    open() {}
    setRequestHeader() {}
    getResponseHeader() { return null; }
    send() { this.onload?.(); }
  }
  vi.stubGlobal("XMLHttpRequest", FakeXHR);
  await expect(uploadJpeg("/api/source", new File(["jpeg"], "foto.jpg"), undefined, vi.fn()))
    .rejects.toThrow("Falha sintética");
});
