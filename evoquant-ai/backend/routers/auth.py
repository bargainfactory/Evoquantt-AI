from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from database import get_session
from models.user import User, UserCreate, UserRead
from security.audit import AuditLogger
from security.jwt_auth import create_access_token, create_refresh_token, verify_token, get_current_user
from security.totp import TOTPManager

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    request: Request,
    user_in: UserCreate,
    session: AsyncSession = Depends(get_session),
):
    existing = await session.scalars(select(User).where(User.email == user_in.email))
    if existing.first():
        raise HTTPException(status_code=400, detail="Email already registered")
    existing_un = await session.scalars(select(User).where(User.username == user_in.username))
    if existing_un.first():
        raise HTTPException(status_code=400, detail="Username already taken")

    user = User(
        email=user_in.email,
        username=user_in.username,
        full_name=user_in.full_name,
        hashed_password=hash_password(user_in.password),
    )
    session.add(user)
    await session.flush()

    al = AuditLogger(session)
    await al.log("register", "user", user_id=user.id, ip_address=request.client.host if request.client else None)
    return user


@router.post("/login")
async def login(
    request: Request,
    email: Annotated[str, Body()],
    password: Annotated[str, Body()],
    totp_code: Annotated[str | None, Body()] = None,
    session: AsyncSession = Depends(get_session),
):
    result = await session.scalars(select(User).where(User.email == email))
    user = result.first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")
    if user.totp_enabled:
        if not totp_code:
            raise HTTPException(status_code=428, detail="TOTP code required")
        if not TOTPManager.verify(user.totp_secret, totp_code):
            raise HTTPException(status_code=401, detail="Invalid TOTP code")

    user.last_login = datetime.utcnow()
    session.add(user)

    al = AuditLogger(session)
    await al.log("login", "user", user_id=user.id, ip_address=request.client.host if request.client else None)

    return {
        "access_token": create_access_token(user.id, {"email": user.email, "username": user.username}),
        "refresh_token": create_refresh_token(user.id),
        "token_type": "bearer",
        "user": UserRead.model_validate(user),
    }


@router.post("/refresh")
async def refresh_token(
    refresh_token: Annotated[str, Body()],
    session: AsyncSession = Depends(get_session),
):
    payload = verify_token(refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user_id = payload["sub"]
    return {
        "access_token": create_access_token(user_id),
        "token_type": "bearer",
    }


@router.post("/2fa/setup")
async def setup_2fa(current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    secret = TOTPManager.generate_secret()
    uri = TOTPManager.get_provisioning_uri(secret, current_user.email)
    qr_b64 = TOTPManager.get_qr_code_b64(uri)
    current_user.totp_secret = secret
    session.add(current_user)
    return {"secret": secret, "uri": uri, "qr_code": qr_b64}


@router.post("/2fa/confirm")
async def confirm_2fa(
    code: Annotated[str, Body()],
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if not TOTPManager.verify(current_user.totp_secret, code):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")
    backup_codes = TOTPManager.generate_backup_codes()
    import json
    current_user.totp_enabled = True
    current_user.totp_backup_codes = json.dumps(backup_codes)
    session.add(current_user)
    return {"message": "2FA enabled", "backup_codes": backup_codes}


@router.delete("/2fa/disable")
async def disable_2fa(
    code: Annotated[str, Body()],
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if not TOTPManager.verify(current_user.totp_secret, code):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")
    current_user.totp_enabled = False
    current_user.totp_secret = None
    current_user.totp_backup_codes = None
    session.add(current_user)
    return {"message": "2FA disabled"}


@router.get("/me", response_model=UserRead)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/logout")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    al = AuditLogger(session)
    await al.log("logout", "user", user_id=current_user.id, ip_address=request.client.host if request.client else None)
    return {"message": "Logged out successfully"}
