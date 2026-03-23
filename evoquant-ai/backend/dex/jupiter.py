"""
Jupiter Aggregator (Solana) routing engine.
Uses the Jupiter V6 Quote + Swap API for best-price routing.
"""
from __future__ import annotations

from typing import Any

import httpx

from config import settings

# Common Solana token mint addresses
SOLANA_TOKENS = {
    "SOL": "So11111111111111111111111111111111111111112",
    "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "USDT": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
    "BTC": "9n4nbM75f5Ui33ZbPYXn59EwSgE8CGsHtAeTH5YFeJ9E",
    "ETH": "7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs",
    "RAY": "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R",
    "ORCA": "orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE",
    "JUP": "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
    "BONK": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
}


class JupiterRouter:
    """
    Jupiter V6 Aggregator routing engine.
    Provides best-price quotes and swap transaction building for Solana.
    """

    QUOTE_URL = f"{settings.JUPITER_API_URL}/quote"
    SWAP_URL = f"{settings.JUPITER_API_URL}/swap"
    TOKENS_URL = f"{settings.JUPITER_API_URL}/tokens"
    PRICE_URL = "https://price.jup.ag/v6/price"

    def __init__(self, rpc_url: str | None = None):
        self.rpc_url = rpc_url or settings.SOLANA_RPC_URL
        self._headers = {"Accept": "application/json"}
        if settings.JUPITER_API_KEY:
            self._headers["x-api-key"] = settings.JUPITER_API_KEY

    async def get_quote(
        self,
        input_mint: str,
        output_mint: str,
        amount: int,
        slippage_bps: int = 50,
        only_direct_routes: bool = False,
        swap_mode: str = "ExactIn",
    ) -> dict[str, Any]:
        """
        Get best swap quote from Jupiter.
        amount: in lamports/base units.
        """
        # Resolve symbols to mint addresses
        in_mint = SOLANA_TOKENS.get(input_mint.upper(), input_mint)
        out_mint = SOLANA_TOKENS.get(output_mint.upper(), output_mint)

        params = {
            "inputMint": in_mint,
            "outputMint": out_mint,
            "amount": str(amount),
            "slippageBps": slippage_bps,
            "onlyDirectRoutes": str(only_direct_routes).lower(),
            "swapMode": swap_mode,
        }

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(self.QUOTE_URL, params=params, headers=self._headers)
            if resp.status_code != 200:
                return {"error": f"Jupiter quote failed: {resp.status_code}", "details": resp.text}
            data = resp.json()

        # Parse route plan
        route_plan = data.get("routePlan", [])
        parsed_routes = [
            {
                "swap_info": r.get("swapInfo", {}),
                "percent": r.get("percent", 100),
            }
            for r in route_plan
        ]

        return {
            "input_mint": in_mint,
            "output_mint": out_mint,
            "in_amount": data.get("inAmount", "0"),
            "out_amount": data.get("outAmount", "0"),
            "other_amount_threshold": data.get("otherAmountThreshold", "0"),
            "swap_mode": data.get("swapMode", swap_mode),
            "slippage_bps": data.get("slippageBps", slippage_bps),
            "price_impact_pct": data.get("priceImpactPct", "0"),
            "route_plan": parsed_routes,
            "context_slot": data.get("contextSlot"),
            "time_taken": data.get("timeTaken"),
            "raw_quote": data,
        }

    async def build_swap_transaction(
        self,
        quote_response: dict[str, Any],
        user_public_key: str,
        wrap_unwrap_sol: bool = True,
        use_shared_accounts: bool = True,
        prioritization_fee_lamports: int = 1000,
    ) -> dict[str, Any]:
        """
        Build Solana swap transaction from a quote response.
        Returns unsigned transaction that frontend wallet must sign.
        """
        if "error" in quote_response:
            return quote_response

        raw_quote = quote_response.get("raw_quote", quote_response)

        payload = {
            "quoteResponse": raw_quote,
            "userPublicKey": user_public_key,
            "wrapAndUnwrapSol": wrap_unwrap_sol,
            "useSharedAccounts": use_shared_accounts,
            "prioritizationFeeLamports": prioritization_fee_lamports,
            "dynamicComputeUnitLimit": True,
            "skipUserAccountsRpcCalls": True,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(self.SWAP_URL, json=payload, headers=self._headers)
            if resp.status_code != 200:
                return {"error": f"Jupiter swap build failed: {resp.status_code}", "details": resp.text}
            data = resp.json()

        return {
            "swap_transaction": data.get("swapTransaction"),
            "last_valid_block_height": data.get("lastValidBlockHeight"),
            "prioritization_fee_lamports": data.get("prioritizationFeeLamports"),
        }

    async def get_price(self, input_mints: list[str], vs_token: str = "USDC") -> dict[str, Any]:
        """Get current prices for multiple tokens."""
        mints = [SOLANA_TOKENS.get(m.upper(), m) for m in input_mints]
        vs_mint = SOLANA_TOKENS.get(vs_token.upper(), vs_token)

        params = {"ids": ",".join(mints), "vsToken": vs_mint}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(self.PRICE_URL, params=params, headers=self._headers)
            if resp.status_code != 200:
                return {}
            data = resp.json()

        prices = {}
        for sym, mint in zip(input_mints, mints):
            price_data = data.get("data", {}).get(mint, {})
            prices[sym] = {
                "price": price_data.get("price", 0),
                "mint": mint,
                "vs_token": vs_token,
            }
        return prices

    async def get_token_list(self) -> list[dict[str, Any]]:
        """Get all Jupiter-supported tokens."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(self.TOKENS_URL, headers=self._headers)
            if resp.status_code != 200:
                return list(SOLANA_TOKENS.keys())
            return resp.json()[:100]  # Return first 100 for brevity

    async def get_indexed_route_map(self) -> dict[str, Any]:
        """Get Jupiter route map for route planning UI."""
        url = f"{settings.JUPITER_API_URL}/indexed-route-map"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=self._headers)
            if resp.status_code == 200:
                return resp.json()
            return {}

    def get_known_tokens(self) -> list[dict[str, str]]:
        return [{"symbol": k, "mint": v} for k, v in SOLANA_TOKENS.items()]
