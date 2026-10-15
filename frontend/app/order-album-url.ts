export function safeExternalAlbumUrl(value: string | null | undefined): string | null {
  if (!value || /[\x00-\x20\x7f\\]/.test(value) || value.length > 2048) return null;
  try {
    const url = new URL(value);
    const hostname = url.hostname.toLowerCase();
    const labels = hostname.replace(/\.$/, "").split(".");
    const reservedSuffix = [".localhost", ".local", ".internal", ".test", ".invalid"]
      .some((suffix) => hostname.endsWith(suffix));
    const publicHostname = hostname.length <= 253 && hostname.includes(".") && !hostname.includes(":")
      && !/^\d+(?:\.\d+){3}$/.test(hostname) && !reservedSuffix
      && labels.every((label) => label.length > 0 && label.length <= 63 && /^[a-z0-9-]+$/i.test(label)
        && !label.startsWith("-") && !label.endsWith("-"));
    const hasShareTarget = (url.pathname !== "" && url.pathname !== "/") || Boolean(url.search || url.hash);
    return url.protocol === "https:" && publicHostname && hasShareTarget
      && !url.username && !url.password && !url.port ? value : null;
  } catch { return null; }
}
