"""
Recursive Sell Improvement Engine.
Uses Optuna (Bayesian) + DEAP (Genetic) for configurable-depth recursive optimization.
Produces full debugger trace for the visual Recursion Debugger UI.
"""
from __future__ import annotations

import json
import math
import time
import warnings
from copy import deepcopy
from dataclasses import dataclass, field, asdict
from typing import Any, Callable

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

try:
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    OPTUNA_AVAILABLE = True
except ImportError:
    OPTUNA_AVAILABLE = False

try:
    from deap import base, creator, tools, algorithms
    import random
    DEAP_AVAILABLE = True
except ImportError:
    DEAP_AVAILABLE = False


@dataclass
class RecursionNode:
    """Single node in the recursion tree (for visual debugger)."""
    depth: int
    iteration: int
    params: dict[str, Any]
    sharpe: float
    profit_uplift: float
    win_rate: float
    max_drawdown: float
    total_return: float
    is_best: bool = False
    children: list["RecursionNode"] = field(default_factory=list)
    optimizer: str = "optuna"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["children"] = [c.to_dict() for c in self.children]
        return d


@dataclass
class RecursionResult:
    """Full result of a recursive sell optimization run."""
    best_params: dict[str, Any]
    best_sharpe: float
    best_return: float
    best_win_rate: float
    best_drawdown: float
    iterations_total: int
    depth_reached: int
    convergence_history: list[dict[str, float]]  # per-iteration metrics
    tree: RecursionNode | None  # full tree for Plotly visualizer
    elapsed_seconds: float

    def to_dict(self) -> dict[str, Any]:
        d = {
            "best_params": self.best_params,
            "best_sharpe": self.best_sharpe,
            "best_return": self.best_return,
            "best_win_rate": self.best_win_rate,
            "best_drawdown": self.best_drawdown,
            "iterations_total": self.iterations_total,
            "depth_reached": self.depth_reached,
            "convergence_history": self.convergence_history,
            "elapsed_seconds": self.elapsed_seconds,
        }
        if self.tree:
            d["tree"] = self.tree.to_dict()
        return d


