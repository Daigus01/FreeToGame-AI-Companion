import "./globals.css";
import type { ReactNode } from "react";

export const metadata = { title: "FreeToGame AI Companion", description: "Descubre juegos F2P con un asistente de IA" };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
