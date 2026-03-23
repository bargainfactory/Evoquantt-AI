"""
Evolution Lab Engine - nightly walk-forward + recursive optimization
across ALL assets, brokers, and DEX routes.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd

from engines.recursive_sell_engine import RecursiveSellEngine
from engines.ta_engine import TAEngine
from engines.ml_engine import MLEngine


class EvolutionEngine:
    """
    Nightly Evolution Engine:
      1. Walk-forward test across rolling windows
      2. Recursive sell optimization per asset
      3. Cross-asset portfolio optimization (Kelly sizing)
      4. Strategy fitness ranking + retirement
    """

    WALK_FORWARD_SPLITS = 5
    IN_SAMPLE_PCT = 0.7
    MIN_TRADES = 10

    def __init__(self, symbols: list[str], asset_class: str = "stock"):
        self.symbols = symbols
        self.asset_class = asset_class

    async def run_nightly_evolution(
        self, data_map: dict[str, pd.DataFrame], max_depth: int = 5
    ) -> dict[str, Any]:
        results: dict[str, Any] = {}
        portfolio_sharpes: dict[str, float] = {}

        for symbol in self.symbols:
            df = data_map.get(symbol)
            if df is None or len(df) < 200:
                continue

            wf_result = self._walk_forward_test(df, symbol)
            rse = RecursiveSellEngine(df, max_depth=max_depth, trials_per_depth=20, genetic_gens=10)
            rec_result = rse.run()

            ml = MLEngine(symbol)
            try:
                rf_metrics = ml.train_rf(df)
            except Exception:
                rf_metrics = {}

            results[symbol] = {
                "walk_forward": wf_result,
                "recursive_sell": rec_result.to_dict(),
                "ml_metrics": rf_metrics,
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            }
            portfolio_sharpes[symbol] = rec_result.best_sharpe

        # Kelly optimal allocation
        allocations = self._kelly_allocations(portfolio_sharpes)
        return {
            "symbols": results,
            "kelly_allocations": allocations,
            "evolved_at": datetime.now(tz=timezone.utc).isoformat(),
        }

    def _walk_forward_test(self, df: pd.DataFrame, symbol: str) -> dict[str, Any]:
        n = len(df)
        split_size = n // self.WALK_FORWARD_SPLITS
        out_of_sample_results: list[dict[str, float]] = []

        for i in range(self.WALK_FORWARD_SPLITS):
            start = i * split_size
            end = start + split_size
            in_end = start + int(split_size * self.IN_SAMPLE_PCT)

            in_sample = df.iloc[start:in_end]
            out_sample = df.iloc[in_end:end]

            if len(in_sample) < 50 or len(out_sample) < 20:
                continue

            # Optimize on in-sample
            rse = RecursiveSellEngine(in_sample, max_depth=2, trials_per_depth=15, genetic_gens=5)
            best = rse.run()

            # Evaluate on out-of-sample with best params
            oos_rse = RecursiveSellEngine(out_sample, max_depth=1, trials_per_depth=1)
            oos_metrics = oos_rse._evaluate(best.best_params)
            out_of_sample_results.append(oos_metrics)

        if not out_of_sample_results:
            return {}

        avg_sharpe = float(np.mean([r["sharpe"] for r in out_of_sample_results]))
        avg_return = float(np.mean([r["total_return"] for r in out_of_sample_results]))
        consistency = float(np.std([r["sharpe"] for r in out_of_sample_results]))

        return {
            "splits": len(out_of_sample_results),
            "avg_oos_sharpe": avg_sharpe,
            "avg_oos_return": avg_return,
            "sharpe_std": consistency,
            "robustness_score": max(0, avg_sharpe - consistency),
            "oos_results": out_of_sample_results,
        }

    def _kelly_allocations(self, sharpes: dict[str, float]) -> dict[str, float]:
        """Kelly criterion allocation based on Sharpe ratios."""
        if not sharpes:
            return {}
        positive_sharpes = {k: max(v, 0) for k, v in sharpes.items()}
        total = sum(positive_sharpes.values())
        if total == 0:
            n = len(sharpes)
            return {k: 1.0 / n for k in sharpes}
        raw = {k: v / total for k, v in positive_sharpes.items()}
        # Half-Kelly for risk management
        half_kelly = {k: v * 0.5 for k, v in raw.items()}
        return half_kelly

    def rank_strategies(self, strategy_runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Rank strategies by composite score: Sharpe * win_rate / max_drawdown."""
        for run in strategy_runs:
            sharpe = run.get("sharpe_ratio", 0) or 0
            win_rate = run.get("win_rate", 0) or 0
            drawdown = run.get("max_drawdown", 1) or 1
            run["fitness_score"] = (sharpe * win_rate) / max(drawdown, 0.01)
        return sorted(strategy_runs, key=lambda x: x["fitness_score"], reverse=True)
