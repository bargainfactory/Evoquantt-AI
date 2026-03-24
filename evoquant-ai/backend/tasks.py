"""
Celery task queue for EvoQuant AI.
Handles background optimization, ML training, and nightly evolution.
"""
from celery import Celery
from celery.schedules import crontab
from celery.utils.log import get_task_logger
import asyncio
import logging
from config import get_settings

settings = get_settings()
logger = get_task_logger(__name__)

# Celery app
celery_app = Celery(
    "evoquant",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=3600,
    beat_schedule={
        "nightly-evolution": {
            "task": "tasks.run_nightly_evolution",
            "schedule": crontab(hour=2, minute=0),  # 2 AM UTC daily
        },
        "refresh-market-cache": {
            "task": "tasks.refresh_market_cache",
            "schedule": crontab(minute="*/5"),  # Every 5 minutes
        },
        "portfolio-snapshots": {
            "task": "tasks.take_portfolio_snapshots",
            "schedule": crontab(hour="*/1", minute=0),  # Hourly
        },
    },
)


def run_async(coro):
    """Run an async coroutine from a sync Celery task."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)


@celery_app.task(bind=True, name="tasks.run_recursive_sell", max_retries=1)
def run_recursive_sell_task(
    self,
    job_id: str,
    symbol: str,
    max_depth: int = 5,
    trials_per_depth: int = 30,
    genetic_pop: int = 50,
    genetic_gens: int = 20,
):
    """
    Background task for recursive sell optimization.
    Updates job status in Redis so the WebSocket can stream progress.
    """
    import json
    import redis as redis_lib
    import yfinance as yf
    import pandas as pd
    from engines.recursive_sell_engine import RecursiveSellEngine

    r = redis_lib.from_url(settings.REDIS_URL)
    key = f"recursive_sell:{job_id}"

    try:
        r.hset(key, mapping={"status": "running", "progress": "0"})
        r.expire(key, 3600)

        logger.info(f"Starting recursive sell for {symbol}, depth={max_depth}")

        # Fetch market data
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="1y", interval="1d")
        if df.empty:
            raise ValueError(f"No data for {symbol}")

        df = df.rename(columns={
            "Open": "open", "High": "high", "Low": "low",
            "Close": "close", "Volume": "volume"
        })

        def on_progress(depth: int, iteration: int, best_sharpe: float):
            progress = int((depth / max_depth) * 100)
            update = json.dumps({
                "type": "progress",
                "depth": depth,
                "iteration": iteration,
                "best_sharpe": best_sharpe,
            })
            r.hset(key, mapping={"progress": str(progress), "last_update": update})
            r.publish(f"ws:recursive_sell:{job_id}", update)

        engine = RecursiveSellEngine(
            df=df,
            max_depth=max_depth,
            trials_per_depth=trials_per_depth,
            genetic_pop=genetic_pop,
            genetic_gens=genetic_gens,
        )
        result = engine.run(progress_callback=on_progress)

        # Serialize result
        result_data = {
            "status": "completed",
            "best_params": result.best_params,
            "best_sharpe": result.best_sharpe,
            "best_return": result.best_return,
            "best_win_rate": result.best_win_rate,
            "best_drawdown": result.best_drawdown,
            "iterations_total": result.iterations_total,
            "depth_reached": result.depth_reached,
            "elapsed_seconds": result.elapsed_seconds,
            "convergence_history": [
                {
                    "depth": c.depth, "iteration": c.iteration,
                    "sharpe": c.sharpe, "total_return": c.total_return,
                }
                for c in result.convergence_history
            ],
        }

        r.hset(key, mapping={
            "status": "completed",
            "result": json.dumps(result_data),
            "progress": "100",
        })

        completed_msg = json.dumps({
            "type": "completed",
            "best_sharpe": result.best_sharpe,
            "best_return": result.best_return,
            "iterations_total": result.iterations_total,
            "convergence": result_data["convergence_history"],
        })
        r.publish(f"ws:recursive_sell:{job_id}", completed_msg)
        logger.info(f"Recursive sell complete for {symbol}: sharpe={result.best_sharpe:.3f}")
        return result_data

    except Exception as exc:
        error_msg = str(exc)
        logger.error(f"Recursive sell failed for {job_id}: {error_msg}")
        r.hset(key, mapping={"status": "error", "error": error_msg})
        import json
        r.publish(f"ws:recursive_sell:{job_id}", json.dumps({"type": "error", "message": error_msg}))
        raise self.retry(exc=exc, countdown=0, max_retries=0)


@celery_app.task(bind=True, name="tasks.run_backtest", max_retries=1)
def run_backtest_task(
    self,
    job_id: str,
    symbol: str,
    strategy: str = "rsi_ema_macd",
    period: str = "1y",
    interval: str = "1d",
    initial_capital: float = 100000,
):
    """Background task for strategy backtesting."""
    import json
    import redis as redis_lib
    import yfinance as yf
    import numpy as np
    import pandas as pd
    from engines.ta_engine import TAEngine

    r = redis_lib.from_url(settings.REDIS_URL)
    key = f"backtest:{job_id}"

    try:
        r.hset(key, mapping={"status": "running"})
        r.expire(key, 3600)

        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
        if df.empty:
            raise ValueError(f"No data for {symbol}")

        df.columns = [c.lower() for c in df.columns]

        # Build signals via TAEngine
        ta = TAEngine(df)
        ta.compute_all()
        signals = []
        closes = df["close"].values

        for i in range(50, len(df)):
            sub = df.iloc[:i+1]
            engine = TAEngine(sub)
            sig = engine.get_ensemble_signal()
            signals.append(sig.get("action", "NEUTRAL"))

        # Backtest loop
        cash = initial_capital
        position = 0.0
        equity_curve = [initial_capital]
        trades = []
        entry_price = 0.0

        for i, (sig, price) in enumerate(zip(signals, closes[50:])):
            if sig == "BUY" and position == 0:
                position = cash / price
                entry_price = price
                cash = 0
            elif sig == "SELL" and position > 0:
                cash = position * price
                pnl = (price - entry_price) / entry_price
                trades.append(pnl)
                position = 0
            equity_curve.append(cash + position * price)

        # Close open position at end
        if position > 0:
            cash = position * closes[-1]
            pnl = (closes[-1] - entry_price) / entry_price
            trades.append(pnl)
            equity_curve.append(cash)

        equity = np.array(equity_curve)
        returns = np.diff(equity) / equity[:-1]

        total_return = (equity[-1] - initial_capital) / initial_capital
        wins = [t for t in trades if t > 0]
        losses = [t for t in trades if t <= 0]
        win_rate = len(wins) / len(trades) if trades else 0

        sharpe = (returns.mean() / (returns.std() + 1e-9)) * np.sqrt(252) if len(returns) > 1 else 0
        running_max = np.maximum.accumulate(equity)
        drawdowns = (equity - running_max) / running_max
        max_drawdown = abs(drawdowns.min())
        avg_win = np.mean(wins) if wins else 0
        avg_loss = abs(np.mean(losses)) if losses else 1
        profit_factor = (sum(wins) / abs(sum(losses))) if losses else float("inf")

        # Monthly returns
        monthly_returns = {}
        try:
            idx = df.index[50:]
            eq_series = pd.Series(equity_curve[1:], index=idx[:len(equity_curve)-1])
            monthly = eq_series.resample("ME").last().pct_change().dropna()
            monthly_returns = {str(d.date())[:7]: float(v) for d, v in monthly.items()}
        except Exception:
            pass

        # Monte Carlo VaR
        mc_sims = np.random.choice(returns, size=(10000, 30), replace=True).cumprod(axis=1) if len(returns) > 0 else np.zeros((1,1))
        mc_final = equity[-1] * (1 + mc_sims[:, -1])
        mc_var_95 = float(np.percentile(equity[-1] - mc_final, 95))
        mc_cvar_95 = float(np.mean(equity[-1] - mc_final[mc_final < np.percentile(mc_final, 5)]))

        result = {
            "status": "completed",
            "symbol": symbol,
            "strategy": strategy,
            "total_return": float(total_return),
            "sharpe_ratio": float(sharpe),
            "win_rate": float(win_rate),
            "max_drawdown": float(max_drawdown),
            "total_trades": len(trades),
            "profit_factor": float(profit_factor),
            "avg_trade_return": float(np.mean(trades)) if trades else 0,
            "equity_curve": equity.tolist(),
            "monthly_returns": monthly_returns,
            "mc_var_95": mc_var_95,
            "mc_cvar_95": mc_cvar_95,
        }

        r.hset(key, mapping={"status": "completed", "result": json.dumps(result)})
        logger.info(f"Backtest complete for {symbol}: return={total_return:.2%}, sharpe={sharpe:.2f}")
        return result

    except Exception as exc:
        logger.error(f"Backtest failed for {job_id}: {exc}")
        r.hset(key, mapping={"status": "error", "error": str(exc)})
        raise


@celery_app.task(name="tasks.run_nightly_evolution")
def run_nightly_evolution():
    """
    Nightly task: walk-forward optimization across all tracked symbols.
    Results stored in DB for the Evolution Lab leaderboard.
    """
    import yfinance as yf
    import json
    import redis as redis_lib
    from engines.evolution_engine import EvolutionEngine

    r = redis_lib.from_url(settings.REDIS_URL)

    symbols_by_class = {
        "stocks": ["AAPL", "MSFT", "TSLA", "NVDA", "GOOGL", "META", "AMZN", "SPY", "QQQ"],
        "crypto": ["BTC-USD", "ETH-USD", "SOL-USD"],
    }

    all_results = []

    for asset_class, symbols in symbols_by_class.items():
        data_map = {}
        for sym in symbols:
            try:
                df = yf.Ticker(sym).history(period="2y", interval="1d")
                if not df.empty:
                    df.columns = [c.lower() for c in df.columns]
                    data_map[sym] = df
            except Exception as e:
                logger.warning(f"Failed to fetch {sym}: {e}")

        if not data_map:
            continue

        try:
            engine = EvolutionEngine(symbols=list(data_map.keys()), asset_class=asset_class)
            results = run_async(engine.run_nightly_evolution(data_map, max_depth=5))
            all_results.extend(results)
        except Exception as e:
            logger.error(f"Evolution failed for {asset_class}: {e}")

    # Store leaderboard in Redis
    r.setex("evolution:leaderboard", 86400, json.dumps(all_results))
    logger.info(f"Nightly evolution complete: {len(all_results)} strategies evaluated")
    return {"evaluated": len(all_results)}


@celery_app.task(name="tasks.refresh_market_cache")
def refresh_market_cache():
    """Refresh market data cache for watchlist symbols."""
    import yfinance as yf
    import json
    import redis as redis_lib

    r = redis_lib.from_url(settings.REDIS_URL)
    watchlist_key = "market:watchlist"
    watchlist_raw = r.get(watchlist_key)

    if not watchlist_raw:
        symbols = ["AAPL", "MSFT", "TSLA", "NVDA", "BTC-USD", "ETH-USD", "SPY", "QQQ"]
    else:
        symbols = json.loads(watchlist_raw)

    refreshed = 0
    for sym in symbols:
        try:
            ticker = yf.Ticker(sym)
            info = ticker.fast_info
            price = float(getattr(info, "last_price", 0) or 0)
            if price > 0:
                r.setex(f"market:quote:{sym}", 60, json.dumps({"price": price, "symbol": sym}))
                refreshed += 1
        except Exception:
            pass

    logger.debug(f"Refreshed {refreshed}/{len(symbols)} market quotes")
    return {"refreshed": refreshed}


@celery_app.task(name="tasks.take_portfolio_snapshots")
def take_portfolio_snapshots():
    """Take hourly portfolio snapshots for all active users."""
    logger.info("Taking portfolio snapshots")
    # Actual implementation would query all portfolios via DB and record snapshots
    # This stub demonstrates the Celery beat schedule integration
    return {"snapshots_taken": 0}


@celery_app.task(name="tasks.train_ml_models")
def train_ml_models(symbol: str):
    """Train ML models for a specific symbol."""
    import yfinance as yf
    from engines.ml_engine import MLEngine

    logger.info(f"Training ML models for {symbol}")
    try:
        df = yf.Ticker(symbol).history(period="2y", interval="1d")
        df.columns = [c.lower() for c in df.columns]
        engine = MLEngine(symbol)
        rf_score = engine.train_rf(df)
        gb_score = engine.train_gb(df)
        logger.info(f"ML training complete for {symbol}: RF={rf_score:.3f}, GB={gb_score:.3f}")
        return {"symbol": symbol, "rf_score": rf_score, "gb_score": gb_score}
    except Exception as exc:
        logger.error(f"ML training failed for {symbol}: {exc}")
        raise
