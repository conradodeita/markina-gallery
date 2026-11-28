const photographerShellRoutes = new Set([
  "/admin",
  "/admin/galleries",
  "/admin/galleries/new",
  "/admin/clients",
  "/admin/payments",
  "/admin/notifications",
  "/admin/pricing",
  "/admin/settings",
]);

export function usesPhotographerShell(pathname: string) {
  return photographerShellRoutes.has(pathname) || /^\/admin\/galleries\/sources\/[^/]+$/.test(pathname);
}
