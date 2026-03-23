from typing import Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from security.jwt_auth import get_current_user
from models.user import User
from engines.options_engine import OptionsEngine

router = APIRouter()


class BSRequest(BaseModel):
    S: float
    K: float
    T: float
    r: float = 0.05
    sigma: float
    option_type: str = "c"


class MCRequest(BSRequest):
    n_sims: int = 50000


class StrategyLeg(BaseModel):
    option_type: str
    strike: float
    iv: float
    T: float
    r: float = 0.05
    side: str
    qty: int = 1
    premium: float


@router.post("/price")
async def price_option(req: BSRequest, current_user: User = Depends(get_current_user)):
    price = OptionsEngine.bs_price(req.S, req.K, req.T, req.r, req.sigma, req.option_type)
    greeks = OptionsEngine.compute_greeks(req.S, req.K, req.T, req.r, req.sigma, req.option_type)
    return {"price": price, "greeks": greeks}


@router.post("/greeks")
async def compute_greeks(req: BSRequest, current_user: User = Depends(get_current_user)):
    return OptionsEngine.compute_greeks(req.S, req.K, req.T, req.r, req.sigma, req.option_type)


@router.post("/implied-volatility")
async def calc_iv(
    market_price: float,
    S: float,
    K: float,
    T: float,
    r: float = 0.05,
    option_type: str = "c",
    current_user: User = Depends(get_current_user),
):
    iv = OptionsEngine.calc_iv(market_price, S, K, T, r, option_type)
    return {"implied_volatility": iv, "iv_pct": iv * 100}


@router.post("/monte-carlo")
async def monte_carlo(req: MCRequest, current_user: User = Depends(get_current_user)):
    return OptionsEngine.monte_carlo(req.S, req.K, req.T, req.r, req.sigma, req.option_type, req.n_sims)


@router.post("/strategy-pnl")
async def strategy_pnl(
    legs: list[StrategyLeg],
    spot_min: float,
    spot_max: float,
    steps: int = 100,
    current_user: User = Depends(get_current_user),
):
    import numpy as np
    price_range = list(np.linspace(spot_min, spot_max, steps))
    legs_dict = [l.model_dump() for l in legs]
    return OptionsEngine.strategy_pnl(legs_dict, price_range)


@router.get("/suggest/{symbol}")
async def suggest_strategy(
    symbol: str,
    S: float = Query(...),
    T: float = Query(0.25),
    iv: float = Query(0.3),
    r: float = Query(0.05),
    regime: str = Query("bull"),
    current_user: User = Depends(get_current_user),
):
    return OptionsEngine.suggest_strategy(S, S, T, r, iv, regime)


@router.get("/chain/{symbol}")
async def get_options_chain(
    symbol: str,
    expiry: Optional[str] = None,
    broker: str = Query("tradier"),
    current_user: User = Depends(get_current_user),
):
    """Fetch real options chain from broker (Tradier or Schwab)."""
    from brokers.tradier_broker import TradierBroker
    from config import settings

    if broker == "tradier" and settings.TRADIER_ACCESS_TOKEN:
        tb = TradierBroker()
        exps = await tb.get_options_expirations(symbol)
        exp = expiry or (exps[0] if exps else None)
        if exp:
            chain = await tb.get_options_chain(symbol, exp)
            return chain
    # Fallback: generate synthetic chain from BS
    import numpy as np
    S = 100.0  # placeholder
    exps = [0.083, 0.25, 0.5, 1.0]
    strikes = list(np.arange(S * 0.8, S * 1.2, S * 0.025))
    calls, puts = [], []
    for K in strikes:
        for T in exps[:1]:
            cp = OptionsEngine.bs_price(S, K, T, 0.05, 0.25, "c")
            pp = OptionsEngine.bs_price(S, K, T, 0.05, 0.25, "p")
            cg = OptionsEngine.compute_greeks(S, K, T, 0.05, 0.25, "c")
            pg = OptionsEngine.compute_greeks(S, K, T, 0.05, 0.25, "p")
            calls.append({"strike": K, "price": cp, "iv": 25.0, **cg, "type": "call"})
            puts.append({"strike": K, "price": pp, "iv": 25.0, **pg, "type": "put"})
    return {"symbol": symbol, "underlying": S, "calls": calls, "puts": puts, "source": "synthetic"}


@router.get("/iv-surface/{symbol}")
async def get_iv_surface(
    symbol: str,
    current_user: User = Depends(get_current_user),
):
    import numpy as np
    S = 100.0
    strikes = list(np.arange(S * 0.8, S * 1.2, S * 0.05))
    expiries = [0.083, 0.25, 0.5, 0.75, 1.0]
    market_prices = []
    for T in expiries:
        row = []
        for K in strikes:
            # Smile effect: vol higher for OTM
            moneyness = abs(K / S - 1)
            smile_iv = 0.20 + 0.05 * moneyness
            price = OptionsEngine.bs_price(S, K, T, 0.05, smile_iv, "c")
            row.append(price)
        market_prices.append(row)
    return OptionsEngine.build_iv_surface(S, 0.05, strikes, expiries, market_prices, "c")
