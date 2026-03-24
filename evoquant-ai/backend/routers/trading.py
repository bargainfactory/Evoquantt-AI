from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from database import get_session
from models.trade import Trade, TradeCreate, TradeRead, OrderStatus
from models.user import User
from security.jwt_auth import get_current_user
from security.audit import AuditLogger
from brokers import BROKER_REGISTRY

router = APIRouter()


@router.post("/order", response_model=TradeRead, status_code=201)
async def place_order(
    order_in: TradeCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Place a paper or live order via the configured broker."""
    trade = Trade(
        **order_in.model_dump(),
        user_id=current_user.id,
        status=OrderStatus.PENDING,
    )
    session.add(trade)
    await session.flush()

    if not order_in.is_paper:
        broker_class = BROKER_REGISTRY.get(order_in.broker.lower())
        if not broker_class:
            raise HTTPException(status_code=400, detail=f"Unknown broker: {order_in.broker}")
        # In production, load credentials from vault
        # For demo, just simulate fill
        trade.status = OrderStatus.OPEN
        trade.broker_order_id = f"demo_{trade.id}"
        session.add(trade)
    else:
        # Paper trading: instant fill at current price
        trade.status = OrderStatus.FILLED
        trade.filled_quantity = order_in.quantity
        trade.filled_price = order_in.price
        session.add(trade)

    al = AuditLogger(session)
    await al.log("place_order", "trade", user_id=current_user.id, resource_id=str(trade.id),
                 details={"symbol": trade.symbol, "side": trade.side, "broker": trade.broker})
    return trade


@router.get("/orders", response_model=list[TradeRead])
async def get_orders(
    status: Optional[str] = None,
    symbol: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    query = select(Trade).where(Trade.user_id == current_user.id)
    if status:
        query = query.where(Trade.status == status)
    if symbol:
        query = query.where(Trade.symbol == symbol)
    query = query.order_by(Trade.created_at.desc()).limit(limit).offset(offset)
    result = await session.scalars(query)
    return result.all()


@router.get("/order/{order_id}", response_model=TradeRead)
async def get_order(
    order_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.scalars(select(Trade).where(Trade.id == order_id, Trade.user_id == current_user.id))
    trade = result.first()
    if not trade:
        raise HTTPException(status_code=404, detail="Order not found")
    return trade


@router.delete("/order/{order_id}/cancel")
async def cancel_order(
    order_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.scalars(select(Trade).where(Trade.id == order_id, Trade.user_id == current_user.id))
    trade = result.first()
    if not trade:
        raise HTTPException(status_code=404, detail="Order not found")
    if trade.status not in (OrderStatus.PENDING, OrderStatus.OPEN):
        raise HTTPException(status_code=400, detail="Order cannot be cancelled")
    trade.status = OrderStatus.CANCELLED
    session.add(trade)
    return {"message": "Order cancelled", "order_id": str(order_id)}


@router.get("/positions")
async def get_positions(
    broker: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    from models.portfolio import PortfolioPosition
    query = select(PortfolioPosition).where(PortfolioPosition.user_id == current_user.id)
    if broker:
        query = query.where(PortfolioPosition.broker == broker)
    result = await session.scalars(query)
    return result.all()
