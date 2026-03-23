"use client";

import { WagmiProvider } from "@/providers/WagmiProvider";
import { SolanaProvider } from "@/providers/SolanaProvider";
import { AppLayout } from "@/components/layout/AppLayout";
import { TradingViewChart } from "@/components/charts/TradingViewChart";
import { OrderPanel } from "@/components/trading/OrderPanel";
import { OrderBook } from "@/components/trading/OrderBook";
import { PositionsList } from "@/components/trading/PositionsList";
import { TradeHistory } from "@/components/trading/TradeHistory";
import { useMarketStore } from "@/store/useMarketStore";
import { useIndicators, useSentiment } from "@/hooks/useMarketData";
import { formatPrice, getPnlColor, cn } from "@/lib/utils";

function IndicatorBar({ symbol }: { symbol: string }) {
  const { data } = useIndicators(symbol);
  const signal = data?.ensemble_signal;
  const latest = data?.latest;

  if (!signal) return null;

  const signalColor = signal.action === "BUY" ? "text-evo-green" : signal.action === "SELL" ? "text-evo-red" : "text-amber-400";
  const signalBg = signal.action === "BUY" ? "bg-evo-green/10 border-evo-green/20" : signal.action === "SELL" ? "bg-evo-red/10 border-evo-red/20" : "bg-amber-500/10 border-amber-500/20";

  return (
    <div className="flex items-center gap-3 px-3 py-2 bg-evo-surface border-b border-evo-border overflow-x-auto">
      <div className={cn("px-3 py-1 rounded-full border text-xs font-semibold flex-shrink-0", signalBg, signalColor)}>
        {signal.action} · {(signal.confidence * 100).toFixed(0)}% confidence
      </div>
      <div className="text-xs text-muted-foreground flex-shrink-0">Regime: <span className="text-white">{signal.regime}</span></div>
      {[
        { label: "RSI", value: signal.rsi_14?.toFixed(1) },
        { label: "ATR", value: signal.atr_14?.toFixed(2) },
        { label: "MACD", value: signal.macd_hist?.toFixed(4) },
        { label: "ADX", value: latest?.adx_14?.toFixed(1) },
      ].map(({ label, value }) => value && (
        <div key={label} className="flex items-center gap-1 text-xs flex-shrink-0">
          <span className="text-muted-foreground">{label}</span>
          <span className="text-white font-mono">{value}</span>
        </div>
      ))}
    </div>
  );
}

export default function TradingPage() {
  const { activeSymbol } = useMarketStore();
  const { data: sentiment } = useSentiment(activeSymbol);

  return (
    <WagmiProvider>
      <SolanaProvider>
        <AppLayout>
          <div className="flex flex-col h-[calc(100vh-60px)] -m-4 overflow-hidden">
            {/* Indicator bar */}
            <IndicatorBar symbol={activeSymbol} />

            <div className="flex flex-1 overflow-hidden">
              {/* Main chart area */}
              <div className="flex-1 flex flex-col overflow-hidden">
                <div className="flex-1 min-h-0">
                  <TradingViewChart symbol={activeSymbol} height={420} />
                </div>
                <div className="p-4 space-y-3 overflow-y-auto max-h-80">
                  <PositionsList />
                  <TradeHistory />
                </div>
              </div>

              {/* Right panel */}
              <div className="w-72 border-l border-evo-border flex flex-col overflow-y-auto">
                <div className="p-3 space-y-3">
                  <OrderPanel />
                  <OrderBook />

                  {/* Sentiment */}
                  {sentiment && (
                    <div className="evo-card">
                      <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">News Sentiment</div>
                      <div className="flex items-center justify-between">
                        <span className={cn("text-sm font-medium capitalize", {
                          "text-evo-green": sentiment.label === "positive",
                          "text-evo-red": sentiment.label === "negative",
                          "text-muted-foreground": sentiment.label === "neutral",
                        })}>
                          {sentiment.label}
                        </span>
                        <span className="font-mono text-sm text-white">{(sentiment.combined_score * 100).toFixed(0)}%</span>
                      </div>
                      <div className="text-xs text-muted-foreground mt-1">{sentiment.article_count} articles analyzed</div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </AppLayout>
      </SolanaProvider>
    </WagmiProvider>
  );
}
