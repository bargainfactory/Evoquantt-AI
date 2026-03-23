"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import api from "@/lib/api";
import { formatPrice, cn } from "@/lib/utils";

interface Greeks {
  delta: number; gamma: number; vega: number; theta: number; rho: number; iv: number;
}

export function GreeksPanel() {
  const [S, setS] = useState("100");
  const [K, setK] = useState("100");
  const [T, setT] = useState("0.25");
  const [r, setR] = useState("0.05");
  const [sigma, setSigma] = useState("0.25");
  const [optType, setOptType] = useState("c");

  const { mutate: calcGreeks, data, isPending } = useMutation({
    mutationFn: () => api.priceOption({
      S: parseFloat(S), K: parseFloat(K), T: parseFloat(T),
      r: parseFloat(r), sigma: parseFloat(sigma), option_type: optType,
    }).then((r) => r.data),
  });

  const greeks: Greeks | undefined = data?.greeks;
  const price: number | undefined = data?.price;

  const greekItems = greeks ? [
    { label: "Delta", value: greeks.delta.toFixed(4), desc: "Price sensitivity", color: "text-evo-blue" },
    { label: "Gamma", value: greeks.gamma.toFixed(6), desc: "Delta sensitivity", color: "text-evo-purple" },
    { label: "Vega", value: greeks.vega.toFixed(4), desc: "Vol sensitivity (per 1%)", color: "text-evo-orange" },
    { label: "Theta", value: greeks.theta.toFixed(4), desc: "Time decay (per day)", color: "text-evo-red" },
    { label: "Rho", value: greeks.rho.toFixed(4), desc: "Rate sensitivity", color: "text-muted-foreground" },
    { label: "IV", value: `${(greeks.iv * 100).toFixed(1)}%`, desc: "Implied volatility", color: "text-evo-green" },
  ] : [];

  return (
    <div className="evo-card space-y-4">
      <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Greeks Calculator</div>

      <div className="grid grid-cols-2 gap-2">
        {[
          { label: "Spot (S)", value: S, setter: setS },
          { label: "Strike (K)", value: K, setter: setK },
          { label: "Time (T years)", value: T, setter: setT },
          { label: "Risk-Free (r)", value: r, setter: setR },
          { label: "Volatility (σ)", value: sigma, setter: setSigma },
        ].map(({ label, value, setter }) => (
          <div key={label}>
            <label className="text-xs text-muted-foreground mb-1 block">{label}</label>
            <input
              type="number"
              value={value}
              onChange={(e) => setter(e.target.value)}
              step="any"
              className="w-full bg-background border border-evo-border rounded px-2 py-1.5 text-xs font-mono text-white focus:outline-none focus:border-evo-green/50"
            />
          </div>
        ))}
        <div>
          <label className="text-xs text-muted-foreground mb-1 block">Type</label>
          <select
            value={optType}
            onChange={(e) => setOptType(e.target.value)}
            className="w-full bg-background border border-evo-border rounded px-2 py-1.5 text-xs text-white focus:outline-none"
          >
            <option value="c">Call</option>
            <option value="p">Put</option>
          </select>
        </div>
      </div>

      <button
        onClick={() => calcGreeks()}
        disabled={isPending}
        className="w-full py-2 bg-evo-green/10 border border-evo-green/30 text-evo-green rounded text-xs font-medium hover:bg-evo-green/20 transition-colors disabled:opacity-50"
      >
        {isPending ? "Calculating..." : "Calculate Greeks"}
      </button>

      {price != null && (
        <div className="bg-background/50 rounded-md p-3 text-center">
          <div className="text-xs text-muted-foreground mb-0.5">Option Price</div>
          <div className="text-2xl font-mono font-bold text-evo-green">${formatPrice(price, 4)}</div>
        </div>
      )}

      {greekItems.length > 0 && (
        <div className="grid grid-cols-2 gap-2">
          {greekItems.map(({ label, value, desc, color }) => (
            <div key={label} className="bg-background/50 rounded p-2">
              <div className="flex items-center justify-between mb-0.5">
                <span className="text-xs text-muted-foreground">{label}</span>
                <span className={cn("text-sm font-mono font-bold", color)}>{value}</span>
              </div>
              <div className="text-xs text-muted-foreground/60">{desc}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
