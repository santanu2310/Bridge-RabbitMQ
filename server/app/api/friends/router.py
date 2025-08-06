from bson import ObjectId
import logging
from typing import Annotated, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, status, Path, HTTPException, Body, Query
from pymongo import ReturnDocument

from app.core.schemas import (
    UserBrief,
    UserAuthOut,
    FriendRequestIn,
    FriendRequestDB,
    Friends_Status,
    FriendRequestOut,
    AddFriendMessage,
    FriendRequestMessage,
    SyncMessageType,
)

from app.core.db import AsyncDatabase, get_async_database
from app.api.user.services import get_full_user
from app.deps import get_user_from_access_token_http
from app.api.sync_socket.router import send_message

from .services import (
    create_friends,
    search_user,
    get_friends_list,
    are_friends,
    reject_friend_request,
    _get_friend,
)

router = APIRouter()

logger = logging.getLogger(__name__)


@router.get("/search")
async def search_potential_friend(
    q: Optional[str] = Query(
        None, description="Search user by username or display name"
    ),
    user: UserAuthOut = Depends(get_user_from_access_token_http),
    db: AsyncDatabase = Depends(get_async_database),
):
    if not q:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="query parameter 'q' can't be empty.",
        )
    users = await search_user(db=db, query=q, current_user_id=user.id)
    return users


@router.post("/make-request", status_code=201)
async def make_friend_request(
    request_data: Annotated[FriendRequestIn, Body()],
    user: UserAuthOut = Depends(get_user_from_access_token_http),
    db: AsyncDatabase = Depends(get_async_database),
):
    # Finding the requested user by username
    requested_user = await db.user_auth.find_one({"username": request_data.username})

    # If the user is not found return a 404 error
    if not requested_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User name not found"
        )

    # Check if the requested user is the same user making the request
    if requested_user["_id"] == user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="cannot make request to this username",
        )
    # Check if they are already friends
    if await are_friends(db, user.id, requested_user["_id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You are already friends"
        )

    # Check if the friend request already exist
    if await db.friend_request.find_one(
        {
            "sender_id": user.id,
            "receiver_id": requested_user["_id"],
            "status": Friends_Status.pending.value,
        }
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Friend request already exist"
        )

    # Creating a friend request
    request = FriendRequestDB(
        sender_id=ObjectId(user.id),
        receiver_id=requested_user["_id"],
        message=request_data.message,
    )

    # Inserting the request into the collection
    result = await db.friend_request.insert_one(
        request.model_dump(by_alias=True, exclude={"id"})
    )

    full_user = await get_full_user(db=db, user_id=request.sender_id)
    user_brief = UserBrief.model_validate(full_user.model_dump())

    message = FriendRequestMessage(
        type=SyncMessageType.friend_request,
        id=str(result.inserted_id),
        message=request.message,
        user=user_brief,
        status=Friends_Status.pending,
        created_time=request.created_at,
    )

    # Send the status update to the message sender
    await send_message(
        user_ids=[request.receiver_id],
        message_data=message,
    )

    return


@router.get("/get-requests")
async def list_friend_request(
    user: UserAuthOut = Depends(get_user_from_access_token_http),
    db: AsyncDatabase = Depends(get_async_database),
):
    data = []

    async for document in db.friend_request.find(
        {"receiver_id": user.id, "status": Friends_Status.pending.value}
    ):
        sender = await get_full_user(db, ObjectId(document["sender_id"]))
        sender_data = UserBrief.model_validate(sender.model_dump())

        request = FriendRequestOut(
            id=str(document["_id"]),
            user=sender_data,
            message=document["message"],
            status=document["status"],
            created_time=document["created_at"],
        )
        data.append(request)

    return data


@router.patch("/accept-request/{request_id}")
async def accept_friend_request(
    request_id: Annotated[str, Path(title="Id of the friend request to be accepted")],
    user: UserAuthOut = Depends(get_user_from_access_token_http),
    db: AsyncDatabase = Depends(get_async_database),
):
    f_request = await db.friend_request.find_one_and_update(
        {
            "_id": ObjectId(request_id),
            "receiver_id": user.id,
            "status": Friends_Status.pending.value,
        },
        {"$set": {"status": Friends_Status.accepted.value}},
        return_document=ReturnDocument.AFTER,
    )

    if f_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No friend request found."
        )

    friend_request = FriendRequestDB.model_validate(f_request)

    friend1_id, friend2_id = await create_friends(
        db, user1_id=friend_request.receiver_id, user2_id=friend_request.sender_id
    )

    freind_message = AddFriendMessage(freind_doc_id=friend2_id)
    await send_message(user_ids=[friend_request.sender_id], message_data=freind_message)

    return {"friendship_document_id": str(friend1_id)}


@router.patch("/reject-request/{request_id}")
async def reject_request(
    request_id: Annotated[str, Path(title="Id of the friend request to be accepted")],
    user: UserAuthOut = Depends(get_user_from_access_token_http),
    db: AsyncDatabase = Depends(get_async_database),
):
    return await reject_friend_request(
        db=db, id=ObjectId(request_id), receiver_id=user.id
    )


@router.get("/get-friends")
async def list_friends(
    user: UserAuthOut = Depends(get_user_from_access_token_http),
    updated_after: Optional[datetime] = Query(
        None,
        alias="updateAfter",
        description="Return only friends updated after this date (ISO 8601 format)",
    ),
    db: AsyncDatabase = Depends(get_async_database),
):
    friend_list = await get_friends_list(db, user.id, updated_after)
    return friend_list


@router.get("/ger-friend/{id}")
async def get_friend(
    id: Annotated[str, Path(title="Id of the friend document")],
    user: UserAuthOut = Depends(get_user_from_access_token_http),
    db: AsyncDatabase = Depends(get_async_database),
):
    return await _get_friend(db=db, user_id=user.id, friend_object_id=ObjectId(id))
