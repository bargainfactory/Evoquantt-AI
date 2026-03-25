"""
WebSocket router for real-time market data, order updates, and recursive sell progress.

Live data sources (no API key required):
  - Crypto: Binance public WebSocket (wss://stream.binance.com) — tick-by-tick
  - Stocks: yfinance polling every 5s — 15-min delayed during market hours
"""
import asyncio
import json
import time
from typing import Any

import httpx
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

router = APIRouter()

CRYPTO_BASES = {
    "BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "AVAX",
    "MATIC", "DOT", "LINK", "UNI", "AAVE", "LTC", "BCH", "ATOM",
    "NEAR", "APT", "ARB", "OP", "SUI", "INJ", "TIA", "SEI",
}


def _is_crypto(symbol: str) -> bool:
    s = symbol.upper().replace("-USDT", "").replace("USDT", "").replace("-USD", "")
    return s in CRYPTO_BASES or symbol.upper().endswith("USDT")


def _binance_ws_symbol(symbol: str) -> str:
    s = symbol.upper().replace("-", "").replace("/", "")
    if not s.endswith("USDT") and not s.endswith("BUSD"):
        s = s + "USDT"
    return s.lower()


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel: str):
        await websocket.accept()
        if channel not in self.active_connections:
            self.active_connections[channel] = []
        self.active_connections[channel].append(websocket)

    def disconnect(self, websocket: WebSocket, channel: str):
        conns = self.active_connections.get(channel, [])
        if websocket in conns:
            conns.remove(websocket)

    async def send_to_channel(self, channel: str, data: dict[str, Any]):
        conns = self.active_connections.get(channel, [])
        dead = []
        for ws in conns:
            try:
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, channel)


manager = ConnectionManager()


async def _stream_binance_crypto(websocket: WebSocket, symbol: str):
    """Connect to Binance public trade stream and relay ticks to client."""
    import websockets as ws_lib
    bs = _binance_ws_symbol(symbol)
    url = f"wss://stream.binance.com:9443/ws/{bs}@aggTrade"
    open_price = None
    try:
        async with ws_lib.connect(url, ping_interval=20) as binance_ws:
            async for raw in binance_ws:
                if websocket.client_state != WebSocketState.CONNECTED:
                    break
                data = json.loads(raw)
                price = float(data["p"])
                if open_price is None:
                    open_price = price
                change = price - open_price
                await websocket.send_json({
                    "type": "tick",
                    "symbol": symbol.upper(),
                    "price": price,
                    "change": round(change, 6),
                    "change_pct": round(change / open_price * 100, 4) if open_price else 0,
                    "volume": float(data.get("q", 0)),
                    "timestamp": data.get("T", time.time() * 1000) / 1000,
                    "source": "binance",
                })
    except Exception:
        pass


async def _stream_yfinance_stock(websocket: WebSocket, symbol: str):
    """Poll yfinance every 5 seconds for stock quotes."""
    import yfinance as yf
    ticker = yf.Ticker(symbol)
    open_price = None
    while websocket.client_state == WebSocketState.CONNECTED:
        try:
            hist = ticker.history(period="1d", interval="1m")
            if not hist.empty:
                price = float(hist["Close"].iloc[-1])
                if open_price is None:
                    open_price = float(hist["Open"].iloc[0])
                change = price - open_price
                await websocket.send_json({
                    "type": "tick",
                    "symbol": symbol.upper(),
                    "price": round(price, 4),
                    "change": round(change, 4),
                    "change_pct": round(change / open_price * 100, 3) if open_price else 0,
                    "timestamp": time.time(),
                    "source": "yfinance",
                })
        except Exception:
            pass
        await asyncio.sleep(5)


@router.websocket("/market/{symbol}")
async def market_stream(websocket: WebSocket, symbol: str):
    """Stream real-time ticker. Binance WS for crypto, yfinance poll for stocks."""
    channel = f"market:{symbol}"
    await manager.connect(websocket, channel)
    try:
        if _is_crypto(symbol):
            await _stream_binance_crypto(websocket, symbol)
        else:
            await _stream_yfinance_stock(websocket, symbol)
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket, channel)


