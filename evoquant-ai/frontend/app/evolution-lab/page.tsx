"use client";

import { useState } from "react";
import { AppLayout } from "@/components/layout/AppLayout";
import { WagmiProvider } from "@/providers/WagmiProvider";
import { SolanaProvider } from "@/providers/SolanaProvider";
import { useMutation, useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import toast from "react-hot-toast";
import { Play, Trophy, TrendingUp, Activity, Dna } from "lucide-react";
import { cn, formatPercent } from "@/lib/utils";
import dynamic from "next/dynamic";
import type { Data, Layout } from "plotly.js";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

const ASSET_CLASSES = ["stocks", "crypto", "forex", "futures"] as const;
const DEFAULT_SYMBOLS: Record<string, string[]> = {
  stocks: ["AAPL", "MSFT", "TSLA", "NVDA", "GOOGL", "META", "AMZN", "SPY"],
  crypto: ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT"],
  forex: ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD"],
  futures: ["ES", "NQ", "CL", "GC"],
};

interface LeaderboardEntry {
  symbol: string;
  sharpe: number;
  total_return: number;
  win_rate: number;
  max_drawdown: number;
  fitness: number;
  optimizer: string;
  depth_reached: number;
}

interface EvolutionJob {
  job_id: string;
  status: string;
  progress?: number;
  results?: LeaderboardEntry[];
}

export default function EvolutionLabPage() {
  const [assetClass, setAssetClass] = useState<string>("stocks");
  const [selectedSymbols, setSelectedSymbols] = useState<string[]>(["AAPL", "MSFT", "TSLA", "NVDA"]);
  const [maxDepth, setMaxDepth] = useState(5);
  const [jobId, setJobId] = useState<string | null>(null);

  const { data: jobStatus, refetch: refetchStatus } = useQuery<EvolutionJob>({
    queryKey: ["evolution-job", jobId],
    queryFn: () => api.getEvolutionStatus(jobId!).then((r) => r.data),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const data = query.state.data as EvolutionJob | undefined;
      return data?.status === "running" ? 3000 : false;
    },
  });

  const { data: leaderboard } = useQuery<LeaderboardEntry[]>({
    queryKey: ["evolution-leaderboard"],
    queryFn: () => api.getEvolutionLeaderboard().then((r) => r.data),
    staleTime: 60000,
  });

  const { mutate: runEvolution, isPending } = useMutation({
    mutationFn: () =>
      api.runEvolution({ symbols: selectedSymbols, asset_class: assetClass, max_depth: maxDepth }).then((r) => r.data),
    onSuccess: (data) => {
      setJobId(data.job_id);
      toast.success("Evolution run started!");
      setTimeout(() => refetchStatus(), 2000);
    },
    onError: () => toast.error("Failed to start evolution"),
  });

  const toggleSymbol = (sym: string) => {
    setSelectedSymbols((prev) =>
      prev.includes(sym) ? prev.filter((s) => s !== sym) : [...prev, sym]
    );
  };

  const displayData = jobStatus?.results ?? leaderboard ?? [];

  const fitnessChart: Data[] = displayData.length > 0 ? [
    {
      type: "bar",
      x: displayData.map((e) => e.symbol),
      y: displayData.map((e) => e.fitness),
      name: "Fitness Score",
      marker: { color: displayData.map((e) => e.fitness > 1 ? "#00D09C" : "#FF4B4B") },
    },
  ] : [];

  const sharpeChart: Data[] = displayData.length > 0 ? [
    {
      type: "scatter",
      mode: "markers+text" as unknown as "markers",
      x: displayData.map((e) => e.max_drawdown * 100),
      y: displayData.map((e) => e.sharpe),
      text: displayData.map((e) => e.symbol),
      textposition: "top center" as const,
      marker: {
        size: displayData.map((e) => Math.max(8, e.win_rate * 30)),
        color: displayData.map((e) => e.fitness),
        colorscale: "Viridis",
        showscale: true as const,
        colorbar: { title: { text: "Fitness" }, thickness: 10, len: 0.6 },
      },
      name: "Risk/Return",
    },
  ] : [];

  const isRunning = jobStatus?.status === "running";
  const isComplete = jobStatus?.status === "completed";

  return (
    <WagmiProvider>
      <SolanaProvider>
        <AppLayout>
          <div className="space-y-6 max-w-7xl mx-auto">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-evo-purple/20 flex items-center justify-center">
                <Dna className="w-5 h-5 text-evo-purple" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-white">Evolution Lab</h1>
                <p className="text-sm text-muted-foreground">Nightly walk-forward + recursive optimization across all assets</p>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              {/* Config */}
              <div className="evo-card space-y-4">
                <div className="text-sm font-semibold text-white">Configuration</div>

                <div>
                  <label className="text-xs text-muted-foreground mb-2 block">Asset Class</label>
                  <div className="grid grid-cols-2 gap-1.5">
                    {ASSET_CLASSES.map((cls) => (
                      <button
                        key={cls}
                        onClick={() => {
                          setAssetClass(cls);
                          setSelectedSymbols(DEFAULT_SYMBOLS[cls].slice(0, 4));
                        }}
                        className={cn(
                          "px-2 py-1.5 rounded text-xs font-medium capitalize transition-colors",
                          assetClass === cls
                            ? "bg-evo-purple text-white"
                            : "bg-background text-muted-foreground hover:text-white border border-evo-border"
                        )}
                      >
                        {cls}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="text-xs text-muted-foreground mb-2 block">
                    Symbols ({selectedSymbols.length} selected)
                  </label>
                  <div className="flex flex-wrap gap-1.5">
                    {DEFAULT_SYMBOLS[assetClass].map((sym) => (
                      <button
                        key={sym}
                        onClick={() => toggleSymbol(sym)}
                        className={cn(
                          "px-2 py-0.5 rounded text-xs font-mono transition-colors",
                          selectedSymbols.includes(sym)
                            ? "bg-evo-green/20 text-evo-green border border-evo-green/30"
                            : "bg-background text-muted-foreground border border-evo-border hover:border-evo-green/30"
                        )}
                      >
                        {sym}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="text-xs text-muted-foreground mb-1 block">
                    Max Recursion Depth: <span className="text-evo-purple font-bold">{maxDepth}</span>
                  </label>
                  <input
                    type="range" min={1} max={10} value={maxDepth}
                    onChange={(e) => setMaxDepth(parseInt(e.target.value))}
                    className="w-full accent-evo-purple"
                  />
                </div>

                <button
                  onClick={() => runEvolution()}
                  disabled={isPending || isRunning || selectedSymbols.length === 0}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-evo-purple text-white rounded-md text-sm font-semibold hover:bg-evo-purple/90 transition-colors disabled:opacity-50"
                >
                  <Play className="w-4 h-4" />
                  {isRunning ? "Evolving..." : isPending ? "Starting..." : "Run Evolution"}
                </button>

                {isRunning && (
                  <div className="space-y-1">
                    <div className="flex justify-between text-xs text-muted-foreground">
                      <span>Progress</span>
                      <span>{jobStatus?.progress ?? 0}%</span>
                    </div>
                    <div className="w-full h-1.5 bg-background rounded-full overflow-hidden">
                      <div
                        className="h-full bg-evo-purple transition-all duration-500 rounded-full"
                        style={{ width: `${jobStatus?.progress ?? 0}%` }}
                      />
                    </div>
                  </div>
                )}

                {isComplete && (
                  <div className="flex items-center gap-2 text-xs text-evo-green">
                    <Activity className="w-3.5 h-3.5" />
                    Evolution complete — {displayData.length} strategies evaluated
                  </div>
                )}
              </div>

              {/* Leaderboard */}
              <div className="lg:col-span-2 evo-card">
                <div className="flex items-center gap-2 mb-4">
                  <Trophy className="w-4 h-4 text-amber-400" />
                  <div className="text-sm font-semibold text-white">Strategy Leaderboard</div>
                </div>

                {displayData.length === 0 ? (
                  <div className="flex items-center justify-center h-32 text-sm text-muted-foreground">
                    Run evolution to see results
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="border-b border-evo-border">
                          {["#", "Symbol", "Fitness", "Sharpe", "Return", "Win Rate", "Drawdown", "Optimizer"].map((h) => (
                            <th key={h} className="text-left text-muted-foreground font-medium pb-2 pr-4">{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {[...displayData]
                          .sort((a, b) => b.fitness - a.fitness)
                          .map((entry, i) => (
                            <tr key={entry.symbol} className="border-b border-evo-border/30 hover:bg-evo-surface/50">
                              <td className="py-2 pr-4">
                                <span className={cn(
                                  "font-bold",
                                  i === 0 ? "text-amber-400" : i === 1 ? "text-slate-300" : i === 2 ? "text-amber-700" : "text-muted-foreground"
                                )}>
                                  {i + 1}
                                </span>
                              </td>
                              <td className="py-2 pr-4 font-mono text-white font-medium">{entry.symbol}</td>
                              <td className="py-2 pr-4">
                                <span className={cn("font-mono font-bold", entry.fitness > 1 ? "text-evo-green" : "text-evo-red")}>
                                  {entry.fitness.toFixed(3)}
                                </span>
                              </td>
                              <td className="py-2 pr-4 font-mono text-white">{entry.sharpe.toFixed(2)}</td>
                              <td className={cn("py-2 pr-4 font-mono", entry.total_return >= 0 ? "text-evo-green" : "text-evo-red")}>
                                {formatPercent(entry.total_return * 100)}
                              </td>
                              <td className="py-2 pr-4 text-white font-mono">{(entry.win_rate * 100).toFixed(1)}%</td>
                              <td className="py-2 pr-4 text-evo-red font-mono">{(entry.max_drawdown * 100).toFixed(1)}%</td>
                              <td className="py-2 pr-4">
                                <span className={cn(
                                  "px-1.5 py-0.5 rounded text-xs",
                                  entry.optimizer === "DEAP" ? "bg-evo-purple/20 text-evo-purple" : "bg-evo-blue/20 text-evo-blue"
                                )}>
                                  {entry.optimizer}
                                </span>
                              </td>
                            </tr>
                          ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>

            {/* Charts */}
            {displayData.length > 0 && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <div className="evo-card">
                  <div className="flex items-center gap-2 mb-3">
                    <TrendingUp className="w-4 h-4 text-evo-green" />
                    <div className="text-sm font-semibold text-white">Fitness Scores</div>
                  </div>
                  <Plot
                    data={fitnessChart}
                    layout={{
                      paper_bgcolor: "transparent", plot_bgcolor: "transparent",
                      font: { color: "#8B949E", size: 11 },
                      xaxis: { gridcolor: "#161B22", tickangle: -30 },
                      yaxis: { title: { text: "Fitness Score" }, gridcolor: "#161B22" },
                      margin: { t: 10, r: 10, b: 60, l: 50 },
                      height: 220,
                      showlegend: false,
                    } as Partial<Layout>}
                    config={{ responsive: true, displayModeBar: false }}
                    style={{ width: "100%" }}
                  />
                </div>

                <div className="evo-card">
                  <div className="flex items-center gap-2 mb-3">
                    <Activity className="w-4 h-4 text-evo-blue" />
                    <div className="text-sm font-semibold text-white">Risk / Return Scatter</div>
                    <span className="text-xs text-muted-foreground ml-auto">Bubble = win rate</span>
                  </div>
                  <Plot
                    data={sharpeChart}
                    layout={{
                      paper_bgcolor: "transparent", plot_bgcolor: "transparent",
                      font: { color: "#8B949E", size: 11 },
                      xaxis: { title: { text: "Max Drawdown (%)" }, gridcolor: "#161B22" },
                      yaxis: { title: { text: "Sharpe Ratio" }, gridcolor: "#161B22" },
                      margin: { t: 10, r: 80, b: 50, l: 50 },
                      height: 220,
                      showlegend: false,
                    } as Partial<Layout>}
                    config={{ responsive: true, displayModeBar: false }}
                    style={{ width: "100%" }}
                  />
                </div>
              </div>
            )}
          </div>
        </AppLayout>
      </SolanaProvider>
    </WagmiProvider>
  );
}
