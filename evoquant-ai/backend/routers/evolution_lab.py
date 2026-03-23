from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from security.jwt_auth import get_current_user
from models.user import User
from engines.evolution_engine import EvolutionEngine

router = APIRouter()

_evo_jobs: dict[str, dict] = {}


class EvolutionConfig(BaseModel):
    symbols: list[str]
    asset_class: str = "stock"
    max_depth: int = 5
    period: str = "2y"


async def _run_evolution(job_id: str, config: EvolutionConfig):
    import yfinance as yf
    import pandas as pd
    try:
        _evo_jobs[job_id] = {"status": "running"}
        data_map = {}
        for sym in config.symbols:
            try:
                ticker = yf.Ticker(sym)
                df = ticker.history(period=config.period, interval="1d")
                df.columns = [c.lower() for c in df.columns]
                data_map[sym] = df[["open", "high", "low", "close", "volume"]]
            except Exception:
                pass

        engine = EvolutionEngine(config.symbols, config.asset_class)
        result = await engine.run_nightly_evolution(data_map, max_depth=config.max_depth)
        _evo_jobs[job_id] = {"status": "completed", "result": result}
    except Exception as e:
        _evo_jobs[job_id] = {"status": "failed", "error": str(e)}


@router.post("/run")
async def run_evolution(
    config: EvolutionConfig,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
):
    import uuid
    job_id = str(uuid.uuid4())
    background_tasks.add_task(_run_evolution, job_id, config)
    return {"job_id": job_id, "status": "started", "symbols": config.symbols}


@router.get("/job/{job_id}")
async def get_evolution_job(job_id: str, current_user: User = Depends(get_current_user)):
    job = _evo_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/leaderboard")
async def get_strategy_leaderboard(current_user: User = Depends(get_current_user)):
    """Return ranked strategies from evolution results."""
    completed = [
        {
            "job_id": jid,
            **{k: v for k, v in job.items() if k != "result"},
            "summary": {
                sym: {
                    "best_sharpe": job["result"]["symbols"][sym].get("recursive_sell", {}).get("best_sharpe"),
                    "best_return": job["result"]["symbols"][sym].get("recursive_sell", {}).get("best_return"),
                }
                for sym in job.get("result", {}).get("symbols", {})
            } if job.get("result") else {}
        }
        for jid, job in _evo_jobs.items()
        if job.get("status") == "completed"
    ]
    return {"leaderboard": completed}
