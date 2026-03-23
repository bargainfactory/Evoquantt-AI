"use client";

import { useOrderBook } from "@/hooks/useMarketData";
import { formatPrice, cn } from "@/lib/utils";
import { useMarketStore } from "@/store/useMarketStore";

export function OrderBook() {
  const { activeSymbol } = useMarketStore();
  const book = useOrderBook(activeSymbol);

  const bids = book?.bids?.slice(0, 10) ?? [];
  const asks = book?.asks?.slice(0, 10) ?? [];

  const maxBidSize = Math.max(...bids.map(([, s]) => s ?? 0), 1);
  const maxAskSize = Math.max(...asks.map(([, s]) => s ?? 0), 1);
  const spread = asks.length && bids.length ? asks[0][0] - bids[0][0] : 0;
  const spreadPct = bids.length ? (spread / bids[0][0]) * 100 : 0;

  return (
    <div className="evo-card h-full flex flex-col">
      <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3">Order Book</div>

      {/* Headers */}
      <div className="grid grid-cols-2 text-xs text-muted-foreground mb-1 px-1">
        <span>Price (USD)</span>
        <span className="text-right">Size</span>
      </div>

      {/* Asks */}
      <div className="flex flex-col-reverse gap-0.5 mb-1">
        {asks.slice().reverse().map(([price, size], i) => (
          <div key={i} className="relative grid grid-cols-2 text-xs px-1 py-0.5 rounded-sm overflow-hidden">
            <div
              className="absolute inset-y-0 right-0 bg-evo-red/10 transition-all"
              style={{ width: `${(size / maxAskSize) * 100}%` }}
            />
            <span className="text-evo-red font-mono relative z-10">{formatPrice(price, 4)}</span>
            <span className="text-right text-white font-mono relative z-10">{size?.toFixed(2)}</span>
          </div>
        ))}
      </div>

      {/* Spread */}
      <div className="text-center py-1 border-y border-evo-border my-1">
        <span className="text-xs text-muted-foreground">
          Spread {formatPrice(spread, 4)} ({spreadPct.toFixed(3)}%)
        </span>
      </div>

      {/* Bids */}
      <div className="flex flex-col gap-0.5">
        {bids.map(([price, size], i) => (
          <div key={i} className="relative grid grid-cols-2 text-xs px-1 py-0.5 rounded-sm overflow-hidden">
            <div
              className="absolute inset-y-0 right-0 bg-evo-green/10 transition-all"
              style={{ width: `${(size / maxBidSize) * 100}%` }}
            />
            <span className="text-evo-green font-mono relative z-10">{formatPrice(price, 4)}</span>
            <span className="text-right text-white font-mono relative z-10">{size?.toFixed(2)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
