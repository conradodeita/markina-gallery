"use client";

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { usesPhotographerShell } from "./admin/photographer-shell-routes";
import { AdminSessionToolbar } from "./admin-session-toolbar";
import { ThemeControl } from "./theme-control";

export function AppearanceToolbar({ children }: { children: ReactNode }) {
  const integrated = usesPhotographerShell(usePathname());
  return (
    <div className={integrated ? "appearance-toolbar appearance-toolbar--integrated" : "appearance-toolbar"}>
      {!integrated && <><ThemeControl /><AdminSessionToolbar /></>}
      {children}
    </div>
  );
}
