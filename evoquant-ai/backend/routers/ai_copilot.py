from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Literal

from security.jwt_auth import get_current_user
from models.user import User
from config import settings

router = APIRouter()


class ConversationMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AskEvoRequest(BaseModel):
    message: str
    context: Optional[dict] = None
    symbol: Optional[str] = None
    history: list[ConversationMessage] = []


class AskEvoResponse(BaseModel):
    response: str
    suggestions: list[str] = []
    related_indicators: list[str] = []


SYSTEM_PROMPT = """You are Evo, the AI co-pilot of EvoQuant AI — the world's most advanced trading platform.
You are an expert in:
- Technical analysis (50+ indicators, regime detection)
- Options strategies (Black-Scholes, Monte Carlo, Greeks)
- Recursive sell optimization (Optuna Bayesian + DEAP genetic algorithms)
- Multi-broker trading (stocks, crypto, futures, forex)
- DEX routing (Uniswap V4, Jupiter)
- Quantum-proof security (Kyber-768, Dilithium-2)
- Portfolio risk management (Kelly criterion, VaR, CVaR)
- Evolution Lab (nightly walk-forward + recursive optimization)

Be concise, accurate, and actionable. When analyzing markets, cite specific indicators.
When discussing trades, always mention risk management and position sizing.
Never give guaranteed profit predictions. Always note risks."""


@router.post("/ask", response_model=AskEvoResponse)
async def ask_evo(
    req: AskEvoRequest,
    current_user: User = Depends(get_current_user),
):
    context_str = f"\nUser context: {req.context}" if req.context else ""
    symbol_str = f"\nAnalyzing symbol: {req.symbol}" if req.symbol else ""
    user_content = req.message + context_str + symbol_str

    # Build multi-turn messages from history
    history_messages = [{"role": m.role, "content": m.content} for m in req.history]

    # Try Anthropic Claude first, then OpenAI, then deterministic fallback
    if settings.ANTHROPIC_API_KEY:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            messages = [*history_messages, {"role": "user", "content": user_content}]
            message = client.messages.create(
                model="claude-opus-4-6",
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=messages,
            )
            return AskEvoResponse(
                response=message.content[0].text,
                suggestions=_extract_suggestions(message.content[0].text),
            )
        except Exception:
            pass

    if settings.OPENAI_API_KEY:
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                *history_messages,
                {"role": "user", "content": user_content},
            ]
            resp = await client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=1024,
            )
            return AskEvoResponse(
                response=resp.choices[0].message.content,
                suggestions=_extract_suggestions(resp.choices[0].message.content),
            )
        except Exception:
            pass

    # Deterministic fallback
    return _deterministic_response(req)


def _extract_suggestions(text: str) -> list[str]:
    """Extract actionable suggestions from AI response."""
    suggestions = []
    keywords = ["consider", "try", "suggest", "recommend", "look at", "use"]
    for line in text.split("\n"):
        if any(kw in line.lower() for kw in keywords) and len(line) < 200:
            suggestions.append(line.strip())
    return suggestions[:3]


def _deterministic_response(req: AskEvoRequest) -> AskEvoResponse:
    """Fallback when no AI API is configured."""
    msg = req.message.lower()
    responses = {
        "rsi": ("RSI measures momentum from 0-100. Oversold below 30, overbought above 70. "
                "EvoQuant uses RSI(14) as part of the ensemble signal. Consider combining with MACD and volume.",
                ["Check RSI divergence", "Combine with volume indicator", "Use RSI with Bollinger Bands"]),
        "macd": ("MACD = EMA(12) - EMA(26), Signal = EMA(9) of MACD. Bullish when histogram turns positive. "
                 "EvoQuant's ensemble weighs MACD crossovers alongside regime detection.",
                 ["Monitor histogram direction", "Look for signal line crossovers"]),
        "kelly": ("Kelly criterion determines optimal position size: f* = W - (1-W)/B. "
                  "EvoQuant uses half-Kelly (0.5x) for safety. Based on your win rate and payoff ratio.",
                  ["Run risk metrics to see your Kelly fraction", "Adjust for current volatility regime"]),
        "recursive": ("The Recursive Sell Engine uses Optuna Bayesian + DEAP genetic optimization. "
                      "Configure depth 1-10, more depth = better optimization but slower. "
                      "Visual debugger shows convergence tree in real-time.",
                      ["Try depth 3 for quick optimization", "Use depth 7-10 for overnight runs"]),
    }
    for key, (response, suggestions) in responses.items():
        if key in msg:
            return AskEvoResponse(response=response, suggestions=suggestions)

    return AskEvoResponse(
        response=(f"I'm Evo, your AI trading co-pilot. I can help you with technical analysis, "
                  f"options pricing, recursive sell optimization, DEX routing, and portfolio risk. "
                  f"Ask me about any indicator, strategy, or market concept!"),
        suggestions=["Analyze current regime", "Run recursive sell optimization", "Check portfolio risk metrics"],
        related_indicators=["RSI", "MACD", "Bollinger Bands", "ATR"],
    )


@router.get("/suggestions/{symbol}")
async def get_symbol_suggestions(
    symbol: str,
    current_user: User = Depends(get_current_user),
):
    """Get AI-powered trade suggestions for a symbol."""
    from engines.ta_engine import TAEngine
    from engines.sentiment_engine import SentimentEngine
    import yfinance as yf
    import pandas as pd

    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="6mo", interval="1d")
        df.columns = [c.lower() for c in df.columns]
        df = df[["open", "high", "low", "close", "volume"]]
        engine = TAEngine(df)
        engine.compute_all()
        signal = engine.get_ensemble_signal()
        latest = engine.get_latest()
        sentiment = await SentimentEngine().get_symbol_sentiment(symbol)

        return {
            "symbol": symbol,
            "ta_signal": signal,
            "sentiment": sentiment.get("label"),
            "key_levels": {
                "pivot": latest.get("pivot"),
                "r1": latest.get("r1"),
                "s1": latest.get("s1"),
                "bb_upper": latest.get("bb_upper_20_2"),
                "bb_lower": latest.get("bb_lower_20_2"),
            },
            "suggestion": (f"EvoQuant ensemble: {signal['action']} with {signal['confidence']:.0%} confidence. "
                           f"Regime: {signal.get('regime', 'unknown')}. "
                           f"Sentiment: {sentiment.get('label', 'neutral')}."),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
