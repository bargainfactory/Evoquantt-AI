from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_session
from models.user import User
from security.jwt_auth import get_current_user
from security.vault import vault
from security.audit import AuditLogger
from brokers import BROKER_REGISTRY

router = APIRouter()


class BrokerCredentials(BaseModel):
    broker: str
    api_key: str
    secret: str
    passphrase: Optional[str] = ""
    testnet: bool = True


@router.post("/connect")
async def connect_broker(
    creds: BrokerCredentials,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Encrypt and store broker credentials in PQ vault."""
    import json
    encrypted = vault.encrypt_api_key(creds.broker, creds.api_key, creds.secret)
    broker_creds = {}
    if current_user.broker_credentials:
        try:
            broker_creds = json.loads(current_user.broker_credentials)
        except Exception:
            pass
    broker_creds[creds.broker] = {
        **encrypted,
        "passphrase_enc": vault.encrypt(creds.passphrase, context=f"broker:{creds.broker}:passphrase"),
        "testnet": creds.testnet,
    }
    current_user.broker_credentials = json.dumps(broker_creds)
    session.add(current_user)
    await session.commit()

    al = AuditLogger(session)
    await al.log("connect_broker", "broker", user_id=current_user.id, details={"broker": creds.broker})
    return {"message": f"{creds.broker} connected successfully"}


@router.get("/list")
async def list_connected_brokers(current_user: User = Depends(get_current_user)):
    import json
    if not current_user.broker_credentials:
        return {"brokers": []}
    try:
        creds = json.loads(current_user.broker_credentials)
        return {"brokers": list(creds.keys())}
    except Exception:
        return {"brokers": []}


@router.get("/{broker}/balances")
async def get_broker_balances(
    broker: str,
    current_user: User = Depends(get_current_user),
):
    import json
    if not current_user.broker_credentials:
        raise HTTPException(status_code=400, detail="No broker credentials stored")
    creds_map = json.loads(current_user.broker_credentials)
    if broker not in creds_map:
        raise HTTPException(status_code=404, detail=f"Broker {broker} not connected")

    broker_class = BROKER_REGISTRY.get(broker)
    if not broker_class:
        raise HTTPException(status_code=400, detail=f"Unknown broker: {broker}")

    enc = creds_map[broker]
    api_key, secret = vault.decrypt_api_key(broker, enc)
    passphrase = vault.decrypt(enc.get("passphrase_enc", ""), context=f"broker:{broker}:passphrase").decode() if enc.get("passphrase_enc") else ""
    testnet = enc.get("testnet", True)

    b = broker_class(broker, api_key, secret, passphrase, testnet)
    await b.connect()
    balances = await b.get_balances()
    await b.disconnect()
    return {"broker": broker, "balances": [{"currency": bal.currency, "total": float(bal.total), "available": float(bal.available)} for bal in balances]}


@router.get("/{broker}/positions")
async def get_broker_positions(
    broker: str,
    current_user: User = Depends(get_current_user),
):
    import json
    if not current_user.broker_credentials:
        raise HTTPException(status_code=400, detail="No broker credentials")
    creds_map = json.loads(current_user.broker_credentials)
    if broker not in creds_map:
        raise HTTPException(status_code=404, detail=f"Broker {broker} not connected")

    broker_class = BROKER_REGISTRY.get(broker)
    if not broker_class:
        raise HTTPException(status_code=400, detail=f"Unknown broker: {broker}")

    enc = creds_map[broker]
    api_key, secret = vault.decrypt_api_key(broker, enc)
    passphrase = vault.decrypt(enc.get("passphrase_enc", ""), context=f"broker:{broker}:passphrase").decode() if enc.get("passphrase_enc") else ""
    testnet = enc.get("testnet", True)

    b = broker_class(broker, api_key, secret, passphrase, testnet)
    await b.connect()
    positions = await b.get_positions()
    await b.disconnect()
    return {
        "broker": broker,
        "positions": [
            {"symbol": p.symbol, "quantity": float(p.quantity), "avg_cost": float(p.avg_cost),
             "current_price": float(p.current_price), "unrealized_pnl": float(p.unrealized_pnl)}
            for p in positions
        ]
    }


# OAuth2 broker flows
@router.get("/etrade/authorize")
async def etrade_authorize(current_user: User = Depends(get_current_user)):
    from brokers.etrade_broker import ETradeBroker
    return ETradeBroker.get_oauth_url()


@router.get("/etrade/callback")
async def etrade_callback(oauth_token: str, oauth_verifier: str, current_user: User = Depends(get_current_user)):
    from brokers.etrade_broker import ETradeBroker
    tokens = ETradeBroker.exchange_token(oauth_token, oauth_verifier)
    return {"message": "E*TRADE connected", "tokens": tokens}


@router.get("/schwab/authorize")
async def schwab_authorize(current_user: User = Depends(get_current_user)):
    from brokers.schwab_broker import SchwabBroker
    return {"authorize_url": SchwabBroker.get_authorize_url()}


@router.get("/schwab/callback")
async def schwab_callback(code: str, current_user: User = Depends(get_current_user)):
    from brokers.schwab_broker import SchwabBroker
    tokens = await SchwabBroker.exchange_code(code)
    return {"message": "Schwab connected", "tokens": tokens}
