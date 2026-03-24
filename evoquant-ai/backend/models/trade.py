from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"
    MOC = "moc"
    LOC = "loc"


class OrderStatus(str, Enum):
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class AssetClass(str, Enum):
    STOCK = "stock"
    CRYPTO = "crypto"
    FOREX = "forex"
    FUTURES = "futures"
    OPTIONS = "options"
    ETF = "etf"
    DEX = "dex"


class TradeBase(SQLModel):
    symbol: str = Field(index=True)
    asset_class: AssetClass
    side: OrderSide
    order_type: OrderType
    quantity: Decimal = Field()
    price: Optional[Decimal] = Field(default=None)
    stop_price: Optional[Decimal] = Field(default=None)
    broker: str
    strategy_id: Optional[UUID] = Field(default=None)
    is_paper: bool = True
    notes: Optional[str] = None


class Trade(TradeBase, table=True):
    __tablename__ = "trades"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: Decimal = Field(default=Decimal("0"))
    filled_price: Optional[Decimal] = Field(default=None)
    commission: Decimal = Field(default=Decimal("0"))
    slippage: Decimal = Field(default=Decimal("0"))
    broker_order_id: Optional[str] = None
    pnl: Optional[Decimal] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    filled_at: Optional[datetime] = None


class TradeCreate(TradeBase):
    pass


class TradeRead(TradeBase):
    id: UUID
    user_id: UUID
    status: OrderStatus
    filled_quantity: Decimal
    filled_price: Optional[Decimal]
    commission: Decimal
    pnl: Optional[Decimal]
    created_at: datetime
    filled_at: Optional[datetime]
