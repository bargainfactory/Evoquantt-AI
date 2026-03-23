"use client";

import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";

export function usePortfolioSummary() {
  return useQuery({
    queryKey: ["portfolio", "summary"],
    queryFn: () => api.getPortfolioSummary().then((r) => r.data),
    refetchInterval: 10000,
  });
}

export function usePortfolioHistory(days = 30) {
  return useQuery({
    queryKey: ["portfolio", "history", days],
    queryFn: () => api.getPortfolioHistory(days).then((r) => r.data),
    staleTime: 60000,
  });
}

export function useRiskMetrics() {
  return useQuery({
    queryKey: ["portfolio", "risk"],
    queryFn: () => api.getRiskMetrics().then((r) => r.data),
    staleTime: 60000,
  });
}

export function useAllocation() {
  return useQuery({
    queryKey: ["portfolio", "allocation"],
    queryFn: () => api.getAllocation().then((r) => r.data),
    staleTime: 30000,
  });
}
