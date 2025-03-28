import json
import asyncio
import logging
from aiokafka import AIOKafkaConsumer  # type: ignore
from typing import List, Callable, Awaitable
from aio_pika import ExchangeType, connect_robust
from aio_pika.abc import (
    AbstractIncomingMessage,
    AbstractChannel,
    AbstractQueue,
    AbstractExchange,
)
from app.core.config import settings
from app.api.msg_socket.router import send_message
from app.api.sync_socket.router import send_message as send_sync_message
from app.core.schemas import (
    OnlineStatusMessage,
    MessageEvent,
    MessageStatusUpdate,
    MessageNoAlias,
    Message,
    FriendRequestDB,
    UserBrief,
    FriendRequestMessage,
    SyncMessageType,
    ProfileMediaUpdate,
)
from app.core.db import (
    AsyncDatabase,
    create_async_client,
)
from app.core.message_broker import rabbit_consumer
from app.api.msg_socket.services import get_user_form_conversation
from app.api.user.services import get_full_user
from .services import (
    distribute_online_status_update,
    send_profilemedia_update_confirmation,
)

logger = logging.getLogger(__name__)


async def on_message(message: AbstractIncomingMessage) -> None:
    async with message.process():
        print(f"[x] {message.body!r}")


# async def rabbit_consumer(
#     func: Callable[[AbstractIncomingMessage, AsyncDatabase | None], Awaitable[None]],
#     topic_name: str,
#     exchange_name: str,
#     db: AsyncDatabase,
# ) -> None:
#     """
#     Consumes messages from a RabbitMQ queue and processes each message using the provided function.

#     This function establishes a robust connection to RabbitMQ, creates a channel,
#     retrieves an exchange by name, declares an exclusive queue, binds the queue to the exchange using a specified routing key,
#     and iterates over incoming messages. Each message is processed by the provided asynchronous function `func`,
#     with error handling in place.

#     Parameters:
#         func (Callable[[AbstractIncomingMessage, AsyncDatabase | None], Awaitable[None]]):
#             An asynchronous callback function to process each incoming message.
#         topic_name (str): The routing key used for binding the queue to the exchange.
#         exchange_name (str): The name of the exchange from which messages are consumed.
#         db (AsyncDatabase): The database instance to be passed to the processing function.

#     Returns:
#         None
#     """
#     connection = await connect_robust(url=settings.CELERY_BROKER_URL)

#     async with connection:
#         channel: AbstractChannel = await connection.channel()
#         await channel.set_qos(prefetch_count=5)

#         exchange: AbstractExchange = await channel.get_exchange(name=exchange_name)

#         queue: AbstractQueue = await channel.declare_queue(exclusive=True)

#         await queue.bind(exchange, routing_key=topic_name)
#         logger.critical("waiting for message in queue")

#         async with queue.iterator() as queue_iter:
#             async for message in queue_iter:
#                 async with message.process():
#                     try:
#                         await func(message, db)
#                     except Exception as e:
#                         logger.error(
#                             f"Error processing {topic_name} message, {message=} error : {e}"
#                         )


async def watch_user_updates():
    client = create_async_client()
    db = AsyncDatabase(client, settings.DATABASE_NAME)

    async with db.user_profile.watch(
        pipeline=[{"$match": {"operationType": "update"}}]
    ) as stream:
        async for change in stream:
            try:
                cursor = db.friends.find({"_id": change["documentKey"]["_id"]})

                # Extracting the `friends_id` values from each result document
                friends_ids = [doc["friends_id"] async for doc in cursor]

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
                print(f"Error processing user update : {e}")


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


async def distribute_published_messages():
    while True:
        consumer = AIOKafkaConsumer(
            settings.KAFKA_TOPICS.message.value,
            bootstrap_servers=settings.KAFKA_CONNECTION,
        )

        try:
            await consumer.start()
            client = create_async_client()
            db = AsyncDatabase(client, settings.DATABASE_NAME)

            # Asyncronous Loop for iterating over the available messages
            async for msg in consumer:
                # Decoding the received data
                data = json.loads(msg.value.decode("utf-8"))
                message_alias = MessageNoAlias(**data)
                message = Message.model_validate(
                    message_alias.model_dump(by_alias=True)
                )

                # Send the message back to sender with all data
                await send_message(user_id=message.sender_id, message_data=message)

                # Getting the receiver's ID
                receiver_id = await get_user_form_conversation(
                    db, message.conversation_id, message.sender_id
                )

                # Sending the message to receiver
                await send_message(user_id=receiver_id, message_data=message)

        except json.JSONDecodeError as e:
            print("Error decoding the kafka message : ", e)
        except Exception as e:
            print("Error in kafka consumer : ", e)

        finally:
            await consumer.stop()
            print("Reconnecting in 5 sec")
            await asyncio.sleep(5)


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
