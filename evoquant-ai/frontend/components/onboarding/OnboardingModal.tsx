"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAppStore } from "@/store/useAppStore";
import {
  X, ChevronRight, ChevronLeft, Zap,
  Plug, Wallet, Bell, FlaskConical, Bot,
  BarChart2, ShieldCheck, CheckCircle2,
} from "lucide-react";
import { cn } from "@/lib/utils";

const STEPS = [
  {
    icon: Zap,
    title: "Welcome to EvoQuant AI",
    color: "text-evo-green",
    bg: "bg-evo-green/10",
    description: "Your quantum-proof trading platform. Let's walk through how to get started — it only takes a few minutes.",
    steps: [
      "EvoQuant AI combines AI-powered trading signals with real-time market data.",
      "You can trade crypto, stocks, and options — all from one platform.",
      "Paper trading mode is on by default so you can practice risk-free.",
    ],
    action: null,
  },
  {
    icon: Plug,
    title: "Connect Your Brokerage Account",
    color: "text-blue-400",
    bg: "bg-blue-400/10",
    description: "Link your broker so EvoQuant can read balances, positions, and place trades on your behalf.",
    steps: [
      "Go to Settings → Brokers tab.",
      "Select your broker (Binance, Bybit, Coinbase, Kraken, OKX for crypto — or Interactive Brokers, E*TRADE, Schwab for stocks).",
      "Enter your API Key and Secret from your broker's API settings page. Enable read + trade permissions, and restrict the key to your IP if possible.",
      "Toggle 'Sandbox / Testnet' ON while testing, then switch to live when ready.",
      "Click Connect — your credentials are encrypted with quantum-resistant encryption and stored securely.",
    ],
    action: { label: "Go to Settings → Brokers", href: "/settings?tab=brokers" },
  },
  {
    icon: Wallet,
    title: "Connect Your Crypto Wallet",
    color: "text-purple-400",
    bg: "bg-purple-400/10",
    description: "Connect MetaMask, WalletConnect, Phantom, or a hardware wallet to trade on-chain and access DEX routing.",
    steps: [
      "Click the Wallet button in the top navigation bar.",
      "Choose your wallet type: MetaMask (EVM chains), Phantom (Solana), WalletConnect (mobile wallets), or Ledger/Trezor.",
      "Approve the connection in your wallet app — EvoQuant only requests read access by default.",
      "Your connected wallet address will appear in Settings → Wallets.",
      "To trade on-chain (Uniswap, Jupiter), ensure your wallet has enough gas/SOL for transaction fees.",
    ],
    action: { label: "Connect Wallet", href: "/settings?tab=wallets" },
  },
  {
    icon: BarChart2,
    title: "Explore the Dashboard & Trading",
    color: "text-yellow-400",
    bg: "bg-yellow-400/10",
    description: "Monitor your portfolio, get AI signals, and place trades all from one screen.",
    steps: [
      "The Dashboard shows your portfolio value, P&L, Sharpe ratio, and a live watchlist.",
      "Go to Trading to search any symbol — you'll see a price chart, AI signal (bullish/bearish/neutral), and technical indicators.",
      "Use the order panel to place Market, Limit, or Stop orders through your connected broker.",
      "The Portfolio page shows all open positions, historical trades, and performance analytics.",
      "Paper trading mode (top bar toggle) lets you practice without real money.",
    ],
    action: { label: "Go to Dashboard", href: "/dashboard" },
  },
  {
    icon: FlaskConical,
    title: "Backtest & Evolve Strategies",
    color: "text-orange-400",
    bg: "bg-orange-400/10",
    description: "Test your trading ideas against historical data before risking real capital.",
    steps: [
      "Go to Backtester and enter a symbol, date range, and starting capital.",
      "Choose a strategy template or define your own entry/exit rules.",
      "Run the backtest to see equity curve, win rate, Sharpe ratio, and max drawdown.",
      "Use Evolution Lab to automatically evolve better strategies using genetic algorithms — set your fitness criteria and let it run overnight.",
      "Strategies that pass backtesting can be promoted to live paper trading for forward testing.",
    ],
    action: { label: "Go to Backtester", href: "/backtester" },
  },
  {
    icon: Bell,
    title: "Set Up Price Alerts",
    color: "text-red-400",
    bg: "bg-red-400/10",
    description: "Never miss a move — get notified when markets hit your target levels.",
    steps: [
      "Go to Alerts in the sidebar.",
      "Click 'New Alert' and enter a symbol (e.g. BTC, AAPL, ETH-USD).",
      "Set your condition: price above, below, % change, or AI signal change.",
      "Alerts appear as notifications in the top bar and can trigger automated actions.",
      "You can create multiple alerts per symbol with different conditions.",
    ],
    action: { label: "Go to Alerts", href: "/alerts" },
  },
  {
    icon: Bot,
    title: "Use the AI Copilot",
    color: "text-cyan-400",
    bg: "bg-cyan-400/10",
    description: "Ask the AI Copilot anything about markets, strategies, or your portfolio.",
    steps: [
      "Go to AI Copilot in the sidebar.",
      "Ask questions like: 'What's the sentiment on NVDA?', 'Should I hedge my BTC position?', or 'Explain the current macro environment.'",
      "The copilot has access to your portfolio, live market data, and news sentiment.",
      "It can suggest entry/exit points, explain technical indicators, and help size positions.",
      "All responses are informational — final trading decisions are always yours.",
    ],
    action: { label: "Open AI Copilot", href: "/ai-copilot" },
  },
  {
    icon: ShieldCheck,
    title: "Security Best Practices",
    color: "text-evo-green",
    bg: "bg-evo-green/10",
    description: "Keep your account and funds safe with these important steps.",
    steps: [
      "Enable 2FA (two-factor authentication) in Settings → Security to protect your account.",
      "Always restrict broker API keys to read + trade only — never enable withdrawals.",
      "Whitelist your IP address in your broker's API settings if possible.",
      "Never share your API keys or password with anyone — EvoQuant staff will never ask for them.",
      "Use the paper trading mode to test new strategies before going live with real capital.",
    ],
    action: { label: "Enable 2FA in Settings", href: "/settings?tab=security" },
  },
];

