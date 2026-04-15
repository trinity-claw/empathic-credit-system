"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  BarChart3,
  Brain,
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
    <aside className="flex w-60 shrink-0 flex-col border-r border-zinc-800 bg-zinc-900">
      <div className="flex items-center gap-2.5 border-b border-zinc-800 px-5 py-5">
        <Brain className="h-5 w-5 shrink-0 text-indigo-400" />
        <span className="text-sm font-semibold tracking-tight">
          Empathic Credit
        </span>
      </div>

      <nav className="flex-1 space-y-0.5 px-3 py-4">
        {links.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
              pathname === href
                ? "bg-indigo-500/20 text-indigo-300"
                : "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100"
            )}
          >
            <Icon className="h-4 w-4 shrink-0" />
            {label}
          </Link>
        ))}
      </nav>

      <div className="border-t border-zinc-800 px-4 py-4 space-y-2">
        <div className="flex items-center gap-2">
          <span
            className={cn(
              "h-2 w-2 rounded-full shrink-0",
              apiStatus === "online" && "bg-emerald-400",
              apiStatus === "offline" && "bg-red-400",
              apiStatus === "checking" && "bg-zinc-500"
            )}
          />
          <span className="text-xs text-zinc-500">
            {apiStatus === "online"
              ? "API online"
              : apiStatus === "offline"
                ? "API offline"
                : "Verificando…"}
          </span>
        </div>
        {modelVersion && (
          <div className="flex items-center gap-2">
            <ChartNoAxesCombined className="h-3.5 w-3.5 text-indigo-400 shrink-0" />
            <span className="text-xs text-zinc-500 truncate">{modelVersion}</span>
          </div>
        )}
      </div>
    </aside>
  );
}
