from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class AlertType(str, Enum):
    PRICE = "price"
    INDICATOR = "indicator"
    PATTERN = "pattern"
    RECURSIVE_SELL = "recursive_sell"
    DEX_ROUTE = "dex_route"
    PORTFOLIO = "portfolio"
    RISK = "risk"
    NEWS = "news"
    CUSTOM = "custom"


class Alert(SQLModel, table=True):
    __tablename__ = "alerts"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    name: str
    alert_type: AlertType
    symbol: Optional[str] = Field(default=None, index=True)
    condition: str  # JSON condition object
    message: str
    channels: str = '["app"]'  # JSON list: app | email | sms | webhook
    webhook_url: Optional[str] = None
    is_active: bool = True
    triggered_count: int = 0
    last_triggered: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))


class AlertCreate(SQLModel):
    name: str
    alert_type: AlertType
    symbol: Optional[str] = None
    condition: dict
    message: str
    channels: list[str] = ["app"]
    webhook_url: Optional[str] = None


class AlertRead(SQLModel):
    id: UUID
    user_id: UUID
    name: str
    alert_type: AlertType
    symbol: Optional[str]
    message: str
    is_active: bool
    triggered_count: int
    last_triggered: Optional[datetime]
    created_at: datetime
