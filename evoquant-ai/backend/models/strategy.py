from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class Strategy(SQLModel, table=True):
    __tablename__ = "strategies"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    name: str
    description: Optional[str] = None
    asset_class: str = "stock"
    symbols: str  # JSON list
    indicators: str  # JSON config
    entry_rules: str  # JSON
    exit_rules: str  # JSON
    risk_params: str  # JSON (Kelly, max_drawdown, etc.)
    recursive_sell_config: Optional[str] = None  # JSON
    is_active: bool = True
    is_paper: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class StrategyRun(SQLModel, table=True):
    __tablename__ = "strategy_runs"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    strategy_id: UUID = Field(foreign_key="strategies.id", index=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    run_type: str  # backtest | live | paper | optimization
    status: str = "running"  # running | completed | failed
    sharpe_ratio: Optional[Decimal] = Field(default=None)
    total_return: Optional[Decimal] = Field(default=None)
    max_drawdown: Optional[Decimal] = Field(default=None)
    win_rate: Optional[Decimal] = Field(default=None)
    total_trades: int = 0
    recursive_iterations: int = 0
    best_params: Optional[str] = None  # JSON
    result_json: Optional[str] = None
    error_message: Optional[str] = None
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


class StrategyCreate(SQLModel):
    name: str
    description: Optional[str] = None
    asset_class: str = "stock"
    symbols: list[str]
    indicators: dict
    entry_rules: dict
    exit_rules: dict
    risk_params: dict
    recursive_sell_config: Optional[dict] = None
    is_paper: bool = True


class StrategyRead(SQLModel):
    id: UUID
    user_id: UUID
    name: str
    description: Optional[str]
    asset_class: str
    is_active: bool
    is_paper: bool
    created_at: datetime
