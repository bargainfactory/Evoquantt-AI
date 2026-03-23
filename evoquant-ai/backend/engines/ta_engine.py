"""
Technical Analysis Engine - 50+ indicators + regime detector.
Uses pandas-ta (primary) with TA-Lib fallback.
"""
from __future__ import annotations

import warnings
from typing import Any

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

try:
    import pandas_ta as ta
    PANDAS_TA_AVAILABLE = True
except ImportError:
    PANDAS_TA_AVAILABLE = False

try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False


class TAEngine:
    """Compute 50+ technical indicators and market regime on OHLCV data."""

    def __init__(self, df: pd.DataFrame):
        required = {"open", "high", "low", "close", "volume"}
        if not required.issubset(set(df.columns)):
            raise ValueError(f"DataFrame must have columns: {required}")
        self.df = df.copy()
        self.df.columns = [c.lower() for c in self.df.columns]
        self._results: dict[str, pd.Series] = {}

    # ------------------------------------------------------------------
    # Core compute method
    # ------------------------------------------------------------------
    def compute_all(self) -> dict[str, Any]:
        self._compute_trend()
        self._compute_momentum()
        self._compute_volatility()
        self._compute_volume_indicators()
        self._compute_pattern_recognition()
        self._compute_support_resistance()
        self._detect_regime()
        return self.to_dict()

    # ------------------------------------------------------------------
    # Trend indicators
    # ------------------------------------------------------------------
    def _compute_trend(self) -> None:
        c = self.df["close"]
        h = self.df["high"]
        l = self.df["low"]

        # SMAs
        for p in [5, 10, 20, 50, 100, 200]:
            self._results[f"sma_{p}"] = c.rolling(p).mean()

        # EMAs
        for p in [5, 9, 12, 21, 26, 50, 200]:
            self._results[f"ema_{p}"] = c.ewm(span=p, adjust=False).mean()

        # MACD
        ema12 = c.ewm(span=12, adjust=False).mean()
        ema26 = c.ewm(span=26, adjust=False).mean()
        self._results["macd"] = ema12 - ema26
        self._results["macd_signal"] = self._results["macd"].ewm(span=9, adjust=False).mean()
        self._results["macd_hist"] = self._results["macd"] - self._results["macd_signal"]

        # ADX
        if PANDAS_TA_AVAILABLE:
            adx = ta.adx(h, l, c, length=14)
            if adx is not None and not adx.empty:
                for col in adx.columns:
                    self._results[col.lower()] = adx[col]
        else:
            self._results["adx_14"] = self._manual_adx(h, l, c, 14)

        # Ichimoku
        if PANDAS_TA_AVAILABLE:
            ich = ta.ichimoku(h, l, c)
            if ich is not None:
                df_ich, _ = ich
                for col in df_ich.columns:
                    self._results[f"ich_{col.lower()}"] = df_ich[col]

        # Supertrend
        if PANDAS_TA_AVAILABLE:
            st = ta.supertrend(h, l, c, length=7, multiplier=3.0)
            if st is not None:
                for col in st.columns:
                    self._results[col.lower()] = st[col]

        # VWAP (intraday approximation)
        typical = (h + l + c) / 3
        self._results["vwap"] = (typical * self.df["volume"]).cumsum() / self.df["volume"].cumsum()

        # Parabolic SAR
        if PANDAS_TA_AVAILABLE:
            psar = ta.psar(h, l, c)
            if psar is not None:
                for col in psar.columns:
                    self._results[col.lower()] = psar[col]

    # ------------------------------------------------------------------
    # Momentum indicators
    # ------------------------------------------------------------------
    def _compute_momentum(self) -> None:
        c = self.df["close"]
        h = self.df["high"]
        l = self.df["low"]

        # RSI
        for p in [7, 14, 21]:
            self._results[f"rsi_{p}"] = self._rsi(c, p)

        # Stochastic
        if PANDAS_TA_AVAILABLE:
            stoch = ta.stoch(h, l, c)
            if stoch is not None:
                for col in stoch.columns:
                    self._results[col.lower()] = stoch[col]

        # Williams %R
        if PANDAS_TA_AVAILABLE:
            wr = ta.willr(h, l, c, length=14)
            if wr is not None:
                self._results["willr_14"] = wr

        # CCI
        if PANDAS_TA_AVAILABLE:
            cci = ta.cci(h, l, c, length=14)
            if cci is not None:
                self._results["cci_14"] = cci

        # ROC
        for p in [5, 10, 20]:
            self._results[f"roc_{p}"] = c.pct_change(p) * 100

        # MFI
        if PANDAS_TA_AVAILABLE:
            mfi = ta.mfi(h, l, c, self.df["volume"], length=14)
            if mfi is not None:
                self._results["mfi_14"] = mfi

        # TSI
        if PANDAS_TA_AVAILABLE:
            tsi = ta.tsi(c)
            if tsi is not None:
                for col in tsi.columns:
                    self._results[col.lower()] = tsi[col]

        # Momentum
        for p in [10, 20]:
            self._results[f"mom_{p}"] = c - c.shift(p)

        # DPO
        if PANDAS_TA_AVAILABLE:
            dpo = ta.dpo(c)
            if dpo is not None:
                self._results["dpo"] = dpo

    # ------------------------------------------------------------------
    # Volatility indicators
    # ------------------------------------------------------------------
    def _compute_volatility(self) -> None:
        c = self.df["close"]
        h = self.df["high"]
        l = self.df["low"]

        # Bollinger Bands
        for p in [20]:
            for std in [2.0, 2.5]:
                mid = c.rolling(p).mean()
                sigma = c.rolling(p).std()
                self._results[f"bb_upper_{p}_{int(std)}"] = mid + std * sigma
                self._results[f"bb_mid_{p}"] = mid
                self._results[f"bb_lower_{p}_{int(std)}"] = mid - std * sigma
                self._results[f"bb_width_{p}"] = (2 * std * sigma) / mid

        # ATR
        for p in [7, 14, 21]:
            self._results[f"atr_{p}"] = self._atr(h, l, c, p)

        # Keltner Channels
        if PANDAS_TA_AVAILABLE:
            kc = ta.kc(h, l, c)
            if kc is not None:
                for col in kc.columns:
                    self._results[col.lower()] = kc[col]

        # Historical Volatility
        returns = np.log(c / c.shift(1))
        for p in [10, 20, 30]:
            self._results[f"hvol_{p}"] = returns.rolling(p).std() * np.sqrt(252) * 100

        # Ulcer Index
        if PANDAS_TA_AVAILABLE:
            ui = ta.ui(c)
            if ui is not None:
                self._results["ulcer_index"] = ui

    # ------------------------------------------------------------------
    # Volume indicators
    # ------------------------------------------------------------------
    def _compute_volume_indicators(self) -> None:
        c = self.df["close"]
        v = self.df["volume"]
        h = self.df["high"]
        l = self.df["low"]

        # OBV
        self._results["obv"] = (np.sign(c.diff()) * v).fillna(0).cumsum()

        # VROC
        self._results["vroc_14"] = v.pct_change(14) * 100

        # CMF
        if PANDAS_TA_AVAILABLE:
            cmf = ta.cmf(h, l, c, v)
            if cmf is not None:
                self._results["cmf"] = cmf

        # Force Index
        self._results["force_index"] = c.diff() * v

        # Volume SMA
        for p in [10, 20, 50]:
            self._results[f"vol_sma_{p}"] = v.rolling(p).mean()

        # Volume ratio
        self._results["vol_ratio_20"] = v / v.rolling(20).mean()

        # VWMA
        self._results["vwma_20"] = (c * v).rolling(20).sum() / v.rolling(20).sum()

    # ------------------------------------------------------------------
    # Pattern recognition
    # ------------------------------------------------------------------
    def _compute_pattern_recognition(self) -> None:
        if not TALIB_AVAILABLE:
            return
        o = self.df["open"].values
        h = self.df["high"].values
        l = self.df["low"].values
        c = self.df["close"].values

        patterns = {
            "cdl_doji": talib.CDLDOJI,
            "cdl_hammer": talib.CDLHAMMER,
            "cdl_engulfing": talib.CDLENGULFING,
            "cdl_morning_star": talib.CDLMORNINGSTAR,
            "cdl_evening_star": talib.CDLEVENINGSTAR,
            "cdl_harami": talib.CDLHARAMI,
            "cdl_shooting_star": talib.CDLSHOOTINGSTAR,
            "cdl_three_white": talib.CDL3WHITESOLDIERS,
            "cdl_three_black": talib.CDL3BLACKCROWS,
        }
        for name, fn in patterns.items():
            try:
                result = fn(o, h, l, c)
                self._results[name] = pd.Series(result, index=self.df.index)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Support / Resistance (pivot points)
    # ------------------------------------------------------------------
    def _compute_support_resistance(self) -> None:
        h = self.df["high"]
        l = self.df["low"]
        c = self.df["close"]

        pivot = (h + l + c) / 3
        self._results["pivot"] = pivot
        self._results["r1"] = 2 * pivot - l
        self._results["s1"] = 2 * pivot - h
        self._results["r2"] = pivot + (h - l)
        self._results["s2"] = pivot - (h - l)
        self._results["r3"] = h + 2 * (pivot - l)
        self._results["s3"] = l - 2 * (h - pivot)

    # ------------------------------------------------------------------
    # Market regime detection
    # ------------------------------------------------------------------
    def _detect_regime(self) -> None:
        c = self.df["close"]
        sma50 = c.rolling(50).mean()
        sma200 = c.rolling(200).mean()
        atr14 = self._results.get("atr_14", self._atr(self.df["high"], self.df["low"], c, 14))

        trend = np.where(sma50 > sma200, 1, np.where(sma50 < sma200, -1, 0))
        volatility_regime = np.where(atr14 > atr14.rolling(50).mean() * 1.5, "high_vol", "normal_vol")

        self._results["regime_trend"] = pd.Series(trend, index=self.df.index)
        self._results["regime_volatility"] = pd.Series(volatility_regime, index=self.df.index)
        self._results["regime_label"] = pd.Series(
            np.where(trend == 1, "bull", np.where(trend == -1, "bear", "sideways")),
            index=self.df.index,
        )

    # ------------------------------------------------------------------
    # Ensemble signal
    # ------------------------------------------------------------------
    def get_ensemble_signal(self) -> dict[str, Any]:
        """Combine multiple indicators into a composite buy/sell/neutral signal."""
        signals: list[int] = []

        rsi14 = self._results.get("rsi_14")
        macd = self._results.get("macd")
        macd_sig = self._results.get("macd_signal")
        regime = self._results.get("regime_trend")
        ema20 = self._results.get("ema_21")
        ema50 = self._results.get("ema_50")
        close = self.df["close"]

        if rsi14 is not None:
            last_rsi = rsi14.iloc[-1]
            if last_rsi < 30:
                signals.append(1)
            elif last_rsi > 70:
                signals.append(-1)
            else:
                signals.append(0)

        if macd is not None and macd_sig is not None:
            m, s = macd.iloc[-1], macd_sig.iloc[-1]
            if m > s:
                signals.append(1)
            elif m < s:
                signals.append(-1)
            else:
                signals.append(0)

        if ema20 is not None and ema50 is not None:
            if ema20.iloc[-1] > ema50.iloc[-1]:
                signals.append(1)
            else:
                signals.append(-1)

        if regime is not None:
            r = regime.iloc[-1]
            if r == 1:
                signals.append(1)
            elif r == -1:
                signals.append(-1)
            else:
                signals.append(0)

        score = sum(signals) / max(len(signals), 1)
        if score > 0.4:
            action = "BUY"
        elif score < -0.4:
            action = "SELL"
        else:
            action = "NEUTRAL"

        return {
            "action": action,
            "confidence": abs(score),
            "score": score,
            "signals": signals,
            "regime": self._results.get("regime_label", pd.Series(["unknown"])).iloc[-1],
            "rsi_14": float(rsi14.iloc[-1]) if rsi14 is not None else None,
            "macd_hist": float(self._results["macd_hist"].iloc[-1]) if "macd_hist" in self._results else None,
            "atr_14": float(self._results["atr_14"].iloc[-1]) if "atr_14" in self._results else None,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _rsi(self, series: pd.Series, period: int = 14) -> pd.Series:
        delta = series.diff()
        gain = delta.clip(lower=0).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()
        rs = gain / loss.replace(0, np.nan)
        return 100 - (100 / (1 + rs))

    def _atr(self, h: pd.Series, l: pd.Series, c: pd.Series, period: int = 14) -> pd.Series:
        tr = pd.concat([
            h - l,
            (h - c.shift(1)).abs(),
            (l - c.shift(1)).abs(),
        ], axis=1).max(axis=1)
        return tr.ewm(span=period, adjust=False).mean()

    def _manual_adx(self, h: pd.Series, l: pd.Series, c: pd.Series, period: int = 14) -> pd.Series:
        up = h.diff()
        down = -l.diff()
        plus_dm = up.where((up > down) & (up > 0), 0)
        minus_dm = down.where((down > up) & (down > 0), 0)
        atr = self._atr(h, l, c, period)
        plus_di = 100 * plus_dm.ewm(span=period, adjust=False).mean() / atr
        minus_di = 100 * minus_dm.ewm(span=period, adjust=False).mean() / atr
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
        return dx.ewm(span=period, adjust=False).mean()

    def to_dict(self) -> dict[str, list[float | str | None]]:
        out: dict[str, Any] = {}
        for key, series in self._results.items():
            if isinstance(series, pd.Series):
                out[key] = [None if (isinstance(v, float) and np.isnan(v)) else v for v in series.tolist()]
        return out

    def get_latest(self) -> dict[str, float | str | None]:
        out: dict[str, Any] = {}
        for key, series in self._results.items():
            if isinstance(series, pd.Series) and len(series) > 0:
                val = series.iloc[-1]
                out[key] = None if (isinstance(val, float) and np.isnan(val)) else val
        return out
