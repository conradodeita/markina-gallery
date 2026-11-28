import { PRODUCT_NAME } from "./product-brand";
import type { Metadata, Viewport } from "next";
import { AppearanceToolbar } from "./appearance-toolbar";
import { InstallApp } from "./install-app";
import { themeBootstrap } from "./theme";
import { SessionBoundary } from "./session-boundary";
import { MonitorActivity } from "./monitor-activity";
import "./local-fonts.css";
import "./design-tokens.css";
import "./design-system.css";
import "./globals.css";
import "./visual-hierarchy.css";
import "./appearance.css";

export const metadata: Metadata = {
  title: PRODUCT_NAME,
  appleWebApp: { capable: true, title: PRODUCT_NAME, statusBarStyle: "default" },
  icons: { apple: "/api/branding/app-icon?size=180", icon: "/api/branding/favicon" },
  description:
    "Plataforma self-hosted de gestão, prova, venda e acompanhamento de fotografias escolares e de eventos",
};

export const viewport: Viewport = { themeColor: "#f2c343" };

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR" suppressHydrationWarning>
      <head><script dangerouslySetInnerHTML={{ __html: themeBootstrap }} /></head>
      <body><AppearanceToolbar><InstallApp /></AppearanceToolbar><SessionBoundary><MonitorActivity />{children}</SessionBoundary></body>
    </html>
  );
}
