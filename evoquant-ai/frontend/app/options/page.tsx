"use client";

import { useState } from "react";
import { AppLayout } from "@/components/layout/AppLayout";
import { WagmiProvider } from "@/providers/WagmiProvider";
import { SolanaProvider } from "@/providers/SolanaProvider";
import { OptionsChain } from "@/components/options/OptionsChain";
import { GreeksPanel } from "@/components/options/GreeksPanel";
import { useMarketStore } from "@/store/useMarketStore";
import { useMutation } from "@tanstack/react-query";
import api from "@/lib/api";
import dynamic from "next/dynamic";
import type { Data, Layout } from "plotly.js";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

export default function OptionsPage() {
  const { activeSymbol } = useMarketStore();
  const [legs, setLegs] = useState<Record<string, unknown>[]>([]);

  const { mutate: calcPnl, data: pnlData } = useMutation({
    mutationFn: () => api.strategyPnl(legs, 80, 120).then((r) => r.data),
  });

  const pnlChart: Data[] = pnlData ? [
    {
      type: "scatter", mode: "lines",
      x: pnlData.price_range,
      y: pnlData.pnl_expiry,
      name: "At Expiry",
      line: { color: "#00D09C", width: 2 },
    },
    {
      type: "scatter", mode: "lines",
      x: pnlData.price_range,
      y: pnlData.pnl_now,
      name: "Now",
      line: { color: "#4A9EFF", width: 1, dash: "dot" },
    },
  ] : [];

  return (
    <WagmiProvider>
      <SolanaProvider>
        <AppLayout>
          <div className="space-y-4 max-w-7xl mx-auto">
            <h1 className="text-xl font-bold text-white">Options — {activeSymbol}</h1>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <div className="lg:col-span-2 space-y-4">
                <OptionsChain
                  symbol={activeSymbol}
                  onLegSelect={(leg) => setLegs((prev) => [...prev, { ...leg, r: 0.05 }])}
                />

                {legs.length > 0 && (
                  <div className="evo-card space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="text-sm font-semibold text-white">Strategy Builder ({legs.length} legs)</div>
                      <div className="flex gap-2">
                        <button onClick={() => setLegs([])} className="text-xs text-muted-foreground hover:text-white">Clear</button>
                        <button onClick={() => calcPnl()} className="text-xs bg-evo-green/10 text-evo-green border border-evo-green/20 px-2 py-0.5 rounded hover:bg-evo-green/20">
                          Calculate P&L
                        </button>
                      </div>
                    </div>
                    {legs.map((leg, i) => (
                      <div key={i} className="flex items-center justify-between text-xs bg-background/50 rounded px-2 py-1.5">
                        <span className="text-muted-foreground capitalize">{String(leg.side)} {String(leg.option_type)}</span>
                        <span className="text-white">K={String(leg.strike)}</span>
                        <span className="text-evo-green">P=${Number(leg.price).toFixed(2)}</span>
                        <button onClick={() => setLegs((prev) => prev.filter((_, j) => j !== i))} className="text-muted-foreground hover:text-evo-red">×</button>
                      </div>
                    ))}

                    {pnlData && (
                      <>
                        <div className="grid grid-cols-3 gap-2 text-xs">
                          <div className="evo-card py-2 text-center">
                            <div className="text-muted-foreground">Max Profit</div>
                            <div className="text-evo-green font-mono">${Number(pnlData.max_profit).toFixed(2)}</div>
                          </div>
                          <div className="evo-card py-2 text-center">
                            <div className="text-muted-foreground">Max Loss</div>
                            <div className="text-evo-red font-mono">${Number(pnlData.max_loss).toFixed(2)}</div>
                          </div>
                          <div className="evo-card py-2 text-center">
                            <div className="text-muted-foreground">Breakevens</div>
                            <div className="text-white font-mono">{pnlData.breakevens.map((b: number) => b.toFixed(2)).join(", ")}</div>
                          </div>
                        </div>
                        <Plot
                          data={pnlChart}
                          layout={{
                            paper_bgcolor: "transparent", plot_bgcolor: "transparent",
                            font: { color: "#8B949E", size: 11 },
                            xaxis: { title: { text: "Underlying Price" }, gridcolor: "#161B22" },
                            yaxis: { title: { text: "P&L ($)" }, gridcolor: "#161B22", zerolinecolor: "#30363D" },
                            margin: { t: 10, r: 10, b: 40, l: 50 },
                            height: 220,
                            shapes: [{
                              type: "line", x0: 0, x1: 1, xref: "paper",
                              y0: 0, y1: 0, yref: "y",
                              line: { color: "#30363D", width: 1 },
                            } as never],
                          } as Partial<Layout>}
                          config={{ responsive: true, displayModeBar: false }}
                          style={{ width: "100%" }}
                        />
                      </>
                    )}
                  </div>
                )}
              </div>

              <div>
                <GreeksPanel />
              </div>
            </div>
          </div>
        </AppLayout>
      </SolanaProvider>
    </WagmiProvider>
  );
}
