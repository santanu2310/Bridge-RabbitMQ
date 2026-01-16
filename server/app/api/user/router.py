from bson import ObjectId
import jwt
import logging
from typing import Annotated
from datetime import timedelta, datetime, timezone
from fastapi import APIRouter, Body, HTTPException, status, Depends, Query, Cookie
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from redis.asyncio import Redis

from app.core.schemas import (
    UserRegistration,
    UserOut,
    UpdatableUserText,
    UserAuthOut,
    UpdatableUserImages,
    MediaType,
)
from app.utils import (
    verify_password,
    create_presigned_upload_url,
    create_presigned_download_url,
)
from app.background_tasks.celery.tasks import process_profile_media

from app.deps import (
    get_user_from_refresh_token,
    get_user_from_access_token_http,
    get_verified_user,
)
from app.core.db import get_async_database, AsyncDatabase, ReturnDocument
from app.core.config import settings
from app.core.redis import get_redis_conn, get_value, delete_key

from .services import (
    register_new_user,
    update_user_profile,
    create_access_token,
    create_refresh_token,
    get_full_user,
    email_verify_request,
    send_password_reset_otp,
    reset_password as _reset_password,
)

from .schemas import (
    EmailVerifyRequest,
    PasswordResetRequest,
    VerifyOtpRequest,
    PassResetOtpRequest,
)

router = APIRouter()

logger = logging.getLogger(__name__)


@router.post("/register")
async def user_register(
    user: UserRegistration = Body(...),
    db: AsyncDatabase = Depends(get_async_database),
    redis_client=Depends(get_redis_conn),
):
    created = await register_new_user(db=db, user=user, redis_client=redis_client)
    return JSONResponse(content=created, status_code=status.HTTP_201_CREATED)


@router.post("/otp")
async def request_otp(
    payload: VerifyOtpRequest = Body(...),
    db: AsyncDatabase = Depends(get_async_database),
    redis_client: Redis = Depends(get_redis_conn),
):
    req_status = await email_verify_request(
        user_id=ObjectId(payload.user_id), db=db, redis_client=redis_client
    )
    return JSONResponse(content=req_status, status_code=status.HTTP_200_OK)


@router.post("/verify-email")
async def verify_email(
    verify_request: EmailVerifyRequest = Body(...),
    db: AsyncDatabase = Depends(get_async_database),
    redis_client=Depends(get_redis_conn),
):
    stored_otp = await get_value(redis_conn=redis_client, key=verify_request.email)

    if not stored_otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP expired or not found. Please request a new one.",
        )
    if stored_otp != verify_request.otp:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Incorrect code",
        )

    updated_user = await db.user_auth.find_one_and_update(
        {"email": verify_request.email},
        {"$set": {"email_verified": True}},
        return_document=ReturnDocument.AFTER,
    )

    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wrong email address",
        )
    await delete_key(redis_conn=redis_client, key=verify_request.email)

    return {"message": "successfully verified email address"}


@router.post("/password/otp")
async def password_reset_opt_request(
    req_data: PassResetOtpRequest,
    db: AsyncDatabase = Depends(get_async_database),
    redis_client=Depends(get_redis_conn),
):
    return await send_password_reset_otp(
        email=req_data.email, redis_client=redis_client, db=db
    )


@router.post("/password/reset")
async def reset_password(
    req_data: PasswordResetRequest,
    db: AsyncDatabase = Depends(get_async_database),
    redis_client=Depends(get_redis_conn),
):
    return await _reset_password(req_data=req_data, db=db, redis_client=redis_client)


@router.post("/get-token")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: AsyncDatabase = Depends(get_async_database),
):
    user = await db.user_auth.find_one({"username": form_data.username})

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User name not found"
        )

    if not verify_password(user["password"], form_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user["_id"])}, expire_delta=access_token_expires
    )

    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token = create_refresh_token(
        data={"sub": str(user["_id"])}, expire_delta=refresh_token_expires
    )

    a_expires = datetime.now(timezone.utc) + access_token_expires
    r_expires = datetime.now(timezone.utc) + refresh_token_expires

    response = JSONResponse(content=None)
    response.set_cookie(
        key="access_t",
        value=access_token,
        httponly=False,
        expires=a_expires,
        samesite="lax",
    )

    response.set_cookie(
        key="refresh_t",
        value=refresh_token,
        httponly=True,
        expires=r_expires,
        samesite="lax",
    )

    return response


@router.get("/me")
async def get_me(
    user: UserOut = Depends(get_user_from_access_token_http),
    db: AsyncDatabase = Depends(get_async_database),
):
    user_data = await get_full_user(db=db, user_id=user.id)
    return user_data


@router.post("/refresh-token")
async def get_refresh_token(user: UserAuthOut = Depends(get_user_from_refresh_token)):
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expire_delta=access_token_expires
    )

    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token = create_refresh_token(
        data={"sub": str(user.id)}, expire_delta=refresh_token_expires
    )

    a_expires = datetime.now(timezone.utc) + access_token_expires
    r_expires = datetime.now(timezone.utc) + refresh_token_expires

    response = JSONResponse(content=None)
    response.set_cookie(
        key="access_t",
        value=access_token,
        httponly=False,
        expires=a_expires,
        samesite="lax",
    )

    response.set_cookie(
        key="refresh_t",
        value=refresh_token,
        httponly=True,
        expires=r_expires,
        samesite="lax",
    )

    return response


@router.post("/clear-token")
async def clear_tokens(
    refresh_token: Annotated[str, Cookie(alias="refresh_t")],
):
    payload = jwt.decode(
        refresh_token,
        settings.JWT_REFRESH_SECRET_KEY,
        algorithms=[settings.ALGORITHM],
    )

    logger.info(f"{payload=}")

    response = JSONResponse(content=None)
    response.delete_cookie(
        key="access_t",
        httponly=False,
        samesite="lax",
    )

    response.delete_cookie(
        key="refresh_t",
        httponly=True,
        samesite="lax",
    )

    return response


@router.patch("/update")
async def update_user_data(
    data: Annotated[UpdatableUserText, Body()],
    user: UserAuthOut = Depends(get_user_from_access_token_http),
    db: AsyncDatabase = Depends(get_async_database),
):
    return await update_user_profile(db, data, user.id)


@router.get("/upload-url")
async def get_presigned_post(
    user: UserAuthOut = Depends(get_verified_user),
):
    return create_presigned_upload_url()


@router.post("/add-profile-image")
async def add_user_image(
    data: Annotated[UpdatableUserImages, Body()],
    user: UserAuthOut = Depends(get_verified_user),
):
    if data.profile_picture_id is None and data.banner_picture_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nither profile_picture_id not banner_picture_id is provided",
        )

    if data.profile_picture_id:
        process_profile_media.delay(
            data.profile_picture_id, str(user.id), MediaType.profile_picture.value
        )
    else:
        process_profile_media.delay(
            data.banner_picture_id, str(user.id), MediaType.banner_picture.value
        )

    return JSONResponse(
        {"message": "Profile picture is being processed"},
        status_code=status.HTTP_202_ACCEPTED,
    )


@router.get("/download-url")
async def get_presigned_download(
    user: UserAuthOut = Depends(get_verified_user),
    key: str = Query(description="Key of the file"),
):
    return create_presigned_download_url(key)
