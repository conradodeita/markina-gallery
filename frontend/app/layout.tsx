import type { Metadata, Viewport } from "next";
import { InstallApp } from "./install-app";
import "./local-fonts.css";
import "./design-tokens.css";
import "./design-system.css";
import "./globals.css";
import "./visual-hierarchy.css";

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
    <html lang="pt-BR">
      <body><InstallApp />{children}</body>
    </html>
  );
}
