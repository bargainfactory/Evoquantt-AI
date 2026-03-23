"use client";

import { useState } from "react";
import { AppLayout } from "@/components/layout/AppLayout";
import { WagmiProvider } from "@/providers/WagmiProvider";
import { SolanaProvider } from "@/providers/SolanaProvider";
import { useMutation, useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import toast from "react-hot-toast";
import { Play, BarChart3, TrendingUp, Activity } from "lucide-react";
import { cn, formatCurrency, formatPercent } from "@/lib/utils";
import dynamic from "next/dynamic";
import type { Data, Layout } from "plotly.js";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

interface BacktestResult {
  job_id: string;
  status: string;
  sharpe_ratio?: number;
  total_return?: number;
  win_rate?: number;
  max_drawdown?: number;
  total_trades?: number;
  profit_factor?: number;
  avg_trade_return?: number;
  equity_curve?: number[];
  timestamps?: string[];
  monthly_returns?: Record<string, number>;
  trade_distribution?: { return: number; count: number }[];
  mc_var_95?: number;
  mc_cvar_95?: number;
}

const STRATEGIES = [
  { id: "rsi_ema_macd", label: "RSI + EMA + MACD Ensemble" },
  { id: "rsi_only", label: "RSI Momentum" },
  { id: "ema_cross", label: "EMA Crossover" },
  { id: "macd_signal", label: "MACD Signal" },
  { id: "bollinger_mean_rev", label: "Bollinger Mean Reversion" },
];

export default function BacktesterPage() {
  const [symbol, setSymbol] = useState("AAPL");
  const [strategy, setStrategy] = useState("rsi_ema_macd");
  const [period, setPeriod] = useState("1y");
  const [interval, setInterval] = useState("1d");
  const [initialCap, setInitialCap] = useState(100000);
  const [jobId, setJobId] = useState<string | null>(null);

  const { data: result, refetch } = useQuery<BacktestResult>({
    queryKey: ["backtest-result", jobId],
    queryFn: () => api.getBacktestResult(jobId!).then((r) => r.data),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const data = query.state.data as BacktestResult | undefined;
      return data?.status === "running" ? 2000 : false;
    },
  });

  const { mutate: runBacktest, isPending } = useMutation({
    mutationFn: () =>
      api.runBacktest({ symbol, strategy, period, interval, initial_capital: initialCap }).then((r) => r.data),
    onSuccess: (data) => {
      setJobId(data.job_id);
      toast.success(`Backtest started for ${symbol}`);
      setTimeout(() => refetch(), 1500);
    },
    onError: () => toast.error("Failed to start backtest"),
  });

  const isRunning = result?.status === "running";
  const isComplete = result?.status === "completed" && result.equity_curve;

  const equityChart: Data[] = isComplete ? [
    {
      type: "scatter",
      mode: "lines",
      x: result.timestamps ?? result.equity_curve!.map((_, i) => i),
      y: result.equity_curve!,
      name: "Portfolio Value",
      fill: "tozeroy",
      fillcolor: "rgba(0,208,156,0.08)",
      line: { color: "#00D09C", width: 2 },
    },
  ] : [];

  const metricsCards = isComplete ? [
    { label: "Total Return", value: formatPercent(result.total_return! * 100), positive: (result.total_return ?? 0) >= 0 },
    { label: "Sharpe Ratio", value: result.sharpe_ratio?.toFixed(2) ?? "—", positive: (result.sharpe_ratio ?? 0) > 1 },
    { label: "Win Rate", value: `${((result.win_rate ?? 0) * 100).toFixed(1)}%`, positive: (result.win_rate ?? 0) > 0.5 },
    { label: "Max Drawdown", value: `${((result.max_drawdown ?? 0) * 100).toFixed(2)}%`, positive: false },
    { label: "Total Trades", value: String(result.total_trades ?? 0), positive: true },
    { label: "Profit Factor", value: result.profit_factor?.toFixed(2) ?? "—", positive: (result.profit_factor ?? 0) > 1 },
    { label: "Avg Trade", value: formatPercent((result.avg_trade_return ?? 0) * 100), positive: (result.avg_trade_return ?? 0) >= 0 },
    { label: "MC VaR 95%", value: formatCurrency(result.mc_var_95), positive: false },
  ] : [];

  return (
    <WagmiProvider>
      <SolanaProvider>
        <AppLayout>
          <div className="space-y-6 max-w-6xl mx-auto">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-evo-blue/20 flex items-center justify-center">
                <BarChart3 className="w-5 h-5 text-evo-blue" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-white">Strategy Backtester</h1>
                <p className="text-sm text-muted-foreground">Walk-forward validation with Monte Carlo equity resampling</p>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
              {/* Config */}
              <div className="evo-card space-y-4">
                <div className="text-sm font-semibold text-white">Configuration</div>

                <div>
                  <label className="text-xs text-muted-foreground mb-1 block">Symbol</label>
                  <input
                    value={symbol}
                    onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                    className="w-full bg-background border border-evo-border rounded px-2 py-1.5 text-sm text-white font-mono focus:outline-none focus:border-evo-green/50"
                  />
                </div>

                <div>
                  <label className="text-xs text-muted-foreground mb-1 block">Strategy</label>
                  <select
                    value={strategy}
                    onChange={(e) => setStrategy(e.target.value)}
                    className="w-full bg-background border border-evo-border rounded px-2 py-1.5 text-sm text-white focus:outline-none focus:border-evo-green/50"
                  >
                    {STRATEGIES.map((s) => (
                      <option key={s.id} value={s.id}>{s.label}</option>
                    ))}
                  </select>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-xs text-muted-foreground mb-1 block">Period</label>
                    <select
                      value={period}
                      onChange={(e) => setPeriod(e.target.value)}
                      className="w-full bg-background border border-evo-border rounded px-2 py-1.5 text-sm text-white focus:outline-none"
                    >
                      {["3mo", "6mo", "1y", "2y", "5y"].map((p) => (
                        <option key={p} value={p}>{p}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="text-xs text-muted-foreground mb-1 block">Interval</label>
                    <select
                      value={interval}
                      onChange={(e) => setInterval(e.target.value)}
                      className="w-full bg-background border border-evo-border rounded px-2 py-1.5 text-sm text-white focus:outline-none"
                    >
                      {["1h", "4h", "1d", "1wk"].map((i) => (
                        <option key={i} value={i}>{i}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div>
                  <label className="text-xs text-muted-foreground mb-1 block">Initial Capital ($)</label>
                  <input
                    type="number"
                    value={initialCap}
                    onChange={(e) => setInitialCap(parseInt(e.target.value))}
                    className="w-full bg-background border border-evo-border rounded px-2 py-1.5 text-sm font-mono text-white focus:outline-none"
                  />
                </div>

                <button
                  onClick={() => runBacktest()}
                  disabled={isPending || isRunning}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-evo-blue text-white rounded-md text-sm font-semibold hover:bg-evo-blue/90 transition-colors disabled:opacity-50"
                >
                  <Play className="w-4 h-4" />
                  {isPending || isRunning ? "Running..." : "Run Backtest"}
                </button>

                {isRunning && (
                  <div className="flex items-center gap-2 text-xs text-amber-400">
                    <Activity className="w-3.5 h-3.5 animate-pulse" />
                    Processing...
                  </div>
                )}
              </div>

              {/* Results */}
              <div className="lg:col-span-3 space-y-4">
                {metricsCards.length > 0 && (
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    {metricsCards.map(({ label, value, positive }) => (
                      <div key={label} className="evo-card py-3">
                        <div className="text-xs text-muted-foreground mb-1">{label}</div>
                        <div className={cn("text-lg font-bold font-mono", positive ? "text-evo-green" : "text-evo-red")}>
                          {value}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {isComplete && (
                  <div className="evo-card">
                    <div className="flex items-center gap-2 mb-3">
                      <TrendingUp className="w-4 h-4 text-evo-green" />
                      <div className="text-sm font-semibold text-white">Equity Curve</div>
                      <span className="text-xs text-muted-foreground ml-auto">{symbol} · {strategy}</span>
                    </div>
                    <Plot
                      data={equityChart}
                      layout={{
                        paper_bgcolor: "transparent",
                        plot_bgcolor: "transparent",
                        font: { color: "#8B949E", size: 11 },
                        xaxis: { gridcolor: "#161B22", showgrid: true },
                        yaxis: { title: "Portfolio Value ($)", gridcolor: "#161B22", tickprefix: "$" },
                        margin: { t: 10, r: 10, b: 40, l: 70 },
                        height: 280,
                        showlegend: false,
                        shapes: [
                          {
                            type: "line", x0: 0, x1: 1, xref: "paper",
                            y0: initialCap, y1: initialCap, yref: "y",
                            line: { color: "#30363D", width: 1, dash: "dot" },
                          } as never,
                        ],
                      } as Partial<Layout>}
                      config={{ responsive: true, displayModeBar: false }}
                      style={{ width: "100%" }}
                    />
                  </div>
                )}

                {!isComplete && !isRunning && (
                  <div className="evo-card flex flex-col items-center justify-center h-64 text-center">
                    <BarChart3 className="w-12 h-12 text-muted-foreground/30 mb-3" />
                    <div className="text-sm text-muted-foreground">Configure and run a backtest to see results</div>
                    <div className="text-xs text-muted-foreground mt-1">Walk-forward validation + Monte Carlo equity resampling</div>
                  </div>
                )}

                {isComplete && result.monthly_returns && (
                  <div className="evo-card">
                    <div className="text-sm font-semibold text-white mb-3">Monthly Returns</div>
                    <div className="grid grid-cols-6 md:grid-cols-12 gap-1">
                      {Object.entries(result.monthly_returns).map(([month, ret]) => (
                        <div
                          key={month}
                          title={`${month}: ${(ret * 100).toFixed(2)}%`}
                          className={cn(
                            "h-8 rounded text-xs flex items-center justify-center font-mono",
                            ret >= 0.02 ? "bg-evo-green/60 text-white" :
                            ret >= 0 ? "bg-evo-green/20 text-evo-green" :
                            ret >= -0.02 ? "bg-evo-red/20 text-evo-red" :
                            "bg-evo-red/60 text-white"
                          )}
                        >
                          {(ret * 100).toFixed(0)}%
                        </div>
                      ))}
                    </div>
                    <div className="flex gap-3 mt-2 text-xs text-muted-foreground">
                      <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-evo-green/60 inline-block" /> &gt;2%</span>
                      <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-evo-green/20 inline-block" /> 0–2%</span>
                      <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-evo-red/20 inline-block" /> 0–-2%</span>
                      <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-evo-red/60 inline-block" /> &lt;-2%</span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </AppLayout>
      </SolanaProvider>
    </WagmiProvider>
  );
}
