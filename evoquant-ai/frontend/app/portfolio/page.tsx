"use client";

import { useState } from "react";
import { AppLayout } from "@/components/layout/AppLayout";
import { WagmiProvider } from "@/providers/WagmiProvider";
import { SolanaProvider } from "@/providers/SolanaProvider";
import { PortfolioChart, AllocationChart } from "@/components/charts/PortfolioChart";
import { usePortfolioSummary, usePortfolioHistory, useRiskMetrics, useAllocation } from "@/hooks/usePortfolio";
import { formatCurrency, formatPercent, getPnlColor, cn } from "@/lib/utils";
import { TrendingUp, TrendingDown, Shield, Activity, BarChart3, PieChart } from "lucide-react";

type Tab = "overview" | "positions" | "risk" | "history";

export default function PortfolioPage() {
  const [activeTab, setActiveTab] = useState<Tab>("overview");
  const [days, setDays] = useState(30);

  const { data: portfolio } = usePortfolioSummary();
  const { data: history } = usePortfolioHistory(days);
  const { data: risk } = useRiskMetrics();
  const { data: allocation } = useAllocation();

  const tabs = [
    { id: "overview" as Tab, label: "Overview", icon: BarChart3 },
    { id: "positions" as Tab, label: "Positions", icon: Activity },
    { id: "risk" as Tab, label: "Risk Metrics", icon: Shield },
    { id: "history" as Tab, label: "History", icon: TrendingUp },
  ];

  const summaryCards = [
    {
      label: "Total Value",
      value: formatCurrency(portfolio?.total_value),
      sub: `Daily P&L: ${formatCurrency(portfolio?.daily_pnl)}`,
      isPositive: (portfolio?.daily_pnl ?? 0) >= 0,
      icon: Activity,
    },
    {
      label: "Total P&L",
      value: formatCurrency(portfolio?.total_pnl),
      sub: portfolio?.is_paper ? "Paper Trading" : "Live Account",
      isPositive: (portfolio?.total_pnl ?? 0) >= 0,
      icon: (portfolio?.total_pnl ?? 0) >= 0 ? TrendingUp : TrendingDown,
    },
    {
      label: "Sharpe Ratio",
      value: portfolio?.sharpe_ratio ? portfolio.sharpe_ratio.toFixed(2) : "—",
      sub: `Max DD: ${portfolio?.max_drawdown ? (portfolio.max_drawdown * 100).toFixed(1) + "%" : "—"}`,
      isPositive: (portfolio?.sharpe_ratio ?? 0) > 1,
      icon: TrendingUp,
    },
    {
      label: "Win Rate",
      value: portfolio?.win_rate ? `${(portfolio.win_rate * 100).toFixed(1)}%` : "—",
      sub: `${portfolio?.open_positions ?? 0} open positions`,
      isPositive: (portfolio?.win_rate ?? 0) > 0.5,
      icon: PieChart,
    },
  ];

  return (
    <WagmiProvider>
      <SolanaProvider>
        <AppLayout>
          <div className="space-y-4 max-w-7xl mx-auto">
            <div className="flex items-center justify-between">
              <h1 className="text-xl font-bold text-white">Portfolio</h1>
              <div className={cn(
                "px-2.5 py-1 rounded-full text-xs font-medium border",
                portfolio?.is_paper
                  ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
                  : "bg-evo-green/10 text-evo-green border-evo-green/20"
              )}>
                {portfolio?.is_paper ? "Paper Trading" : "Live Account"}
              </div>
            </div>

            {/* Summary cards */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              {summaryCards.map((card) => (
                <div key={card.label} className="evo-card">
                  <div className="flex items-center gap-2 mb-2">
                    <card.icon className="w-4 h-4 text-muted-foreground" />
                    <span className="text-xs text-muted-foreground">{card.label}</span>
                  </div>
                  <div className="text-xl font-bold text-white">{card.value}</div>
                  <div className={cn("text-xs mt-0.5", card.isPositive ? "text-evo-green" : "text-evo-red")}>
                    {card.sub}
                  </div>
                </div>
              ))}
            </div>

            {/* Tabs */}
            <div className="flex gap-1 border-b border-evo-border">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={cn(
                    "flex items-center gap-1.5 px-3 py-2 text-sm font-medium transition-colors border-b-2 -mb-px",
                    activeTab === tab.id
                      ? "text-white border-evo-green"
                      : "text-muted-foreground border-transparent hover:text-white"
                  )}
                >
                  <tab.icon className="w-3.5 h-3.5" />
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Tab content */}
            {activeTab === "overview" && (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                <div className="lg:col-span-2 evo-card">
                  <div className="flex items-center justify-between mb-3">
                    <div className="text-sm font-semibold text-white">Portfolio Performance</div>
                    <div className="flex gap-1">
                      {[7, 30, 90, 365].map((d) => (
                        <button
                          key={d}
                          onClick={() => setDays(d)}
                          className={cn(
                            "px-2 py-0.5 text-xs rounded transition-colors",
                            days === d ? "bg-evo-green/20 text-evo-green" : "text-muted-foreground hover:text-white"
                          )}
                        >
                          {d}d
                        </button>
                      ))}
                    </div>
                  </div>
                  <PortfolioChart days={days} height={250} />
                </div>

                <div className="space-y-3">
                  <div className="evo-card">
                    <div className="text-sm font-semibold text-white mb-3">Allocation</div>
                    {allocation ? (
                      <AllocationChart allocation={allocation} />
                    ) : (
                      <div className="h-32 flex items-center justify-center text-sm text-muted-foreground">No positions</div>
                    )}
                  </div>

                  {portfolio && (
                    <div className="evo-card space-y-2">
                      <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Quick Stats</div>
                      {[
                        { label: "Cash", value: formatCurrency(portfolio.cash_balance) },
                        { label: "Margin Used", value: formatCurrency(portfolio.margin_used) },
                        { label: "Open Positions", value: String(portfolio.open_positions) },
                        { label: "Total Trades", value: String(portfolio.total_trades ?? "—") },
                      ].map(({ label, value }) => (
                        <div key={label} className="flex justify-between text-xs">
                          <span className="text-muted-foreground">{label}</span>
                          <span className="text-white font-mono">{value}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {activeTab === "positions" && (
              <div className="evo-card overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-evo-border">
                      {["Symbol", "Asset Class", "Qty", "Avg Cost", "Current", "Unrealized P&L", "Weight", "P&L %"].map((h) => (
                        <th key={h} className="text-left text-muted-foreground font-medium pb-2 pr-4">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {(portfolio?.positions ?? []).length === 0 ? (
                      <tr>
                        <td colSpan={8} className="py-8 text-center text-muted-foreground">No open positions</td>
                      </tr>
                    ) : (
                      (portfolio?.positions ?? []).map((pos: {
                        symbol: string;
                        asset_class: string;
                        quantity: number;
                        avg_cost: number;
                        current_price: number;
                        unrealized_pnl: number;
                        weight: number;
                      }) => {
                        const pnlPct = pos.avg_cost > 0 ? ((pos.current_price - pos.avg_cost) / pos.avg_cost) * 100 : 0;
                        return (
                          <tr key={pos.symbol} className="border-b border-evo-border/30 hover:bg-evo-surface/50">
                            <td className="py-2 pr-4 font-mono text-white font-medium">{pos.symbol}</td>
                            <td className="py-2 pr-4 text-muted-foreground capitalize">{pos.asset_class}</td>
                            <td className="py-2 pr-4 text-white font-mono">{pos.quantity.toFixed(4)}</td>
                            <td className="py-2 pr-4 text-white font-mono">{formatCurrency(pos.avg_cost)}</td>
                            <td className="py-2 pr-4 text-white font-mono">{formatCurrency(pos.current_price)}</td>
                            <td className={cn("py-2 pr-4 font-mono", getPnlColor(pos.unrealized_pnl))}>
                              {pos.unrealized_pnl >= 0 ? "+" : ""}{formatCurrency(pos.unrealized_pnl)}
                            </td>
                            <td className="py-2 pr-4 text-muted-foreground">{(pos.weight * 100).toFixed(1)}%</td>
                            <td className={cn("py-2 pr-4 font-mono", getPnlColor(pnlPct))}>
                              {pnlPct >= 0 ? "+" : ""}{pnlPct.toFixed(2)}%
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>
            )}

            {activeTab === "risk" && risk && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <div className="evo-card space-y-3">
                  <div className="text-sm font-semibold text-white">Value at Risk</div>
                  {[
                    { label: "VaR 95% (1-day)", value: formatCurrency(risk.var_95), color: "text-amber-400" },
                    { label: "VaR 99% (1-day)", value: formatCurrency(risk.var_99), color: "text-evo-red" },
                    { label: "CVaR 95%", value: formatCurrency(risk.cvar_95), color: "text-evo-red" },
                    { label: "Parametric VaR", value: formatCurrency(risk.parametric_var), color: "text-amber-400" },
                  ].map(({ label, value, color }) => (
                    <div key={label} className="flex justify-between items-center text-xs">
                      <span className="text-muted-foreground">{label}</span>
                      <span className={cn("font-mono font-semibold", color)}>{value}</span>
                    </div>
                  ))}
                </div>

                <div className="evo-card space-y-3">
                  <div className="text-sm font-semibold text-white">Performance Ratios</div>
                  {[
                    { label: "Sharpe Ratio", value: risk.sharpe?.toFixed(3) ?? "—" },
                    { label: "Sortino Ratio", value: risk.sortino?.toFixed(3) ?? "—" },
                    { label: "Calmar Ratio", value: risk.calmar?.toFixed(3) ?? "—" },
                    { label: "Max Drawdown", value: risk.max_drawdown ? `${(risk.max_drawdown * 100).toFixed(2)}%` : "—" },
                  ].map(({ label, value }) => (
                    <div key={label} className="flex justify-between items-center text-xs">
                      <span className="text-muted-foreground">{label}</span>
                      <span className="text-white font-mono font-semibold">{value}</span>
                    </div>
                  ))}
                </div>

                {risk.kelly_fraction !== undefined && (
                  <div className="evo-card lg:col-span-2">
                    <div className="text-sm font-semibold text-white mb-3">Kelly Criterion</div>
                    <div className="flex items-center gap-4">
                      <div className="text-3xl font-bold text-evo-green">
                        {(risk.kelly_fraction * 100).toFixed(1)}%
                      </div>
                      <div className="text-xs text-muted-foreground">
                        Recommended position size per trade (half-Kelly applied, max 25%)
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === "history" && (
              <div className="evo-card overflow-x-auto">
                <div className="text-sm font-semibold text-white mb-4">Portfolio Snapshots</div>
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-evo-border">
                      {["Date", "Total Value", "Daily P&L", "Cash", "Positions"].map((h) => (
                        <th key={h} className="text-left text-muted-foreground font-medium pb-2 pr-4">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {(history ?? []).length === 0 ? (
                      <tr>
                        <td colSpan={5} className="py-8 text-center text-muted-foreground">No history available</td>
                      </tr>
                    ) : (
                      (history ?? []).map((snap: {
                        timestamp: string;
                        total_value: number;
                        daily_pnl: number;
                        cash_balance: number;
                        open_positions: number;
                      }, i: number) => (
                        <tr key={i} className="border-b border-evo-border/30 hover:bg-evo-surface/50">
                          <td className="py-2 pr-4 text-muted-foreground">
                            {new Date(snap.timestamp).toLocaleDateString()}
                          </td>
                          <td className="py-2 pr-4 text-white font-mono">{formatCurrency(snap.total_value)}</td>
                          <td className={cn("py-2 pr-4 font-mono", getPnlColor(snap.daily_pnl))}>
                            {snap.daily_pnl >= 0 ? "+" : ""}{formatCurrency(snap.daily_pnl)}
                          </td>
                          <td className="py-2 pr-4 text-muted-foreground font-mono">{formatCurrency(snap.cash_balance)}</td>
                          <td className="py-2 pr-4 text-muted-foreground">{snap.open_positions}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </AppLayout>
      </SolanaProvider>
    </WagmiProvider>
  );
}
