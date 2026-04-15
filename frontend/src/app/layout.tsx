import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/sidebar";
import { WebGLRings } from "@/components/webgl-rings";
import { Toaster } from "sonner";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans" });

export const metadata: Metadata = {
  title: "Empathic Credit System",
  description: "ML-powered credit scoring with explainable AI",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" className={`${inter.variable} h-full`} suppressHydrationWarning>
      <body className="h-full antialiased">
        {/* Animated ring background */}
        <WebGLRings />

        {/* Radial glow blobs */}
        <div className="bg-blob bg-blob-green" aria-hidden="true" />
        <div className="bg-blob bg-blob-cyan" aria-hidden="true" />

        {/* App shell — above background layers */}
        <div className="relative z-10 flex h-full">
          <Sidebar />
          <main className="flex-1 overflow-auto">{children}</main>
        </div>

        <Toaster
          theme="dark"
          position="bottom-right"
          toastOptions={{
            style: {
              background: "#0e180e",
              border: "1px solid rgba(0, 230, 118, 0.2)",
              color: "#e8f5e9",
            },
          }}
        />
      </body>
    </html>
  );
}
