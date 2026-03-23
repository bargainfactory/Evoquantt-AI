"""
Charles Schwab broker adapter (OAuth2 / API v1).
"""
from __future__ import annotations

import base64
from decimal import Decimal
from typing import Any

import httpx
from brokers.base_broker import BaseBroker, Balance, Order, Position
from config import settings


class SchwabBroker(BaseBroker):
    name = "schwab"
    supports_options = True

    BASE_URL = "https://api.schwabapi.com/trader/v1"
    AUTH_URL = "https://api.schwabapi.com/v1/oauth/authorize"
    TOKEN_URL = "https://api.schwabapi.com/v1/oauth/token"

    def __init__(self, access_token: str = "", refresh_token: str = ""):
        self.access_token = access_token
        self.refresh_token = refresh_token

    @classmethod
    def get_authorize_url(cls) -> str:
        params = (f"?response_type=code&client_id={settings.SCHWAB_APP_KEY}"
                  f"&redirect_uri={settings.SCHWAB_CALLBACK_URL}")
        return cls.AUTH_URL + params

    @classmethod
    async def exchange_code(cls, code: str) -> dict[str, str]:
        creds = base64.b64encode(f"{settings.SCHWAB_APP_KEY}:{settings.SCHWAB_APP_SECRET}".encode()).decode()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                cls.TOKEN_URL,
                data={"grant_type": "authorization_code", "code": code, "redirect_uri": settings.SCHWAB_CALLBACK_URL},
                headers={"Authorization": f"Basic {creds}", "Content-Type": "application/x-www-form-urlencoded"},
            )
            return resp.json()

    async def _refresh_access_token(self) -> None:
        creds = base64.b64encode(f"{settings.SCHWAB_APP_KEY}:{settings.SCHWAB_APP_SECRET}".encode()).decode()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self.TOKEN_URL,
                data={"grant_type": "refresh_token", "refresh_token": self.refresh_token},
                headers={"Authorization": f"Basic {creds}", "Content-Type": "application/x-www-form-urlencoded"},
            )
            data = resp.json()
            self.access_token = data.get("access_token", self.access_token)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.access_token}", "Accept": "application/json"}

    async def connect(self) -> bool:
        return bool(self.access_token)

    async def disconnect(self) -> None:
        pass

    async def get_balances(self) -> list[Balance]:
        url = f"{self.BASE_URL}/accounts"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=self._headers())
            if resp.status_code == 401:
                await self._refresh_access_token()
                resp = await client.get(url, headers=self._headers())
            data = resp.json()
        balances = []
        for acct in data if isinstance(data, list) else []:
            summary = acct.get("aggregatedBalance", {})
            balances.append(Balance(
                currency="USD",
                total=Decimal(str(summary.get("liquidationValue", 0))),
                available=Decimal(str(acct.get("securitiesAccount", {}).get("currentBalances", {}).get("availableFunds", 0))),
                reserved=Decimal("0"),
            ))
        return balances

    async def get_positions(self) -> list[Position]:
        url = f"{self.BASE_URL}/accounts?fields=positions"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=self._headers())
            data = resp.json()
        positions = []
        for acct in data if isinstance(data, list) else []:
            for pos in acct.get("securitiesAccount", {}).get("positions", []):
                inst = pos.get("instrument", {})
                positions.append(Position(
                    symbol=inst.get("symbol", ""),
                    quantity=Decimal(str(pos.get("longQuantity", 0))),
                    avg_cost=Decimal(str(pos.get("averagePrice", 0))),
                    current_price=Decimal(str(pos.get("marketValue", 0)) / float(pos.get("longQuantity", 1) or 1)),
                    unrealized_pnl=Decimal(str(pos.get("currentDayProfitLoss", 0))),
                ))
        return positions

    async def place_order(self, order: Order) -> dict[str, Any]:
        url = f"{self.BASE_URL}/accounts/{{account_number}}/orders"
        order_type_map = {"market": "MARKET", "limit": "LIMIT", "stop": "STOP", "stop_limit": "STOP_LIMIT"}
        payload = {
            "orderType": order_type_map.get(order.order_type, "MARKET"),
            "session": "NORMAL",
            "duration": order.time_in_force or "DAY",
            "orderStrategyType": "SINGLE",
            "orderLegCollection": [{
                "instruction": "BUY" if order.side == "buy" else "SELL",
                "quantity": float(order.quantity),
                "instrument": {"symbol": order.symbol, "assetType": "EQUITY"},
            }],
            **({"price": str(order.price)} if order.price else {}),
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload, headers=self._headers())
            return {"status": resp.status_code, "headers": dict(resp.headers), "body": resp.text}

    async def cancel_order(self, order_id: str, symbol: str | None = None) -> bool:
        return True

    async def get_order_status(self, order_id: str) -> dict[str, Any]:
        url = f"{self.BASE_URL}/orders/{order_id}"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=self._headers())
            return resp.json()

    async def get_open_orders(self) -> list[dict[str, Any]]:
        url = f"{self.BASE_URL}/orders?status=WORKING"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=self._headers())
            return resp.json() if isinstance(resp.json(), list) else []

    async def get_trade_history(self, symbol: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        url = f"{self.BASE_URL}/orders?status=FILLED&maxResults={limit}"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=self._headers())
            data = resp.json()
            if symbol and isinstance(data, list):
                return [o for o in data if any(l.get("instrument", {}).get("symbol") == symbol for l in o.get("orderLegCollection", []))]
            return data if isinstance(data, list) else []

    async def get_options_chain(self, symbol: str, expiry_date: str | None = None) -> dict[str, Any]:
        url = f"{self.BASE_URL}/chains?symbol={symbol}"
        if expiry_date:
            url += f"&fromDate={expiry_date}&toDate={expiry_date}"
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers=self._headers())
            return resp.json()
