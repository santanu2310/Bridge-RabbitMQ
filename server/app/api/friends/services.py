import logging
from bson import ObjectId
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from fastapi import HTTPException, status
from app.core.schemas import Friends, Friends_Status, UserOut
from app.core.db import AsyncDatabase
from app.api.user.services import get_full_user
from app.utils import create_presigned_download_url

from .pipelines import search_user_by_name
from .schemas import UserBrief

logger = logging.getLogger(__name__)


async def are_friends(
    db: AsyncDatabase, user_id: ObjectId, friend_id: ObjectId
) -> bool:
    friend = await db.friends.find_one({"user_id": user_id, "friend_id": friend_id})
    if not friend:
        return False
    return True


async def search_user(
    db: AsyncDatabase, query: str, current_user_id: ObjectId
) -> list[UserBrief]:
    try:
        cursor = db.user_profile.aggregate(
            search_user_by_name(name=query, user_id=current_user_id)
        )

        users = await cursor.to_list(length=None)
        processed_user = []

        for user in users:
            if (
                user["friend_status"] != Friends_Status.accepted
                and user["id"] != current_user_id
            ):
                user_brief = UserBrief(**user)
                user_brief.profile_picture = create_presigned_download_url(
                    user_brief.profile_picture
                )
                processed_user.append(user_brief)

        return processed_user

    except Exception as e:
        logger.critical(f"Internal Error : {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="error fetching users list",
        )


async def create_friends(
    db: AsyncDatabase, user1_id: ObjectId, user2_id: ObjectId
) -> Tuple[ObjectId, ObjectId]:
    """
    This function creates two friend document one for each user and other user as friend.

    Input:
        db -> AsyncDatabase (database instance)
        user1_id, user2_id -> ObjectId (id of user)

    Output: friend_document_id as ObjectId where user2 is friend
    """

    friend_for_1 = Friends(user_id=user1_id, friend_id=user2_id)
    friend_for_2 = Friends(user_id=user2_id, friend_id=user1_id)

    if await are_friends(db, user1_id, user2_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You are already friends"
        )

    friend1 = await db.friends.insert_one(friend_for_1.model_dump(exclude={"id"}))
    friend2 = await db.friends.insert_one(friend_for_2.model_dump(exclude={"id"}))

    return friend1.inserted_id, friend2.inserted_id


async def get_friends_list(
    db: AsyncDatabase, id: ObjectId, updated_after: Optional[datetime] = None
) -> List[UserOut]:
    """
    This function gets the merged data of user_auth and user_profile from the database and return list of UserOut

    Input:
        db -> AsyncDatabase instance
        id -> User ID as ObjectId
        updated_after -> datetime Optional
    """
    # Pipeline to get users from user_id in friends collection
    pipeline: List[Dict[str, Any]] = [
        {"$match": {"user_id": id}},
        {"$addFields": {"friendsObjectId": {"$toObjectId": "$friend_id"}}},
        {
            "$lookup": {
                "from": "user_profile",
                "localField": "friendsObjectId",
                "foreignField": "auth_id",
                "as": "profile",
            }
        },
        {"$unwind": "$profile"},
        {
            "$lookup": {
                "from": "user_auth",
                "localField": "friendsObjectId",
                "foreignField": "_id",
                "as": "auth",
            }
        },
        {"$unwind": "$auth"},
        {"$addFields": {"mergedData": {"$mergeObjects": ["$profile", "$auth"]}}},
        {"$sort": {"profile.firstname": 1}},
        {"$replaceRoot": {"newRoot": "$mergedData"}},
    ]

    if updated_after:
        pipeline[0]["$match"]["update_at"] = {"$gt": updated_after}

    try:
        cursor = db.friends.aggregate(pipeline)
        friends = await cursor.to_list(length=None)

        friends_list: List[UserOut] = []

        for user in friends:
            user_out = UserOut(**user)
            user_out.profile_picture = create_presigned_download_url(
                user_out.profile_picture
            )
            user_out.banner_picture = create_presigned_download_url(
                user_out.banner_picture
            )

            friends_list.append(user_out)
        return friends_list

    except Exception as e:
        logger.critical(f"Internal Server Error : {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="error fetching users list",
        )


async def reject_friend_request(db: AsyncDatabase, id: ObjectId, receiver_id: ObjectId):
    """
    This function set the freind request status to rejected

    Input:
        db -> AsyncDatabase instance
        id -> Friend Request ID as ObjectId
        receiver_id -> User's id who receive the request
    """

    friend_request = await db.friend_request.find_one_and_update(
        {"_id": id, "receiver_id": receiver_id, "status": Friends_Status.pending.value},
        {"$set": {"status": Friends_Status.rejected.value}},
    )

    if not friend_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Friend request not found."
        )

    return {"message": "Friend request rejected successfully."}


async def _get_friend(
    db: AsyncDatabase, user_id: ObjectId, friend_object_id: ObjectId
) -> UserOut:
    """
    Thid function checks if the users are friends and return the friend details.

    Input:
        db -> database instance.
        user_id -> Id of the user requesting.
        friend_id -> Id of the friend whose data is being requested.
    """
    friend_doc = await db.friends.find_one(
        {"_id": friend_object_id, "user_id": user_id}
    )
    if not friend_doc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You don't have friend with friend_id {friend_object_id}",
        )

    return await get_full_user(db=db, user_id=friend_doc["friend_id"])
