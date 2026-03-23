from typing import Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from database import get_session
from models.strategy import StrategyRun
from models.user import User
from security.jwt_auth import get_current_user
from engines.recursive_sell_engine import RecursiveSellEngine

import json

router = APIRouter()

# In-memory job store (use Redis in production)
_jobs: dict[str, dict] = {}


class RecursiveSellConfig(BaseModel):
    symbol: str
    period: str = "1y"
    interval: str = "1d"
    max_depth: int = 5
    trials_per_depth: int = 30
    genetic_pop: int = 50
    genetic_gens: int = 20
    objective: str = "sharpe"


async def _fetch_df(symbol: str, period: str, interval: str):
    import yfinance as yf
    import pandas as pd
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period, interval=interval)
    df.columns = [c.lower() for c in df.columns]
    return df[["open", "high", "low", "close", "volume"]]


async def _run_optimization(job_id: str, config: RecursiveSellConfig, user_id: str):
    try:
        _jobs[job_id] = {"status": "running", "progress": {}}
        df = await _fetch_df(config.symbol, config.period, config.interval)

        def progress_cb(data: dict):
            _jobs[job_id]["progress"] = data

        engine = RecursiveSellEngine(
            df=df,
            max_depth=config.max_depth,
            trials_per_depth=config.trials_per_depth,
            genetic_pop=config.genetic_pop,
            genetic_gens=config.genetic_gens,
            objective=config.objective,
        )
        result = engine.run(progress_callback=progress_cb)
        _jobs[job_id] = {
            "status": "completed",
            "result": result.to_dict(),
            "symbol": config.symbol,
        }
    except Exception as e:
        _jobs[job_id] = {"status": "failed", "error": str(e)}


@router.post("/run")
async def run_recursive_optimization(
    config: RecursiveSellConfig,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
):
    import uuid
    job_id = str(uuid.uuid4())
    background_tasks.add_task(_run_optimization, job_id, config, str(current_user.id))
    return {"job_id": job_id, "status": "started", "symbol": config.symbol}


@router.get("/job/{job_id}")
async def get_job_status(job_id: str, current_user: User = Depends(get_current_user)):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/result/{job_id}")
async def get_job_result(job_id: str, current_user: User = Depends(get_current_user)):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "completed":
        raise HTTPException(status_code=202, detail=f"Job {job['status']}")
    return job["result"]


@router.post("/quick-evaluate")
async def quick_evaluate(
    symbol: str,
    params: dict,
    period: str = "1y",
    current_user: User = Depends(get_current_user),
):
    """Evaluate a single parameter set quickly."""
    df = await _fetch_df(symbol, period, "1d")
    engine = RecursiveSellEngine(df, max_depth=1, trials_per_depth=1)
    metrics = engine._evaluate(params)
    return {"symbol": symbol, "params": params, "metrics": metrics}


@router.get("/convergence/{job_id}")
async def get_convergence(job_id: str, current_user: User = Depends(get_current_user)):
    """Get convergence history for the visual debugger chart."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] == "completed" and "result" in job:
        return {"convergence": job["result"].get("convergence_history", [])}
    return {"convergence": [], "progress": job.get("progress", {})}


@router.get("/tree/{job_id}")
async def get_recursion_tree(job_id: str, current_user: User = Depends(get_current_user)):
    """Get full recursion tree for the visual Plotly tree diagram."""
    job = _jobs.get(job_id)
    if not job or job["status"] != "completed":
        raise HTTPException(status_code=404 if not job else 202, detail="Job not ready")
    return {"tree": job["result"].get("tree", {})}
