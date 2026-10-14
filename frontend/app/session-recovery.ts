export function protectedContext(pathname: string): "admin" | "client" | null {
  if (["/admin/reset-password", "/admin/verify-email"].includes(pathname)) return null;
  if (pathname === "/admin" || pathname.startsWith("/admin/")) return "admin";
  if (["/library", "/gallery", "/public-galleries"].some((base) => pathname === base || pathname.startsWith(`${base}/`))) return "client";
  return null;
}

export function safeAdminReturn(value: string) {
  return /^\/admin(?:\/[a-zA-Z0-9_-]+)*$/.test(value) && protectedContext(value) === "admin" ? value : "/admin";
}

export function safeClientGalleryReturn(value: string) {
  const match = /^\/public-galleries\/([0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})$/i.exec(value);
  return match ? { path: value, galleryId: match[1] } : null;
}

export function recoveryLocation(pathname: string) {
  const context = protectedContext(pathname) ?? "client";
  const params = new URLSearchParams({ reauth: context });
  if (context === "admin") params.set("return_to", safeAdminReturn(pathname));
  if (context === "client") {
    const target = safeClientGalleryReturn(pathname);
    if (target) params.set("return_to", target.path);
  }
  return `/?${params}`;
}
