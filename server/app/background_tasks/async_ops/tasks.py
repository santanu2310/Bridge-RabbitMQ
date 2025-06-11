import logging
from aio_pika.abc import AbstractIncomingMessage
from app.core.config import settings
from app.api.sync_socket.router import send_message as send_sync_message
from app.core.schemas import (
    MessageEvent,
    MessageStatusUpdate,
    Message,
    FriendRequestDB,
    UserBrief,
    FriendRequestMessage,
    SyncMessageType,
)
from app.core.db import (
    AsyncDatabase,
    create_async_client,
)
from app.core.message_broker import rabbit_consumer
from app.api.user.services import get_full_user
from .services import (
    distribute_online_status_update,
    send_profilemedia_update_confirmation,
    _distribute_published_messages,
)

logger = logging.getLogger(__name__)


async def watch_user_updates():
    client = create_async_client()
    db = AsyncDatabase(client, settings.DATABASE_NAME)

    async with db.user_profile.watch(
        pipeline=[{"$match": {"operationType": "update"}}], full_document="updateLookup"
    ) as stream:
        async for change in stream:
            try:
                # user_id = await db.user_profile.find_one({"_id": change['documentKey']['auth_id']})
                cursor = db.friends.find({"user_id": change["fullDocument"]["auth_id"]})

                # Extracting the `friends_id` values from each result document
                friends_ids = [doc["friend_id"] async for doc in cursor]

                logger.critical(f"{friends_ids=}")
                # Sending the data to the online frinds
                await send_sync_message(
                    friends_ids, change["updateDescription"]["updatedFields"]
                )

                # updating the lastupdate fo friends data
                await db.friends.update_many(
                    {"friends_id": change["documentKey"]["_id"]},
                    {"$set": {"update_at": change["wallTime"]}},
                )

            except Exception as e:
                logger.error(f"Error processing user update : {e}")


@rabbit_consumer(
    topic_name=settings.TOPICS.online_status.value,
    exchange_name=settings.EXCHANGES.sync_message.value,
)
async def handle_online_status_update(
    message: AbstractIncomingMessage, db: AsyncDatabase
):
    await distribute_online_status_update(message=message, db=db)


async def watch_message_updates():
    """
    Watches for updates in the MessageCollection and sends message status updates
    to the sender when the message status changes.
    """

    client = create_async_client()
    db = AsyncDatabase(client, settings.DATABASE_NAME)

    async with db.message.watch(
        pipeline=[{"$match": {"operationType": "update"}}],
        full_document="updateLookup",
    ) as stream:
        async for change in stream:
            try:
                if not change["updateDescription"]["updatedFields"]["status"]:
                    continue

                message_id = change["documentKey"]["_id"]
                updated_field = change["updateDescription"]["updatedFields"]
                status = change["updateDescription"]["updatedFields"]["status"]

                # Get the timestamp of the update
                timestamp = next(iter(updated_field.values()))

                # Fetch the updated message from the database
                message = Message.model_validate(change["fullDocument"])

                # Construct a MessageEvent Object
                message_event = MessageEvent(
                    message_id=str(message_id), timestamp=timestamp
                )

                # Create a MessageStatusUpdate object to send to the user
                sync_message = MessageStatusUpdate(
                    data=[message_event],
                    status=status,
                )

                # Send the status update to the message sender
                await send_sync_message(
                    user_ids=[message.sender_id], message_data=sync_message
                )

            except Exception as e:
                print(f"Error processing user update(line:147) : {e}")


@rabbit_consumer(
    topic_name=settings.TOPICS.message.value,
    exchange_name=settings.EXCHANGES.sync_message.value,
)
async def distribute_published_messages(
    message: AbstractIncomingMessage, db: AsyncDatabase
):
    await _distribute_published_messages(data=message, db=db)


async def watch_friend_requests():
    """
    Watches for updates in the MessageCollection and sends message status updates
    to the sender when the message status changes.
    """
    # I don't think this task i really necessary message can be directly send from the router function
    client = create_async_client()
    db = AsyncDatabase(client, settings.DATABASE_NAME)

    try:
        async with db.friend_request.watch(
            pipeline=[{"$match": {"operationType": "insert"}}],
            full_document="updateLookup",
        ) as stream:
            async for change in stream:
                try:
                    friend_request = FriendRequestDB.model_validate(
                        change["fullDocument"]
                    )

                    full_user = await get_full_user(
                        db=db, user_id=friend_request.sender_id
                    )
                    user_brief = UserBrief.model_validate(full_user.model_dump())

                    message = FriendRequestMessage(
                        type=SyncMessageType.friend_request,
                        id=str(friend_request.id),
                        message=friend_request.message,
                        user=user_brief,
                        status=friend_request.status,
                        created_time=friend_request.created_at,
                    )

                    # Send the status update to the message sender
                    await send_sync_message(
                        user_ids=[friend_request.receiver_id],
                        message_data=message,
                    )

                except Exception as e:
                    print(f"Error processing user update : {e}")
    finally:
        client.close()


@rabbit_consumer(
    topic_name=settings.TOPICS.media_update.value,
    exchange_name=settings.EXCHANGES.task_updates.value,
)
async def profile_media_update_confirmation(
    message: AbstractIncomingMessage,
):
    logger.error(f"{message=}")
    await send_profilemedia_update_confirmation(data=message)
