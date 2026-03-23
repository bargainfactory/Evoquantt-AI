"use client";

import { useState } from "react";
import { usePlaceOrder } from "@/hooks/useTrade";
import { useAppStore } from "@/store/useAppStore";
import { useMarketStore } from "@/store/useMarketStore";
import { formatPrice, cn } from "@/lib/utils";
import { ChevronDown } from "lucide-react";

const ORDER_TYPES = ["market", "limit", "stop", "stop_limit"] as const;
const BROKERS = ["paper", "binance", "bybit", "ibkr", "etrade", "schwab", "tradier"];
const ASSET_CLASSES = ["stock", "crypto", "forex", "futures", "options", "dex"];

export function OrderPanel() {
  const { isPaper } = useAppStore();
  const { activeSymbol, ticks } = useMarketStore();
  const { mutate: placeOrder, isPending } = usePlaceOrder();

  const [side, setSide] = useState<"buy" | "sell">("buy");
  const [orderType, setOrderType] = useState<string>("market");
  const [qty, setQty] = useState("");
  const [price, setPrice] = useState("");
  const [stopPrice, setStopPrice] = useState("");
  const [broker, setBroker] = useState("paper");
  const [assetClass, setAssetClass] = useState("stock");
  const [showAdvanced, setShowAdvanced] = useState(false);

  const tick = ticks[activeSymbol];
  const currentPrice = tick?.price;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!qty || parseFloat(qty) <= 0) return;

    placeOrder({
      symbol: activeSymbol,
      asset_class: assetClass,
      side,
      order_type: orderType,
      quantity: parseFloat(qty),
      price: price ? parseFloat(price) : undefined,
      stop_price: stopPrice ? parseFloat(stopPrice) : undefined,
      broker,
      is_paper: isPaper || broker === "paper",
    });
  };

  return (
    <div className="evo-card space-y-3">
      <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Place Order</div>

      {/* Side buttons */}
      <div className="grid grid-cols-2 gap-1.5">
        {(["buy", "sell"] as const).map((s) => (
          <button
            key={s}
            onClick={() => setSide(s)}
            className={cn(
              "py-2 rounded-md text-sm font-semibold capitalize transition-all",
              side === s
                ? s === "buy" ? "bg-evo-green text-black" : "bg-evo-red text-white"
                : "bg-white/5 text-muted-foreground hover:bg-white/10 hover:text-white"
            )}
          >
            {s}
          </button>
        ))}
      </div>

      {/* Symbol display */}
      <div className="bg-background/50 rounded-md px-3 py-2 flex items-center justify-between">
        <span className="text-sm font-medium text-white">{activeSymbol}</span>
        {currentPrice && (
          <span className="text-sm font-mono text-evo-green">${formatPrice(currentPrice)}</span>
        )}
      </div>

      {/* Order type */}
      <div className="grid grid-cols-2 gap-1.5">
        {ORDER_TYPES.map((t) => (
          <button
            key={t}
            onClick={() => setOrderType(t)}
            className={cn(
              "py-1 text-xs rounded capitalize transition-colors",
              orderType === t ? "bg-white/10 text-white" : "text-muted-foreground hover:text-white"
            )}
          >
            {t.replace("_", " ")}
          </button>
        ))}
      </div>

      <form onSubmit={handleSubmit} className="space-y-2.5">
        {/* Quantity */}
        <div>
          <label className="text-xs text-muted-foreground mb-1 block">Quantity</label>
          <input
            type="number"
            value={qty}
            onChange={(e) => setQty(e.target.value)}
            placeholder="0.00"
            step="any"
            className="w-full bg-background border border-evo-border rounded-md px-3 py-2 text-sm font-mono text-white placeholder:text-muted-foreground focus:outline-none focus:border-evo-green/50"
          />
        </div>

        {/* Limit price */}
        {(orderType === "limit" || orderType === "stop_limit") && (
          <div>
            <label className="text-xs text-muted-foreground mb-1 block">Limit Price</label>
            <input
              type="number"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              placeholder={currentPrice ? formatPrice(currentPrice) : "0.00"}
              step="any"
              className="w-full bg-background border border-evo-border rounded-md px-3 py-2 text-sm font-mono text-white placeholder:text-muted-foreground focus:outline-none focus:border-evo-green/50"
            />
          </div>
        )}

        {/* Stop price */}
        {(orderType === "stop" || orderType === "stop_limit") && (
          <div>
            <label className="text-xs text-muted-foreground mb-1 block">Stop Price</label>
            <input
              type="number"
              value={stopPrice}
              onChange={(e) => setStopPrice(e.target.value)}
              placeholder="0.00"
              step="any"
              className="w-full bg-background border border-evo-border rounded-md px-3 py-2 text-sm font-mono text-white placeholder:text-muted-foreground focus:outline-none focus:border-evo-green/50"
            />
          </div>
        )}

        {/* Advanced */}
        <button type="button" onClick={() => setShowAdvanced(!showAdvanced)} className="flex items-center gap-1 text-xs text-muted-foreground hover:text-white">
          <ChevronDown className={cn("w-3 h-3 transition-transform", showAdvanced && "rotate-180")} />
          Advanced
        </button>

        {showAdvanced && (
          <div className="space-y-2">
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">Broker</label>
              <select
                value={broker}
                onChange={(e) => setBroker(e.target.value)}
                className="w-full bg-background border border-evo-border rounded-md px-3 py-2 text-sm text-white focus:outline-none focus:border-evo-green/50"
              >
                {BROKERS.map((b) => <option key={b} value={b}>{b}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">Asset Class</label>
              <select
                value={assetClass}
                onChange={(e) => setAssetClass(e.target.value)}
                className="w-full bg-background border border-evo-border rounded-md px-3 py-2 text-sm text-white focus:outline-none focus:border-evo-green/50"
              >
                {ASSET_CLASSES.map((a) => <option key={a} value={a}>{a}</option>)}
              </select>
            </div>
          </div>
        )}

        {/* Submit */}
        <button
          type="submit"
          disabled={isPending || !qty}
          className={cn(
            "w-full py-2.5 rounded-md text-sm font-semibold transition-all",
            side === "buy"
              ? "bg-evo-green text-black hover:bg-evo-green/90 disabled:opacity-50"
              : "bg-evo-red text-white hover:bg-evo-red/90 disabled:opacity-50",
            isPending && "opacity-50 cursor-not-allowed"
          )}
        >
          {isPending ? "Placing..." : `${side.toUpperCase()} ${activeSymbol}`}
        </button>
      </form>
    </div>
  );
}
