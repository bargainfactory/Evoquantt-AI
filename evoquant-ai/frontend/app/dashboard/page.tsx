"use client";

import { useQuery } from "@tanstack/react-query";
import { AppLayout } from "@/components/layout/AppLayout";
import { WagmiProvider } from "@/providers/WagmiProvider";
import { SolanaProvider } from "@/providers/SolanaProvider";
import { PortfolioChart } from "@/components/charts/PortfolioChart";
import api from "@/lib/api";
import { usePortfolioSummary } from "@/hooks/usePortfolio";
import { useMarketStore } from "@/store/useMarketStore";
import { useRealTimeTick } from "@/hooks/useMarketData";
import { formatCurrency, formatPercent, getPnlColor, cn } from "@/lib/utils";
import { TrendingUp, TrendingDown, Activity, Shield, Zap, Globe } from "lucide-react";
import Link from "next/link";

function WatchlistItem({ symbol }: { symbol: string }) {
  const tick = useRealTimeTick(symbol);
  return (
    <div className="flex items-center justify-between py-2 border-b border-evo-border/50 last:border-0">
      <span className="text-sm font-medium text-white">{symbol}</span>
      <div className="text-right">
        <div className="text-sm font-mono text-white">{tick?.price ? `$${tick.price.toFixed(4)}` : "—"}</div>
        {tick && (
          <div className={cn("text-xs font-mono", tick.change_pct >= 0 ? "text-evo-green" : "text-evo-red")}>
            {tick.change_pct >= 0 ? "+" : ""}{tick.change_pct.toFixed(2)}%
          </div>
        )}
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const { data: portfolio } = usePortfolioSummary();
  const { data: macro } = useQuery({ queryKey: ["macro"], queryFn: () => api.getMacro().then((r) => r.data), staleTime: 600000 });
  const watchlist = useMarketStore((s) => s.watchlist);

  const stats = [
    {
      label: "Portfolio Value",
      value: formatCurrency(portfolio?.total_value),
      change: formatPercent(portfolio?.daily_pnl ? (portfolio.daily_pnl / (portfolio.total_value - portfolio.daily_pnl)) * 100 : 0),
      isPositive: (portfolio?.daily_pnl ?? 0) >= 0,
      icon: Activity,
      href: "/portfolio",
    },
    {
      label: "Today's P&L",
      value: formatCurrency(portfolio?.daily_pnl),
      change: portfolio?.is_paper ? "Paper" : "Live",
      isPositive: (portfolio?.daily_pnl ?? 0) >= 0,
      icon: portfolio?.daily_pnl >= 0 ? TrendingUp : TrendingDown,
      href: "/trading",
    },
    {
      label: "Sharpe Ratio",
      value: portfolio?.sharpe_ratio ? portfolio.sharpe_ratio.toFixed(2) : "—",
      change: portfolio?.max_drawdown ? `DD: ${(portfolio.max_drawdown * 100).toFixed(1)}%` : "",
      isPositive: (portfolio?.sharpe_ratio ?? 0) > 1,
      icon: TrendingUp,
      href: "/portfolio",
    },
    {
      label: "Win Rate",
      value: portfolio?.win_rate ? `${(portfolio.win_rate * 100).toFixed(1)}%` : "—",
      change: `Total P&L: ${formatCurrency(portfolio?.total_pnl)}`,
      isPositive: (portfolio?.win_rate ?? 0) > 0.5,
      icon: Zap,
      href: "/portfolio",
    },
  ];

  return (
    <WagmiProvider>
      <SolanaProvider>
        <AppLayout>
          <div className="space-y-4 max-w-7xl mx-auto">
            <div className="flex items-center justify-between">
              <h1 className="text-xl font-bold text-white">Dashboard</h1>
              <div className="flex items-center gap-2">
                {macro?.macro_regime && (
                  <span className={cn(
                    "text-xs px-2.5 py-1 rounded-full border",
                    macro.macro_regime.overall === "bullish" ? "evo-badge-green" : "evo-badge-red"
                  )}>
                    Macro: {macro.macro_regime.overall}
                  </span>
                )}
              </div>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              {stats.map((stat) => (
                <Link key={stat.label} href={stat.href}>
                  <div className="evo-card hover:border-evo-green/30 transition-colors cursor-pointer">
                    <div className="flex items-center gap-2 mb-2">
                      <stat.icon className="w-4 h-4 text-muted-foreground" />
                      <span className="text-xs text-muted-foreground">{stat.label}</span>
                    </div>
                    <div className="text-xl font-bold text-white">{stat.value}</div>
                    <div className={cn("text-xs mt-0.5", stat.isPositive ? "text-evo-green" : "text-evo-red")}>
                      {stat.change}
                    </div>
                  </div>
                </Link>
              ))}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              {/* Portfolio chart */}
              <div className="lg:col-span-2 evo-card">
                <div className="flex items-center justify-between mb-3">
                  <div className="text-sm font-semibold text-white">Portfolio Performance</div>
                  <div className="flex gap-1">
                    {[7, 30, 90].map((d) => (
                      <button key={d} className="px-2 py-0.5 text-xs text-muted-foreground hover:text-white rounded">{d}d</button>
                    ))}
                  </div>
                </div>
                <PortfolioChart days={30} height={200} />
              </div>

              {/* Watchlist */}
              <div className="evo-card">
                <div className="text-sm font-semibold text-white mb-3">Watchlist</div>
                {watchlist.slice(0, 8).map((sym) => (
                  <WatchlistItem key={sym} symbol={sym} />
                ))}
                <Link href="/trading" className="text-xs text-evo-green hover:underline mt-2 block">View all →</Link>
              </div>
            </div>

            {/* Quick actions */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {[
                { href: "/trading", icon: TrendingUp, label: "Start Trading", color: "text-evo-green", bg: "bg-evo-green/10" },
                { href: "/recursive-sell", icon: Zap, label: "Recursive Sell Lab", color: "text-evo-purple", bg: "bg-evo-purple/10" },
                { href: "/dex", icon: Globe, label: "DEX Routing", color: "text-evo-blue", bg: "bg-evo-blue/10" },
                { href: "/security", icon: Shield, label: "Security Status", color: "text-evo-orange", bg: "bg-evo-orange/10" },
              ].map(({ href, icon: Icon, label, color, bg }) => (
                <Link key={href} href={href}>
                  <div className={cn("evo-card flex items-center gap-3 hover:border-evo-green/20 transition-colors cursor-pointer")}>
                    <div className={cn("w-8 h-8 rounded-lg flex items-center justify-center", bg)}>
                      <Icon className={cn("w-4 h-4", color)} />
                    </div>
                    <span className="text-sm text-white">{label}</span>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </AppLayout>
      </SolanaProvider>
    </WagmiProvider>
  );
}
