"use client";

import { usePositions } from "@/hooks/useTrade";
import { formatPrice, formatPercent, getPnlColor, cn } from "@/lib/utils";

export function PositionsList() {
  const { data: positions, isLoading } = usePositions();

  if (isLoading) {
    return (
      <div className="evo-card">
        <div className="text-xs font-semibold text-muted-foreground uppercase mb-3">Positions</div>
        <div className="flex justify-center py-6">
          <div className="w-5 h-5 border-2 border-evo-green border-t-transparent rounded-full animate-spin" />
        </div>
      </div>
    );
  }

  return (
    <div className="evo-card">
      <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3">
        Open Positions ({positions?.length ?? 0})
      </div>

      {!positions?.length ? (
        <div className="text-center py-8 text-muted-foreground text-sm">No open positions</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-muted-foreground border-b border-evo-border">
                <th className="text-left py-2 pr-3">Symbol</th>
                <th className="text-right py-2 pr-3">Qty</th>
                <th className="text-right py-2 pr-3">Avg Cost</th>
                <th className="text-right py-2 pr-3">Price</th>
                <th className="text-right py-2 pr-3">Unrealized P&L</th>
                <th className="text-right py-2">Weight</th>
              </tr>
            </thead>
            <tbody>
              {positions.map((pos: {
                symbol: string; asset_class: string; quantity: number;
                avg_cost: number; current_price?: number; unrealized_pnl?: number; weight?: number;
              }) => {
                const pnlPct = pos.avg_cost ? ((pos.current_price ?? pos.avg_cost) - pos.avg_cost) / pos.avg_cost * 100 : 0;
                return (
                  <tr key={pos.symbol} className="border-b border-evo-border/50 hover:bg-white/2">
                    <td className="py-2 pr-3">
                      <div className="font-medium text-white">{pos.symbol}</div>
                      <div className="text-muted-foreground capitalize">{pos.asset_class}</div>
                    </td>
                    <td className="text-right py-2 pr-3 font-mono text-white">{pos.quantity}</td>
                    <td className="text-right py-2 pr-3 font-mono">{formatPrice(pos.avg_cost)}</td>
                    <td className="text-right py-2 pr-3 font-mono">{pos.current_price ? formatPrice(pos.current_price) : "—"}</td>
                    <td className={cn("text-right py-2 pr-3 font-mono", getPnlColor(pos.unrealized_pnl))}>
                      {pos.unrealized_pnl != null ? (
                        <div>
                          <div>${formatPrice(pos.unrealized_pnl)}</div>
                          <div className="text-xs opacity-75">{formatPercent(pnlPct)}</div>
                        </div>
                      ) : "—"}
                    </td>
                    <td className="text-right py-2 font-mono text-muted-foreground">
                      {pos.weight != null ? `${(pos.weight * 100).toFixed(1)}%` : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
