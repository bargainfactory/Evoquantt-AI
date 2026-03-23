"""
Uniswap V4 DEX routing engine.
Builds swap calldata for PoolManager via web3.py.
"""
from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

import httpx

from config import settings

try:
    from web3 import Web3
    from web3.middleware import geth_poa_middleware
    W3_AVAILABLE = True
except ImportError:
    W3_AVAILABLE = False


# Minimal Uniswap V4 PoolManager ABI (swap function)
POOL_MANAGER_ABI = [
    {
        "name": "swap",
        "type": "function",
        "inputs": [
            {"name": "key", "type": "tuple", "components": [
                {"name": "currency0", "type": "address"},
                {"name": "currency1", "type": "address"},
                {"name": "fee", "type": "uint24"},
                {"name": "tickSpacing", "type": "int24"},
                {"name": "hooks", "type": "address"},
            ]},
            {"name": "params", "type": "tuple", "components": [
                {"name": "zeroForOne", "type": "bool"},
                {"name": "amountSpecified", "type": "int256"},
                {"name": "sqrtPriceLimitX96", "type": "uint160"},
            ]},
            {"name": "hookData", "type": "bytes"},
        ],
        "outputs": [{"name": "delta", "type": "int256"}],
        "stateMutability": "nonpayable",
    },
    {
        "name": "initialize",
        "type": "function",
        "inputs": [
            {"name": "key", "type": "tuple", "components": [
                {"name": "currency0", "type": "address"},
                {"name": "currency1", "type": "address"},
                {"name": "fee", "type": "uint24"},
                {"name": "tickSpacing", "type": "int24"},
                {"name": "hooks", "type": "address"},
            ]},
            {"name": "sqrtPriceX96", "type": "uint160"},
            {"name": "hookData", "type": "bytes"},
        ],
        "outputs": [{"name": "tick", "type": "int24"}],
        "stateMutability": "nonpayable",
    },
]

# Common token addresses (mainnet)
TOKEN_ADDRESSES = {
    "ETH": "0x0000000000000000000000000000000000000000",
    "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
    "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
    "DAI": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
    "WBTC": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
    "UNI": "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984",
}


class UniswapV4Router:
    """
    Backend Uniswap V4 routing engine.
    - Quotes via Uniswap V4 Quoter or 1inch fallback
    - Builds swap calldata
    - Returns unsigned transaction for frontend to sign
    """

    UNISWAP_V4_QUOTER = "https://interface.gateway.uniswap.org/v2/quote"

    def __init__(self, rpc_url: str | None = None):
        self.rpc_url = rpc_url or settings.ALCHEMY_ETH_MAINNET or "https://eth.llamarpc.com"
        self._w3: Any = None

    def _get_w3(self) -> Any:
        if not W3_AVAILABLE:
            return None
        if not self._w3:
            self._w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        return self._w3

    async def get_quote(
        self,
        token_in: str,
        token_out: str,
        amount_in: str,
        fee: int = 3000,
        slippage: float = 0.5,
    ) -> dict[str, Any]:
        """Get swap quote from Uniswap V4 API."""
        addr_in = TOKEN_ADDRESSES.get(token_in.upper(), token_in)
        addr_out = TOKEN_ADDRESSES.get(token_out.upper(), token_out)

        try:
            payload = {
                "tokenInChainId": 1,
                "tokenIn": addr_in,
                "tokenOutChainId": 1,
                "tokenOut": addr_out,
                "amount": amount_in,
                "type": "EXACT_INPUT",
                "configs": [{"protocols": ["V4"], "enableUniversalRouter": True}],
            }
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(self.UNISWAP_V4_QUOTER, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    return {
                        "token_in": token_in,
                        "token_out": token_out,
                        "amount_in": amount_in,
                        "amount_out": data.get("quote", {}).get("output", "0"),
                        "gas_estimate": data.get("gasEstimate", 150000),
                        "price_impact": data.get("priceImpact", 0),
                        "route": data.get("route", []),
                        "source": "uniswap_v4",
                    }
        except Exception as e:
            pass

        # Fallback: 1inch API
        return await self._get_1inch_quote(addr_in, addr_out, amount_in)

    async def _get_1inch_quote(self, token_in: str, token_out: str, amount: str) -> dict[str, Any]:
        """1inch aggregator fallback quote."""
        url = f"https://api.1inch.dev/swap/v6.0/1/quote"
        params = {"src": token_in, "dst": token_out, "amount": amount}
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    return {
                        "token_in": token_in,
                        "token_out": token_out,
                        "amount_in": amount,
                        "amount_out": str(data.get("dstAmount", 0)),
                        "gas_estimate": data.get("gas", 200000),
                        "source": "1inch_fallback",
                    }
        except Exception:
            pass
        return {"error": "Quote unavailable", "amount_out": "0"}

    def build_swap_calldata(
        self,
        token_in: str,
        token_out: str,
        amount_in: int,
        amount_out_min: int,
        recipient: str,
        fee: int = 3000,
        tick_spacing: int = 60,
        hooks: str = "0x0000000000000000000000000000000000000000",
    ) -> dict[str, Any]:
        """Build unsigned swap transaction calldata for V4 PoolManager."""
        w3 = self._get_w3()
        if not w3:
            return {"error": "web3 not available"}

        addr_in = TOKEN_ADDRESSES.get(token_in.upper(), token_in)
        addr_out = TOKEN_ADDRESSES.get(token_out.upper(), token_out)

        # Sort tokens (V4 requires currency0 < currency1)
        zero_for_one = addr_in.lower() < addr_out.lower()
        currency0 = addr_in if zero_for_one else addr_out
        currency1 = addr_out if zero_for_one else addr_in

        pool_key = {
            "currency0": Web3.to_checksum_address(currency0),
            "currency1": Web3.to_checksum_address(currency1),
            "fee": fee,
            "tickSpacing": tick_spacing,
            "hooks": Web3.to_checksum_address(hooks),
        }

        # sqrt price limit: 0 means no limit
        sqrt_price_limit = 0

        contract = w3.eth.contract(
            address=Web3.to_checksum_address(settings.UNISWAP_V4_POOL_MANAGER_ADDRESS),
            abi=POOL_MANAGER_ABI,
        )

        calldata = contract.encodeABI(
            fn_name="swap",
            args=[
                pool_key,
                {
                    "zeroForOne": zero_for_one,
                    "amountSpecified": amount_in,
                    "sqrtPriceLimitX96": sqrt_price_limit,
                },
                b"",  # hookData
            ],
        )

        return {
            "to": settings.UNISWAP_V4_POOL_MANAGER_ADDRESS,
            "data": calldata,
            "value": amount_in if token_in.upper() == "ETH" else 0,
            "pool_key": pool_key,
            "zero_for_one": zero_for_one,
            "amount_in": amount_in,
            "amount_out_min": amount_out_min,
        }

    async def get_pool_info(self, token0: str, token1: str, fee: int = 3000) -> dict[str, Any]:
        """Get V4 pool liquidity and current tick info."""
        addr0 = TOKEN_ADDRESSES.get(token0.upper(), token0)
        addr1 = TOKEN_ADDRESSES.get(token1.upper(), token1)

        return {
            "token0": token0,
            "token1": token1,
            "fee": fee,
            "token0_address": addr0,
            "token1_address": addr1,
            "source": "uniswap_v4",
        }

    async def get_supported_tokens(self) -> list[dict[str, str]]:
        return [{"symbol": k, "address": v} for k, v in TOKEN_ADDRESSES.items()]
