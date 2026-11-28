const photographerShellRoutes = new Set([
  "/admin",
  "/admin/galleries",
  "/admin/galleries/new",
  "/admin/clients",
  "/admin/payments",
  "/admin/notifications",
  "/admin/pricing",
]);

export function usesPhotographerShell(pathname: string) {
  return photographerShellRoutes.has(pathname);
}
