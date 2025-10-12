import logging
from typing import Optional
from bson import ObjectId
from pymongo.errors import PyMongoError
from app.core.db import AsyncDatabase
from app.core.schemas import UserProfile, UserAuth, UserRegistration, UserAuthOut
from app.core.exceptions import InternalServerError

logger = logging.getLogger(__name__)


async def find_user_by_username_email(
    db: AsyncDatabase, username: str, email: str
) -> Optional[UserAuthOut]:
    user_auth = await db.user_auth.find_one(
        {"$or": [{"username": username}, {"email": email}]}
    )
    if not user_auth:
        return None

    return UserAuthOut(**user_auth)


async def create_user(db: AsyncDatabase, user: UserRegistration) -> ObjectId:
    created = None
    try:
        user_data = UserAuth.model_validate(user.model_dump())
        created = await db.user_auth.insert_one(user_data.model_dump(exclude={"id"}))

        profile_data = UserProfile(
            auth_id=created.inserted_id, full_name=user.full_name
        )
        await db.user_profile.insert_one(profile_data.model_dump(exclude={"id"}))

        return created.inserted_id
    except PyMongoError as e:
        if created:
            await db.user_auth.delete_one({"_id": created.inserted_id})
        logger.critical(f"Failed to query db for user returning error: {e}")
        raise InternalServerError()


async def drop_user(db: AsyncDatabase, user_id: ObjectId) -> bool:
    try:
        await db.user_auth.delete_one({"_id": user_id})
        await db.user_profile.delete_one({"auth_id": user_id})
        return True

    except PyMongoError as e:
        logger.critical(f"Failed to query db for user returning error: {e}")
        raise InternalServerError()
