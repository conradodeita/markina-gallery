const photographerShellRoutes = new Set(["/admin", "/admin/galleries", "/admin/clients", "/admin/payments"]);

export function usesPhotographerShell(pathname: string) {
  return photographerShellRoutes.has(pathname);
}
