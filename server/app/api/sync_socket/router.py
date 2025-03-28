from bson import ObjectId
import logging
from typing import Literal, List, Dict
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pymongo import UpdateOne
from app.core.schemas import (
    SyncSocketMessage,
    SyncPacket,
    PacketType,
    SyncMessageType,
    MessageStatusUpdate,
    Message_Status,
    UserAuthOut,
)
from app.deps import get_user_from_access_token_ws
from app.core.config import settings
from app.core.db import AsyncDatabase, get_async_database_from_socket
from app.core.message_broker import (
    publish_message,
    AbstractRobustConnection,
    get_rabbit_connection,
)

router = APIRouter()
logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connection: Dict[ObjectId, WebSocket] = {}

    async def connect(
        self,
        user_id: ObjectId,
        websocket: WebSocket,
        connection: AbstractRobustConnection,
    ):
        await websocket.accept()
        self.active_connection[user_id] = websocket
        await notify_online_status(connection, user_id, "online")

    async def disconnect(self, user_id: ObjectId, connection: AbstractRobustConnection):
        if user_id in self.active_connection:
            del self.active_connection[user_id]
            await notify_online_status(connection, user_id, "offline")

    def is_online(self, user_id: ObjectId):
        return user_id in self.active_connection

    async def send_personal_message(self, user_id: ObjectId, message: SyncPacket):
        if self.active_connection[user_id]:
            await self.active_connection[user_id].send_text(message.model_dump_json())


connections = ConnectionManager()


@router.websocket("/")
async def websocket_endpoint(
    websocket: WebSocket,
    user: UserAuthOut = Depends(get_user_from_access_token_ws),
    db: AsyncDatabase = Depends(get_async_database_from_socket),
    queue_connection: AbstractRobustConnection = Depends(get_rabbit_connection),
):
    await connections.connect(user.id, websocket, queue_connection)

    try:
        while True:
            data = await websocket.receive_text()
            packet: SyncPacket = SyncPacket.model_validate_json(data)
            if packet.type == PacketType.ping:
                await connections.send_personal_message(
                    user_id=user.id, message=SyncPacket(type=PacketType.pong)
                )
            elif packet.type == PacketType.message and packet.data:
                await handle_recieved_message(db, user_id=user.id, message=packet.data)

    except WebSocketDisconnect:
        await connections.disconnect(user.id, queue_connection)
    return


async def handle_recieved_message(
    db: AsyncDatabase, user_id: ObjectId, message: SyncSocketMessage
):
    print(f"{message=}")
    if message.type == SyncMessageType.message_status:
        try:
            # Parse the incoming message data into a structured model
            message = MessageStatusUpdate.model_validate(message.model_dump())
            message_status = message.status.value

            # Determine the correct field to update in the database
            time_field = (
                "seen_time"
                if message_status == Message_Status.seen
                else "received_time"
            )
            # Prepare bulk update operations for each message in the update list
            updates = [
                UpdateOne(
                    {"_id": ObjectId(obj.message_id), time_field: None},
                    {
                        "$set": {
                            "status": message_status,
                            time_field: obj.timestamp,
                        }
                    },
                )
                for obj in message.data
            ]

            # Only proceed with the database update if there are updates to make
            if updates:
                await db.message.bulk_write(updates)
        except Exception as e:
            print(e)


async def send_message(user_ids: List[ObjectId], message_data: SyncSocketMessage):
    """
    Send message to list of users IDs if online

    Args:
        user_ids : List of IDs to send the message to.
        message_data : The message to send.
    """

    try:
        for user_id in user_ids:
            if connections.is_online(user_id):
                data_packet = SyncPacket(type=PacketType.message, data=message_data)

                await connections.send_personal_message(user_id, data_packet)
    except Exception as e:
        print(e)


async def notify_online_status(
    connection: AbstractRobustConnection,
    user_id: ObjectId,
    is_online: Literal["online", "offline"],
):
    data = {"user_id": str(user_id), "status": is_online}
    await publish_message(
        connection=connection,
        exchange_name=settings.EXCHANGES.sync_message.value,
        topic=settings.TOPICS.online_status.value,
        data=data,
    )
