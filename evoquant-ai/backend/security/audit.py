import json
from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Field, SQLModel, select

logger = structlog.get_logger()


class AuditLogEntry(SQLModel, table=True):
    __tablename__ = "audit_logs"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: Optional[UUID] = Field(default=None, index=True)
    action: str = Field(index=True)
    resource: str
    resource_id: Optional[str] = None
    details: Optional[str] = None  # JSON string
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    status: str = "success"  # success | failure
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AuditLogger:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def log(
        self,
        action: str,
        resource: str,
        user_id: Optional[UUID] = None,
        resource_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        status: str = "success",
    ) -> None:
        entry = AuditLogEntry(
            user_id=user_id,
            action=action,
            resource=resource,
            resource_id=resource_id,
            details=json.dumps(details) if details else None,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
        )
        self.session.add(entry)
        await self.session.flush()
        logger.info(
            "audit",
            action=action,
            resource=resource,
            user_id=str(user_id) if user_id else None,
            status=status,
        )

    async def get_logs(
        self,
        user_id: Optional[UUID] = None,
        action: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLogEntry]:
        query = select(AuditLogEntry).order_by(AuditLogEntry.created_at.desc())
        if user_id:
            query = query.where(AuditLogEntry.user_id == user_id)
        if action:
            query = query.where(AuditLogEntry.action == action)
        query = query.limit(limit).offset(offset)
        result = await self.session.scalars(query)
        return result.all()


def audit_log(action: str, resource: str):
    """Decorator for automatic audit logging on route handlers."""
    import functools
    from fastapi import Request

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            request: Optional[Request] = kwargs.get("request")
            session: Optional[AsyncSession] = kwargs.get("session")
            current_user = kwargs.get("current_user")
            try:
                result = await func(*args, **kwargs)
                if session and request:
                    al = AuditLogger(session)
                    await al.log(
                        action=action,
                        resource=resource,
                        user_id=current_user.id if current_user else None,
                        ip_address=request.client.host if request.client else None,
                        user_agent=request.headers.get("user-agent"),
                        status="success",
                    )
                return result
            except Exception as e:
                if session and request:
                    al = AuditLogger(session)
                    await al.log(
                        action=action,
                        resource=resource,
                        user_id=current_user.id if current_user else None,
                        ip_address=request.client.host if request.client else None,
                        status="failure",
                        details={"error": str(e)},
                    )
                raise
        return wrapper
    return decorator
