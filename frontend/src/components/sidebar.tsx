"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  BarChart3,
  ChartNoAxesCombined,
  History,
  Home,
  Scale,
  Zap,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";

const links = [
  { href: "/", label: "Dashboard", icon: Home },
  { href: "/evaluate", label: "Avaliar Crédito", icon: Zap },
  { href: "/history", label: "Histórico", icon: History },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/fairness", label: "Fairness", icon: Scale },
];

type ApiStatus = "checking" | "online" | "offline";

export function Sidebar() {
  const pathname = usePathname();
  const [apiStatus, setApiStatus] = useState<ApiStatus>("checking");
  const [modelVersion, setModelVersion] = useState<string | null>(null);

  useEffect(() => {
    const check = async () => {
      try {
        const data = await api.health();
        setApiStatus("online");
        setModelVersion(data.model_version);
      } catch {
        setApiStatus("offline");
      }
    };
    check();
    const id = setInterval(check, 30_000);
    return () => clearInterval(id);
  }, []);

  return (
    <aside
      className="flex w-60 shrink-0 flex-col"
      style={{
        background: "rgba(8, 14, 8, 0.92)",
        borderRight: "1px solid rgba(0, 230, 118, 0.12)",
        backdropFilter: "blur(12px)",
      }}
    >
      {/* Brand header */}
      <div
        className="flex flex-col gap-2 px-5 py-5"
        style={{ borderBottom: "1px solid rgba(0, 230, 118, 0.10)" }}
      >
        {/* InfinityPay logo — inverted for dark background */}
        <div className="flex items-center">
          <Image
            src="/infinitypay-logo.svg"
            alt="InfinityPay"
            width={110}
            height={28}
            className="select-none"
            style={{ filter: "brightness(0) invert(1)" }}
            priority
          />
        </div>
        {/* Subtitle */}
        <span
          className="text-xs font-medium tracking-widest uppercase"
          style={{ color: "rgba(0, 230, 118, 0.6)" }}
        >
          Empathic Credit System
        </span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-0.5 px-3 py-4">
        {links.map(({ href, label, icon: Icon }) => {
          const isActive = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-all duration-150",
                isActive
                  ? "text-[#080c08] font-medium"
                  : "text-zinc-400 hover:text-white"
              )}
              style={
                isActive
                  ? {
                      background: "#00e676",
                      boxShadow: "0 0 14px rgba(0, 230, 118, 0.35)",
                    }
                  : undefined
              }
              onMouseEnter={(e) => {
                if (!isActive) {
                  (e.currentTarget as HTMLElement).style.background =
                    "rgba(0, 230, 118, 0.08)";
                }
              }}
              onMouseLeave={(e) => {
                if (!isActive) {
                  (e.currentTarget as HTMLElement).style.background = "";
                }
              }}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Status footer */}
      <div
        className="px-4 py-4 space-y-2"
        style={{ borderTop: "1px solid rgba(0, 230, 118, 0.10)" }}
      >
        <div className="flex items-center gap-2">
          <span
            className={cn("h-2 w-2 rounded-full shrink-0", {
              "bg-[#00e676]": apiStatus === "online",
              "bg-red-400": apiStatus === "offline",
              "bg-zinc-500": apiStatus === "checking",
            })}
            style={
              apiStatus === "online"
                ? { boxShadow: "0 0 6px rgba(0, 230, 118, 0.8)" }
                : undefined
            }
          />
          <span className="text-xs" style={{ color: "rgba(255,255,255,0.4)" }}>
            {apiStatus === "online"
              ? "API online"
              : apiStatus === "offline"
                ? "API offline"
                : "Verificando…"}
          </span>
        </div>
        {modelVersion && (
          <div className="flex items-center gap-2">
            <ChartNoAxesCombined
              className="h-3.5 w-3.5 shrink-0"
              style={{ color: "rgba(0, 230, 118, 0.5)" }}
            />
            <span
              className="text-xs truncate"
              style={{ color: "rgba(255,255,255,0.35)" }}
            >
              {modelVersion}
            </span>
          </div>
        )}
      </div>
    </aside>
  );
}
