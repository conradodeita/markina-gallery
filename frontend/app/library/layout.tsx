import { ClientShell } from "../client-shell";

export default function LibraryLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <ClientShell>{children}</ClientShell>;
}
