from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from security.jwt_auth import get_current_user
from models.user import User
from dex.uniswap_v4 import UniswapV4Router
from dex.jupiter import JupiterRouter

router = APIRouter()
uni_router = UniswapV4Router()
jup_router = JupiterRouter()


class UniswapQuoteRequest(BaseModel):
    token_in: str
    token_out: str
    amount_in: str
    fee: int = 3000
    slippage: float = 0.5


class JupiterQuoteRequest(BaseModel):
    input_mint: str
    output_mint: str
    amount: int
    slippage_bps: int = 50
    swap_mode: str = "ExactIn"


class SwapCallRequest(BaseModel):
    token_in: str
    token_out: str
    amount_in: int
    amount_out_min: int
    recipient: str
    fee: int = 3000


class JupiterSwapRequest(BaseModel):
    quote_response: dict
    user_public_key: str
    wrap_unwrap_sol: bool = True
    prioritization_fee_lamports: int = 1000


# Uniswap V4 endpoints
@router.post("/uniswap/quote")
async def uniswap_quote(req: UniswapQuoteRequest, current_user: User = Depends(get_current_user)):
    return await uni_router.get_quote(req.token_in, req.token_out, req.amount_in, req.fee, req.slippage)


@router.post("/uniswap/build-swap")
async def uniswap_build_swap(req: SwapCallRequest, current_user: User = Depends(get_current_user)):
    return uni_router.build_swap_calldata(
        req.token_in, req.token_out, req.amount_in,
        req.amount_out_min, req.recipient, req.fee
    )


@router.get("/uniswap/pool")
async def uniswap_pool_info(
    token0: str,
    token1: str,
    fee: int = Query(3000),
    current_user: User = Depends(get_current_user),
):
    return await uni_router.get_pool_info(token0, token1, fee)


@router.get("/uniswap/tokens")
async def uniswap_tokens(current_user: User = Depends(get_current_user)):
    return await uni_router.get_supported_tokens()


# Jupiter endpoints
@router.post("/jupiter/quote")
async def jupiter_quote(req: JupiterQuoteRequest, current_user: User = Depends(get_current_user)):
    return await jup_router.get_quote(
        req.input_mint, req.output_mint, req.amount,
        req.slippage_bps, swap_mode=req.swap_mode
    )


@router.post("/jupiter/swap")
async def jupiter_build_swap(req: JupiterSwapRequest, current_user: User = Depends(get_current_user)):
    return await jup_router.build_swap_transaction(
        req.quote_response, req.user_public_key,
        req.wrap_unwrap_sol, prioritization_fee_lamports=req.prioritization_fee_lamports
    )


@router.get("/jupiter/price")
async def jupiter_price(
    tokens: str = Query(..., description="Comma-separated token symbols"),
    vs: str = Query("USDC"),
    current_user: User = Depends(get_current_user),
):
    token_list = [t.strip() for t in tokens.split(",")]
    return await jup_router.get_price(token_list, vs)


@router.get("/jupiter/tokens")
async def jupiter_tokens(current_user: User = Depends(get_current_user)):
    return jup_router.get_known_tokens()


# Combined best-route endpoint
@router.get("/best-route")
async def get_best_route(
    chain: str = Query(..., description="eth | solana"),
    token_in: str = Query(...),
    token_out: str = Query(...),
    amount: str = Query(...),
    current_user: User = Depends(get_current_user),
):
    """Compare routes across DEXes and return the best."""
    if chain.lower() == "eth":
        quote = await uni_router.get_quote(token_in, token_out, amount)
        return {"chain": "ethereum", "dex": "uniswap_v4", "quote": quote}
    elif chain.lower() == "solana":
        try:
            amount_int = int(amount)
            quote = await jup_router.get_quote(token_in, token_out, amount_int)
            return {"chain": "solana", "dex": "jupiter", "quote": quote}
        except ValueError:
            raise HTTPException(status_code=400, detail="Amount must be integer for Solana")
    raise HTTPException(status_code=400, detail="Unsupported chain. Use eth or solana")
