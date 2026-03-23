"""
Macro + On-Chain + Futures OI + Forex Carry environment fusion engine.
"""
from __future__ import annotations

import httpx
import asyncio
from typing import Any

from config import settings


class MacroEngine:
    """Aggregate macro, on-chain, OI, and carry data into a unified regime signal."""

    BASE_FRED = "https://api.stlouisfed.org/fred/series/observations"

    async def get_full_macro_picture(self) -> dict[str, Any]:
        tasks = [
            self._get_fred_series("DFF"),        # Fed Funds Rate
            self._get_fred_series("T10Y2Y"),      # Yield curve
            self._get_fred_series("VIXCLS"),      # VIX
            self._get_fred_series("DTWEXBGS"),    # USD Index
            self._get_coinglass_oi(),
            self._get_fear_greed(),
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        labels = ["fed_funds_rate", "yield_curve", "vix", "usd_index", "crypto_oi", "fear_greed"]
        out: dict[str, Any] = {}
        for label, result in zip(labels, results):
            if isinstance(result, Exception):
                out[label] = {"error": str(result)}
            else:
                out[label] = result

        out["macro_regime"] = self._classify_regime(out)
        return out

    async def _get_fred_series(self, series_id: str, limit: int = 5) -> dict[str, Any]:
        if not settings.FRED_API_KEY:
            return {"value": None, "source": "FRED (no key)"}
        url = f"{self.BASE_FRED}?series_id={series_id}&api_key={settings.FRED_API_KEY}&file_type=json&limit={limit}&sort_order=desc"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
        observations = data.get("observations", [])
        if observations:
            latest = observations[0]
            return {"value": float(latest["value"]) if latest["value"] != "." else None, "date": latest["date"]}
        return {"value": None}

    async def _get_coinglass_oi(self) -> dict[str, Any]:
        if not settings.COINGLASS_API_KEY:
            return {"btc_oi": None, "eth_oi": None}
        try:
            url = "https://open-api.coinglass.com/public/v2/open_interest"
            headers = {"coinglassSecret": settings.COINGLASS_API_KEY}
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url, headers=headers)
                data = resp.json()
            return {"data": data.get("data", [])[:5]}
        except Exception as e:
            return {"error": str(e)}

    async def _get_fear_greed(self) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get("https://api.alternative.me/fng/?limit=1")
                data = resp.json()
            fg = data.get("data", [{}])[0]
            return {"value": int(fg.get("value", 50)), "label": fg.get("value_classification", "Neutral")}
        except Exception:
            return {"value": 50, "label": "Neutral"}

    async def get_forex_carry(self, pairs: list[str] | None = None) -> dict[str, Any]:
        """Approximate carry trade opportunities from rate differentials."""
        rate_map = {
            "USD": 5.33, "EUR": 4.50, "GBP": 5.25, "JPY": 0.10,
            "AUD": 4.35, "NZD": 5.50, "CHF": 1.75, "CAD": 5.00,
        }
        if pairs is None:
            pairs = ["EUR/USD", "GBP/JPY", "AUD/JPY", "NZD/JPY"]
        carries = {}
        for pair in pairs:
            parts = pair.replace("/", "").replace("-", "")
            base_ccy = parts[:3].upper()
            quote_ccy = parts[3:].upper()
            base_rate = rate_map.get(base_ccy, 3.0)
            quote_rate = rate_map.get(quote_ccy, 3.0)
            carry = base_rate - quote_rate
            carries[pair] = {"carry_pct": carry, "long_base": carry > 0}
        return carries

    def _classify_regime(self, macro: dict[str, Any]) -> dict[str, str]:
        vix_data = macro.get("vix", {})
        vix = vix_data.get("value") if isinstance(vix_data, dict) else None
        yc_data = macro.get("yield_curve", {})
        yc = yc_data.get("value") if isinstance(yc_data, dict) else None
        fg_data = macro.get("fear_greed", {})
        fg = fg_data.get("value", 50) if isinstance(fg_data, dict) else 50

        risk_regime = "risk_on"
        if vix and vix > 25:
            risk_regime = "risk_off"
        elif vix and vix > 20:
            risk_regime = "elevated_risk"

        yield_regime = "normal"
        if yc is not None:
            if yc < 0:
                yield_regime = "inverted"
            elif yc < 0.5:
                yield_regime = "flattening"

        sentiment = "greed" if fg > 60 else "fear" if fg < 40 else "neutral"

        return {
            "risk": risk_regime,
            "yield_curve": yield_regime,
            "sentiment": sentiment,
            "overall": "bullish" if (risk_regime == "risk_on" and sentiment != "fear") else "bearish",
        }
