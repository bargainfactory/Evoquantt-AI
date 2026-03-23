from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from database import get_session
from models.portfolio import Portfolio, PortfolioPosition, PortfolioSnapshot
from models.user import User
from security.jwt_auth import get_current_user
from engines.risk_engine import RiskEngine

import json
from decimal import Decimal

router = APIRouter()


@router.get("/summary")
async def get_portfolio_summary(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.exec(select(Portfolio).where(Portfolio.user_id == current_user.id))
    portfolio = result.first()
    if not portfolio:
        portfolio = Portfolio(user_id=current_user.id)
        session.add(portfolio)
        await session.flush()

    pos_result = await session.exec(
        select(PortfolioPosition).where(PortfolioPosition.user_id == current_user.id)
    )
    positions = pos_result.all()

    total_value = float(portfolio.cash_balance)
    for pos in positions:
        if pos.market_value:
            total_value += float(pos.market_value)

    return {
        "total_value": total_value,
        "cash_balance": float(portfolio.cash_balance),
        "daily_pnl": float(portfolio.daily_pnl),
        "total_pnl": float(portfolio.total_pnl),
        "sharpe_ratio": float(portfolio.sharpe_ratio) if portfolio.sharpe_ratio else None,
        "max_drawdown": float(portfolio.max_drawdown) if portfolio.max_drawdown else None,
        "win_rate": float(portfolio.win_rate) if portfolio.win_rate else None,
        "position_count": len(positions),
        "is_paper": portfolio.is_paper,
    }


@router.get("/positions")
async def get_positions(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.exec(
        select(PortfolioPosition).where(PortfolioPosition.user_id == current_user.id)
    )
    positions = result.all()
    return [
        {
            "id": str(p.id),
            "symbol": p.symbol,
            "asset_class": p.asset_class,
            "broker": p.broker,
            "quantity": float(p.quantity),
            "avg_cost": float(p.avg_cost),
            "current_price": float(p.current_price) if p.current_price else None,
            "unrealized_pnl": float(p.unrealized_pnl) if p.unrealized_pnl else None,
            "realized_pnl": float(p.realized_pnl),
            "market_value": float(p.market_value) if p.market_value else None,
            "weight": float(p.weight) if p.weight else None,
        }
        for p in positions
    ]


@router.get("/history")
async def get_portfolio_history(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    from datetime import datetime, timedelta, timezone
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
    result = await session.exec(
        select(PortfolioSnapshot)
        .where(PortfolioSnapshot.user_id == current_user.id)
        .where(PortfolioSnapshot.timestamp >= cutoff)
        .order_by(PortfolioSnapshot.timestamp)
    )
    snapshots = result.all()
    return [
        {
            "timestamp": s.timestamp.isoformat(),
            "total_value": float(s.total_value),
            "cash_balance": float(s.cash_balance),
        }
        for s in snapshots
    ]


@router.get("/risk-metrics")
async def get_risk_metrics(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.exec(
        select(PortfolioSnapshot)
        .where(PortfolioSnapshot.user_id == current_user.id)
        .order_by(PortfolioSnapshot.timestamp)
    )
    snapshots = result.all()

    if len(snapshots) < 10:
        return {"message": "Insufficient history for risk metrics"}

    values = [float(s.total_value) for s in snapshots]
    import pandas as pd
    import numpy as np
    series = pd.Series(values)
    returns = series.pct_change().dropna().tolist()

    return {
        "sharpe_ratio": RiskEngine.sharpe_ratio(returns),
        "sortino_ratio": RiskEngine.sortino_ratio(returns),
        "max_drawdown": RiskEngine.max_drawdown(values),
        "calmar_ratio": RiskEngine.calmar_ratio(returns),
        "var_95": RiskEngine.var(returns, 0.95),
        "cvar_95": RiskEngine.cvar(returns, 0.95),
        "return_30d": (values[-1] / values[-min(30, len(values))] - 1) if len(values) > 1 else 0,
    }


@router.get("/allocation")
async def get_allocation(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.exec(
        select(PortfolioPosition).where(PortfolioPosition.user_id == current_user.id)
    )
    positions = result.all()
    total = sum(float(p.market_value or 0) for p in positions)
    if total == 0:
        return {"allocations": []}
    return {
        "allocations": [
            {
                "symbol": p.symbol,
                "asset_class": p.asset_class,
                "weight": float(p.market_value or 0) / total,
                "value": float(p.market_value or 0),
            }
            for p in positions
        ]
    }
