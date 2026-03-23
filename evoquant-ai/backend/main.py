import logging
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from config import settings
from database import init_db
from routers import (
    auth,
    market_data,
    trading,
    portfolio,
    options,
    recursive_sell,
    evolution_lab,
    dex_routing,
    brokers,
    wallets,
    alerts,
    backtester,
    ai_copilot,
    websocket as ws_router,
)

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
)

logger = structlog.get_logger()
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("evoquant_startup", env=settings.APP_ENV)
    await init_db()
    yield
    logger.info("evoquant_shutdown")


app = FastAPI(
    title="EvoQuant AI",
    description="Production-ready full-stack trading platform with quantum-proof security",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs" if not settings.is_production else None,
    redoc_url="/api/redoc" if not settings.is_production else None,
)

# Middlewares
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
if settings.is_production:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["yourdomain.com", "*.yourdomain.com"])

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Prometheus metrics
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# Routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(market_data.router, prefix="/api/market", tags=["market-data"])
app.include_router(trading.router, prefix="/api/trading", tags=["trading"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["portfolio"])
app.include_router(options.router, prefix="/api/options", tags=["options"])
app.include_router(recursive_sell.router, prefix="/api/recursive-sell", tags=["recursive-sell"])
app.include_router(evolution_lab.router, prefix="/api/evolution", tags=["evolution-lab"])
app.include_router(dex_routing.router, prefix="/api/dex", tags=["dex"])
app.include_router(brokers.router, prefix="/api/brokers", tags=["brokers"])
app.include_router(wallets.router, prefix="/api/wallets", tags=["wallets"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["alerts"])
app.include_router(backtester.router, prefix="/api/backtest", tags=["backtester"])
app.include_router(ai_copilot.router, prefix="/api/ai", tags=["ai-copilot"])
app.include_router(ws_router.router, prefix="/ws", tags=["websocket"])


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "healthy", "version": "1.0.0", "env": settings.APP_ENV}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("unhandled_exception", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )
