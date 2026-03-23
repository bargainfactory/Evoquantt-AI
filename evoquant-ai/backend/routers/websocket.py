"""
WebSocket router for real-time market data, order updates, and recursive sell progress.
"""
import asyncio
import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from starlette.websockets import WebSocketState

router = APIRouter()


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


@router.websocket("/market/{symbol}")
async def market_stream(websocket: WebSocket, symbol: str):
    """Stream real-time ticker data for a symbol."""
    channel = f"market:{symbol}"
    await manager.connect(websocket, channel)
    try:
        import yfinance as yf
        import random
        ticker = yf.Ticker(symbol)
        base_info = ticker.fast_info
        base_price = float(base_info.last_price or 100)

        while True:
            # Simulate real-time tick (replace with ccxt-pro watch_ticker in production)
            change = random.gauss(0, base_price * 0.001)
            price = base_price + change
            base_price = price
            await websocket.send_json({
                "type": "tick",
                "symbol": symbol,
                "price": round(price, 4),
                "change": round(change, 4),
                "change_pct": round(change / base_price * 100, 3),
                "timestamp": __import__("time").time(),
            })
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel)
    except Exception:
        manager.disconnect(websocket, channel)


@router.websocket("/orderbook/{symbol}")
async def orderbook_stream(websocket: WebSocket, symbol: str):
    """Stream order book depth."""
    channel = f"orderbook:{symbol}"
    await manager.connect(websocket, channel)
    try:
        import random
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        base_price = float(ticker.fast_info.last_price or 100)

        while True:
            bids = [[round(base_price - i * 0.01, 4), round(random.uniform(1, 100), 2)] for i in range(1, 11)]
            asks = [[round(base_price + i * 0.01, 4), round(random.uniform(1, 100), 2)] for i in range(1, 11)]
            await websocket.send_json({
                "type": "orderbook",
                "symbol": symbol,
                "bids": bids,
                "asks": asks,
                "timestamp": __import__("time").time(),
            })
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
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
