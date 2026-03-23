"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useAccount, useWalletClient } from "wagmi";
import { ConnectButton } from "@rainbow-me/rainbowkit";
import api from "@/lib/api";
import { formatPrice, cn } from "@/lib/utils";
import { ArrowUpDown, ExternalLink } from "lucide-react";

const ETH_TOKENS = ["ETH", "WETH", "USDC", "USDT", "DAI", "WBTC", "UNI"];

export function UniswapV4Widget() {
  const { address, isConnected } = useAccount();
  const { data: walletClient } = useWalletClient();

  const [tokenIn, setTokenIn] = useState("ETH");
  const [tokenOut, setTokenOut] = useState("USDC");
  const [amountIn, setAmountIn] = useState("");
  const [slippage, setSlippage] = useState(0.5);
  const [fee, setFee] = useState(3000);

  const { mutate: getQuote, data: quote, isPending: isQuoting } = useMutation({
    mutationFn: () => api.uniswapQuote({
      token_in: tokenIn,
      token_out: tokenOut,
      amount_in: amountIn,
      fee,
      slippage,
    }).then((r) => r.data),
  });

  const { mutate: executeSwap, isPending: isSwapping } = useMutation({
    mutationFn: async () => {
      if (!address || !walletClient) throw new Error("Wallet not connected");
      const txData = await api.uniswapBuildSwap({
        token_in: tokenIn, token_out: tokenOut,
        amount_in: parseInt(amountIn),
        amount_out_min: 0,
        recipient: address,
        fee,
      }).then((r) => r.data);

      if (txData.error) throw new Error(txData.error);
      const hash = await walletClient.sendTransaction({
        to: txData.to as `0x${string}`,
        data: txData.data as `0x${string}`,
        value: BigInt(txData.value ?? 0),
      });
      return hash;
    },
  });

  const swapTokens = () => {
    setTokenIn(tokenOut);
    setTokenOut(tokenIn);
  };

  return (
    <div className="evo-card space-y-4">
      <div className="flex items-center justify-between">
        <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Uniswap V4</div>
        <span className="evo-badge-green text-xs">ETH Mainnet</span>
      </div>

      {/* Token In */}
      <div className="bg-background/50 rounded-lg p-3 space-y-2">
        <div className="text-xs text-muted-foreground">You Pay</div>
        <div className="flex items-center gap-2">
          <select
            value={tokenIn}
            onChange={(e) => setTokenIn(e.target.value)}
            className="bg-transparent text-white font-semibold text-sm focus:outline-none"
          >
            {ETH_TOKENS.map((t) => <option key={t} value={t}>{t}</option>)}
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

      {/* Swap button */}
      <button onClick={swapTokens} className="w-8 h-8 mx-auto flex items-center justify-center rounded-full bg-evo-border hover:bg-evo-green/20 hover:border-evo-green/50 border border-evo-border transition-colors">
        <ArrowUpDown className="w-3.5 h-3.5 text-muted-foreground" />
      </button>

      {/* Token Out */}
      <div className="bg-background/50 rounded-lg p-3 space-y-2">
        <div className="text-xs text-muted-foreground">You Receive</div>
        <div className="flex items-center gap-2">
          <select
            value={tokenOut}
            onChange={(e) => setTokenOut(e.target.value)}
            className="bg-transparent text-white font-semibold text-sm focus:outline-none"
          >
            {ETH_TOKENS.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
          <div className="flex-1 text-right text-xl font-mono text-evo-green">
            {isQuoting ? "..." : quote?.amount_out ? formatPrice(parseInt(quote.amount_out) / 1e6, 4) : "0.0"}
          </div>
        </div>
      </div>

      {/* Quote details */}
      {quote && !isQuoting && (
        <div className="bg-background/30 rounded p-2 space-y-1">
          <div className="flex justify-between text-xs">
            <span className="text-muted-foreground">Price Impact</span>
            <span className={cn("font-mono", parseFloat(String(quote.price_impact || 0)) > 2 ? "text-evo-red" : "text-evo-green")}>
              {parseFloat(String(quote.price_impact || 0)).toFixed(3)}%
            </span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-muted-foreground">Slippage</span>
            <span className="font-mono text-white">{slippage}%</span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-muted-foreground">Source</span>
            <span className="text-evo-blue">{quote.source}</span>
          </div>
        </div>
      )}

      {/* Fee tiers */}
      <div className="flex gap-1.5">
        {[500, 3000, 10000].map((f) => (
          <button key={f} onClick={() => setFee(f)}
            className={cn("flex-1 py-1 text-xs rounded transition-colors",
              fee === f ? "bg-evo-green/10 text-evo-green border border-evo-green/20" : "bg-white/5 text-muted-foreground hover:text-white")}>
            {f / 10000}%
          </button>
        ))}
      </div>

      {/* Action buttons */}
      {!isConnected ? (
        <ConnectButton />
      ) : (
        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={() => getQuote()}
            disabled={!amountIn || isQuoting}
            className="py-2 bg-evo-surface border border-evo-border text-white rounded text-sm hover:border-evo-green/50 transition-colors disabled:opacity-50"
          >
            {isQuoting ? "Quoting..." : "Get Quote"}
          </button>
          <button
            onClick={() => executeSwap()}
            disabled={!quote || isSwapping || !amountIn}
            className="py-2 bg-evo-green text-black rounded text-sm font-semibold hover:bg-evo-green/90 transition-colors disabled:opacity-50"
          >
            {isSwapping ? "Swapping..." : "Swap"}
          </button>
        </div>
      )}
    </div>
  );
}
