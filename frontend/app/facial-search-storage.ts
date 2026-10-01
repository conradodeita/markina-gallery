// Somente UUID da consulta: nenhum token, arquivo, vetor ou identidade pessoal.
const prefix = "markina:facial-search:";

export function clearFacialSearchStorage(context?: string) {
  try {
    const keepPrefix = context ? `${prefix}v2:${context}:` : null;
    for (const key of Object.keys(window.sessionStorage)) {
      if (key.startsWith(prefix) && (!keepPrefix || !key.startsWith(keepPrefix))) {
        window.sessionStorage.removeItem(key);
      }
    }
  } catch { /* A retomada é opcional quando storage está indisponível. */ }
}

export function facialSearchStorageKey(context: string | undefined, galleryId: string) {
  return context && /^[a-f0-9]{64}$/.test(context) ? `${prefix}v2:${context}:${galleryId}` : null;
}

export function readFacialSearchStorage(key: string | null) {
  try { return key ? window.sessionStorage.getItem(key) : null; } catch { return null; }
}

export function rememberFacialSearch(key: string | null, requestId: string | null) {
  try {
    if (!key) return;
    if (requestId) window.sessionStorage.setItem(key, requestId);
    else window.sessionStorage.removeItem(key);
  } catch { /* O backend continua sendo a fonte autorizada da consulta. */ }
}
