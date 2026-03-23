const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

type MessageHandler = (data: Record<string, unknown>) => void;

export class EvoWebSocket {
  private ws: WebSocket | null = null;
  private handlers: Map<string, MessageHandler[]> = new Map();
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectDelay = 1000;
  private maxReconnectDelay = 30000;

  constructor(private url: string) {}

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) return;
    this.ws = new WebSocket(this.url);
    this.ws.onopen = () => {
      this.reconnectDelay = 1000;
      this.emit("connection", { status: "connected" });
    };
    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        const type = data.type || "message";
        this.emit(type, data);
        this.emit("*", data);
      } catch {}
    };
    this.ws.onclose = () => {
      this.emit("connection", { status: "disconnected" });
      this.scheduleReconnect();
    };
    this.ws.onerror = () => {
      this.emit("error", { message: "WebSocket error" });
    };
  }

  private scheduleReconnect() {
    if (this.reconnectTimer) return;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxReconnectDelay);
      this.connect();
    }, this.reconnectDelay);
  }

  on(event: string, handler: MessageHandler): () => void {
    if (!this.handlers.has(event)) this.handlers.set(event, []);
    this.handlers.get(event)!.push(handler);
    return () => this.off(event, handler);
  }

  off(event: string, handler: MessageHandler): void {
    const handlers = this.handlers.get(event);
    if (handlers) {
      const idx = handlers.indexOf(handler);
      if (idx !== -1) handlers.splice(idx, 1);
    }
  }

  private emit(event: string, data: Record<string, unknown>): void {
    this.handlers.get(event)?.forEach((h) => h(data));
  }

  disconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.ws?.close();
    this.ws = null;
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

// Factory functions for each WS endpoint
export function createMarketSocket(symbol: string): EvoWebSocket {
  return new EvoWebSocket(`${WS_URL}/ws/market/${symbol}`);
}

export function createOrderBookSocket(symbol: string): EvoWebSocket {
  return new EvoWebSocket(`${WS_URL}/ws/orderbook/${symbol}`);
}

export function createPortfolioSocket(userId: string): EvoWebSocket {
  return new EvoWebSocket(`${WS_URL}/ws/portfolio/${userId}`);
}

export function createRecursiveSellSocket(jobId: string): EvoWebSocket {
  return new EvoWebSocket(`${WS_URL}/ws/recursive-sell/${jobId}`);
}
