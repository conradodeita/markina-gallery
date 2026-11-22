export function safeExternalAlbumUrl(value: string | null | undefined): string | null {
  if (!value || /[\x00-\x20\x7f\\]/.test(value) || value.length > 2048) return null;
  try {
    const url = new URL(value);
    const hostname = url.hostname.toLowerCase();
    const validGooglePhotosPath = (hostname === "photos.app.goo.gl" && /^\/[^/]+\/?$/.test(url.pathname))
      || (hostname === "photos.google.com" && /^\/share\/[^/]+\/?$/.test(url.pathname));
    return url.protocol === "https:" && validGooglePhotosPath
      && !url.username && !url.password && !url.port ? value : null;
  } catch { return null; }
}
