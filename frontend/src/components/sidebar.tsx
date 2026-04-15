"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  Brain,
  ChartNoAxesCombined,
  Home,
  Scale,
  Zap,
} from "lucide-react";
import { cn } from "@/lib/utils";

const links = [
  { href: "/", label: "Dashboard", icon: Home },
  { href: "/evaluate", label: "Avaliar Crédito", icon: Zap },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/fairness", label: "Fairness", icon: Scale },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex w-60 flex-col border-r border-zinc-800 bg-zinc-900">
      <div className="flex items-center gap-2.5 px-5 py-5 border-b border-zinc-800">
        <Brain className="h-5 w-5 text-indigo-400 shrink-0" />
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

      <div className="px-4 py-4 border-t border-zinc-800">
        <div className="flex items-center gap-2">
          <ChartNoAxesCombined className="h-4 w-4 text-emerald-400" />
          <span className="text-xs text-zinc-500">XGBoost · AUC 0.87</span>
        </div>
      </div>
    </aside>
  );
}
