from bson import ObjectId
import logging
from aio_pika.abc import AbstractIncomingMessage
from pymongo.errors import PyMongoError
from app.core.config import settings
from app.api.sync_socket.router import send_message as send_sync_message
from app.core.schemas import (
    MessageEvent,
    FriendUpdateMessage,
    MessageStatusUpdate,
    Message,
    FriendRequestDB,
    UserBrief,
    FriendRequestMessage,
    SyncMessageType,
    BrodcastMessage,
    Message_Status,
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


# async def watch_user_updates():
#     client = create_async_client()
#     db = AsyncDatabase(client, settings.DATABASE_NAME)

#     async with db.user_profile.watch(
#         pipeline=[{"$match": {"operationType": "update"}}], full_document="updateLookup"
#     ) as stream:
#         async for change in stream:
#             try:
#                 # user_id = await db.user_profile.find_one({"_id": change['documentKey']['auth_id']})
#                 cursor = db.friends.find({"user_id": change["fullDocument"]["auth_id"]})

#                 # Extracting the `friends_id` values from each result document
#                 friend_ids = [doc["friend_id"] async for doc in cursor]

#                 # Sending the data to the online frinds
#                 data: dict[str:any] = change["updateDescription"]["updatedFields"]
#                 data["id"] = change["fullDocument"]["auth_id"]

#                 friend_update = FriendUpdateMessage.model_validate(data)
#                 await send_sync_message(friend_ids, friend_update)

#                 # updating the lastupdate fo friends data
#                 await db.friends.update_many(
#                     {"friend_id": change["fullDocument"]["auth_id"]},
#                     {"$set": {"update_at": change["wallTime"]}},
#                 )

#             except Exception as e:
#                 logger.error(f"Error processing user update : {e}")


@rabbit_consumer(
    topic_name=settings.TOPICS.online_status.value,
    exchange_name=settings.EXCHANGES.sync_message.value,
)
async def handle_online_status_update(
    message: AbstractIncomingMessage, db: AsyncDatabase
):
    await distribute_online_status_update(message=message, db=db)


@rabbit_consumer(
    topic_name=settings.TOPICS.message_status_update.value,
    exchange_name=settings.EXCHANGES.sync_message.value,
)
async def process_message_status_updates(
    message: AbstractIncomingMessage, db: AsyncDatabase
):
    """
    Processes message status updates and forwards them to relevant senders.

    This function:
    1. Decodes incoming message status updates
    2. Queries affected messages from database
    3. Groups messages by sender
    4. Forwards status updates to each sender

    Args:
        message: Incoming RabbitMQ message containing status update payload
        db: Async database connection
    """
    try:
        try:
            decoded_data = message.body.decode("utf-8")
            payload: MessageStatusUpdate = MessageStatusUpdate.model_validate_json(
                decoded_data
            )

            message_ids = [ObjectId(data.message_id) for data in payload.data]

        except (UnicodeDecodeError, ValueError) as e:
            logger.error(f"Failed to decode or validate message payload: {e}")
            return
        state = (
            "received_time"
            if payload.status == Message_Status.recieved.value
            else "seen_time"
        )

        try:
            cursor = db.message.find(
                {"_id": {"$in": message_ids}},
                projection={"sender_id": 1, state: 1},
            )
        except PyMongoError as e:
            logger.error(f"Database query failed: {e}")
            return

        sender_data: dict[str, list[dict[str, any]]] = {}
        try:
            async for db_message in cursor:
                sender_id = db_message["sender_id"]

                # Initialize sender list if not exists
                if sender_id not in sender_data:
                    sender_data[sender_id] = []

                # Skip messages without timestamp
                if db_message[state] is None:
                    logger.warning(f"Message {db_message['_id']} has null {state}")
                    continue

                # Add message data to sender's list
                sender_data[sender_id].append(
                    {"timestamp": db_message[state], "message_id": db_message["_id"]}
                )

        except PyMongoError as e:
            logger.error(f"Error iterating database cursor: {e}")
            return

        # send the data to the sender
        for sender_id, data in sender_data.items():
            try:
                data = [
                    MessageEvent(
                        message_id=str(msg["message_id"]), timestamp=msg["timestamp"]
                    )
                    for msg in data
                ]
                await send_sync_message(
                    user_ids=[sender_id],
                    message_data=MessageStatusUpdate(data=data, status=payload.status),
                )

            except Exception as e:
                logger.error(f"Failed to send status update to sender {sender_id}: {e}")

    except Exception as e:
        logger.error(
            f"Unexpected error in process_message_status_updates: {e}", exc_info=True
        )
    finally:
        # retry won't happen
        message.ack()


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
    await send_profilemedia_update_confirmation(data=message)


@rabbit_consumer(
    topic_name=settings.TOPICS.chat_broadcast_selected.value,
    exchange_name=settings.EXCHANGES.sync_message.value,
)
async def send_message_to_users(
    message: AbstractIncomingMessage,
):
    decoded_data = message.body.decode("utf-8")
    logger.info(f"{decoded_data=}")
    payload: BrodcastMessage = BrodcastMessage.model_validate_json(decoded_data)

    await send_sync_message(user_ids=payload.ids, message_data=payload.data)
