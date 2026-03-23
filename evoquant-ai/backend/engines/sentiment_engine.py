"""
Sentiment Engine: News + social + on-chain fusion.
"""
from __future__ import annotations

import asyncio
import re
from typing import Any

import httpx

from config import settings


class SentimentEngine:
    FINNHUB_NEWS = "https://finnhub.io/api/v1/company-news"
    NEWSAPI_URL = "https://newsapi.org/v2/everything"

    async def get_symbol_sentiment(self, symbol: str) -> dict[str, Any]:
        tasks = [
            self._get_finnhub_news(symbol),
            self._get_newsapi_sentiment(symbol),
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        finnhub = results[0] if not isinstance(results[0], Exception) else {"articles": [], "score": 0.5}
        newsapi = results[1] if not isinstance(results[1], Exception) else {"articles": [], "score": 0.5}

        combined_score = (finnhub.get("score", 0.5) + newsapi.get("score", 0.5)) / 2
        label = "positive" if combined_score > 0.6 else "negative" if combined_score < 0.4 else "neutral"

        return {
            "symbol": symbol,
            "combined_score": round(combined_score, 3),
            "label": label,
            "sources": {
                "finnhub": finnhub,
                "newsapi": newsapi,
            },
            "article_count": len(finnhub.get("articles", [])) + len(newsapi.get("articles", [])),
        }

    async def _get_finnhub_news(self, symbol: str) -> dict[str, Any]:
        if not settings.FINNHUB_API_KEY:
            return {"articles": [], "score": 0.5, "error": "no API key"}
        from datetime import datetime, timedelta, timezone
        to_dt = datetime.now(tz=timezone.utc)
        from_dt = to_dt - timedelta(days=7)
        url = f"{self.FINNHUB_NEWS}?symbol={symbol}&from={from_dt.strftime('%Y-%m-%d')}&to={to_dt.strftime('%Y-%m-%d')}&token={settings.FINNHUB_API_KEY}"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            articles = resp.json() if resp.status_code == 200 else []

        scored = [self._simple_sentiment_score(a.get("headline", "")) for a in articles[:20]]
        avg = sum(scored) / len(scored) if scored else 0.5
        return {"articles": articles[:10], "score": avg, "count": len(articles)}

    async def _get_newsapi_sentiment(self, symbol: str) -> dict[str, Any]:
        if not settings.NEWS_API_KEY:
            return {"articles": [], "score": 0.5, "error": "no API key"}
        params = {"q": symbol, "language": "en", "sortBy": "publishedAt", "pageSize": 20, "apiKey": settings.NEWS_API_KEY}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(self.NEWSAPI_URL, params=params)
            data = resp.json() if resp.status_code == 200 else {}

        articles = data.get("articles", [])
        scored = [self._simple_sentiment_score(a.get("title", "") + " " + (a.get("description") or "")) for a in articles]
        avg = sum(scored) / len(scored) if scored else 0.5
        return {"articles": articles[:10], "score": avg, "count": len(articles)}

    def _simple_sentiment_score(self, text: str) -> float:
        """Lexicon-based sentiment scoring."""
        text = text.lower()
        positive_words = {
            "bullish", "surge", "rally", "gain", "profit", "record", "beat", "strong",
            "growth", "rise", "soar", "breakout", "upgrade", "buy", "outperform", "positive",
        }
        negative_words = {
            "bearish", "crash", "drop", "fall", "loss", "miss", "weak", "decline",
            "plunge", "downgrade", "sell", "underperform", "negative", "risk", "concern", "fear",
        }
        words = re.findall(r"\w+", text)
        pos = sum(1 for w in words if w in positive_words)
        neg = sum(1 for w in words if w in negative_words)
        total = pos + neg
        if total == 0:
            return 0.5
        return pos / total

    async def get_market_sentiment_overview(self) -> dict[str, Any]:
        """Aggregate fear/greed, VIX proxy, and trending topics."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get("https://api.alternative.me/fng/?limit=7")
                fg_data = resp.json().get("data", [])
        except Exception:
            fg_data = []

        trend = "up" if len(fg_data) > 1 and int(fg_data[0].get("value", 50)) > int(fg_data[-1].get("value", 50)) else "down"
        return {
            "fear_greed": fg_data[:3] if fg_data else [],
            "fg_trend": trend,
            "latest_value": int(fg_data[0].get("value", 50)) if fg_data else 50,
            "latest_label": fg_data[0].get("value_classification", "Neutral") if fg_data else "Neutral",
        }
