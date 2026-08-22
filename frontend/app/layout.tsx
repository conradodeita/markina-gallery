import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Markina Gallery",
  description:
    "Plataforma self-hosted de gestão, prova, venda e acompanhamento de fotografias escolares e de eventos",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
