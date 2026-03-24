from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class PortfolioPosition(SQLModel, table=True):
    __tablename__ = "portfolio_positions"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    symbol: str = Field(index=True)
    asset_class: str
    broker: str
    quantity: Decimal = Field()
    avg_cost: Decimal = Field()
    current_price: Optional[Decimal] = Field(default=None)
    unrealized_pnl: Optional[Decimal] = Field(default=None)
    realized_pnl: Decimal = Field(default=Decimal("0"))
    market_value: Optional[Decimal] = Field(default=None)
    weight: Optional[Decimal] = Field(default=None)
    is_paper: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Portfolio(SQLModel, table=True):
    __tablename__ = "portfolios"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", unique=True)
    total_value: Decimal = Field(default=Decimal("0"))
    cash_balance: Decimal = Field(default=Decimal("100000"))
    daily_pnl: Decimal = Field(default=Decimal("0"))
    total_pnl: Decimal = Field(default=Decimal("0"))
    sharpe_ratio: Optional[Decimal] = Field(default=None)
    max_drawdown: Optional[Decimal] = Field(default=None)
    win_rate: Optional[Decimal] = Field(default=None)
    is_paper: bool = True
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PortfolioSnapshot(SQLModel, table=True):
    __tablename__ = "portfolio_snapshots"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    total_value: Decimal = Field()
    cash_balance: Decimal = Field()
    positions_json: str  # JSON snapshot of positions
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
