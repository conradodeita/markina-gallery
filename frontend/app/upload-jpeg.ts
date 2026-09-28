/** Identidade estável para retomar o mesmo conteúdo dentro da mesma pasta. */
export async function jpegStorageKey(galleryId: string, folderId: string, file: File) {
  const digest = await crypto.subtle.digest("SHA-256", await file.arrayBuffer());
  const hash = Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
  return `${galleryId}/${folderId}/${hash}.jpg`;
}

function putWithProgress(path: string, file: File, onProgress: (loaded: number, total: number) => void) {
  return new Promise<{ ok: boolean; status: number; retryAfter: number; detail: string | null }>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", path);
    xhr.withCredentials = true;
    xhr.setRequestHeader("content-type", "image/jpeg");
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

/** Retenta a mesma foto sob pressão; nunca cria outro ativo a cada 503. */
export async function uploadJpeg(path: string, file: File, onWaiting?: () => void,
  onProgress?: (loaded: number, total: number) => void) {
  for (let attempt = 0; attempt <= 20; attempt++) {
    if (onProgress) {
      onProgress(0, file.size);
      const response = await putWithProgress(path, file, onProgress);
      if (response.ok) return;
      if (response.status === 503 && response.retryAfter > 0 && attempt < 20) {
        onWaiting?.();
        await new Promise((resolve) => setTimeout(resolve, Math.max(1, Math.min(60, response.retryAfter)) * 1000));
        continue;
      }
      throw new Error(response.detail ?? "Não foi possível enviar a foto. Tente novamente.");
    }
    const response = await fetch(path, { method: "PUT", credentials: "same-origin",
      headers: { "content-type": "image/jpeg" }, body: file });
    if (response.ok) return;
    const retryAfter = Number(response.headers?.get("Retry-After"));
    if (response.status === 503 && retryAfter > 0 && attempt < 20) {
      onWaiting?.();
      await new Promise((resolve) => setTimeout(resolve, Math.max(1, Math.min(60, retryAfter)) * 1000));
      continue;
    }
    const payload = await response.json().catch(() => null);
    throw new Error(payload?.detail ?? "Não foi possível enviar a foto. Tente novamente.");
  }
}
