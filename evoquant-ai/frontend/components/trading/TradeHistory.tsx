"use client";

import { useOrders, useCancelOrder } from "@/hooks/useTrade";
import { formatPrice, formatTimestamp, getPnlColor, cn } from "@/lib/utils";
import { X } from "lucide-react";

const STATUS_STYLES: Record<string, string> = {
  filled: "evo-badge-green",
  open: "evo-badge-blue",
  pending: "evo-badge-blue",
  partially_filled: "bg-yellow-500/10 text-yellow-400 border border-yellow-500/20 text-xs px-2 py-0.5 rounded-full",
  cancelled: "bg-white/5 text-muted-foreground text-xs px-2 py-0.5 rounded-full",
  rejected: "evo-badge-red",
};

export function TradeHistory() {
  const { data: orders, isLoading } = useOrders({ limit: 50 });
  const { mutate: cancelOrder } = useCancelOrder();

  if (isLoading) {
    return (
      <div className="evo-card">
        <div className="text-xs font-semibold text-muted-foreground uppercase mb-3">Trade History</div>
        <div className="flex justify-center py-6">
          <div className="w-5 h-5 border-2 border-evo-green border-t-transparent rounded-full animate-spin" />
        </div>
      </div>
    );
  }

  return (
    <div className="evo-card">
      <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3">
        Orders ({orders?.length ?? 0})
      </div>

      {!orders?.length ? (
        <div className="text-center py-8 text-muted-foreground text-sm">No orders yet</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-muted-foreground border-b border-evo-border">
                <th className="text-left py-2 pr-3">Time</th>
                <th className="text-left py-2 pr-3">Symbol</th>
                <th className="text-left py-2 pr-3">Side</th>
                <th className="text-left py-2 pr-3">Type</th>
                <th className="text-right py-2 pr-3">Qty</th>
                <th className="text-right py-2 pr-3">Price</th>
                <th className="text-right py-2 pr-3">P&L</th>
                <th className="text-left py-2 pr-3">Status</th>
                <th className="py-2" />
              </tr>
            </thead>
            <tbody>
              {orders.map((order: {
                id: string; created_at: string; symbol: string; side: string;
                order_type: string; quantity: number; filled_price?: number; price?: number;
                pnl?: number; status: string;
              }) => (
                <tr key={order.id} className="border-b border-evo-border/50 hover:bg-white/2">
                  <td className="py-2 pr-3 text-muted-foreground whitespace-nowrap">{formatTimestamp(order.created_at)}</td>
                  <td className="py-2 pr-3 font-medium text-white">{order.symbol}</td>
                  <td className={cn("py-2 pr-3 font-medium capitalize", order.side === "buy" ? "text-evo-green" : "text-evo-red")}>{order.side}</td>
                  <td className="py-2 pr-3 text-muted-foreground capitalize">{order.order_type.replace("_", " ")}</td>
                  <td className="text-right py-2 pr-3 font-mono text-white">{order.quantity}</td>
                  <td className="text-right py-2 pr-3 font-mono">{formatPrice(order.filled_price ?? order.price)}</td>
                  <td className={cn("text-right py-2 pr-3 font-mono", getPnlColor(order.pnl))}>
                    {order.pnl != null ? `$${formatPrice(order.pnl)}` : "—"}
                  </td>
                  <td className="py-2 pr-3">
                    <span className={STATUS_STYLES[order.status] || STATUS_STYLES.cancelled}>{order.status}</span>
                  </td>
                  <td className="py-2">
                    {(order.status === "open" || order.status === "pending") && (
                      <button onClick={() => cancelOrder(order.id)} className="text-muted-foreground hover:text-evo-red">
                        <X className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
