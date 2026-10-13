/** Identidade estável para retomar o mesmo conteúdo dentro da mesma pasta. */
export async function jpegStorageKey(galleryId: string, folderId: string, file: File) {
  let digest: ArrayBuffer;
  if (isRawFilename(file.name)) {
    const chunks: Uint8Array[] = [];
    for (let offset = 0; offset < file.size; offset += 8 * 1024 * 1024) {
      chunks.push(new Uint8Array(await crypto.subtle.digest("SHA-256", await file.slice(offset, offset + 8 * 1024 * 1024).arrayBuffer())));
    }
    const tree = new Uint8Array(chunks.length * 32);
    chunks.forEach((chunk, index) => tree.set(chunk, index * 32));
    digest = await crypto.subtle.digest("SHA-256", tree);
  } else {
    digest = await crypto.subtle.digest("SHA-256", await file.arrayBuffer());
  }
  const hash = Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
  return `${galleryId}/${folderId}/${hash}.jpg`;
}

const RAW_EXTENSIONS = new Set([".arw", ".cr2", ".cr3", ".dng", ".nef", ".nrw", ".raf", ".rw2", ".rwl", ".pef", ".orf"]);

export function isRawFilename(filename: string) {
  const extension = filename.slice(filename.lastIndexOf(".")).toLowerCase();
  return RAW_EXTENSIONS.has(extension);
}

function putWithProgress(path: string, file: File, contentType: string, onProgress: (loaded: number, total: number) => void) {
  return new Promise<{ ok: boolean; status: number; retryAfter: number; detail: string | null }>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", path);
    xhr.withCredentials = true;
    xhr.setRequestHeader("content-type", contentType);
    xhr.upload.addEventListener("progress", (event) => {
      if (event.lengthComputable) onProgress(event.loaded, event.total);
    });
    xhr.onload = () => {
      let detail: string | null = null;
      try { detail = JSON.parse(xhr.responseText)?.detail ?? null; } catch { /* erro sem JSON */ }
      resolve({ ok: xhr.status >= 200 && xhr.status < 300, status: xhr.status,
        retryAfter: Number(xhr.getResponseHeader("Retry-After")), detail });
    };
    xhr.onerror = () => reject(new Error("Não foi possível enviar a foto. Verifique a conexão e tente novamente."));
    xhr.send(file);
  });
}

/** Envia JPEG pela rota existente, preservando progresso e tentativas atuais. */
export async function uploadJpeg(path: string, file: File, onWaiting?: () => void,
  onProgress?: (loaded: number, total: number) => void) {
  return uploadSource(path, file, "image/jpeg", onWaiting, onProgress);
}

/** RAW usa a mesma rota autenticada, mas entra no staging de conversão opt-in. */
export async function uploadPhotoSource(path: string, file: File, onWaiting?: () => void,
  onProgress?: (loaded: number, total: number) => void) {
  return uploadSource(path, file, isRawFilename(file.name) ? "application/octet-stream" : "image/jpeg", onWaiting, onProgress);
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
      throw new Error(response.detail ?? "Não foi possível enviar o arquivo para processamento.");
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
    throw new Error(payload?.detail ?? "Não foi possível enviar o arquivo para processamento.");
  }
}
