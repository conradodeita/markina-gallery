export function safeOrderAlbumUrl(value: string | null | undefined): string | null {
  if (!value || /[\x00-\x20\x7f\\]/.test(value) || value.length > 2048) return null;
  try {
    const url = new URL(value);
    const pathAllowed = url.hostname === "photos.app.goo.gl" ? /^\/[A-Za-z0-9_-]+\/?$/.test(url.pathname)
      : url.hostname === "photos.google.com" && /^\/share\/[A-Za-z0-9_-]+\/?$/.test(url.pathname);
    return url.protocol === "https:" && !url.username && !url.password && !url.port && pathAllowed ? value : null;
  } catch { return null; }
}
