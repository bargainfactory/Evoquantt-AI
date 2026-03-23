"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { formatPrice, cn } from "@/lib/utils";

interface OptionRow {
  strike: number;
  price: number;
  iv: number;
  delta: number;
  gamma: number;
  theta: number;
  vega: number;
  type: "call" | "put";
}

interface OptionsChainProps {
  symbol: string;
  onLegSelect?: (leg: OptionRow & { side: "buy" | "sell" }) => void;
}

export function OptionsChain({ symbol, onLegSelect }: OptionsChainProps) {
  const [expiry, setExpiry] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["options-chain", symbol, expiry],
    queryFn: () => api.getOptionsChain(symbol, expiry || undefined).then((r) => r.data),
    staleTime: 60000,
    enabled: !!symbol,
  });

  const calls: OptionRow[] = data?.calls ?? [];
  const puts: OptionRow[] = data?.puts ?? [];
  const underlying = data?.underlying ?? 0;

  // Merge by strike
  const allStrikes = [...new Set([...calls.map((c) => c.strike), ...puts.map((p) => p.strike)])].sort((a, b) => a - b);

  const callMap = Object.fromEntries(calls.map((c) => [c.strike, c]));
  const putMap = Object.fromEntries(puts.map((p) => [p.strike, p]));

  return (
    <div className="evo-card">
      <div className="flex items-center justify-between mb-4">
        <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
          Options Chain — {symbol}
        </div>
        <input
          type="date"
          value={expiry}
          onChange={(e) => setExpiry(e.target.value)}
          className="bg-background border border-evo-border rounded px-2 py-1 text-xs text-white"
        />
      </div>

      {isLoading ? (
        <div className="flex justify-center py-8">
          <div className="w-5 h-5 border-2 border-evo-green border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-evo-border">
                {/* Call headers */}
                <th className="text-right py-2 pr-2 text-evo-green">Delta</th>
                <th className="text-right py-2 pr-2 text-evo-green">IV%</th>
                <th className="text-right py-2 pr-2 text-evo-green">Bid</th>
                <th className="text-right py-2 pr-3 text-evo-green">Ask</th>
                {/* Strike */}
                <th className="text-center py-2 px-3 text-white font-semibold">Strike</th>
                {/* Put headers */}
                <th className="text-left py-2 pl-3 text-evo-red">Bid</th>
                <th className="text-left py-2 pl-2 text-evo-red">Ask</th>
                <th className="text-left py-2 pl-2 text-evo-red">IV%</th>
                <th className="text-left py-2 pl-2 text-evo-red">Delta</th>
              </tr>
            </thead>
            <tbody>
              {allStrikes.map((strike) => {
                const call = callMap[strike];
                const put = putMap[strike];
                const isAtm = Math.abs(strike - underlying) <= underlying * 0.02;
                return (
                  <tr
                    key={strike}
                    className={cn(
                      "border-b border-evo-border/30",
                      isAtm ? "bg-white/5" : "hover:bg-white/2",
                    )}
                  >
                    {/* Call */}
                    <td className="text-right py-1.5 pr-2 font-mono text-evo-green">
                      {call ? call.delta?.toFixed(3) : "—"}
                    </td>
                    <td className="text-right py-1.5 pr-2 font-mono text-evo-green">
                      {call ? `${(call.iv).toFixed(1)}%` : "—"}
                    </td>
                    <td className="text-right py-1.5 pr-2 font-mono text-evo-green">
                      {call ? formatPrice(call.price * 0.97, 2) : "—"}
                    </td>
                    <td
                      className="text-right py-1.5 pr-3 font-mono text-evo-green cursor-pointer hover:underline"
                      onClick={() => call && onLegSelect?.({ ...call, side: "buy" })}
                    >
                      {call ? formatPrice(call.price, 2) : "—"}
                    </td>
                    {/* Strike */}
                    <td className={cn("text-center py-1.5 px-3 font-mono font-semibold", isAtm ? "text-evo-orange" : "text-white")}>
                      {formatPrice(strike, 0)}
                      {isAtm && <span className="ml-1 text-xs text-evo-orange">ATM</span>}
                    </td>
                    {/* Put */}
                    <td
                      className="text-left py-1.5 pl-3 font-mono text-evo-red cursor-pointer hover:underline"
                      onClick={() => put && onLegSelect?.({ ...put, side: "buy" })}
                    >
                      {put ? formatPrice(put.price, 2) : "—"}
                    </td>
                    <td className="text-left py-1.5 pl-2 font-mono text-evo-red">
                      {put ? formatPrice(put.price * 1.03, 2) : "—"}
                    </td>
                    <td className="text-left py-1.5 pl-2 font-mono text-evo-red">
                      {put ? `${(put.iv).toFixed(1)}%` : "—"}
                    </td>
                    <td className="text-left py-1.5 pl-2 font-mono text-evo-red">
                      {put ? put.delta?.toFixed(3) : "—"}
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
