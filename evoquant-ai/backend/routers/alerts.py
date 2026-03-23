import json
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from database import get_session
from models.alert import Alert, AlertCreate, AlertRead
from models.user import User
from security.jwt_auth import get_current_user

router = APIRouter()


@router.post("/", response_model=AlertRead, status_code=201)
async def create_alert(
    alert_in: AlertCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    alert = Alert(
        user_id=current_user.id,
        name=alert_in.name,
        alert_type=alert_in.alert_type,
        symbol=alert_in.symbol,
        condition=json.dumps(alert_in.condition),
        message=alert_in.message,
        channels=json.dumps(alert_in.channels),
        webhook_url=alert_in.webhook_url,
    )
    session.add(alert)
    await session.flush()
    return alert


@router.get("/", response_model=list[AlertRead])
async def list_alerts(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.exec(
        select(Alert).where(Alert.user_id == current_user.id).order_by(Alert.created_at.desc())
    )
    return result.all()


@router.delete("/{alert_id}")
async def delete_alert(
    alert_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.exec(select(Alert).where(Alert.id == alert_id, Alert.user_id == current_user.id))
    alert = result.first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    await session.delete(alert)
    return {"message": "Alert deleted"}


@router.patch("/{alert_id}/toggle")
async def toggle_alert(
    alert_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.exec(select(Alert).where(Alert.id == alert_id, Alert.user_id == current_user.id))
    alert = result.first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.is_active = not alert.is_active
    session.add(alert)
    return {"is_active": alert.is_active}
