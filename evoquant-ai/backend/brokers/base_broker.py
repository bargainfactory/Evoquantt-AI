"""Abstract base broker interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass
class Order:
    symbol: str
    side: str  # buy | sell
    order_type: str  # market | limit | stop | stop_limit
    quantity: Decimal
    price: Decimal | None = None
    stop_price: Decimal | None = None
    client_order_id: str | None = None
    time_in_force: str = "GTC"


@dataclass
class Position:
    symbol: str
    quantity: Decimal
    avg_cost: Decimal
    current_price: Decimal
    unrealized_pnl: Decimal
    side: str = "long"


@dataclass
class Balance:
    currency: str
    total: Decimal
    available: Decimal
    reserved: Decimal


class BaseBroker(ABC):
    name: str = "base"
    supports_options: bool = False
    supports_futures: bool = False
    supports_crypto: bool = False
    supports_forex: bool = False

    @abstractmethod
    async def connect(self) -> bool: ...

    @abstractmethod
    async def disconnect(self) -> None: ...

    @abstractmethod
    async def get_balances(self) -> list[Balance]: ...

    @abstractmethod
    async def get_positions(self) -> list[Position]: ...

    @abstractmethod
    async def place_order(self, order: Order) -> dict[str, Any]: ...

    @abstractmethod
    async def cancel_order(self, order_id: str, symbol: str | None = None) -> bool: ...

    @abstractmethod
    async def get_order_status(self, order_id: str) -> dict[str, Any]: ...

    @abstractmethod
    async def get_open_orders(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def get_trade_history(self, symbol: str | None = None, limit: int = 50) -> list[dict[str, Any]]: ...

    async def is_connected(self) -> bool:
        return False
