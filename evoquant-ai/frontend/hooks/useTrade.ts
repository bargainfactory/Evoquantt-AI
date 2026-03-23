"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import api from "@/lib/api";
import { useTradeStore } from "@/store/useTradeStore";

export function useOrders(params?: Record<string, unknown>) {
  const setOrders = useTradeStore((s) => s.setOrders);
  return useQuery({
    queryKey: ["orders", params],
    queryFn: async () => {
      const r = await api.getOrders(params);
      setOrders(r.data);
      return r.data;
    },
    refetchInterval: 5000,
  });
}

export function usePlaceOrder() {
  const qc = useQueryClient();
  const addOrder = useTradeStore((s) => s.addOrder);

  return useMutation({
    mutationFn: (order: Record<string, unknown>) => api.placeOrder(order),
    onSuccess: (r) => {
      addOrder(r.data);
      qc.invalidateQueries({ queryKey: ["orders"] });
      qc.invalidateQueries({ queryKey: ["portfolio"] });
      toast.success(`Order placed: ${r.data.symbol} ${r.data.side}`);
    },
    onError: (e: unknown) => {
      const err = e as { response?: { data?: { detail?: string } } };
      toast.error(err?.response?.data?.detail || "Order failed");
    },
  });
}

export function useCancelOrder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.cancelOrder(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["orders"] });
      toast.success("Order cancelled");
    },
    onError: () => toast.error("Failed to cancel order"),
  });
}

export function usePositions() {
  const setPositions = useTradeStore((s) => s.setPositions);
  return useQuery({
    queryKey: ["positions"],
    queryFn: async () => {
      const r = await api.getPositions();
      setPositions(r.data);
      return r.data;
    },
    refetchInterval: 10000,
  });
}
