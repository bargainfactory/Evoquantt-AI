"use client";

import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useWallet } from "@solana/wallet-adapter-react";
import { WalletMultiButton } from "@solana/wallet-adapter-react-ui";
import { Connection, VersionedTransaction } from "@solana/web3.js";
import api from "@/lib/api";
import { cn } from "@/lib/utils";
import { ArrowUpDown, Info } from "lucide-react";

const SOL_TOKENS = ["SOL", "USDC", "USDT", "BTC", "ETH", "RAY", "JUP", "BONK"];
const DECIMALS: Record<string, number> = {
  SOL: 9, USDC: 6, USDT: 6, BTC: 8, ETH: 8, RAY: 6, JUP: 6, BONK: 5,
};

export function JupiterWidget() {
  const { publicKey, signTransaction, connected } = useWallet();
  const [tokenIn, setTokenIn] = useState("SOL");
  const [tokenOut, setTokenOut] = useState("USDC");
  const [amountIn, setAmountIn] = useState("");
  const [slippageBps, setSlippageBps] = useState(50);

  const amountInLamports = amountIn
    ? Math.floor(parseFloat(amountIn) * Math.pow(10, DECIMALS[tokenIn] ?? 9))
    : 0;

  const { mutate: getQuote, data: quote, isPending: isQuoting } = useMutation({
    mutationFn: () => api.jupiterQuote({
      input_mint: tokenIn,
      output_mint: tokenOut,
      amount: amountInLamports,
      slippage_bps: slippageBps,
    }).then((r) => r.data),
  });

  const { mutate: executeSwap, isPending: isSwapping } = useMutation({
    mutationFn: async () => {
      if (!publicKey || !signTransaction || !quote) throw new Error("Not ready");
      const swapRes = await api.jupiterSwap({
        quote_response: quote.raw_quote ?? quote,
        user_public_key: publicKey.toBase58(),
      }).then((r) => r.data);

      if (swapRes.error) throw new Error(swapRes.error);
      const rpc = process.env.NEXT_PUBLIC_SOLANA_RPC || "https://api.mainnet-beta.solana.com";
      const connection = new Connection(rpc, "confirmed");
      const txBuf = Buffer.from(swapRes.swap_transaction, "base64");
      const tx = VersionedTransaction.deserialize(txBuf);
      const signedTx = await signTransaction(tx);
      const sig = await connection.sendRawTransaction(signedTx.serialize());
      return sig;
    },
  });

  const outAmount = quote?.out_amount
    ? (parseInt(String(quote.out_amount)) / Math.pow(10, DECIMALS[tokenOut] ?? 6)).toFixed(6)
    : "0";

  const priceImpact = parseFloat(String(quote?.price_impact_pct ?? 0));

  return (
    <div className="evo-card space-y-4">
      <div className="flex items-center justify-between">
        <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Jupiter Aggregator</div>
        <span className="evo-badge-blue text-xs">Solana</span>
      </div>

      {/* Token In */}
      <div className="bg-background/50 rounded-lg p-3">
        <div className="text-xs text-muted-foreground mb-2">You Pay</div>
        <div className="flex items-center gap-2">
          <select value={tokenIn} onChange={(e) => setTokenIn(e.target.value)}
            className="bg-transparent text-white font-semibold text-sm focus:outline-none">
            {SOL_TOKENS.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
          <input
            type="number"
            value={amountIn}
            onChange={(e) => setAmountIn(e.target.value)}
            placeholder="0.0"
            className="flex-1 bg-transparent text-right text-xl font-mono text-white focus:outline-none placeholder:text-muted-foreground"
          />
        </div>
      </div>

      <button onClick={() => { setTokenIn(tokenOut); setTokenOut(tokenIn); }}
        className="w-8 h-8 mx-auto flex items-center justify-center rounded-full bg-evo-border hover:bg-evo-blue/20 border border-evo-border transition-colors">
        <ArrowUpDown className="w-3.5 h-3.5 text-muted-foreground" />
      </button>

      {/* Token Out */}
      <div className="bg-background/50 rounded-lg p-3">
        <div className="text-xs text-muted-foreground mb-2">You Receive</div>
        <div className="flex items-center gap-2">
          <select value={tokenOut} onChange={(e) => setTokenOut(e.target.value)}
            className="bg-transparent text-white font-semibold text-sm focus:outline-none">
            {SOL_TOKENS.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
          <div className="flex-1 text-right text-xl font-mono text-evo-blue">{isQuoting ? "..." : outAmount}</div>
        </div>
      </div>

      {/* Route */}
      {quote?.route_plan?.length > 0 && (
        <div className="bg-background/30 rounded p-2">
          <div className="text-xs text-muted-foreground mb-1">Route</div>
          <div className="flex items-center gap-1 flex-wrap text-xs">
            <span className="text-white">{tokenIn}</span>
            {quote.route_plan.map((step: { swap_info?: { label?: string } }, i: number) => (
              <span key={i} className="flex items-center gap-1">
                <span className="text-muted-foreground">→</span>
                <span className="text-evo-blue">{step.swap_info?.label || "Pool"}</span>
              </span>
            ))}
            <span className="text-muted-foreground">→</span>
            <span className="text-white">{tokenOut}</span>
          </div>
          <div className="flex justify-between text-xs mt-1">
            <span className="text-muted-foreground">Price Impact</span>
            <span className={cn("font-mono", priceImpact > 2 ? "text-evo-red" : "text-evo-green")}>
              {priceImpact.toFixed(3)}%
            </span>
          </div>
        </div>
      )}

      {/* Slippage */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-muted-foreground">Slippage</span>
        <div className="flex gap-1 flex-1">
          {[10, 50, 100].map((bps) => (
            <button key={bps} onClick={() => setSlippageBps(bps)}
              className={cn("flex-1 py-0.5 text-xs rounded transition-colors",
                slippageBps === bps ? "bg-evo-blue/10 text-evo-blue border border-evo-blue/20" : "bg-white/5 text-muted-foreground hover:text-white")}>
              {bps / 100}%
            </button>
          ))}
        </div>
      </div>

      {/* Actions */}
      {!connected ? (
        <WalletMultiButton style={{ width: "100%", justifyContent: "center" }} />
      ) : (
        <div className="grid grid-cols-2 gap-2">
          <button onClick={() => getQuote()} disabled={!amountIn || isQuoting}
            className="py-2 bg-evo-surface border border-evo-border text-white rounded text-sm hover:border-evo-blue/50 transition-colors disabled:opacity-50">
            {isQuoting ? "Quoting..." : "Get Quote"}
          </button>
          <button onClick={() => executeSwap()} disabled={!quote || isSwapping || !amountIn}
            className="py-2 bg-evo-blue text-white rounded text-sm font-semibold hover:bg-evo-blue/90 transition-colors disabled:opacity-50">
            {isSwapping ? "Swapping..." : "Swap"}
          </button>
        </div>
      )}
    </div>
  );
}
