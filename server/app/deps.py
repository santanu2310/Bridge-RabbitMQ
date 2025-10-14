import jwt
import logging
from datetime import datetime
from typing import Annotated
from bson import ObjectId
from fastapi import HTTPException, status, Cookie, Depends, WebSocketException
from app.core.schemas import UserAuthOut
from app.core.config import settings
from app.core.db import (
    AsyncDatabase,
    get_async_database,
    get_async_database_from_socket,
)
from app.core.exceptions import EmailNotVerifiedError

logger = logging.getLogger(__name__)


async def get_user_from_refresh_token(
    refresh_token: Annotated[str, Cookie(alias="refresh_t")],
    db: AsyncDatabase = Depends(get_async_database),
) -> UserAuthOut:
    try:
        payload = jwt.decode(
            refresh_token,
            settings.JWT_REFRESH_SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )

        if datetime.fromtimestamp(payload["exp"]) < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await db.user_auth.find_one({"_id": ObjectId(payload["sub"])})

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Could not find user",
        )

    return UserAuthOut(**user)


async def _get_user_from_access_token(
    access_token: str,
    db: AsyncDatabase,
) -> UserAuthOut:
    try:
        payload = jwt.decode(
            access_token,
            settings.JWT_ACCESS_SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )

        if datetime.fromtimestamp(payload["exp"]) < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await db.user_auth.find_one({"_id": ObjectId(payload["sub"])})

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Could not find user",
        )

    return UserAuthOut(**user)


async def get_user_from_access_token_http(
    access_token: Annotated[str, Cookie(alias="access_t")],
    db: AsyncDatabase = Depends(get_async_database),
) -> UserAuthOut:
    return await _get_user_from_access_token(access_token=access_token, db=db)


async def get_verified_user(
    user: UserAuthOut = Depends(get_user_from_access_token_http),
) -> UserAuthOut:
    if not user.email_verified:
        raise EmailNotVerifiedError()

    return user


async def get_user_from_access_token_ws(
    access_token: Annotated[str, Cookie(alias="access_t")],
    db: AsyncDatabase = Depends(get_async_database_from_socket),
) -> UserAuthOut:
    user = await _get_user_from_access_token(access_token=access_token, db=db)
    if not user.email_verified:
        logger.error("raising socket exception for email not being verified")
        raise WebSocketException(code=4004, reason="email not verified")

    return user


__all__ = [
    "get_user_from_refresh_token",
    "get_user_from_access_token_http",
    "get_verified_user",
    "get_user_from_access_token_ws",
]
