"use client";

import { usePathname } from "next/navigation";
import { AdminSessionToolbar } from "./admin-session-toolbar";
import { InstallApp } from "./install-app";
import { ThemeControl } from "./theme-control";

export function AppearanceToolbar() {
  if (usePathname() === "/admin") return null;

  return (
    <div className="appearance-toolbar">
      <ThemeControl />
      <AdminSessionToolbar />
      <InstallApp />
    </div>
  );
}
