/** Identidade estável para retomar o mesmo conteúdo dentro da mesma pasta. */
export async function jpegStorageKey(galleryId: string, folderId: string, file: File) {
  const digest = await crypto.subtle.digest("SHA-256", await file.arrayBuffer());
  const hash = Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
  return `${galleryId}/${folderId}/${hash}.jpg`;
}

/** Retenta a mesma foto sob pressão; nunca cria outro ativo a cada 503. */
export async function uploadJpeg(path: string, file: File, onWaiting?: () => void) {
  for (let attempt = 0; attempt <= 20; attempt++) {
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
