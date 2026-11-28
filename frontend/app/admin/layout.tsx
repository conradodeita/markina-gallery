"use client";

import { BrandLogo } from "../brand-logo";
import { OnboardingGateNotice } from "./onboarding-gate-notice";
import { TenantAddressNotice } from "./tenant-address-notice";
import Link from "next/link";
import { AdminNavigation } from "./admin-navigation";
import { usePathname } from "next/navigation";
import { OverviewShell } from "./overview-shell";

export default function AdminLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  if (usePathname() === "/admin") return <OverviewShell>{children}</OverviewShell>;

  return <div className="admin-frame"><header className="admin-topbar"><Link className="admin-brand" href="/admin"><BrandLogo /><small>Central do fotógrafo</small></Link><AdminNavigation /></header><OnboardingGateNotice /><main className="admin-content"><TenantAddressNotice />{children}</main></div>;
}
