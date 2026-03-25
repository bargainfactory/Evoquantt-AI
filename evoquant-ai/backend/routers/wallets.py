from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import json

from security.jwt_auth import get_current_user
from security.vault import vault
from models.user import User
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_session

router = APIRouter()


class WalletConnect(BaseModel):
    chain: str  # eth | solana | bsc | polygon
    address: str
    wallet_type: str = "metamask"  # metamask | walletconnect | phantom | ledger | trezor


@router.post("/connect")
async def connect_wallet(
    wallet: WalletConnect,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    wallets = {}
    if current_user.wallet_addresses:
        try:
            wallets = json.loads(current_user.wallet_addresses)
        except Exception:
            pass
    wallets[wallet.chain] = {
        "address": wallet.address,
        "wallet_type": wallet.wallet_type,
        "connected_at": __import__("datetime").datetime.now().isoformat(),
    }
    current_user.wallet_addresses = json.dumps(wallets)
    session.add(current_user)
    await session.commit()
    return {"message": f"{wallet.chain} wallet connected", "address": wallet.address}


@router.get("/list")
async def list_wallets(current_user: User = Depends(get_current_user)):
    if not current_user.wallet_addresses:
        return {"wallets": {}}
    try:
        return {"wallets": json.loads(current_user.wallet_addresses)}
    except Exception:
        return {"wallets": {}}


@router.delete("/{chain}/disconnect")
async def disconnect_wallet(
    chain: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    wallets = {}
    if current_user.wallet_addresses:
        try:
            wallets = json.loads(current_user.wallet_addresses)
        except Exception:
            pass
    wallets.pop(chain, None)
    current_user.wallet_addresses = json.dumps(wallets)
    session.add(current_user)
    await session.commit()
    return {"message": f"{chain} wallet disconnected"}


@router.get("/balance/{chain}/{address}")
async def get_wallet_balance(
    chain: str,
    address: str,
    current_user: User = Depends(get_current_user),
):
    from config import settings
    if chain == "eth":
        try:
            import httpx
            rpc = settings.ALCHEMY_ETH_MAINNET or "https://eth.llamarpc.com"
            payload = {"jsonrpc": "2.0", "id": 1, "method": "eth_getBalance", "params": [address, "latest"]}
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(rpc, json=payload)
                data = resp.json()
            balance_wei = int(data.get("result", "0x0"), 16)
            return {"chain": "eth", "address": address, "balance": balance_wei / 1e18, "unit": "ETH"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    elif chain == "solana":
        try:
            import httpx
            payload = {"jsonrpc": "2.0", "id": 1, "method": "getBalance", "params": [address]}
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(settings.SOLANA_RPC_URL, json=payload)
                data = resp.json()
            lamports = data.get("result", {}).get("value", 0)
            return {"chain": "solana", "address": address, "balance": lamports / 1e9, "unit": "SOL"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    return {"chain": chain, "address": address, "balance": 0, "error": "Unsupported chain"}
