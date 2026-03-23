import { create } from "zustand";

interface Tick {
  price: number;
  change: number;
  change_pct: number;
  timestamp: number;
}

interface MarketStore {
  watchlist: string[];
  ticks: Record<string, Tick>;
  activeSymbol: string;
  activeInterval: string;
  activeAssetClass: string;
  orderBook: Record<string, { bids: number[][]; asks: number[][] }>;
  addToWatchlist: (symbol: string) => void;
  removeFromWatchlist: (symbol: string) => void;
  setTick: (symbol: string, tick: Tick) => void;
  setActiveSymbol: (symbol: string) => void;
  setActiveInterval: (interval: string) => void;
  setActiveAssetClass: (ac: string) => void;
  setOrderBook: (symbol: string, data: { bids: number[][]; asks: number[][] }) => void;
}

export const useMarketStore = create<MarketStore>((set) => ({
  watchlist: ["AAPL", "NVDA", "TSLA", "BTC/USDT", "ETH/USDT", "EURUSD=X"],
  ticks: {},
  activeSymbol: "AAPL",
  activeInterval: "1d",
  activeAssetClass: "stock",
  orderBook: {},
  addToWatchlist: (symbol) =>
    set((s) => ({
      watchlist: s.watchlist.includes(symbol) ? s.watchlist : [...s.watchlist, symbol],
    })),
  removeFromWatchlist: (symbol) =>
    set((s) => ({ watchlist: s.watchlist.filter((w) => w !== symbol) })),
  setTick: (symbol, tick) =>
    set((s) => ({ ticks: { ...s.ticks, [symbol]: tick } })),
  setActiveSymbol: (symbol) => set({ activeSymbol: symbol }),
  setActiveInterval: (interval) => set({ activeInterval: interval }),
  setActiveAssetClass: (ac) => set({ activeAssetClass: ac }),
  setOrderBook: (symbol, data) =>
    set((s) => ({ orderBook: { ...s.orderBook, [symbol]: data } })),
}));
