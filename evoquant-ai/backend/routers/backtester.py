from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from security.jwt_auth import get_current_user
from models.user import User
from engines.ta_engine import TAEngine
from engines.risk_engine import RiskEngine

import pandas as pd
import numpy as np

router = APIRouter()
_backtest_jobs: dict[str, dict] = {}


class BacktestConfig(BaseModel):
    symbol: str
    period: str = "2y"
    interval: str = "1d"
    initial_capital: float = 100000.0
    commission: float = 0.001
    slippage: float = 0.0005
    strategy: str = "ensemble_ta"  # ensemble_ta | sma_crossover | rsi_mean_revert
    params: dict = {}
    monte_carlo_sims: int = 1000
    broker: Optional[str] = None  # for broker-specific slippage


async def _run_backtest(job_id: str, config: BacktestConfig):
    try:
        _backtest_jobs[job_id] = {"status": "running"}
        import yfinance as yf
        ticker = yf.Ticker(config.symbol)
        df = ticker.history(period=config.period, interval=config.interval)
        df.columns = [c.lower() for c in df.columns]
        df = df[["open", "high", "low", "close", "volume"]]

        # Run TA engine
        engine = TAEngine(df)
        indicators = engine.compute_all()
        for key, vals in indicators.items():
            if len(vals) == len(df):
                df[key] = vals

        # Simple backtest
        results = _backtest_strategy(df, config)
        _backtest_jobs[job_id] = {"status": "completed", "result": results}
    except Exception as e:
        _backtest_jobs[job_id] = {"status": "failed", "error": str(e)}


def _backtest_strategy(df: pd.DataFrame, config: BacktestConfig) -> dict:
    c = df["close"]
    rsi = df.get("rsi_14", pd.Series(50, index=df.index))
    ema20 = df.get("ema_21", c.ewm(21).mean())
    ema50 = df.get("ema_50", c.ewm(50).mean())
    macd_hist = df.get("macd_hist", pd.Series(0, index=df.index))

    capital = config.initial_capital
    position = 0
    entry_price = 0.0
    trades = []
    equity_curve = [capital]

    for i in range(50, len(c)):
        price = float(c.iloc[i])
        r = float(rsi.iloc[i]) if not pd.isna(rsi.iloc[i]) else 50

        # Ensemble signal
        buy_sig = (r < 35 and ema20.iloc[i] > ema50.iloc[i] and macd_hist.iloc[i] > 0)
        sell_sig = (r > 65 or ema20.iloc[i] < ema50.iloc[i])

        if position == 0 and buy_sig:
            slippage_adj = price * (1 + config.slippage)
            position = (capital * 0.95) / slippage_adj
            entry_price = slippage_adj
            commission_cost = position * entry_price * config.commission
            capital -= commission_cost

        elif position > 0 and sell_sig:
            exit_price = price * (1 - config.slippage)
            gross = position * exit_price
            commission_cost = gross * config.commission
            pnl = gross - commission_cost - (position * entry_price)
            capital += position * entry_price + pnl
            trades.append({
                "entry": entry_price,
                "exit": exit_price,
                "pnl": pnl,
                "pnl_pct": pnl / (position * entry_price),
                "timestamp": str(df.index[i]),
            })
            position = 0

        if position > 0:
            equity = capital + position * price
        else:
            equity = capital
        equity_curve.append(equity)

    final_capital = capital + (position * float(c.iloc[-1]) if position > 0 else 0)
    returns = pd.Series(equity_curve).pct_change().dropna().tolist()

    # Monte Carlo
    mc_returns = []
    if config.monte_carlo_sims > 0 and returns:
        rng = np.random.default_rng(42)
        for _ in range(min(config.monte_carlo_sims, 1000)):
            sample = rng.choice(returns, size=len(returns), replace=True)
            mc_eq = np.cumprod(1 + np.array(sample)) * config.initial_capital
            mc_returns.append(float(mc_eq[-1]))

    win_trades = [t for t in trades if t["pnl"] > 0]
    return {
        "symbol": config.symbol,
        "initial_capital": config.initial_capital,
        "final_capital": round(final_capital, 2),
        "total_return": round((final_capital / config.initial_capital - 1) * 100, 2),
        "total_trades": len(trades),
        "win_rate": round(len(win_trades) / len(trades) * 100, 1) if trades else 0,
        "sharpe_ratio": round(RiskEngine.sharpe_ratio(returns), 3),
        "sortino_ratio": round(RiskEngine.sortino_ratio(returns), 3),
        "max_drawdown": round(RiskEngine.max_drawdown(equity_curve) * 100, 2),
        "calmar_ratio": round(RiskEngine.calmar_ratio(returns), 3),
        "var_95": round(RiskEngine.var(returns) * 100, 2),
        "trades": trades[-20:],
        "equity_curve": equity_curve[::max(1, len(equity_curve)//200)],
        "monte_carlo": {
            "median": round(float(np.median(mc_returns)), 2) if mc_returns else None,
            "p5": round(float(np.percentile(mc_returns, 5)), 2) if mc_returns else None,
            "p95": round(float(np.percentile(mc_returns, 95)), 2) if mc_returns else None,
        } if mc_returns else None,
    }


@router.post("/run")
async def run_backtest(
    config: BacktestConfig,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
):
    import uuid
    job_id = str(uuid.uuid4())
    background_tasks.add_task(_run_backtest, job_id, config)
    return {"job_id": job_id, "status": "started"}


@router.get("/job/{job_id}")
async def get_backtest_result(job_id: str, current_user: User = Depends(get_current_user)):
    job = _backtest_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
