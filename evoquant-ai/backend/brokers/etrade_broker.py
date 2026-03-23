"""
E*TRADE OAuth2 broker adapter.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

import httpx
from brokers.base_broker import BaseBroker, Balance, Order, Position
from config import settings


class ETradeBroker(BaseBroker):
    name = "etrade"
    supports_options = True

    BASE_URL_LIVE = "https://api.etrade.com/v1"
    BASE_URL_SANDBOX = "https://apisb.etrade.com/v1"

    def __init__(self, access_token: str = "", access_token_secret: str = ""):
        self.access_token = access_token
        self.access_token_secret = access_token_secret
        self.base_url = self.BASE_URL_SANDBOX if settings.ETRADE_SANDBOX else self.BASE_URL_LIVE

    @classmethod
    def get_oauth_url(cls) -> dict[str, str]:
        """Step 1: Get request token and OAuth URL."""
        from requests_oauthlib import OAuth1Session
        sandbox = settings.ETRADE_SANDBOX
        request_url = "https://apisb.etrade.com/oauth/request_token" if sandbox else "https://api.etrade.com/oauth/request_token"
        authorize_url = "https://us.etrade.com/e/t/etws/authorize"
        oauth = OAuth1Session(settings.ETRADE_CONSUMER_KEY, client_secret=settings.ETRADE_CONSUMER_SECRET, callback_uri=settings.ETRADE_CALLBACK_URL)
        fetch_response = oauth.fetch_request_token(request_url)
        oauth_token = fetch_response.get("oauth_token")
        return {
            "oauth_token": oauth_token,
            "authorize_url": f"{authorize_url}?key={settings.ETRADE_CONSUMER_KEY}&token={oauth_token}",
        }

    @classmethod
    def exchange_token(cls, oauth_token: str, oauth_verifier: str) -> dict[str, str]:
        """Step 3: Exchange verifier for access token."""
        from requests_oauthlib import OAuth1Session
        sandbox = settings.ETRADE_SANDBOX
        access_url = "https://apisb.etrade.com/oauth/access_token" if sandbox else "https://api.etrade.com/oauth/access_token"
        oauth = OAuth1Session(
            settings.ETRADE_CONSUMER_KEY, client_secret=settings.ETRADE_CONSUMER_SECRET,
            resource_owner_key=oauth_token, verifier=oauth_verifier,
        )
        tokens = oauth.fetch_access_token(access_url)
        return {"access_token": tokens["oauth_token"], "access_token_secret": tokens["oauth_token_secret"]}

    def _auth_headers(self) -> dict[str, str]:
        from requests_oauthlib import OAuth1
        from requests import Request
        auth = OAuth1(settings.ETRADE_CONSUMER_KEY, settings.ETRADE_CONSUMER_SECRET,
                      self.access_token, self.access_token_secret)
        return {"Authorization": str(auth)}

    async def connect(self) -> bool:
        return bool(self.access_token)

    async def disconnect(self) -> None:
        pass

    async def get_balances(self) -> list[Balance]:
        url = f"{self.base_url}/accounts/list.json"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=self._auth_headers())
            data = resp.json()
        accounts = data.get("AccountListResponse", {}).get("Accounts", {}).get("Account", [])
        balances = []
        for acct in accounts:
            balances.append(Balance(
                currency="USD",
                total=Decimal(str(acct.get("accountBalance", {}).get("netCash", 0))),
                available=Decimal(str(acct.get("accountBalance", {}).get("cashAvailableForInvestment", 0))),
                reserved=Decimal("0"),
            ))
        return balances

    async def get_positions(self) -> list[Position]:
        url = f"{self.base_url}/accounts/list.json"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=self._auth_headers())
            data = resp.json()
        accounts = data.get("AccountListResponse", {}).get("Accounts", {}).get("Account", [])
        positions = []
        for acct in accounts:
            acct_key = acct.get("accountIdKey", "")
            pos_url = f"{self.base_url}/accounts/{acct_key}/portfolio.json"
            pos_resp = await client.get(pos_url, headers=self._auth_headers())
            pos_data = pos_resp.json()
            for p in pos_data.get("PortfolioResponse", {}).get("AccountPortfolio", [{}])[0].get("Position", []):
                prod = p.get("Product", {})
                qty = Decimal(str(p.get("quantity", 0)))
                avg = Decimal(str(p.get("costPerShare", 0)))
                curr = Decimal(str(p.get("marketValue", 0)) ) / (qty if qty != 0 else Decimal("1"))
                positions.append(Position(
                    symbol=prod.get("symbol", ""),
                    quantity=qty,
                    avg_cost=avg,
                    current_price=curr,
                    unrealized_pnl=Decimal(str(p.get("totalGain", 0))),
                ))
        return positions

    async def place_order(self, order: Order) -> dict[str, Any]:
        url = f"{self.base_url}/accounts/{{account_id}}/orders/place.json"
        order_type_map = {"market": "MARKET", "limit": "LIMIT", "stop": "STOP", "stop_limit": "STOP_LIMIT"}
        payload = {
            "PlaceOrderRequest": {
                "orderType": order_type_map.get(order.order_type, "MARKET"),
                "clientOrderId": order.client_order_id or f"evq_{int(__import__('time').time())}",
                "Instrument": [{
                    "Product": {"symbol": order.symbol, "securityType": "EQ"},
                    "orderAction": "BUY" if order.side == "buy" else "SELL",
                    "quantityType": "QUANTITY",
                    "quantity": str(order.quantity),
                    **({"limitPrice": str(order.price)} if order.price else {}),
                }],
            }
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload, headers=self._auth_headers())
            return resp.json()

    async def cancel_order(self, order_id: str, symbol: str | None = None) -> bool:
        return True

    async def get_order_status(self, order_id: str) -> dict[str, Any]:
        return {"order_id": order_id, "status": "unknown"}

    async def get_open_orders(self) -> list[dict[str, Any]]:
        return []

    async def get_trade_history(self, symbol: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        return []
