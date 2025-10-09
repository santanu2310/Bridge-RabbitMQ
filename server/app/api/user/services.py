import jwt
import random
import asyncio
import logging
from bson import ObjectId
from datetime import datetime, timedelta
from typing import Dict, Any, List
from fastapi import status
from fastapi.exceptions import HTTPException
from pymongo import ReturnDocument
from redis.asyncio import Redis
from app.utils import hash_password
from app.background_tasks.celery.tasks import send_email
from app.core.db import AsyncDatabase
from app.core.schemas import (
    UserProfile,
    UserRegistration,
    UpdatableUserText,
    UserOut,
)
from app.core.config import settings
from app.core.redis import set_key_value
from app.core.exceptions import UserAlreadyExistsError, InternalServerError
from .repository import find_user_by_username_email, create_user, drop_user


logger = logging.getLogger(__name__)


async def register_new_user(
    db: AsyncDatabase, user: UserRegistration, redis_client: Redis
):
    if await find_user_by_username_email(
        db=db, username=user.username, email=user.email
    ):
        raise UserAlreadyExistsError()

    created_user = None
    try:
        user.password = await asyncio.to_thread(hash_password, user.password)
        created_user = await create_user(db, user)

        otp = await create_and_store_otp(redis_conn=redis_client, email=user.email)
        await asyncio.to_thread(send_email.delay, email=user.email, otp=otp)

        return created_user
    except Exception as e:
        logger.critical(f"Unexpected error occur e: {e}")

        if created_user:
            logger.info(f"Attempting to roll back creation of user {created_user}")
            await drop_user(db=db, user_id=created_user)
        raise InternalServerError()


async def get_full_user(db: AsyncDatabase, user_id: ObjectId) -> UserOut:
    pipeline: List[Dict[str, Any]] = [
        # Match the user_auth document by its _id (or another unique identifier)
        {"$match": {"_id": user_id}},
        # Lookup the profile document from the user_profile collection
        {
            "$lookup": {
                "from": "user_profile",
                "localField": "_id",  # _id from user_auth
                "foreignField": "auth_id",  # user_id in user_profile
                "as": "profile",
            }
        },
        # Unwind the profile array (if profile doesn't exist, preserve the original document)
        {"$unwind": {"path": "$profile", "preserveNullAndEmptyArrays": True}},
        # Merge the original user_auth document with the profile document
        {"$replaceRoot": {"newRoot": {"$mergeObjects": ["$profile", "$$ROOT"]}}},
    ]

    cursor = db.user_auth.aggregate(pipeline=pipeline)
    user_response = await cursor.to_list(length=1)

    if not user_response:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return UserOut.model_validate(user_response[0])


async def update_user_profile(
    db: AsyncDatabase, data: UpdatableUserText, user_id: ObjectId
):
    cleaned_data = data.model_dump(exclude_none=True, exclude={"created_at"})
    if not cleaned_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No data to update"
        )

    user_data = await db.user_profile.find_one_and_update(
        {"auth_id": ObjectId(user_id)},
        update={"$set": cleaned_data},
        return_document=ReturnDocument.AFTER,
    )

    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User details not found"
        )

    return UserProfile(**user_data)


def create_access_token(data: dict, expire_delta: timedelta | None = None):
    to_encode = data.copy()

    if expire_delta:
        expire = datetime.utcnow() + expire_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=3)

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode, key=settings.JWT_ACCESS_SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(data: dict, expire_delta: timedelta | None = None):
    to_encode = data.copy()

    if expire_delta:
        expire = datetime.utcnow() + expire_delta
    else:
        expire = datetime.utcnow() + timedelta(days=7)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, key=settings.JWT_REFRESH_SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


async def create_and_store_otp(redis_conn: Redis, email: str) -> str:
    """
    Generates a 6-digit OTP and stores it in Redis with the user's email as the key.
    The OTP expires in 10 minutes.
    """
    otp = "".join([str(random.randint(0, 9)) for _ in range(6)])

    await set_key_value(
        redis_conn=redis_conn, key=email, value=otp, ex=600
    )  # Expires in 600 seconds (10 minutes)
    return otp
