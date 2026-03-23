"""
Interactive Brokers adapter via ib_insync.
Supports stocks, options, futures, forex, and crypto.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from brokers.base_broker import BaseBroker, Balance, Order, Position

try:
    from ib_insync import IB, Contract, Order as IBOrder, Stock, Option, Future, Forex, Crypto
    IB_AVAILABLE = True
except ImportError:
    IB_AVAILABLE = False

from config import settings


class IBKRBroker(BaseBroker):
    name = "ibkr"
    supports_options = True
    supports_futures = True
    supports_forex = True
    supports_crypto = True

    def __init__(self, host: str | None = None, port: int | None = None, client_id: int | None = None):
        self.host = host or settings.IBKR_HOST
        self.port = port or settings.IBKR_PORT
        self.client_id = client_id or settings.IBKR_CLIENT_ID
        self._ib: Any = None

    async def connect(self) -> bool:
        if not IB_AVAILABLE:
            raise RuntimeError("ib_insync not installed")
        self._ib = IB()
        await self._ib.connectAsync(self.host, self.port, clientId=self.client_id)
        return self._ib.isConnected()

    async def disconnect(self) -> None:
        if self._ib and self._ib.isConnected():
            self._ib.disconnect()

    async def get_balances(self) -> list[Balance]:
        if not self._ib:
            return []
        account_values = self._ib.accountValues()
        balances: dict[str, dict[str, float]] = {}
        for av in account_values:
            if av.tag in ("TotalCashValue", "AvailableFunds", "NetLiquidation"):
                ccy = av.currency
                if ccy not in balances:
                    balances[ccy] = {}
                balances[ccy][av.tag] = float(av.value or 0)
        result = []
        for ccy, vals in balances.items():
            total = vals.get("NetLiquidation", 0)
            available = vals.get("AvailableFunds", 0)
            result.append(Balance(
                currency=ccy,
                total=Decimal(str(total)),
                available=Decimal(str(available)),
                reserved=Decimal(str(total - available)),
            ))
        return result

    async def get_positions(self) -> list[Position]:
        if not self._ib:
            return []
        positions = []
        for pos in self._ib.positions():
            contract = pos.contract
            mkt_price = 0.0
            try:
                ticker = self._ib.reqMktData(contract, "", False, False)
                await self._ib.sleep(0.5)
                mkt_price = float(ticker.last or ticker.close or 0)
            except Exception:
                pass
            avg_cost = float(pos.avgCost or 0)
            qty = float(pos.position or 0)
            positions.append(Position(
                symbol=f"{contract.symbol}.{contract.exchange}",
                quantity=Decimal(str(qty)),
                avg_cost=Decimal(str(avg_cost)),
                current_price=Decimal(str(mkt_price)),
                unrealized_pnl=Decimal(str((mkt_price - avg_cost) * qty)),
            ))
        return positions

    def _create_contract(self, symbol: str, asset_class: str = "stock", exchange: str = "SMART") -> Any:
        if not IB_AVAILABLE:
            return None
        aclass = asset_class.lower()
        if aclass == "stock":
            return Stock(symbol, exchange, "USD")
        elif aclass == "forex":
            base, quote = (symbol[:3], symbol[3:]) if len(symbol) == 6 else symbol.split("/")
            return Forex(f"{base}{quote}")
        elif aclass == "futures":
            return Future(symbol, exchange=exchange)
        elif aclass == "crypto":
            return Crypto(symbol, "PAXOS", "USD")
        return Stock(symbol, exchange, "USD")

    async def place_order(self, order: Order) -> dict[str, Any]:
        if not self._ib:
            raise RuntimeError("Not connected to IBKR")
        contract = self._create_contract(order.symbol)
        ib_order = IBOrder()
        ib_order.action = order.side.upper()
        ib_order.totalQuantity = float(order.quantity)
        order_type_map = {"market": "MKT", "limit": "LMT", "stop": "STP", "stop_limit": "STP LMT"}
        ib_order.orderType = order_type_map.get(order.order_type, "MKT")
        if order.price:
            ib_order.lmtPrice = float(order.price)
        if order.stop_price:
            ib_order.auxPrice = float(order.stop_price)

        trade = self._ib.placeOrder(contract, ib_order)
        await self._ib.sleep(1)
        return {
            "order_id": str(trade.order.orderId),
            "status": str(trade.orderStatus.status),
            "symbol": order.symbol,
        }

    async def cancel_order(self, order_id: str, symbol: str | None = None) -> bool:
        if not self._ib:
            return False
        trades = self._ib.trades()
        for trade in trades:
            if str(trade.order.orderId) == order_id:
                self._ib.cancelOrder(trade.order)
                return True
        return False

    async def get_order_status(self, order_id: str) -> dict[str, Any]:
        trades = self._ib.trades()
        for trade in trades:
            if str(trade.order.orderId) == order_id:
                return {
                    "order_id": order_id,
                    "status": trade.orderStatus.status,
                    "filled": trade.orderStatus.filled,
                    "remaining": trade.orderStatus.remaining,
                }
        return {"order_id": order_id, "status": "not_found"}

    async def get_open_orders(self) -> list[dict[str, Any]]:
        if not self._ib:
            return []
        return [
            {"order_id": str(t.order.orderId), "symbol": t.contract.symbol,
             "side": t.order.action, "qty": t.order.totalQuantity,
             "status": t.orderStatus.status}
            for t in self._ib.trades() if t.isActive()
        ]

    async def get_trade_history(self, symbol: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        if not self._ib:
            return []
        fills = self._ib.fills()
        result = []
        for fill in fills[:limit]:
            if symbol and fill.contract.symbol != symbol:
                continue
            result.append({
                "symbol": fill.contract.symbol,
                "side": fill.execution.side,
                "quantity": fill.execution.shares,
                "price": fill.execution.price,
                "time": str(fill.execution.time),
            })
        return result

    async def get_options_chain(self, symbol: str, expiry: str) -> list[dict[str, Any]]:
        """Fetch options chain from IBKR."""
        if not self._ib:
            return []
        chains = await self._ib.reqSecDefOptParamsAsync("", "", symbol, "STK")
        return [{"strike": c.strikes, "expiry": c.expirations} for c in chains[:5]]
