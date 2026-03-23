"use client";

import { useState, useEffect, useRef } from "react";
import { AppLayout } from "@/components/layout/AppLayout";
import { WagmiProvider } from "@/providers/WagmiProvider";
import { SolanaProvider } from "@/providers/SolanaProvider";
import { RecursionDebugger } from "@/components/charts/RecursionDebugger";
import { useMutation } from "@tanstack/react-query";
import api from "@/lib/api";
import { createRecursiveSellSocket } from "@/lib/websocket";
import toast from "react-hot-toast";
import { Play, Square, Zap } from "lucide-react";

export default function RecursiveSellPage() {
  const [symbol, setSymbol] = useState("AAPL");
  const [maxDepth, setMaxDepth] = useState(5);
  const [trials, setTrials] = useState(30);
  const [geneticPop, setGeneticPop] = useState(50);
  const [geneticGens, setGeneticGens] = useState(20);
  const [jobId, setJobId] = useState<string | null>(null);
  const [wsData, setWsData] = useState<{
    convergence: unknown[];
    tree: unknown | null;
    isRunning: boolean;
    bestSharpe?: number;
    bestReturn?: number;
    iterations?: number;
    depthReached?: number;
    currentDepth?: number;
  }>({ convergence: [], tree: null, isRunning: false });
  const socketRef = useRef<ReturnType<typeof createRecursiveSellSocket> | null>(null);

  const { mutate: runOptimization, isPending } = useMutation({
    mutationFn: () =>
      api.runRecursiveSell({ symbol, max_depth: maxDepth, trials_per_depth: trials, genetic_pop: geneticPop, genetic_gens: geneticGens }).then((r) => r.data),
    onSuccess: (data) => {
      setJobId(data.job_id);
      setWsData({ convergence: [], tree: null, isRunning: true });
      toast.success(`Optimization started for ${symbol}`);
    },
    onError: () => toast.error("Failed to start optimization"),
  });

  useEffect(() => {
    if (!jobId) return;
    socketRef.current = createRecursiveSellSocket(jobId);
    socketRef.current.connect();
    const unsub = socketRef.current.on("*", (data) => {
      if (data.type === "progress") {
        setWsData((prev) => ({
          ...prev,
          isRunning: true,
          currentDepth: Number(data.depth),
          bestSharpe: data.best_sharpe != null ? Number(data.best_sharpe) : prev.bestSharpe,
        }));
      } else if (data.type === "completed") {
        const conv = Array.isArray(data.convergence) ? data.convergence as unknown[] : [];
        setWsData({
          convergence: conv,
          tree: null,
          isRunning: false,
          bestSharpe: data.best_sharpe != null ? Number(data.best_sharpe) : undefined,
          bestReturn: data.best_return != null ? Number(data.best_return) : undefined,
          iterations: data.iterations_total != null ? Number(data.iterations_total) : undefined,
          depthReached: maxDepth,
        });
        toast.success("Optimization complete!");
        // Fetch full result
        api.getRecursiveSellResult(jobId).then((r) => {
          setWsData((prev) => ({
            ...prev,
            convergence: r.data.convergence_history ?? prev.convergence,
            tree: r.data.tree ?? null,
            bestSharpe: r.data.best_sharpe,
            bestReturn: r.data.best_return,
            iterations: r.data.iterations_total,
            depthReached: r.data.depth_reached,
          }));
        });
      }
    });
    return () => {
      unsub();
      socketRef.current?.disconnect();
    };
  }, [jobId, maxDepth]);

  return (
    <WagmiProvider>
      <SolanaProvider>
        <AppLayout>
          <div className="space-y-6 max-w-5xl mx-auto">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-evo-purple/20 flex items-center justify-center">
                <Zap className="w-5 h-5 text-evo-purple" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-white">Recursive Sell Lab</h1>
                <p className="text-sm text-muted-foreground">Optuna Bayesian + DEAP Genetic recursive optimization with visual debugger</p>
              </div>
            </div>

            {/* Config panel */}
            <div className="evo-card">
              <div className="text-sm font-semibold text-white mb-4">Configuration</div>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <div>
                  <label className="text-xs text-muted-foreground mb-1 block">Symbol</label>
                  <input
                    value={symbol}
                    onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                    className="w-full bg-background border border-evo-border rounded px-2 py-1.5 text-sm text-white font-mono focus:outline-none focus:border-evo-green/50"
                  />
                </div>

                <div className="md:col-span-2">
                  <label className="text-xs text-muted-foreground mb-1 block">
                    Recursion Depth: <span className="text-evo-purple font-bold">{maxDepth}</span> / 10
                  </label>
                  <input
                    type="range" min={1} max={10} value={maxDepth}
                    onChange={(e) => setMaxDepth(parseInt(e.target.value))}
                    className="w-full accent-evo-purple"
                  />
                  <div className="flex justify-between text-xs text-muted-foreground mt-0.5">
                    <span>1 (fast)</span>
                    <span>10 (thorough)</span>
                  </div>
                </div>

                <div>
                  <label className="text-xs text-muted-foreground mb-1 block">Optuna Trials/depth</label>
                  <input type="number" value={trials} onChange={(e) => setTrials(parseInt(e.target.value))} min={5} max={200}
                    className="w-full bg-background border border-evo-border rounded px-2 py-1.5 text-sm font-mono text-white focus:outline-none" />
                </div>

                <div>
                  <label className="text-xs text-muted-foreground mb-1 block">DEAP Pop Size</label>
                  <input type="number" value={geneticPop} onChange={(e) => setGeneticPop(parseInt(e.target.value))} min={10} max={500}
                    className="w-full bg-background border border-evo-border rounded px-2 py-1.5 text-sm font-mono text-white focus:outline-none" />
                </div>

                <div>
                  <label className="text-xs text-muted-foreground mb-1 block">DEAP Generations</label>
                  <input type="number" value={geneticGens} onChange={(e) => setGeneticGens(parseInt(e.target.value))} min={5} max={200}
                    className="w-full bg-background border border-evo-border rounded px-2 py-1.5 text-sm font-mono text-white focus:outline-none" />
                </div>
              </div>

              <div className="flex gap-2 mt-4">
                <button
                  onClick={() => runOptimization()}
                  disabled={isPending || wsData.isRunning}
                  className="flex items-center gap-2 px-4 py-2 bg-evo-purple text-white rounded-md text-sm font-semibold hover:bg-evo-purple/90 transition-colors disabled:opacity-50"
                >
                  <Play className="w-4 h-4" />
                  {isPending || wsData.isRunning ? "Optimizing..." : "Start Optimization"}
                </button>
              </div>
            </div>

            {/* Visual debugger */}
            <RecursionDebugger
              convergence={wsData.convergence as {depth: number; sharpe: number; total_return: number; iteration: number}[]}
              tree={wsData.tree as {depth: number; iteration: number; params: Record<string, number>; sharpe: number; profit_uplift: number; win_rate: number; max_drawdown: number; total_return: number; is_best: boolean; optimizer: string; children?: unknown[]} | null}
              isRunning={wsData.isRunning}
              bestSharpe={wsData.bestSharpe}
              bestReturn={wsData.bestReturn}
              iterationsTotal={wsData.iterations}
              depthReached={wsData.depthReached}
              maxDepth={maxDepth}
              currentDepth={wsData.currentDepth}
            />
          </div>
        </AppLayout>
      </SolanaProvider>
    </WagmiProvider>
  );
}