@router.websocket("/orderbook/{symbol}")
async def orderbook_stream(websocket: WebSocket, symbol: str):
    """Stream live order book from Binance (crypto) or simulated depth (stocks)."""
    channel = f"orderbook:{symbol}"
    await manager.connect(websocket, channel)
    try:
        if _is_crypto(symbol):
            import websockets as ws_lib
            bs = _binance_ws_symbol(symbol)
            url = f"wss://stream.binance.com:9443/ws/{bs}@depth10@100ms"
            try:
                async with ws_lib.connect(url, ping_interval=20) as binance_ws:
                    async for raw in binance_ws:
                        if websocket.client_state != WebSocketState.CONNECTED:
                            break
                        data = json.loads(raw)
                        await websocket.send_json({
                            "type": "orderbook",
                            "symbol": symbol.upper(),
                            "bids": [[float(p), float(q)] for p, q in data.get("bids", [])],
                            "asks": [[float(p), float(q)] for p, q in data.get("asks", [])],
                            "timestamp": time.time(),
                            "source": "binance",
                        })
            except Exception:
                pass
        else:
            # For stocks, poll Binance REST for mid-price simulation
            import yfinance as yf
            import random
            ticker = yf.Ticker(symbol)
            try:
                base_price = float(ticker.fast_info.last_price or 100)
            except Exception:
                try:
                    hist = ticker.history(period="1d")
                    base_price = float(hist["Close"].iloc[-1]) if not hist.empty else 100.0
                except Exception:
                    base_price = 100.0
            while websocket.client_state == WebSocketState.CONNECTED:
                spread = base_price * 0.0002
                bids = [[round(base_price - spread * i, 4), round(random.uniform(10, 500), 0)] for i in range(1, 11)]
                asks = [[round(base_price + spread * i, 4), round(random.uniform(10, 500), 0)] for i in range(1, 11)]
                await websocket.send_json({
                    "type": "orderbook", "symbol": symbol.upper(),
                    "bids": bids, "asks": asks, "timestamp": time.time(), "source": "estimated",
                })
                await asyncio.sleep(2)
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket, channel)


@router.websocket("/portfolio/{user_id}")
async def portfolio_stream(websocket: WebSocket, user_id: str):
    """Stream portfolio updates."""
    channel = f"portfolio:{user_id}"
    await manager.connect(websocket, channel)
    try:
        while True:
            await websocket.send_json({"type": "heartbeat", "user_id": user_id})
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket, channel)


@router.websocket("/recursive-sell/{job_id}")
async def recursive_sell_stream(websocket: WebSocket, job_id: str):
    """Stream recursive sell optimization progress."""
    from routers.recursive_sell import _jobs
    await websocket.accept()
    try:
        prev_depth = -1
        while True:
            job = _jobs.get(job_id, {})
            status = job.get("status", "not_found")
            progress = job.get("progress", {})
            current_depth = progress.get("depth", 0)

            if status == "completed":
                await websocket.send_json({
                    "type": "completed",
                    "job_id": job_id,
                    "best_sharpe": job.get("result", {}).get("best_sharpe"),
                    "best_return": job.get("result", {}).get("best_return"),
                    "iterations_total": job.get("result", {}).get("iterations_total"),
                    "convergence": job.get("result", {}).get("convergence_history", []),
                })
                break
            elif status == "failed":
                await websocket.send_json({"type": "error", "error": job.get("error")})
                break
            elif status == "running" and current_depth != prev_depth:
                await websocket.send_json({
                    "type": "progress",
                    "job_id": job_id,
                    "depth": current_depth,
                    "max_depth": progress.get("max_depth"),
                    "best_sharpe": progress.get("best_sharpe"),
                })
                prev_depth = current_depth

            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        pass
