import { notifyPhotographerOnboardingGate } from "./photographer-onboarding-gate";

/** Fingerprint do conteúdo, independente da identidade de uma tentativa de envio. */
export async function jpegFingerprint(file: File) {
  const digest = await crypto.subtle.digest("SHA-256", await file.arrayBuffer());
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

export class UploadJpegError extends Error {
  constructor(message: string, readonly httpStatus: number | null) {
    super(message);
    this.name = "UploadJpegError";
  }
}

/** Identidade estável do mesmo intento e distinta para cada novo envio deliberado. */
export async function jpegStorageKey(galleryId: string, folderId: string, file: File,
  uploadIntentId = crypto.randomUUID()) {
  const hash = await jpegFingerprint(file);
  return `${galleryId}/${folderId}/${hash}-${uploadIntentId}.jpg`;
}

/** Lê fingerprints de chaves novas e legadas, inclusive as lógicas de lote. */
export function jpegFingerprintFromStorageKey(storageKey: string) {
  const basename = storageKey.split("/").at(-1) ?? "";
  const match = /^([a-f0-9]{64})(?:-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})?\.jpg$/i.exec(basename);
  return match?.[1]?.toLowerCase() ?? null;
}

export async function confirmDuplicateJpegs<T>(
  items: T[],
  fileFor: (item: T) => File,
  existingFingerprints: Array<string | null | undefined>,
) {
  const known = new Set(existingFingerprints.filter((fingerprint): fingerprint is string =>
    typeof fingerprint === "string" && /^[a-f0-9]{64}$/i.test(fingerprint)));
  const duplicateIndexes = new Set<number>();
  for (const [index, item] of items.entries()) {
    const fingerprint = await jpegFingerprint(fileFor(item));
    if (known.has(fingerprint)) duplicateIndexes.add(index);
    else known.add(fingerprint);
  }
  if (!duplicateIndexes.size) {
    return { items, duplicateCount: 0, duplicateIndexes: [], skippedCount: 0, confirmed: false };
  }

  const duplicateCount = duplicateIndexes.size;
  const duplicateLabel = duplicateCount === 1
    ? "1 arquivo repetido"
    : `${duplicateCount} arquivos repetidos`;
  const confirmed = window.confirm(
    `Esta seleção contém ${duplicateLabel} (com os mesmos bytes de fotos da pasta ou de outro arquivo selecionado). Reenviar cria cópias e, em carteiras finitas, consome até ${duplicateCount} crédito(s) adicional(is). A conta ilimitada do proprietário não tem débito.\n\nConfirmar envia as repetidas. Cancelar pula somente essas fotos e continua com os arquivos novos.`,
  );
  return {
    items: confirmed ? items : items.filter((_item, index) => !duplicateIndexes.has(index)),
    duplicateCount,
    duplicateIndexes: [...duplicateIndexes],
    skippedCount: confirmed ? 0 : duplicateCount,
    confirmed,
  };
}

export function isJpegFilename(filename: string) {
  return /\.(jpe?g)$/i.test(filename);
}

function putWithProgress(path: string, file: File, contentType: string, onProgress: (loaded: number, total: number) => void) {
  return new Promise<{ ok: boolean; status: number; retryAfter: number; detail: unknown }>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", path);
    xhr.withCredentials = true;
    xhr.setRequestHeader("content-type", contentType);
    xhr.upload.addEventListener("progress", (event) => {
      if (event.lengthComputable) onProgress(event.loaded, event.total);
    });
    xhr.onload = () => {
      let detail: unknown = null;
      try { detail = JSON.parse(xhr.responseText)?.detail ?? null; } catch { /* erro sem JSON */ }
      resolve({ ok: xhr.status >= 200 && xhr.status < 300, status: xhr.status,
        retryAfter: Number(xhr.getResponseHeader("Retry-After")), detail });
    };
    xhr.onerror = () => reject(new UploadJpegError("Não foi possível enviar a foto. Verifique a conexão e tente novamente.", null));
    xhr.send(file);
  });
}

/** Envia JPEG pela rota existente, preservando progresso e tentativas atuais. */
export async function uploadJpeg(path: string, file: File, onWaiting?: () => void,
  onProgress?: (loaded: number, total: number) => void) {
  if (!isJpegFilename(file.name)) throw new Error("Envie um arquivo JPEG.");
  return uploadSource(path, file, "image/jpeg", onWaiting, onProgress);
}

async function uploadSource(path: string, file: File, contentType: string, onWaiting?: () => void,
  onProgress?: (loaded: number, total: number) => void) {
  for (let attempt = 0; attempt <= 20; attempt++) {
    if (onProgress) {
      onProgress(0, file.size);
      const response = await putWithProgress(path, file, contentType, onProgress);
      if (response.ok) return;
      if (response.status === 503 && response.retryAfter > 0 && attempt < 20) {
        onWaiting?.();
        await new Promise((resolve) => setTimeout(resolve, Math.max(1, Math.min(60, response.retryAfter)) * 1000));
        continue;
      }
      if (notifyPhotographerOnboardingGate(response.detail)) {
        throw new UploadJpegError("Complete as etapas pendentes em Configurações e tente enviar novamente.", response.status);
      }
      throw new UploadJpegError(typeof response.detail === "string"
        ? response.detail : "Não foi possível enviar o arquivo para processamento.", response.status);
    }
    const response = await fetch(path, { method: "PUT", credentials: "same-origin",
      headers: { "content-type": contentType }, body: file });
    if (response.ok) return;
    const retryAfter = Number(response.headers?.get("Retry-After"));
    if (response.status === 503 && retryAfter > 0 && attempt < 20) {
      onWaiting?.();
      await new Promise((resolve) => setTimeout(resolve, Math.max(1, Math.min(60, retryAfter)) * 1000));
      continue;
    }
    const payload = await response.json().catch(() => null);
    const detail = payload && typeof payload === "object" ? payload.detail : null;
    if (notifyPhotographerOnboardingGate(detail)) {
      throw new UploadJpegError("Complete as etapas pendentes em Configurações e tente enviar novamente.", response.status);
    }
    throw new UploadJpegError(typeof detail === "string"
      ? detail : "Não foi possível enviar o arquivo para processamento.", response.status);
  }
}