export function OnboardingModal() {
  const { onboardingDone, setOnboardingDone } = useAppStore();
  const [step, setStep] = useState(0);
  const router = useRouter();

  if (onboardingDone) return null;

  const current = STEPS[step];
  const Icon = current.icon;
  const isLast = step === STEPS.length - 1;

  const handleAction = () => {
    if (current.action) {
      setOnboardingDone();
      router.push(current.action.href);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="w-full max-w-lg bg-evo-card border border-evo-border rounded-2xl shadow-2xl flex flex-col max-h-[90vh]">

        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-evo-border">
          <div className="flex items-center gap-2">
            <Zap className="w-5 h-5 text-evo-green" />
            <span className="text-sm font-semibold text-white">Getting Started</span>
          </div>
          <button
            onClick={setOnboardingDone}
            className="text-muted-foreground hover:text-white transition-colors"
            title="Skip tour"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Progress bar */}
        <div className="px-5 pt-4">
          <div className="flex gap-1">
            {STEPS.map((_, i) => (
              <button
                key={i}
                onClick={() => setStep(i)}
                className={cn(
                  "h-1 flex-1 rounded-full transition-all",
                  i <= step ? "bg-evo-green" : "bg-evo-border"
                )}
              />
            ))}
          </div>
          <p className="text-xs text-muted-foreground mt-1.5">Step {step + 1} of {STEPS.length}</p>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          <div className={cn("inline-flex items-center justify-center w-12 h-12 rounded-xl", current.bg)}>
            <Icon className={cn("w-6 h-6", current.color)} />
          </div>

          <div>
            <h2 className="text-xl font-bold text-white">{current.title}</h2>
            <p className="text-sm text-muted-foreground mt-1">{current.description}</p>
          </div>

          <ol className="space-y-3">
            {current.steps.map((s, i) => (
              <li key={i} className="flex gap-3">
                <span className={cn(
                  "flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold mt-0.5",
                  current.bg, current.color
                )}>
                  {i + 1}
                </span>
                <span className="text-sm text-white/80 leading-relaxed">{s}</span>
              </li>
            ))}
          </ol>
        </div>

        {/* Footer */}
        <div className="p-5 border-t border-evo-border flex items-center justify-between gap-3">
          <button
            onClick={() => setStep((s) => Math.max(0, s - 1))}
            disabled={step === 0}
            className="flex items-center gap-1 text-sm text-muted-foreground hover:text-white transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
          >
            <ChevronLeft className="w-4 h-4" /> Back
          </button>

          <div className="flex items-center gap-2">
            {current.action && (
              <button
                onClick={handleAction}
                className={cn(
                  "px-4 py-2 rounded-lg text-sm font-medium border transition-colors",
                  "border-evo-border text-white/70 hover:text-white hover:border-white/30"
                )}
              >
                {current.action.label}
              </button>
            )}

            {isLast ? (
              <button
                onClick={setOnboardingDone}
                className="flex items-center gap-2 px-5 py-2 bg-evo-green text-black font-semibold rounded-lg hover:bg-evo-green/90 transition-colors text-sm"
              >
                <CheckCircle2 className="w-4 h-4" /> Start Trading
              </button>
            ) : (
              <button
                onClick={() => setStep((s) => s + 1)}
                className="flex items-center gap-2 px-5 py-2 bg-evo-green text-black font-semibold rounded-lg hover:bg-evo-green/90 transition-colors text-sm"
              >
                Next <ChevronRight className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
