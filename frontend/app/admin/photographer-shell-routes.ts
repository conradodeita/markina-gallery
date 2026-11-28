const photographerShellRoutes = new Set(["/admin", "/admin/galleries", "/admin/clients"]);

export function usesPhotographerShell(pathname: string) {
  return photographerShellRoutes.has(pathname);
}
