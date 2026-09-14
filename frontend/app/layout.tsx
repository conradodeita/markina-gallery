import type { Metadata, Viewport } from "next";
import { InstallApp } from "./install-app";
import { ThemeControl } from "./theme-control";
import { themeBootstrap } from "./theme";
import "./local-fonts.css";
import "./design-tokens.css";
import "./design-system.css";
import "./globals.css";
import "./visual-hierarchy.css";
import "./appearance.css";

export const metadata: Metadata = {
  title: "Markina Gallery",
  appleWebApp: { capable: true, title: "Markina", statusBarStyle: "default" },
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
      <body><div className="appearance-toolbar"><ThemeControl /><InstallApp /></div>{children}</body>
    </html>
  );
}
