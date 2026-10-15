"use client";
import Link from "next/link";
import { useMonitorPermissions } from "./use-permissions";

export function MonitorLink() {
  const { permissions } = useMonitorPermissions();
  if (!permissions || !Object.values(permissions).some(Boolean)) return null;
  return <Link href="/admin/system-monitor">Monitor do sistema</Link>;
}
