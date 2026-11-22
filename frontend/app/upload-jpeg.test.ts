import { afterEach, expect, it, vi } from "vitest";
import { webcrypto } from "node:crypto";
import { confirmDuplicateJpegs, isJpegFilename, jpegFingerprint, jpegFingerprintFromStorageKey, jpegStorageKey, uploadJpeg } from "./upload-jpeg";

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  vi.useRealTimers();
  window.history.replaceState({}, "", "/");
});
it("separa uma nova intenção de upload sem perder a identidade do conteúdo", async () => {
  vi.stubGlobal("crypto", webcrypto);
  const file = new File(["synthetic-jpeg"], "foto.jpg");
  Object.defineProperty(file, "arrayBuffer", {value: async () => new TextEncoder().encode("synthetic-jpeg").buffer});
  const first = await jpegStorageKey("gallery", "folder", file, "00000000-0000-4000-8000-000000000001");
  expect(await jpegStorageKey("gallery", "folder", file, "00000000-0000-4000-8000-000000000001")).toBe(first);
  const deliberateResend = await jpegStorageKey("gallery", "folder", file, "00000000-0000-4000-8000-000000000002");
  expect(deliberateResend).not.toBe(first);
  expect(await jpegFingerprint(file)).toBe(jpegFingerprintFromStorageKey(first));
  expect(jpegFingerprintFromStorageKey("gallery/folder/" + "a".repeat(64) + ".jpg")).toBe("a".repeat(64));
  expect(await jpegStorageKey("gallery", "another-folder", file, "00000000-0000-4000-8000-000000000001")).not.toBe(first);
  expect(first).toMatch(/^gallery\/folder\/[a-f0-9]{64}-[a-f0-9-]{36}\.jpg$/);
});
it("pede confirmação de duplicadas e, ao recusar, mantém só arquivos novos", async () => {
  vi.stubGlobal("crypto", webcrypto);
  const duplicate = new File(["already-here"], "duplicate.jpg");
  const fresh = new File(["new-content"], "fresh.jpg");
  const duplicateHash = await jpegFingerprint(duplicate);
  const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
  const result = await confirmDuplicateJpegs([duplicate, fresh], (file) => file, [duplicateHash]);
  expect(result.items.map((file) => file.name)).toEqual(["fresh.jpg"]);
  expect(result.duplicateCount).toBe(1);
  expect(result.duplicateIndexes).toEqual([0]);
  expect(result.skippedCount).toBe(1);
  expect(result.confirmed).toBe(false);
  expect(confirm).toHaveBeenCalledWith(expect.stringContaining("1 crédito(s) adicional(is)"));
  confirm.mockRestore();
});

it("confirma todas as duplicadas quando o fotógrafo escolhe enviá-las", async () => {
  vi.stubGlobal("crypto", webcrypto);
  const duplicate = new File(["already-here"], "duplicate.jpg");
  const duplicateHash = await jpegFingerprint(duplicate);
  vi.spyOn(window, "confirm").mockReturnValue(true);
  const result = await confirmDuplicateJpegs([duplicate], (file) => file, [duplicateHash]);
  expect(result.items).toEqual([duplicate]);
  expect(result.duplicateIndexes).toEqual([0]);
  expect(result.confirmed).toBe(true);
  expect(result.skippedCount).toBe(0);
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

it("notifica o gate de onboarding sem transformar a resposta em sucesso", async () => {
  window.history.replaceState({}, "", "/admin/galleries/source-a?token=not-forwarded");
  const onGate = vi.fn();
  window.addEventListener("photographer-onboarding-required", onGate, { once: true });
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({
    detail: { code: "photographer_onboarding_required", settings_url: "/admin/settings" },
  }), { status: 409 })));

  await expect(uploadJpeg("/api/source", new File(["jpeg"], "foto.jpg")))
    .rejects.toThrow("Complete as etapas pendentes em Configurações");
  expect(onGate).toHaveBeenCalledOnce();
  expect((onGate.mock.calls[0][0] as CustomEvent).detail).toEqual({ returnTo: "/admin/galleries/source-a" });
});

it("rejeita fonte que não seja JPEG antes do envio", async () => {
  const fetch = vi.fn();
  vi.stubGlobal("fetch", fetch);
  const file = new File(["raw"], "evento.ARW");
  expect(isJpegFilename(file.name)).toBe(false);
  await expect(uploadJpeg("/api/source", file)).rejects.toThrow("Envie um arquivo JPEG.");
  expect(fetch).not.toHaveBeenCalled();
});
