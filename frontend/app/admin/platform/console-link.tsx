"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useConsoleAccess } from "./use-console-access";

export function ConsoleLink() {
  const { access, revalidating } = useConsoleAccess();
  const pathname = usePathname();
  return access === true && !revalidating ? <Link href="/admin/platform" aria-current={pathname.startsWith("/admin/platform") ? "page" : undefined}>Plataforma</Link> : null;
}
