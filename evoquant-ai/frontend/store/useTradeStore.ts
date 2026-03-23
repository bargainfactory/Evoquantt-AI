import { create } from "zustand";

interface Order {
  id: string;
  symbol: string;
  side: "buy" | "sell";
  order_type: string;
  quantity: number;
  price?: number;
  status: string;
  filled_price?: number;
  pnl?: number;
  created_at: string;
  is_paper: boolean;
  broker: string;
  asset_class: string;
}

interface Position {
  symbol: string;
  quantity: number;
  avg_cost: number;
  current_price?: number;
  unrealized_pnl?: number;
  realized_pnl: number;
  market_value?: number;
  weight?: number;
  broker: string;
  asset_class: string;
}

interface TradeStore {
  orders: Order[];
  positions: Position[];
  pendingOrder: Partial<Order> | null;
  setOrders: (orders: Order[]) => void;
  setPositions: (positions: Position[]) => void;
  addOrder: (order: Order) => void;
  updateOrder: (id: string, updates: Partial<Order>) => void;
  setPendingOrder: (order: Partial<Order> | null) => void;
  clearPendingOrder: () => void;
}

export const useTradeStore = create<TradeStore>((set) => ({
  orders: [],
  positions: [],
  pendingOrder: null,
  setOrders: (orders) => set({ orders }),
  setPositions: (positions) => set({ positions }),
  addOrder: (order) => set((s) => ({ orders: [order, ...s.orders] })),
  updateOrder: (id, updates) =>
    set((s) => ({
      orders: s.orders.map((o) => (o.id === id ? { ...o, ...updates } : o)),
    })),
  setPendingOrder: (order) => set({ pendingOrder: order }),
  clearPendingOrder: () => set({ pendingOrder: null }),
}));
