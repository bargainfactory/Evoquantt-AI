from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

import httpx
import pandas as pd

from database import get_session
from security.jwt_auth import get_current_user
from models.user import User
from engines.ta_engine import TAEngine
from engines.ml_engine import MLEngine
from engines.sentiment_engine import SentimentEngine
from engines.macro_engine import MacroEngine
from config import settings

router = APIRouter()


async def _fetch_ohlcv_yfinance(symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
        if df.empty:
            raise ValueError("No data")
        df.columns = [c.lower() for c in df.columns]
        df = df.rename(columns={"stock splits": "splits", "dividends": "dividends"})
        return df[["open", "high", "low", "close", "volume"]]
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Could not fetch {symbol}: {e}")


@router.get("/quote/{symbol}")
async def get_quote(symbol: str, current_user: User = Depends(get_current_user)):
    """Real-time quote for any asset."""
    if settings.FINNHUB_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={settings.FINNHUB_API_KEY}"
                )
                data = resp.json()
                return {
                    "symbol": symbol,
                    "price": data.get("c", 0),
                    "change": data.get("d", 0),
                    "change_pct": data.get("dp", 0),
                    "high": data.get("h", 0),
                    "low": data.get("l", 0),
                    "open": data.get("o", 0),
                    "prev_close": data.get("pc", 0),
                    "source": "finnhub",
                }
        except Exception:
            pass
    # Fallback: yfinance
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info
        try:
            price = float(info.last_price or 0)
        except Exception:
            hist = ticker.history(period="1d")
            price = float(hist["Close"].iloc[-1]) if not hist.empty else 0
        return {
            "symbol": symbol,
            "price": price,
            "high": float(info.day_high or 0),
            "low": float(info.day_low or 0),
            "source": "yfinance",
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not fetch quote for {symbol}: {e}")


@router.get("/ohlcv/{symbol}")
async def get_ohlcv(
    symbol: str,
    period: str = Query("1y", description="Period: 1d,5d,1mo,3mo,6mo,1y,2y,5y"),
    interval: str = Query("1d", description="Interval: 1m,5m,15m,1h,4h,1d,1wk,1mo"),
    current_user: User = Depends(get_current_user),
):
    df = await _fetch_ohlcv_yfinance(symbol, period, interval)
    return {
        "symbol": symbol,
        "period": period,
        "interval": interval,
        "count": len(df),
        "timestamps": [str(t) for t in df.index.tolist()],
        "open": df["open"].tolist(),
        "high": df["high"].tolist(),
        "low": df["low"].tolist(),
        "close": df["close"].tolist(),
        "volume": df["volume"].tolist(),
    }


@router.get("/indicators/{symbol}")
async def get_indicators(
    symbol: str,
    period: str = Query("1y"),
    interval: str = Query("1d"),
    current_user: User = Depends(get_current_user),
):
    df = await _fetch_ohlcv_yfinance(symbol, period, interval)
    engine = TAEngine(df)
    indicators = engine.compute_all()
    signal = engine.get_ensemble_signal()
    latest = engine.get_latest()
    return {
        "symbol": symbol,
        "ensemble_signal": signal,
        "latest": latest,
        "history": {k: v[-50:] for k, v in indicators.items()},
    }


@router.get("/ml-predict/{symbol}")
async def ml_predict(
    symbol: str,
    period: str = Query("2y"),
    current_user: User = Depends(get_current_user),
):
    df = await _fetch_ohlcv_yfinance(symbol, period, "1d")
    ta_engine = TAEngine(df)
    ta_engine.compute_all()
    ta_latest = ta_engine.get_latest()
    df_with_ta = pd.concat([df, pd.DataFrame([ta_latest])], ignore_index=False)

    ml = MLEngine(symbol)
    # Add TA columns to df
    for key, series_list in ta_engine.to_dict().items():
        if len(series_list) == len(df):
            df[key] = series_list

    try:
        rf_metrics = ml.train_rf(df)
        prediction = ml.predict_ensemble(df)
        feature_importance = ml.get_feature_importance()
        return {
            "symbol": symbol,
            "prediction": prediction,
            "rf_metrics": rf_metrics,
            "feature_importance": feature_importance[:10],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ML prediction failed: {e}")


@router.get("/sentiment/{symbol}")
async def get_sentiment(symbol: str, current_user: User = Depends(get_current_user)):
    engine = SentimentEngine()
    return await engine.get_symbol_sentiment(symbol)


@router.get("/macro")
async def get_macro(current_user: User = Depends(get_current_user)):
    engine = MacroEngine()
    return await engine.get_full_macro_picture()


@router.get("/forex-carry")
async def get_forex_carry(current_user: User = Depends(get_current_user)):
    engine = MacroEngine()
    return await engine.get_forex_carry()


@router.get("/search")
async def search_symbols(
    q: str = Query(..., min_length=1),
    current_user: User = Depends(get_current_user),
):
    if not settings.FINNHUB_API_KEY:
        return {"result": []}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"https://finnhub.io/api/v1/search?q={q}&token={settings.FINNHUB_API_KEY}"
        )
        return resp.json()


@router.get("/news/{symbol}")
async def get_news(symbol: str, current_user: User = Depends(get_current_user)):
    engine = SentimentEngine()
    return await engine._get_finnhub_news(symbol)


@router.get("/earnings/{symbol}")
async def get_earnings(symbol: str, current_user: User = Depends(get_current_user)):
    import yfinance as yf
    ticker = yf.Ticker(symbol)
    try:
        earnings = ticker.earnings_dates
        if earnings is not None:
            return {"symbol": symbol, "earnings": earnings.head(8).to_dict()}
    except Exception:
        pass
    return {"symbol": symbol, "earnings": {}}
