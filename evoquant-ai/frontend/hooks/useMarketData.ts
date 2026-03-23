"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import api from "@/lib/api";
import { createMarketSocket, createOrderBookSocket } from "@/lib/websocket";
import { useMarketStore } from "@/store/useMarketStore";

export function useQuote(symbol: string) {
  return useQuery({
    queryKey: ["quote", symbol],
    queryFn: () => api.getQuote(symbol).then((r) => r.data),
    refetchInterval: 10000,
    enabled: !!symbol,
  });
}

export function useOHLCV(symbol: string, period = "1y", interval = "1d") {
  return useQuery({
    queryKey: ["ohlcv", symbol, period, interval],
    queryFn: () => api.getOHLCV(symbol, period, interval).then((r) => r.data),
    staleTime: 60000,
    enabled: !!symbol,
  });
}

export function useIndicators(symbol: string, period = "1y") {
  return useQuery({
    queryKey: ["indicators", symbol, period],
    queryFn: () => api.getIndicators(symbol, period).then((r) => r.data),
    staleTime: 60000,
    enabled: !!symbol,
  });
}

export function useMlPredict(symbol: string) {
  return useQuery({
    queryKey: ["ml-predict", symbol],
    queryFn: () => api.getMlPredict(symbol).then((r) => r.data),
    staleTime: 300000,
    enabled: !!symbol,
  });
}

export function useSentiment(symbol: string) {
  return useQuery({
    queryKey: ["sentiment", symbol],
    queryFn: () => api.getSentiment(symbol).then((r) => r.data),
    staleTime: 300000,
    enabled: !!symbol,
  });
}

export function useMacro() {
  return useQuery({
    queryKey: ["macro"],
    queryFn: () => api.getMacro().then((r) => r.data),
    staleTime: 600000,
  });
}

export function useRealTimeTick(symbol: string) {
  const setTick = useMarketStore((s) => s.setTick);
  const socketRef = useRef<ReturnType<typeof createMarketSocket> | null>(null);

  useEffect(() => {
    if (!symbol) return;
    socketRef.current = createMarketSocket(symbol);
    socketRef.current.connect();
    const unsubscribe = socketRef.current.on("tick", (data) => {
      setTick(symbol, {
        price: Number(data.price),
        change: Number(data.change),
        change_pct: Number(data.change_pct),
        timestamp: Number(data.timestamp),
      });
    });
    return () => {
      unsubscribe();
      socketRef.current?.disconnect();
    };
  }, [symbol, setTick]);

  return useMarketStore((s) => s.ticks[symbol]);
}

export function useOrderBook(symbol: string) {
  const setOrderBook = useMarketStore((s) => s.setOrderBook);
  const socketRef = useRef<ReturnType<typeof createOrderBookSocket> | null>(null);

  useEffect(() => {
    if (!symbol) return;
    socketRef.current = createOrderBookSocket(symbol);
    socketRef.current.connect();
    const unsubscribe = socketRef.current.on("orderbook", (data) => {
      setOrderBook(symbol, {
        bids: data.bids as number[][],
        asks: data.asks as number[][],
      });
    });
    return () => {
      unsubscribe();
      socketRef.current?.disconnect();
    };
  }, [symbol, setOrderBook]);

  return useMarketStore((s) => s.orderBook[symbol]);
}

export function useSearchSymbols(query: string) {
  return useQuery({
    queryKey: ["search", query],
    queryFn: () => api.searchSymbols(query).then((r) => r.data),
    enabled: query.length > 1,
    staleTime: 60000,
  });
}
