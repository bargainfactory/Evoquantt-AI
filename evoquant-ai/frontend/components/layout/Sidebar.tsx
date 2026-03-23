"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/store/useAppStore";
import {
  LayoutDashboard, TrendingUp, Activity, FlaskConical, Zap,
  Wallet, BarChart3, Shield, Settings, ChevronLeft, ChevronRight,
  Bot, Bell, BookOpen, Repeat2, Globe,
} from "lucide-react";

const NAV_ITEMS = [
  { href: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
  { href: "/trading", icon: TrendingUp, label: "Trading" },
  { href: "/options", icon: BarChart3, label: "Options" },
  { href: "/recursive-sell", icon: Repeat2, label: "Recursive Sell" },
  { href: "/evolution-lab", icon: FlaskConical, label: "Evolution Lab" },
  { href: "/dex", icon: Globe, label: "DEX Routing" },
  { href: "/portfolio", icon: Activity, label: "Portfolio" },
  { href: "/backtester", icon: BookOpen, label: "Backtester" },
  { href: "/alerts", icon: Bell, label: "Alerts" },
  { href: "/ai-copilot", icon: Bot, label: "Ask Evo" },
  { href: "/security", icon: Shield, label: "Security" },
  { href: "/settings", icon: Settings, label: "Settings" },
];

export function Sidebar() {
  const pathname = usePathname();
  const { sidebarCollapsed, toggleSidebar, isPaper, togglePaper } = useAppStore();

  return (
    <aside
      className={cn(
        "flex flex-col bg-evo-surface border-r border-evo-border transition-all duration-300 relative z-20",
        sidebarCollapsed ? "w-16" : "w-56"
      )}
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 py-4 border-b border-evo-border min-h-[60px]">
        <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-evo-green/20 flex items-center justify-center">
          <Zap className="w-4 h-4 text-evo-green" />
        </div>
        {!sidebarCollapsed && (
          <div>
            <div className="text-sm font-bold text-white leading-none">EvoQuant</div>
            <div className="text-xs text-evo-green leading-none mt-0.5">AI Trading</div>
          </div>
        )}
      </div>

      {/* Paper / Live toggle */}
      {!sidebarCollapsed && (
        <div className="px-3 py-3 border-b border-evo-border">
          <button
            onClick={togglePaper}
            className={cn(
              "w-full flex items-center justify-center gap-2 py-1.5 rounded-md text-xs font-medium transition-colors",
              isPaper
                ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                : "bg-green-500/10 text-green-400 border border-green-500/20"
            )}
          >
            <div className={cn("w-2 h-2 rounded-full", isPaper ? "bg-amber-400" : "bg-green-400 animate-pulse")} />
            {isPaper ? "Paper Trading" : "Live Trading"}
          </button>
        </div>
      )}

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-2">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-3 py-2 mx-2 my-0.5 rounded-md text-sm transition-all group",
                isActive
                  ? "bg-evo-green/10 text-evo-green border border-evo-green/20"
                  : "text-muted-foreground hover:text-white hover:bg-white/5"
              )}
            >
              <item.icon className={cn("w-4 h-4 flex-shrink-0", isActive ? "text-evo-green" : "")} />
              {!sidebarCollapsed && <span className="truncate">{item.label}</span>}
            </Link>
          );
        })}
      </nav>

      {/* Collapse button */}
      <button
        onClick={toggleSidebar}
        className="absolute -right-3 top-1/2 -translate-y-1/2 w-6 h-6 rounded-full bg-evo-surface border border-evo-border flex items-center justify-center hover:border-evo-green/50 transition-colors"
      >
        {sidebarCollapsed ? (
          <ChevronRight className="w-3 h-3 text-muted-foreground" />
        ) : (
          <ChevronLeft className="w-3 h-3 text-muted-foreground" />
        )}
      </button>
    </aside>
  );
}
