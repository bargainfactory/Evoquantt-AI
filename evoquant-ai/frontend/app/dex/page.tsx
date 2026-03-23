"use client";

import { useState } from "react";
import { AppLayout } from "@/components/layout/AppLayout";
import { WagmiProvider } from "@/providers/WagmiProvider";
import { SolanaProvider } from "@/providers/SolanaProvider";
import { UniswapV4Widget } from "@/components/dex/UniswapV4Widget";
import { JupiterWidget } from "@/components/dex/JupiterWidget";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { Globe, Zap, ArrowLeftRight, TrendingUp } from "lucide-react";
import { cn } from "@/lib/utils";

type Chain = "ethereum" | "solana";

interface BestRoute {
  chain: string;
  dex: string;
  out_amount: number;
  price_impact: number;
  fee: number;
}

export default function DexPage() {
  const [activeChain, setActiveChain] = useState<Chain>("ethereum");
  const [fromToken, setFromToken] = useState("ETH");
  const [toToken, setToToken] = useState("USDC");
  const [amount, setAmount] = useState("1");

  const { data: bestRoute } = useQuery<BestRoute>({
    queryKey: ["best-route", fromToken, toToken, amount],
    queryFn: () =>
      api.getBestRoute({ from_token: fromToken, to_token: toToken, amount: parseFloat(amount), chain: activeChain }).then((r) => r.data),
    enabled: !!amount && parseFloat(amount) > 0,
    staleTime: 10000,
  });

  const chains = [
    { id: "ethereum" as Chain, label: "Ethereum", sub: "Uniswap V4", color: "text-evo-blue", bg: "bg-evo-blue/10", icon: "⟠" },
    { id: "solana" as Chain, label: "Solana", sub: "Jupiter V6", color: "text-evo-purple", bg: "bg-evo-purple/10", icon: "◎" },
  ];

  return (
    <WagmiProvider>
      <SolanaProvider>
        <AppLayout>
          <div className="space-y-6 max-w-5xl mx-auto">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-evo-blue/20 flex items-center justify-center">
                <Globe className="w-5 h-5 text-evo-blue" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-white">DEX Routing</h1>
                <p className="text-sm text-muted-foreground">Best-price execution across Uniswap V4 and Jupiter Aggregator</p>
              </div>
            </div>

            {/* Chain selector */}
            <div className="grid grid-cols-2 gap-3">
              {chains.map((chain) => (
                <button
                  key={chain.id}
                  onClick={() => setActiveChain(chain.id)}
                  className={cn(
                    "evo-card flex items-center gap-3 transition-all",
                    activeChain === chain.id ? "border-evo-green/40" : "hover:border-evo-border/80"
                  )}
                >
                  <div className={cn("w-10 h-10 rounded-xl flex items-center justify-center text-xl font-bold", chain.bg)}>
                    {chain.icon}
                  </div>
                  <div className="text-left">
                    <div className="text-sm font-semibold text-white">{chain.label}</div>
                    <div className={cn("text-xs", chain.color)}>{chain.sub}</div>
                  </div>
                  {activeChain === chain.id && (
                    <div className="ml-auto w-2 h-2 rounded-full bg-evo-green" />
                  )}
                </button>
              ))}
            </div>

            {/* Best route banner */}
            {bestRoute && (
              <div className="flex items-center gap-4 px-4 py-3 bg-evo-green/5 border border-evo-green/20 rounded-xl text-sm">
                <Zap className="w-4 h-4 text-evo-green flex-shrink-0" />
                <div className="flex-1 flex items-center gap-6">
                  <div>
                    <span className="text-muted-foreground">Best route: </span>
                    <span className="text-white font-medium">{bestRoute.dex} on {bestRoute.chain}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Out: </span>
                    <span className="text-evo-green font-mono font-semibold">{bestRoute.out_amount.toFixed(4)}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Impact: </span>
                    <span className={cn("font-mono", bestRoute.price_impact > 1 ? "text-evo-red" : "text-amber-400")}>
                      {bestRoute.price_impact.toFixed(3)}%
                    </span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Fee: </span>
                    <span className="text-white font-mono">{bestRoute.fee.toFixed(4)}</span>
                  </div>
                </div>
                <TrendingUp className="w-4 h-4 text-evo-green flex-shrink-0" />
              </div>
            )}

            {/* Swap widget */}
            <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
              <div className="lg:col-span-3">
                {activeChain === "ethereum" ? (
                  <UniswapV4Widget />
                ) : (
                  <JupiterWidget />
                )}
              </div>

              {/* Info panel */}
              <div className="lg:col-span-2 space-y-3">
                <div className="evo-card">
                  <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3">
                    {activeChain === "ethereum" ? "Uniswap V4" : "Jupiter"} Features
                  </div>
                  {activeChain === "ethereum" ? (
                    <ul className="space-y-2 text-xs text-muted-foreground">
                      {[
                        "Singleton PoolManager contract",
                        "Custom hooks support",
                        "Flash accounting (ERC-1155)",
                        "0.01% / 0.05% / 0.3% / 1% fee tiers",
                        "Native ETH support (no WETH wrap)",
                        "Concentrated liquidity positions",
                        "1inch fallback routing",
                      ].map((f) => (
                        <li key={f} className="flex items-start gap-2">
                          <span className="text-evo-green mt-0.5">✓</span>
                          <span>{f}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <ul className="space-y-2 text-xs text-muted-foreground">
                      {[
                        "V6 Quote API with route optimization",
                        "Versioned transactions (V0)",
                        "Dynamic slippage protection",
                        "Multi-hop routing across Orca, Raydium",
                        "Priority fee auto-computation",
                        "Token ledger support",
                        "Price API for real-time rates",
                      ].map((f) => (
                        <li key={f} className="flex items-start gap-2">
                          <span className="text-evo-purple mt-0.5">✓</span>
                          <span>{f}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>

                <div className="evo-card">
                  <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3">Route Comparison</div>
                  <div className="flex items-center gap-2 text-xs mb-2">
                    <ArrowLeftRight className="w-3.5 h-3.5 text-muted-foreground" />
                    <span className="text-muted-foreground">Cross-chain best execution</span>
                  </div>
                  <div className="space-y-2">
                    {[
                      { label: "Uniswap V4", chain: "ETH", color: "text-evo-blue", available: true },
                      { label: "Jupiter", chain: "SOL", color: "text-evo-purple", available: true },
                      { label: "1inch", chain: "ETH", color: "text-amber-400", available: true },
                      { label: "Orca", chain: "SOL", color: "text-evo-green", available: true },
                    ].map((r) => (
                      <div key={r.label} className="flex items-center justify-between text-xs">
                        <div className="flex items-center gap-2">
                          <div className={cn("w-1.5 h-1.5 rounded-full", r.available ? "bg-evo-green" : "bg-muted-foreground")} />
                          <span className="text-white">{r.label}</span>
                        </div>
                        <span className={r.color}>{r.chain}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </AppLayout>
      </SolanaProvider>
    </WagmiProvider>
  );
}
