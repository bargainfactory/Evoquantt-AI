"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import type { Data, Layout } from "plotly.js";
import { cn } from "@/lib/utils";
import { TrendingUp, GitBranch, Clock, Zap } from "lucide-react";

// Dynamic import to avoid SSR issues
const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

interface ConvergencePoint {
  depth: number;
  sharpe: number;
  total_return: number;
  iteration: number;
}

interface TreeNode {
  depth: number;
  iteration: number;
  params: Record<string, number>;
  sharpe: number;
  profit_uplift: number;
  win_rate: number;
  max_drawdown: number;
  total_return: number;
  is_best: boolean;
  optimizer: string;
  children?: TreeNode[];
}

interface RecursionDebuggerProps {
  convergence: ConvergencePoint[];
  tree?: TreeNode | null;
  isRunning?: boolean;
  bestSharpe?: number;
  bestReturn?: number;
  iterationsTotal?: number;
  depthReached?: number;
  maxDepth?: number;
  currentDepth?: number;
}

function flattenTree(node: TreeNode | null | undefined, nodes: TreeNode[] = []): TreeNode[] {
  if (!node) return nodes;
  nodes.push(node);
  (node.children || []).forEach((c) => flattenTree(c, nodes));
  return nodes;
}

export function RecursionDebugger({
  convergence,
  tree,
  isRunning,
  bestSharpe,
  bestReturn,
  iterationsTotal,
  depthReached,
  maxDepth,
  currentDepth,
}: RecursionDebuggerProps) {
  const [activeTab, setActiveTab] = useState<"convergence" | "tree" | "params">("convergence");

  // Build convergence chart data
  const convergenceData: Data[] = convergence.length > 0 ? [
    {
      type: "scatter",
      mode: "lines+markers",
      x: convergence.map((c) => c.iteration),
      y: convergence.map((c) => c.sharpe),
      name: "Sharpe Ratio",
      line: { color: "#00D09C", width: 2 },
      marker: { size: 6, color: convergence.map((c) => (c.sharpe === Math.max(...convergence.map((x) => x.sharpe)) ? "#FFD700" : "#00D09C")) },
    },
    {
      type: "scatter",
      mode: "lines",
      x: convergence.map((c) => c.iteration),
      y: convergence.map((c) => c.total_return * 100),
      name: "Return %",
      yaxis: "y2",
      line: { color: "#4A9EFF", width: 1, dash: "dot" },
    },
  ] : [];

  const convergenceLayout: Partial<Layout> = {
    paper_bgcolor: "transparent",
    plot_bgcolor: "transparent",
    font: { color: "#8B949E", size: 11 },
    xaxis: { title: { text: "Iteration" }, gridcolor: "#161B22", zerolinecolor: "#30363D" },
    yaxis: { title: { text: "Sharpe Ratio" }, gridcolor: "#161B22", zerolinecolor: "#30363D" },
    yaxis2: { title: { text: "Return %" }, overlaying: "y", side: "right", gridcolor: "transparent" },
    legend: { x: 0, y: 1, bgcolor: "transparent" },
    margin: { t: 20, r: 50, b: 40, l: 50 },
    height: 300,
    shapes: isRunning ? [] : [
      {
        type: "line",
        x0: convergence.length > 0 ? convergence[convergence.length - 1].iteration : 0,
        x1: convergence.length > 0 ? convergence[convergence.length - 1].iteration : 0,
        y0: 0, y1: 1,
        yref: "paper",
        line: { color: "#FFD700", width: 1, dash: "dot" },
      } as never,
    ],
  };

  // Build tree diagram
  const allNodes = flattenTree(tree);
  const treeData: Data[] = allNodes.length > 0 ? [
    {
      type: "scatter" as const,
      mode: "markers+text" as unknown as "markers",
      x: allNodes.map((n) => n.depth + (n.iteration % 3) * 0.3),
      y: allNodes.map((n) => n.sharpe),
      text: allNodes.map((n) => n.is_best ? "★" : ""),
      textposition: "top center",
      marker: {
        size: allNodes.map((n) => (n.is_best ? 14 : 8)),
        color: allNodes.map((n) =>
          n.optimizer === "optuna" ? "#4A9EFF"
          : n.optimizer === "deap_genetic" ? "#8B5CF6"
          : n.is_best ? "#FFD700" : "#00D09C"
        ),
        symbol: allNodes.map((n) => (n.is_best ? "star" : "circle")),
        line: { color: "#30363D", width: 1 },
      },
      customdata: allNodes.map((n) => [
        `Depth: ${n.depth}`,
        `Sharpe: ${n.sharpe.toFixed(3)}`,
        `Win Rate: ${(n.win_rate * 100).toFixed(1)}%`,
        `Optimizer: ${n.optimizer}`,
      ]),
      hovertemplate: "%{customdata[0]}<br>%{customdata[1]}<br>%{customdata[2]}<br>%{customdata[3]}<extra></extra>",
    },
  ] : [];

  const treeLayout: Partial<Layout> = {
    paper_bgcolor: "transparent",
    plot_bgcolor: "transparent",
    font: { color: "#8B949E", size: 11 },
    xaxis: { title: { text: "Depth Level" }, gridcolor: "#161B22", zerolinecolor: "#30363D", dtick: 1 },
    yaxis: { title: { text: "Sharpe Ratio" }, gridcolor: "#161B22", zerolinecolor: "#30363D" },
    margin: { t: 20, r: 20, b: 40, l: 50 },
    height: 300,
  };

  return (
    <div className="space-y-4">
      {/* Stats row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { icon: TrendingUp, label: "Best Sharpe", value: bestSharpe?.toFixed(3) ?? "—", color: "text-evo-green" },
          { icon: Zap, label: "Best Return", value: bestReturn != null ? `${(bestReturn * 100).toFixed(1)}%` : "—", color: "text-evo-blue" },
          { icon: Clock, label: "Iterations", value: iterationsTotal?.toString() ?? "—", color: "text-evo-purple" },
          { icon: GitBranch, label: "Depth", value: depthReached != null ? `${depthReached}/${maxDepth ?? "?"}` : "—", color: "text-evo-orange" },
        ].map((stat) => (
          <div key={stat.label} className="evo-card">
            <div className="flex items-center gap-2 mb-1">
              <stat.icon className={cn("w-3.5 h-3.5", stat.color)} />
              <span className="text-xs text-muted-foreground">{stat.label}</span>
            </div>
            <div className={cn("text-lg font-mono font-bold", stat.color)}>{stat.value}</div>
          </div>
        ))}
      </div>

      {/* Progress bar */}
      {isRunning && (
        <div className="evo-card">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-muted-foreground">Optimizing depth {currentDepth}/{maxDepth}</span>
            <div className="w-3 h-3 border-2 border-evo-green border-t-transparent rounded-full animate-spin" />
          </div>
          <div className="w-full bg-evo-border rounded-full h-1.5">
            <div
              className="bg-evo-green h-1.5 rounded-full transition-all duration-500"
              style={{ width: `${((currentDepth ?? 0) / (maxDepth ?? 1)) * 100}%` }}
            />
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="evo-card p-0 overflow-hidden">
        <div className="flex border-b border-evo-border">
          {(["convergence", "tree", "params"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={cn(
                "px-4 py-2 text-xs font-medium capitalize transition-colors",
                activeTab === tab ? "text-evo-green border-b-2 border-evo-green bg-evo-green/5" : "text-muted-foreground hover:text-white"
              )}
            >
              {tab === "convergence" ? "Convergence Graph" : tab === "tree" ? "Recursion Tree" : "Best Params"}
            </button>
          ))}
        </div>

        <div className="p-4">
          {activeTab === "convergence" && (
            <>
              {convergenceData.length > 0 ? (
                <Plot data={convergenceData} layout={convergenceLayout} config={{ responsive: true, displayModeBar: false }} style={{ width: "100%" }} />
              ) : (
                <div className="h-48 flex items-center justify-center text-muted-foreground text-sm">
                  {isRunning ? "Waiting for first iteration..." : "No data yet. Start an optimization to see convergence."}
                </div>
              )}
            </>
          )}

          {activeTab === "tree" && (
            <>
              {treeData.length > 0 ? (
                <>
                  <div className="flex gap-3 mb-3 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#4A9EFF] inline-block" />Optuna</span>
                    <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#8B5CF6] inline-block" />DEAP Genetic</span>
                    <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#FFD700] inline-block" />Best</span>
                  </div>
                  <Plot data={treeData} layout={treeLayout} config={{ responsive: true, displayModeBar: false }} style={{ width: "100%" }} />
                </>
              ) : (
                <div className="h-48 flex items-center justify-center text-muted-foreground text-sm">
                  {isRunning ? "Building recursion tree..." : "No tree data yet."}
                </div>
              )}
            </>
          )}

          {activeTab === "params" && tree && (
            <div className="grid grid-cols-2 gap-2">
              {Object.entries(tree.params || {}).map(([k, v]) => (
                <div key={k} className="flex items-center justify-between bg-background/50 rounded px-2 py-1.5">
                  <span className="text-xs text-muted-foreground">{k.replace(/_/g, " ")}</span>
                  <span className="text-xs font-mono text-white">{typeof v === "number" ? v.toFixed(4) : String(v)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