class RecursiveSellEngine:
    """
    Recursive Sell Improvement Engine.
    At each depth level:
      1. Run Optuna (Bayesian) optimization for n_trials
      2. Run DEAP genetic optimization on the best Optuna population
      3. Re-seed next level with winners
      4. Track full tree + convergence for debugger UI
    """

    PARAM_SPACE = {
        "rsi_oversold": (20, 45),
        "rsi_overbought": (55, 85),
        "atr_multiplier": (1.0, 4.0),
        "take_profit_pct": (0.02, 0.25),
        "stop_loss_pct": (0.005, 0.15),
        "trailing_stop_pct": (0.005, 0.10),
        "min_holding_bars": (1, 20),
        "max_holding_bars": (5, 120),
        "volume_threshold": (0.5, 3.0),
        "macd_threshold": (0.0, 0.05),
    }

    def __init__(
        self,
        df: pd.DataFrame,
        max_depth: int = 5,
        trials_per_depth: int = 30,
        genetic_pop: int = 50,
        genetic_gens: int = 20,
        objective: str = "sharpe",  # sharpe | profit | win_rate
        seed: int = 42,
    ):
        self.df = df.copy()
        self.max_depth = max(1, min(max_depth, 10))
        self.trials_per_depth = trials_per_depth
        self.genetic_pop = genetic_pop
        self.genetic_gens = genetic_gens
        self.objective = objective
        self.seed = seed
        self._iteration_counter = 0
        self._convergence: list[dict[str, float]] = []

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------
    def run(self, progress_callback: Callable[[dict], None] | None = None) -> RecursionResult:
        t0 = time.time()
        np.random.seed(self.seed)

        # Initial params (center of search space)
        initial_params = {k: (v[0] + v[1]) / 2 for k, v in self.PARAM_SPACE.items()}
        initial_metrics = self._evaluate(initial_params)
        best_params = initial_params.copy()
        best_sharpe = initial_metrics["sharpe"]

        root = RecursionNode(
            depth=0,
            iteration=0,
            params=initial_params,
            sharpe=initial_metrics["sharpe"],
            profit_uplift=0.0,
            win_rate=initial_metrics["win_rate"],
            max_drawdown=initial_metrics["max_drawdown"],
            total_return=initial_metrics["total_return"],
            is_best=True,
            optimizer="init",
        )

        current_node = root
        current_params = initial_params.copy()

        for depth in range(1, self.max_depth + 1):
            # --- Optuna Bayesian phase ---
            optuna_best, optuna_node = self._run_optuna_phase(
                depth, current_params, current_node, best_sharpe, progress_callback
            )
            if optuna_best["sharpe"] > best_sharpe:
                best_sharpe = optuna_best["sharpe"]
                best_params = optuna_best["params"].copy()
                optuna_node.is_best = True

            # --- DEAP Genetic phase ---
            if DEAP_AVAILABLE:
                genetic_best, genetic_node = self._run_genetic_phase(
                    depth, optuna_best["params"], current_node, best_sharpe, progress_callback
                )
                if genetic_best["sharpe"] > best_sharpe:
                    best_sharpe = genetic_best["sharpe"]
                    best_params = genetic_best["params"].copy()
                    genetic_node.is_best = True
                current_params = genetic_best["params"].copy()
            else:
                current_params = optuna_best["params"].copy()

            self._convergence.append({
                "depth": depth,
                "sharpe": best_sharpe,
                "total_return": self._evaluate(best_params)["total_return"],
                "iteration": self._iteration_counter,
            })

            if progress_callback:
                progress_callback({"depth": depth, "max_depth": self.max_depth, "best_sharpe": best_sharpe})

            # Check convergence
            if depth > 2 and len(self._convergence) > 2:
                improvement = abs(self._convergence[-1]["sharpe"] - self._convergence[-2]["sharpe"])
                if improvement < 0.001:
                    break

        final_metrics = self._evaluate(best_params)
        return RecursionResult(
            best_params=best_params,
            best_sharpe=float(best_sharpe),
            best_return=float(final_metrics["total_return"]),
            best_win_rate=float(final_metrics["win_rate"]),
            best_drawdown=float(final_metrics["max_drawdown"]),
            iterations_total=self._iteration_counter,
            depth_reached=depth,
            convergence_history=self._convergence,
            tree=root,
            elapsed_seconds=time.time() - t0,
        )

    # ------------------------------------------------------------------
    # Optuna phase
    # ------------------------------------------------------------------
    def _run_optuna_phase(
        self, depth: int, seed_params: dict, parent_node: RecursionNode,
        baseline_sharpe: float, progress_callback
    ) -> tuple[dict, RecursionNode]:
        if not OPTUNA_AVAILABLE:
            metrics = self._evaluate(seed_params)
            node = RecursionNode(depth=depth, iteration=self._iteration_counter, params=seed_params,
                                sharpe=metrics["sharpe"], profit_uplift=metrics["sharpe"] - baseline_sharpe,
                                win_rate=metrics["win_rate"], max_drawdown=metrics["max_drawdown"],
                                total_return=metrics["total_return"], optimizer="fallback")
            parent_node.children.append(node)
            return {"params": seed_params, "sharpe": metrics["sharpe"]}, node

        study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=self.seed + depth))
        best_trial_metrics: dict[str, Any] = {}

        def objective(trial: optuna.Trial) -> float:
            params = {}
            for k, (lo, hi) in self.PARAM_SPACE.items():
                if k in ("min_holding_bars", "max_holding_bars"):
                    params[k] = trial.suggest_int(k, int(lo), int(hi))
                else:
                    # Narrow search around seed + depth-adjusted range
                    center = seed_params.get(k, (lo + hi) / 2)
                    width = (hi - lo) * max(0.1, 1.0 / depth)
                    lo_adj = max(lo, center - width / 2)
                    hi_adj = min(hi, center + width / 2)
                    params[k] = trial.suggest_float(k, lo_adj, hi_adj)
            metrics = self._evaluate(params)
            best_trial_metrics.update({"params": params, **metrics})
            self._iteration_counter += 1
            return metrics["sharpe"]

        study.optimize(objective, n_trials=self.trials_per_depth, show_progress_bar=False)
        best = study.best_params
        metrics = self._evaluate(best)
        node = RecursionNode(
            depth=depth, iteration=self._iteration_counter, params=best,
            sharpe=metrics["sharpe"], profit_uplift=metrics["sharpe"] - baseline_sharpe,
            win_rate=metrics["win_rate"], max_drawdown=metrics["max_drawdown"],
            total_return=metrics["total_return"], optimizer="optuna",
        )
        parent_node.children.append(node)
        return {"params": best, "sharpe": metrics["sharpe"]}, node

    # ------------------------------------------------------------------
    # DEAP Genetic phase
    # ------------------------------------------------------------------
    def _run_genetic_phase(
        self, depth: int, seed_params: dict, parent_node: RecursionNode,
        baseline_sharpe: float, progress_callback
    ) -> tuple[dict, RecursionNode]:
        keys = list(self.PARAM_SPACE.keys())
        bounds_low = [self.PARAM_SPACE[k][0] for k in keys]
        bounds_high = [self.PARAM_SPACE[k][1] for k in keys]

        try:
            creator.create("FitnessMax", base.Fitness, weights=(1.0,))
            creator.create("Individual", list, fitness=creator.FitnessMax)
        except Exception:
            pass

        toolbox = base.Toolbox()
        seed_vals = [seed_params.get(k, (self.PARAM_SPACE[k][0] + self.PARAM_SPACE[k][1]) / 2) for k in keys]

        def rand_individual():
            ind = []
            for i, k in enumerate(keys):
                lo, hi = self.PARAM_SPACE[k]
                noise = (hi - lo) * 0.1 * np.random.randn()
                val = np.clip(seed_vals[i] + noise, lo, hi)
                ind.append(val)
            return creator.Individual(ind)

        toolbox.register("individual", rand_individual)
        toolbox.register("population", tools.initRepeat, list, toolbox.individual)

        def eval_ind(ind):
            params = {k: v for k, v in zip(keys, ind)}
            metrics = self._evaluate(params)
            self._iteration_counter += 1
            return (metrics["sharpe"],)

        toolbox.register("evaluate", eval_ind)
        toolbox.register("mate", tools.cxBlend, alpha=0.3)
        toolbox.register("mutate", tools.mutGaussian, mu=0, sigma=0.05, indpb=0.2)
        toolbox.register("select", tools.selTournament, tournsize=3)

        pop = toolbox.population(n=self.genetic_pop)
        hof = tools.HallOfFame(1)
        algorithms.eaSimple(pop, toolbox, cxpb=0.5, mutpb=0.2, ngen=self.genetic_gens,
                            halloffame=hof, verbose=False)

        best_ind = hof[0]
        best_params = {k: v for k, v in zip(keys, best_ind)}
        metrics = self._evaluate(best_params)

        node = RecursionNode(
            depth=depth, iteration=self._iteration_counter, params=best_params,
            sharpe=metrics["sharpe"], profit_uplift=metrics["sharpe"] - baseline_sharpe,
            win_rate=metrics["win_rate"], max_drawdown=metrics["max_drawdown"],
            total_return=metrics["total_return"], optimizer="deap_genetic",
        )
        parent_node.children.append(node)
        return {"params": best_params, "sharpe": metrics["sharpe"]}, node

    # ------------------------------------------------------------------
    # Strategy evaluation (backtest on df)
    # ------------------------------------------------------------------
    def _evaluate(self, params: dict[str, Any]) -> dict[str, float]:
        """Fast vectorized backtest for a parameter set."""
        df = self.df.copy()
        c = df["close"] if "close" in df.columns else df.iloc[:, 3]

        rsi = self._rsi(c, 14)
        atr = self._atr(df, 14) if all(x in df.columns for x in ["high", "low"]) else c.rolling(14).std()

        signals = pd.Series(0, index=df.index)
        signals[(rsi < params["rsi_oversold"])] = 1
        signals[(rsi > params["rsi_overbought"])] = -1

        position = 0
        entry_price = 0.0
        bars_held = 0
        trades: list[float] = []
        equity = [1.0]
        eq = 1.0

        for i in range(1, len(c)):
            price = c.iloc[i]
            sig = signals.iloc[i]
            atr_val = float(atr.iloc[i]) if not pd.isna(atr.iloc[i]) else 0.01

            if position == 0 and sig == 1:
                position = 1
                entry_price = price
                bars_held = 0
            elif position == 1:
                bars_held += 1
                pnl_pct = (price - entry_price) / entry_price
                tp = params["take_profit_pct"]
                sl = params["stop_loss_pct"]
                ts = params["trailing_stop_pct"]
                max_bars = int(params["max_holding_bars"])

                if pnl_pct >= tp or pnl_pct <= -sl or bars_held >= max_bars:
                    trade_pnl = pnl_pct - 0.001  # 0.1% commission
                    trades.append(trade_pnl)
                    eq *= (1 + trade_pnl)
                    position = 0

            equity.append(eq)

        eq_series = pd.Series(equity)
        returns = eq_series.pct_change().dropna()

        if len(trades) == 0:
            return {"sharpe": -1.0, "total_return": 0.0, "win_rate": 0.0, "max_drawdown": 0.0}

        total_return = eq - 1.0
        win_rate = sum(1 for t in trades if t > 0) / len(trades)

        roll_max = eq_series.cummax()
        drawdown = (eq_series - roll_max) / roll_max
        max_drawdown = abs(float(drawdown.min()))

        ann_returns = returns * 252
        std = float(returns.std() * math.sqrt(252)) if len(returns) > 1 else 0.01
        sharpe = float(ann_returns.mean()) / std if std > 0 else 0.0

        # Penalize excessive drawdown
        if max_drawdown > 0.30:
            sharpe *= 0.5

        return {
            "sharpe": round(sharpe, 4),
            "total_return": round(total_return, 4),
            "win_rate": round(win_rate, 4),
            "max_drawdown": round(max_drawdown, 4),
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

    def _atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        h, l, c = df["high"], df["low"], df["close"]
        tr = pd.concat([h - l, (h - c.shift(1)).abs(), (l - c.shift(1)).abs()], axis=1).max(axis=1)
        return tr.ewm(span=period, adjust=False).mean()
