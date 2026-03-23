"""
Tradier broker adapter - stocks + options.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

import httpx
from brokers.base_broker import BaseBroker, Balance, Order, Position
from config import settings


class TradierBroker(BaseBroker):
    name = "tradier"
    supports_options = True

    BASE_URL_LIVE = "https://api.tradier.com/v1"
    BASE_URL_SANDBOX = "https://sandbox.tradier.com/v1"

    def __init__(self, access_token: str = ""):
        self.access_token = access_token or settings.TRADIER_ACCESS_TOKEN
        self.base_url = self.BASE_URL_SANDBOX if settings.TRADIER_SANDBOX else self.BASE_URL_LIVE

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.access_token}", "Accept": "application/json"}

    async def connect(self) -> bool:
        return bool(self.access_token)

    async def disconnect(self) -> None:
        pass

    async def _get_account_id(self) -> str:
        url = f"{self.base_url}/user/profile"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=self._headers())
            data = resp.json()
        accounts = data.get("profile", {}).get("account", [])
        if isinstance(accounts, list):
            return accounts[0].get("account_number", "")
        return accounts.get("account_number", "")

    async def get_balances(self) -> list[Balance]:
        acct_id = await self._get_account_id()
        if not acct_id:
            return []
        url = f"{self.base_url}/accounts/{acct_id}/balances"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=self._headers())
            data = resp.json()
        b = data.get("balances", {})
        return [Balance(
            currency="USD",
            total=Decimal(str(b.get("total_equity", 0))),
            available=Decimal(str(b.get("cash", {}).get("cash_available", 0))),
            reserved=Decimal(str(b.get("pending_cash", 0))),
        )]

    async def get_positions(self) -> list[Position]:
        acct_id = await self._get_account_id()
        if not acct_id:
            return []
        url = f"{self.base_url}/accounts/{acct_id}/positions"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=self._headers())
            data = resp.json()
        raw_positions = data.get("positions", {}).get("position", [])
        if not isinstance(raw_positions, list):
            raw_positions = [raw_positions]
        positions = []
        for p in raw_positions:
            qty = Decimal(str(p.get("quantity", 0)))
            cost = Decimal(str(p.get("cost_basis", 0))) / (qty if qty != 0 else Decimal("1"))
            positions.append(Position(
                symbol=p.get("symbol", ""),
                quantity=qty,
                avg_cost=cost,
                current_price=Decimal("0"),
                unrealized_pnl=Decimal("0"),
            ))
        return positions

    async def place_order(self, order: Order) -> dict[str, Any]:
        acct_id = await self._get_account_id()
        url = f"{self.base_url}/accounts/{acct_id}/orders"
        order_type_map = {"market": "market", "limit": "limit", "stop": "stop", "stop_limit": "stop_limit"}
        data = {
            "class": "equity",
            "symbol": order.symbol,
            "side": "buy" if order.side == "buy" else "sell",
            "quantity": str(order.quantity),
            "type": order_type_map.get(order.order_type, "market"),
            "duration": "day",
            **({"price": str(order.price)} if order.price else {}),
            **({"stop": str(order.stop_price)} if order.stop_price else {}),
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, data=data, headers=self._headers())
            return resp.json()

    async def cancel_order(self, order_id: str, symbol: str | None = None) -> bool:
        acct_id = await self._get_account_id()
        url = f"{self.base_url}/accounts/{acct_id}/orders/{order_id}"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.delete(url, headers=self._headers())
            return resp.status_code == 200

    async def get_order_status(self, order_id: str) -> dict[str, Any]:
        acct_id = await self._get_account_id()
        url = f"{self.base_url}/accounts/{acct_id}/orders/{order_id}"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=self._headers())
            return resp.json()

    async def get_open_orders(self) -> list[dict[str, Any]]:
        acct_id = await self._get_account_id()
        url = f"{self.base_url}/accounts/{acct_id}/orders"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=self._headers())
            data = resp.json()
        orders = data.get("orders", {}).get("order", [])
        return orders if isinstance(orders, list) else [orders] if orders else []

    async def get_trade_history(self, symbol: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        acct_id = await self._get_account_id()
        url = f"{self.base_url}/accounts/{acct_id}/history?limit={limit}"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=self._headers())
            data = resp.json()
        history = data.get("history", {}).get("event", [])
        return history if isinstance(history, list) else []

    async def get_options_chain(self, symbol: str, expiry: str) -> dict[str, Any]:
        url = f"{self.base_url}/markets/options/chains?symbol={symbol}&expiration={expiry}&greeks=true"
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers=self._headers())
            return resp.json()

    async def get_options_expirations(self, symbol: str) -> list[str]:
        url = f"{self.base_url}/markets/options/expirations?symbol={symbol}"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=self._headers())
            data = resp.json()
        dates = data.get("expirations", {}).get("date", [])
        return dates if isinstance(dates, list) else [dates]
