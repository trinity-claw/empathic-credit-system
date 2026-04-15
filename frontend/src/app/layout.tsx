import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/sidebar";
import { Toaster } from "sonner";

// Inter is the industry standard for dashboards — crisp, legible, neutral
const inter = Inter({ subsets: ["latin"], variable: "--font-sans" });

export const metadata: Metadata = {
  title: "Empathic Credit System",
  description: "ML-powered credit scoring with explainable AI",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" className={`${inter.variable} h-full`} suppressHydrationWarning>
      <body className="h-full bg-zinc-950 text-zinc-100 antialiased">
        <div className="flex h-full">
          <Sidebar />
          <main className="flex-1 overflow-auto">{children}</main>
        </div>
        <Toaster
          theme="dark"
          position="bottom-right"
          toastOptions={{
            style: { background: "#18181b", border: "1px solid #3f3f46", color: "#e4e4e7" },
          }}
        />
      </body>
    </html>
  );
}
