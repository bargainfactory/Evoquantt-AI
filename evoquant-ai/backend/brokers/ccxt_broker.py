"""
ccxt-pro broker adapter: Binance, Bybit, Coinbase, Kraken, OKX + futures/perpetuals.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from brokers.base_broker import BaseBroker, Balance, Order, Position

try:
    import ccxt.pro as ccxtpro
    import ccxt
    CCXT_AVAILABLE = True
except ImportError:
    CCXT_AVAILABLE = False


EXCHANGE_CONFIGS: dict[str, dict[str, Any]] = {
    "binance": {"options": {"defaultType": "spot"}, "enableRateLimit": True},
    "binance_futures": {"options": {"defaultType": "future"}, "enableRateLimit": True},
    "bybit": {"options": {"defaultType": "spot"}, "enableRateLimit": True},
    "coinbase": {"enableRateLimit": True},
    "kraken": {"enableRateLimit": True},
    "okx": {"enableRateLimit": True},
}


class CCXTBroker(BaseBroker):
    name = "ccxt"
    supports_crypto = True
    supports_futures = True

    def __init__(
        self,
        exchange_id: str,
        api_key: str,
        secret: str,
        passphrase: str = "",
        testnet: bool = True,
    ):
        self.exchange_id = exchange_id
        self.api_key = api_key
        self.secret = secret
        self.passphrase = passphrase
        self.testnet = testnet
        self._exchange: Any = None

    async def connect(self) -> bool:
        if not CCXT_AVAILABLE:
            raise RuntimeError("ccxt-pro not installed")
        exchange_class = getattr(ccxtpro, self.exchange_id, None)
        if exchange_class is None:
            exchange_class = getattr(ccxt, self.exchange_id)
        cfg = EXCHANGE_CONFIGS.get(self.exchange_id, {"enableRateLimit": True})
        cfg["apiKey"] = self.api_key
        cfg["secret"] = self.secret
        if self.passphrase:
            cfg["password"] = self.passphrase
        if self.testnet:
            cfg["sandbox"] = True
        self._exchange = exchange_class(cfg)
        if self.testnet and hasattr(self._exchange, "set_sandbox_mode"):
            self._exchange.set_sandbox_mode(True)
        await self._exchange.load_markets()
        return True

    async def disconnect(self) -> None:
        if self._exchange and hasattr(self._exchange, "close"):
            await self._exchange.close()

    async def get_balances(self) -> list[Balance]:
        raw = await self._exchange.fetch_balance()
        balances = []
        for currency, info in raw.get("total", {}).items():
            if float(info or 0) > 0:
                balances.append(Balance(
                    currency=currency,
                    total=Decimal(str(raw["total"].get(currency, 0) or 0)),
                    available=Decimal(str(raw["free"].get(currency, 0) or 0)),
                    reserved=Decimal(str(raw["used"].get(currency, 0) or 0)),
                ))
        return balances

    async def get_positions(self) -> list[Position]:
        try:
            raw = await self._exchange.fetch_positions()
        except Exception:
            return []
        positions = []
        for pos in raw:
            if not pos or float(pos.get("contracts", 0) or 0) == 0:
                continue
            positions.append(Position(
                symbol=pos["symbol"],
                quantity=Decimal(str(pos.get("contracts", 0) or 0)),
                avg_cost=Decimal(str(pos.get("entryPrice", 0) or 0)),
                current_price=Decimal(str(pos.get("markPrice", 0) or 0)),
                unrealized_pnl=Decimal(str(pos.get("unrealizedPnl", 0) or 0)),
                side=pos.get("side", "long"),
            ))
        return positions

    async def place_order(self, order: Order) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if order.order_type == "stop":
            params["stopPrice"] = float(order.stop_price)
        result = await self._exchange.create_order(
            symbol=order.symbol,
            type=order.order_type,
            side=order.side,
            amount=float(order.quantity),
            price=float(order.price) if order.price else None,
            params=params,
        )
        return result

    async def cancel_order(self, order_id: str, symbol: str | None = None) -> bool:
        try:
            await self._exchange.cancel_order(order_id, symbol)
            return True
        except Exception:
            return False

    async def get_order_status(self, order_id: str) -> dict[str, Any]:
        return await self._exchange.fetch_order(order_id)

    async def get_open_orders(self) -> list[dict[str, Any]]:
        return await self._exchange.fetch_open_orders()

    async def get_trade_history(self, symbol: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        return await self._exchange.fetch_my_trades(symbol=symbol, limit=limit)

    async def get_ticker(self, symbol: str) -> dict[str, Any]:
        return await self._exchange.fetch_ticker(symbol)

    async def get_ohlcv(self, symbol: str, timeframe: str = "1h", limit: int = 500) -> list[list[float]]:
        return await self._exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)

    async def watch_ticker(self, symbol: str):
        """WebSocket ticker stream."""
        while True:
            ticker = await self._exchange.watch_ticker(symbol)
            yield ticker

    async def watch_order_book(self, symbol: str, limit: int = 20):
        """WebSocket order book stream."""
        while True:
            book = await self._exchange.watch_order_book(symbol, limit=limit)
            yield book
