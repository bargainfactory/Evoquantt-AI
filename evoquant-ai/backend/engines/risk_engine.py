"""
Risk Engine: Kelly sizing, VaR, CVaR, portfolio risk metrics.
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats


class RiskEngine:
    """Portfolio and position risk management engine."""

    # ------------------------------------------------------------------
    # Kelly Criterion
    # ------------------------------------------------------------------
    @staticmethod
    def kelly_fraction(win_rate: float, avg_win: float, avg_loss: float) -> float:
        """Full Kelly fraction. Returns half-Kelly (0.5x) for safety."""
        if avg_loss == 0:
            return 0.0
        b = abs(avg_win / avg_loss)
        q = 1 - win_rate
        full_kelly = win_rate - (q / b)
        return max(0.0, min(full_kelly * 0.5, 0.25))  # cap at 25%

    @staticmethod
    def recursive_kelly_sizing(
        trades: list[float],
        equity: float,
        max_risk_per_trade: float = 0.02,
    ) -> dict[str, float]:
        if len(trades) < 10:
            return {"fraction": max_risk_per_trade, "position_size": equity * max_risk_per_trade}

        wins = [t for t in trades if t > 0]
        losses = [t for t in trades if t <= 0]
        win_rate = len(wins) / len(trades) if trades else 0
        avg_win = float(np.mean(wins)) if wins else 0
        avg_loss = abs(float(np.mean(losses))) if losses else 0.01

        k = RiskEngine.kelly_fraction(win_rate, avg_win, avg_loss)
        k = min(k, max_risk_per_trade)
        return {
            "fraction": k,
            "position_size": equity * k,
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
        }

    # ------------------------------------------------------------------
    # Value at Risk
    # ------------------------------------------------------------------
    @staticmethod
    def var(returns: pd.Series | list[float], confidence: float = 0.95) -> float:
        returns_arr = np.array(returns)
        return float(np.percentile(returns_arr, (1 - confidence) * 100))

    @staticmethod
    def cvar(returns: pd.Series | list[float], confidence: float = 0.95) -> float:
        returns_arr = np.array(returns)
        var = RiskEngine.var(returns_arr, confidence)
        return float(returns_arr[returns_arr <= var].mean())

    @staticmethod
    def parametric_var(
        returns: pd.Series | list[float], confidence: float = 0.95, horizon_days: int = 1
    ) -> float:
        returns_arr = np.array(returns)
        mu = np.mean(returns_arr)
        sigma = np.std(returns_arr)
        z = stats.norm.ppf(1 - confidence)
        return float((mu + z * sigma) * math.sqrt(horizon_days))

    # ------------------------------------------------------------------
    # Portfolio metrics
    # ------------------------------------------------------------------
    @staticmethod
    def sharpe_ratio(returns: pd.Series | list[float], risk_free: float = 0.05) -> float:
        returns_arr = np.array(returns)
        annual_return = np.mean(returns_arr) * 252
        annual_vol = np.std(returns_arr) * math.sqrt(252)
        if annual_vol == 0:
            return 0.0
        return float((annual_return - risk_free) / annual_vol)

    @staticmethod
    def sortino_ratio(returns: pd.Series | list[float], risk_free: float = 0.05) -> float:
        returns_arr = np.array(returns)
        annual_return = np.mean(returns_arr) * 252
        downside = returns_arr[returns_arr < 0]
        downside_vol = np.std(downside) * math.sqrt(252) if len(downside) > 0 else 0.001
        return float((annual_return - risk_free) / downside_vol)

    @staticmethod
    def max_drawdown(equity_curve: pd.Series | list[float]) -> float:
        eq = pd.Series(equity_curve)
        roll_max = eq.cummax()
        drawdown = (eq - roll_max) / roll_max
        return float(abs(drawdown.min()))

    @staticmethod
    def calmar_ratio(returns: pd.Series | list[float]) -> float:
        returns_arr = np.array(returns)
        annual_return = np.mean(returns_arr) * 252
        eq = np.cumprod(1 + returns_arr)
        mdd = RiskEngine.max_drawdown(eq)
        return float(annual_return / mdd) if mdd > 0 else 0.0

    # ------------------------------------------------------------------
    # Position sizing
    # ------------------------------------------------------------------
    @staticmethod
    def atr_position_size(
        equity: float, risk_pct: float, entry: float, atr: float, atr_multiplier: float = 2.0
    ) -> dict[str, float]:
        risk_amount = equity * risk_pct
        stop_distance = atr * atr_multiplier
        if stop_distance == 0:
            return {"shares": 0, "risk_amount": 0, "stop_price": entry}
        shares = risk_amount / stop_distance
        return {
            "shares": round(shares, 4),
            "risk_amount": risk_amount,
            "stop_price": entry - stop_distance,
            "position_value": shares * entry,
        }

    # ------------------------------------------------------------------
    # Correlation matrix
    # ------------------------------------------------------------------
    @staticmethod
    def correlation_matrix(price_dict: dict[str, pd.Series]) -> dict[str, Any]:
        df = pd.DataFrame(price_dict).pct_change().dropna()
        corr = df.corr()
        return {
            "symbols": list(corr.columns),
            "matrix": corr.values.tolist(),
        }

    # ------------------------------------------------------------------
    # Portfolio VaR (Monte Carlo)
    # ------------------------------------------------------------------
    @staticmethod
    def portfolio_mc_var(
        weights: list[float],
        mean_returns: list[float],
        cov_matrix: list[list[float]],
        portfolio_value: float,
        confidence: float = 0.95,
        horizon: int = 1,
        n_sims: int = 10000,
    ) -> dict[str, float]:
        w = np.array(weights)
        mu = np.array(mean_returns)
        cov = np.array(cov_matrix)

        rng = np.random.default_rng(42)
        sim_returns = rng.multivariate_normal(mu, cov, n_sims)
        port_returns = sim_returns @ w

        var_pct = float(np.percentile(port_returns, (1 - confidence) * 100) * math.sqrt(horizon))
        cvar_pct = float(port_returns[port_returns <= np.percentile(port_returns, (1 - confidence) * 100)].mean())

        return {
            "var_pct": var_pct,
            "cvar_pct": cvar_pct,
            "var_dollars": portfolio_value * abs(var_pct),
            "cvar_dollars": portfolio_value * abs(cvar_pct),
        }
