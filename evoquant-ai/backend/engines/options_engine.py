"""
Options Engine: Black-Scholes + Monte Carlo + Greeks + Strategy optimizer.
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy.stats import norm

try:
    from py_vollib.black_scholes import black_scholes
    from py_vollib.black_scholes.greeks.analytical import delta, gamma, vega, theta, rho
    from py_vollib.black_scholes.implied_volatility import implied_volatility
    VOLLIB_AVAILABLE = True
except Exception:
    VOLLIB_AVAILABLE = False


class OptionsEngine:
    """
    Full options pricing and strategy engine.
    Supports: Black-Scholes, Monte Carlo, Greeks, IV surface, strategy P&L.
    """

    # ------------------------------------------------------------------
    # Black-Scholes pricing
    # ------------------------------------------------------------------
    @staticmethod
    def bs_price(
        S: float, K: float, T: float, r: float, sigma: float, option_type: str = "c"
    ) -> float:
        """
        Black-Scholes option price.
        S=spot, K=strike, T=time-to-expiry (years), r=risk-free, sigma=vol, option_type=c/p
        """
        if T <= 0 or sigma <= 0:
            intrinsic = max(S - K, 0) if option_type == "c" else max(K - S, 0)
            return intrinsic

        if VOLLIB_AVAILABLE:
            try:
                return float(black_scholes(option_type, S, K, T, r, sigma))
            except Exception:
                pass

        d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)

        if option_type == "c":
            return S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
        else:
            return K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)

    # ------------------------------------------------------------------
    # Greeks
    # ------------------------------------------------------------------
    @staticmethod
    def compute_greeks(
        S: float, K: float, T: float, r: float, sigma: float, option_type: str = "c"
    ) -> dict[str, float]:
        if T <= 0 or sigma <= 0:
            return {"delta": 0, "gamma": 0, "vega": 0, "theta": 0, "rho": 0, "iv": sigma}

        if VOLLIB_AVAILABLE:
            try:
                return {
                    "delta": float(delta(option_type, S, K, T, r, sigma)),
                    "gamma": float(gamma(option_type, S, K, T, r, sigma)),
                    "vega": float(vega(option_type, S, K, T, r, sigma)),
                    "theta": float(theta(option_type, S, K, T, r, sigma)),
                    "rho": float(rho(option_type, S, K, T, r, sigma)),
                    "iv": sigma,
                }
            except Exception:
                pass

        d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)
        pdf_d1 = norm.pdf(d1)

        _delta = norm.cdf(d1) if option_type == "c" else norm.cdf(d1) - 1
        _gamma = pdf_d1 / (S * sigma * math.sqrt(T))
        _vega = S * pdf_d1 * math.sqrt(T) / 100
        theta_call = (-S * pdf_d1 * sigma / (2 * math.sqrt(T)) - r * K * math.exp(-r * T) * norm.cdf(d2)) / 365
        theta_put = (-S * pdf_d1 * sigma / (2 * math.sqrt(T)) + r * K * math.exp(-r * T) * norm.cdf(-d2)) / 365
        _theta = theta_call if option_type == "c" else theta_put
        rho_call = K * T * math.exp(-r * T) * norm.cdf(d2) / 100
        rho_put = -K * T * math.exp(-r * T) * norm.cdf(-d2) / 100
        _rho = rho_call if option_type == "c" else rho_put

        return {"delta": _delta, "gamma": _gamma, "vega": _vega, "theta": _theta, "rho": _rho, "iv": sigma}

    # ------------------------------------------------------------------
    # Implied Volatility
    # ------------------------------------------------------------------
    @staticmethod
    def calc_iv(
        market_price: float, S: float, K: float, T: float, r: float, option_type: str = "c"
    ) -> float:
        if VOLLIB_AVAILABLE:
            try:
                return float(implied_volatility(market_price, S, K, T, r, option_type))
            except Exception:
                pass

        # Newton-Raphson fallback
        sigma = 0.2
        for _ in range(100):
            price = OptionsEngine.bs_price(S, K, T, r, sigma, option_type)
            vega_val = S * norm.pdf((math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))) * math.sqrt(T)
            if abs(vega_val) < 1e-10:
                break
            sigma -= (price - market_price) / vega_val
            if sigma <= 0:
                sigma = 0.001
        return max(sigma, 0.001)

    # ------------------------------------------------------------------
    # Monte Carlo simulation
    # ------------------------------------------------------------------
    @staticmethod
    def monte_carlo(
        S: float, K: float, T: float, r: float, sigma: float,
        option_type: str = "c", n_sims: int = 50000, steps: int = 252
    ) -> dict[str, float]:
        dt = T / steps
        drift = (r - 0.5 * sigma**2) * dt
        diffusion = sigma * math.sqrt(dt)

        rng = np.random.default_rng(42)
        Z = rng.standard_normal((n_sims, steps))
        log_returns = drift + diffusion * Z
        ST = S * np.exp(log_returns.sum(axis=1))

        if option_type == "c":
            payoffs = np.maximum(ST - K, 0)
        else:
            payoffs = np.maximum(K - ST, 0)

        discounted = payoffs * math.exp(-r * T)
        price = float(discounted.mean())
        std_err = float(discounted.std() / math.sqrt(n_sims))

        return {
            "price": price,
            "std_error": std_err,
            "ci_lower": price - 1.96 * std_err,
            "ci_upper": price + 1.96 * std_err,
            "prob_itm": float((payoffs > 0).mean()),
            "expected_payoff": float(payoffs.mean()),
            "var_95": float(np.percentile(payoffs, 5)),
            "cvar_95": float(payoffs[payoffs <= np.percentile(payoffs, 5)].mean()),
        }

    # ------------------------------------------------------------------
    # Strategy P&L
    # ------------------------------------------------------------------
    @staticmethod
    def strategy_pnl(
        legs: list[dict[str, Any]], price_range: list[float]
    ) -> dict[str, list[float]]:
        """
        legs: [{"option_type": "c/p", "strike": K, "iv": sigma, "T": T, "r": r,
                "side": "buy/sell", "qty": n, "premium": cost}]
        price_range: list of underlying prices to evaluate at
        """
        pnl_at_expiry = []
        pnl_now = []

        for S in price_range:
            total_expiry = 0.0
            total_now = 0.0
            for leg in legs:
                K = leg["strike"]
                otype = leg["option_type"]
                iv = leg["iv"]
                T = leg["T"]
                r = leg["r"]
                qty = leg["qty"]
                premium = leg["premium"]
                sign = 1 if leg["side"] == "buy" else -1

                exp_val = max(S - K, 0) if otype == "c" else max(K - S, 0)
                total_expiry += sign * qty * (exp_val - premium)

                now_val = OptionsEngine.bs_price(S, K, T, r, iv, otype)
                total_now += sign * qty * (now_val - premium)

            pnl_at_expiry.append(total_expiry)
            pnl_now.append(total_now)

        return {
            "price_range": price_range,
            "pnl_expiry": pnl_at_expiry,
            "pnl_now": pnl_now,
            "max_profit": max(pnl_at_expiry),
            "max_loss": min(pnl_at_expiry),
            "breakevens": OptionsEngine._find_breakevens(price_range, pnl_at_expiry),
        }

    @staticmethod
    def _find_breakevens(prices: list[float], pnl: list[float]) -> list[float]:
        breakevens = []
        for i in range(len(pnl) - 1):
            if (pnl[i] <= 0 <= pnl[i + 1]) or (pnl[i] >= 0 >= pnl[i + 1]):
                if pnl[i + 1] != pnl[i]:
                    be = prices[i] + (0 - pnl[i]) * (prices[i + 1] - prices[i]) / (pnl[i + 1] - pnl[i])
                    breakevens.append(round(be, 4))
        return breakevens

    # ------------------------------------------------------------------
    # IV Surface
    # ------------------------------------------------------------------
    @staticmethod
    def build_iv_surface(
        S: float, r: float,
        strikes: list[float], expiries: list[float],
        market_prices: list[list[float]], option_type: str = "c"
    ) -> dict[str, Any]:
        surface = []
        for i, T in enumerate(expiries):
            row = []
            for j, K in enumerate(strikes):
                try:
                    mp = market_prices[i][j]
                    iv = OptionsEngine.calc_iv(mp, S, K, T, r, option_type)
                    row.append(round(iv * 100, 2))
                except Exception:
                    row.append(None)
            surface.append(row)
        return {"strikes": strikes, "expiries": expiries, "iv_surface": surface}

    # ------------------------------------------------------------------
    # Optimal strategy selector
    # ------------------------------------------------------------------
    @staticmethod
    def suggest_strategy(
        S: float, K: float, T: float, r: float, iv: float, regime: str = "bull"
    ) -> list[dict[str, Any]]:
        strategies = []

        # Long Call (bullish)
        if regime in ("bull", "breakout"):
            call_price = OptionsEngine.bs_price(S, K, T, r, iv, "c")
            greeks = OptionsEngine.compute_greeks(S, K, T, r, iv, "c")
            strategies.append({
                "name": "Long Call",
                "legs": [{"type": "call", "strike": K, "side": "buy", "premium": call_price}],
                "max_profit": "unlimited",
                "max_loss": -call_price,
                "greeks": greeks,
                "score": 0.8,
                "rationale": "Strong uptrend detected. Long call captures upside with limited downside.",
            })

        # Protective Put (hedge)
        put_price = OptionsEngine.bs_price(S, S, T, r, iv, "p")
        strategies.append({
            "name": "Protective Put",
            "legs": [{"type": "stock", "side": "long"}, {"type": "put", "strike": S, "side": "buy", "premium": put_price}],
            "max_profit": "unlimited",
            "max_loss": -put_price,
            "score": 0.7,
            "rationale": "Downside protection with full upside participation.",
        })

        # Iron Condor (sideways)
        if regime == "sideways":
            strategies.append({
                "name": "Iron Condor",
                "legs": [
                    {"type": "call", "strike": K * 1.05, "side": "sell"},
                    {"type": "call", "strike": K * 1.10, "side": "buy"},
                    {"type": "put", "strike": K * 0.95, "side": "sell"},
                    {"type": "put", "strike": K * 0.90, "side": "buy"},
                ],
                "max_profit": "net premium",
                "max_loss": "spread width - premium",
                "score": 0.75,
                "rationale": "Range-bound market. Iron condor profits from theta decay.",
            })

        return sorted(strategies, key=lambda x: x["score"], reverse=True)
