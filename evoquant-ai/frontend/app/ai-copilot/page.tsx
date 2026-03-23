"use client";

import { AppLayout } from "@/components/layout/AppLayout";
import { WagmiProvider } from "@/providers/WagmiProvider";
import { SolanaProvider } from "@/providers/SolanaProvider";
import { AskEvo } from "@/components/ai/AskEvo";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { useMarketStore } from "@/store/useMarketStore";
import { Bot, TrendingUp, BarChart3, Zap } from "lucide-react";
import { cn } from "@/lib/utils";

export default function AiCopilotPage() {
  const { activeSymbol } = useMarketStore();

  const { data: suggestions } = useQuery({
    queryKey: ["evo-suggestions", activeSymbol],
    queryFn: () => api.getSymbolSuggestions(activeSymbol).then((r) => r.data),
    staleTime: 60000,
  });

  const featureCards = [
    {
      icon: TrendingUp,
      color: "text-evo-green",
      bg: "bg-evo-green/10",
      title: "Market Analysis",
      desc: "Ask about any stock, crypto, or forex pair. Evo analyzes technicals, sentiment, and macro regime.",
    },
    {
      icon: BarChart3,
      color: "text-evo-blue",
      bg: "bg-evo-blue/10",
      title: "Strategy Advice",
      desc: "Get personalized strategy suggestions based on current market conditions and your risk profile.",
    },
    {
      icon: Zap,
      color: "text-evo-purple",
      bg: "bg-evo-purple/10",
      title: "Recursive Optimization",
      desc: "Ask Evo to explain optimization results, interpret Sharpe ratios, and tune parameters.",
    },
  ];

  return (
    <WagmiProvider>
      <SolanaProvider>
        <AppLayout>
          <div className="space-y-6 max-w-5xl mx-auto">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-evo-green/20 flex items-center justify-center">
                <Bot className="w-5 h-5 text-evo-green" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-white">Evo AI Copilot</h1>
                <p className="text-sm text-muted-foreground">Powered by Claude — your personal quant trading assistant</p>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              {featureCards.map(({ icon: Icon, color, bg, title, desc }) => (
                <div key={title} className="evo-card flex items-start gap-3">
                  <div className={cn("w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0", bg)}>
                    <Icon className={cn("w-4 h-4", color)} />
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-white mb-1">{title}</div>
                    <div className="text-xs text-muted-foreground">{desc}</div>
                  </div>
                </div>
              ))}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              {/* Chat */}
              <div className="lg:col-span-2">
                <AskEvo />
              </div>

              {/* Suggestions panel */}
              <div className="space-y-3">
                {suggestions && (
                  <div className="evo-card">
                    <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3">
                      {activeSymbol} Analysis
                    </div>

                    {suggestions.signal && (
                      <div className={cn(
                        "flex items-center justify-between px-3 py-2 rounded-lg border mb-3",
                        suggestions.signal.action === "BUY"
                          ? "bg-evo-green/10 border-evo-green/20"
                          : suggestions.signal.action === "SELL"
                          ? "bg-evo-red/10 border-evo-red/20"
                          : "bg-amber-500/10 border-amber-500/20"
                      )}>
                        <span className={cn(
                          "text-sm font-bold",
                          suggestions.signal.action === "BUY" ? "text-evo-green" :
                          suggestions.signal.action === "SELL" ? "text-evo-red" : "text-amber-400"
                        )}>
                          {suggestions.signal.action}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {(suggestions.signal.confidence * 100).toFixed(0)}% confidence
                        </span>
                      </div>
                    )}

                    {suggestions.sentiment && (
                      <div className="space-y-1.5 text-xs mb-3">
                        <div className="text-muted-foreground">News Sentiment</div>
                        <div className="flex items-center justify-between">
                          <span className={cn(
                            "capitalize font-medium",
                            suggestions.sentiment.label === "positive" ? "text-evo-green" :
                            suggestions.sentiment.label === "negative" ? "text-evo-red" : "text-muted-foreground"
                          )}>
                            {suggestions.sentiment.label}
                          </span>
                          <span className="text-muted-foreground">{suggestions.sentiment.article_count} articles</span>
                        </div>
                      </div>
                    )}

                    {suggestions.strategy_suggestions?.length > 0 && (
                      <div className="space-y-1.5">
                        <div className="text-xs text-muted-foreground mb-2">Suggested Strategies</div>
                        {suggestions.strategy_suggestions.map((s: string, i: number) => (
                          <div key={i} className="text-xs text-white bg-background/50 px-2 py-1.5 rounded">
                            {s}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                <div className="evo-card">
                  <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3">Quick Prompts</div>
                  <div className="space-y-2">
                    {[
                      `Analyze ${activeSymbol} technicals`,
                      `What's the macro regime right now?`,
                      `Suggest an options strategy for ${activeSymbol}`,
                      `Explain the recursive sell engine`,
                      `How do I manage risk with Kelly criterion?`,
                      `Compare Uniswap V4 vs Jupiter routing`,
                    ].map((prompt) => (
                      <button
                        key={prompt}
                        className="w-full text-left text-xs text-muted-foreground hover:text-white px-2 py-1.5 rounded hover:bg-evo-surface/70 transition-colors border border-transparent hover:border-evo-border"
                      >
                        {prompt}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="evo-card">
                  <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">AI Models</div>
                  <div className="space-y-2 text-xs">
                    {[
                      { name: "Claude (Primary)", status: "active", color: "bg-evo-green" },
                      { name: "GPT-4o (Fallback)", status: "standby", color: "bg-amber-400" },
                      { name: "Deterministic (Emergency)", status: "standby", color: "bg-muted-foreground" },
                    ].map(({ name, status, color }) => (
                      <div key={name} className="flex items-center justify-between">
                        <span className="text-muted-foreground">{name}</span>
                        <div className="flex items-center gap-1.5">
                          <div className={cn("w-1.5 h-1.5 rounded-full", color)} />
                          <span className="text-muted-foreground capitalize">{status}</span>
                        </div>
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
