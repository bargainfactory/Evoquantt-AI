from datetime import datetime, timezone
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
    quantity: Decimal = Field(max_digits=20, decimal_places=8)
    avg_cost: Decimal = Field(max_digits=20, decimal_places=8)
    current_price: Optional[Decimal] = Field(default=None, max_digits=20, decimal_places=8)
    unrealized_pnl: Optional[Decimal] = Field(default=None, max_digits=20, decimal_places=8)
    realized_pnl: Decimal = Field(default=Decimal("0"), max_digits=20, decimal_places=8)
    market_value: Optional[Decimal] = Field(default=None, max_digits=20, decimal_places=8)
    weight: Optional[Decimal] = Field(default=None, max_digits=6, decimal_places=4)
    is_paper: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))


class Portfolio(SQLModel, table=True):
    __tablename__ = "portfolios"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", unique=True)
    total_value: Decimal = Field(default=Decimal("0"), max_digits=20, decimal_places=2)
    cash_balance: Decimal = Field(default=Decimal("100000"), max_digits=20, decimal_places=2)
    daily_pnl: Decimal = Field(default=Decimal("0"), max_digits=20, decimal_places=2)
    total_pnl: Decimal = Field(default=Decimal("0"), max_digits=20, decimal_places=2)
    sharpe_ratio: Optional[Decimal] = Field(default=None, max_digits=8, decimal_places=4)
    max_drawdown: Optional[Decimal] = Field(default=None, max_digits=8, decimal_places=4)
    win_rate: Optional[Decimal] = Field(default=None, max_digits=6, decimal_places=4)
    is_paper: bool = True
    updated_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))


class PortfolioSnapshot(SQLModel, table=True):
    __tablename__ = "portfolio_snapshots"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    total_value: Decimal = Field(max_digits=20, decimal_places=2)
    cash_balance: Decimal = Field(max_digits=20, decimal_places=2)
    positions_json: str  # JSON snapshot of positions
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc), index=True)
