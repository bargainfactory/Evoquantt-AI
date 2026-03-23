from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from pydantic import EmailStr
from sqlmodel import Field, SQLModel


class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True)
    username: str = Field(unique=True, index=True, min_length=3, max_length=50)
    full_name: Optional[str] = None
    is_active: bool = True
    is_superuser: bool = False
    totp_enabled: bool = False
    preferred_broker: Optional[str] = None
    preferred_currency: str = "USD"
    risk_tolerance: str = "moderate"  # conservative | moderate | aggressive
    timezone: str = "UTC"


class User(UserBase, table=True):
    __tablename__ = "users"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    hashed_password: str
    totp_secret: Optional[str] = None
    totp_backup_codes: Optional[str] = None  # JSON-encoded list
    wallet_addresses: Optional[str] = None   # JSON-encoded dict
    broker_credentials: Optional[str] = None  # PQ-encrypted JSON
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    last_login: Optional[datetime] = None


class UserCreate(SQLModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    password: str


class UserRead(UserBase):
    id: UUID
    created_at: datetime
    last_login: Optional[datetime] = None


class UserUpdate(SQLModel):
    full_name: Optional[str] = None
    preferred_broker: Optional[str] = None
    preferred_currency: Optional[str] = None
    risk_tolerance: Optional[str] = None
    timezone: Optional[str] = None
