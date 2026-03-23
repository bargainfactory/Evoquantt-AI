import type { Metadata, Viewport } from "next";
import { Toaster } from "react-hot-toast";
import { QueryProvider } from "@/providers/QueryProvider";
import "./globals.css";

export const metadata: Metadata = {
  title: "EvoQuant AI — Advanced Trading Platform",
  description: "Production-ready full-stack trading platform with quantum-proof security, recursive sell optimization, Uniswap V4, Jupiter DEX routing, and multi-broker support.",
  manifest: "/manifest.json",
  icons: { icon: "/favicon.ico" },
  openGraph: {
    title: "EvoQuant AI",
    description: "The most advanced AI-powered trading platform",
    type: "website",
  },
};

export const viewport: Viewport = {
  themeColor: "#00D09C",
  colorScheme: "dark",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased">
        <QueryProvider>
          {children}
          <Toaster
            position="top-right"
            toastOptions={{
              style: {
                background: "#161B22",
                color: "#F0F6FC",
                border: "1px solid #30363D",
                fontSize: "13px",
              },
              success: { iconTheme: { primary: "#00D09C", secondary: "#0D1117" } },
              error: { iconTheme: { primary: "#FF4B4B", secondary: "#0D1117" } },
            }}
          />
        </QueryProvider>
      </body>
    </html>
  );
}
