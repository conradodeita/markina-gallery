import { ClientShell } from "../client-shell";

export default function GalleryLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <ClientShell>{children}</ClientShell>;
}
