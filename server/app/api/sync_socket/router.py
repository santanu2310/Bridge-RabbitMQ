from datetime import datetime
from bson import ObjectId
import logging
from typing import Literal, List, Dict, Annotated
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Path
from pymongo import UpdateOne
from app.core.schemas import (
    SyncSocketMessage,
    SyncPacket,
    PacketType,
    SyncMessageType,
    MessageStatusUpdate,
    Message_Status,
    UserAuthOut,
    WebRTCOffer,
    WebRTCAnswer,
    WebRTCIceCandidate,
    CallStatus,
    CallEndedPayLoad,
    CallStatusUpdate,
)
from app.deps import get_user_from_access_token_ws, get_user_from_access_token_http
from app.core.config import settings
from app.core.db import (
    AsyncDatabase,
    get_async_database_from_socket,
    get_async_database,
)
from app.core.message_broker import (
    publish_message,
    AbstractRobustConnection,
    get_rabbit_connection,
)
from .services import (
    create_call,
    process_call_reception,
    process_call_end,
    get_call_record,
    list_call_record,
)

router = APIRouter()
logger = logging.getLogger(__name__)


# TODO:This way of handling websocket objects will fail if a user connect from two different devices
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

    except WebSocketDisconnect as e:
        logger.error(e)
        await connections.disconnect(user.id, queue_connection)
    return


async def handle_recieved_message(
    db: AsyncDatabase, user_id: ObjectId, message: SyncSocketMessage
):
    if message.type == SyncMessageType.message_status:
        try:
            # Parse the incoming message data into a structured model
            msg: MessageStatusUpdate = MessageStatusUpdate.model_validate(
                message.model_dump()
            )
            message_status = msg.status.value

            # Determine the correct field to update in the database
            time_field = (
                "seen_time"
                if message_status == Message_Status.seen
                else "received_time"
            )
            # Prepare bulk update operations for each message in the update list
            updates = [
                UpdateOne(
                    {
                        "_id": ObjectId(obj.message_id),
                        time_field: None,
                        "sender_id": {"$ne": user_id},
                    },
                    {
                        "$set": {
                            "status": message_status,
                            time_field: obj.timestamp,
                        }
                    },
                )
                for obj in msg.data
            ]

            if updates:
                await db.message.bulk_write(updates)
        except Exception as e:
            logger.critical(e)

    # Handle WebRTC "offer" message (incoming call offer)
    elif message.type == "offer":
        offer: WebRTCOffer = message

        # Set default call status
        call_status = CallStatus.CALLING
        # If receiver is online, mark the call as ringing
        if connections.is_online(ObjectId(offer.receiver_id)):
            call_status = CallStatus.RINGING

        # Create the call record and get the initial status update
        call_status_update: CallStatusUpdate = await create_call(
            call_offer=offer, call_status=call_status, db=db
        )

        # Notify the caller with the call status
        await send_message(user_ids=[user_id], message_data=call_status_update)

        # Attach call ID to offer and send it to the receiver
        offer.call_id = call_status_update.call_id
        await send_message(user_ids=[ObjectId(offer.receiver_id)], message_data=offer)

    # Handle WebRTC "answer" message (receiver accepted the call)
    elif message.type == "answer":
        answer: WebRTCAnswer = message
        # Update call and participant status to "accepted" and "joined"
        call_status_update = await process_call_reception(
            payload=answer,
            db=db,
        )

        # send caller the answer
        await send_message(user_ids=[answer.receiver_id], message_data=answer)
        # Notify callee of the accepted status (mainly for timestamp)
        await send_message(user_ids=[answer.sender_id], message_data=call_status_update)

    # Handle "ice-candidate" message (for peer connection negotiation)
    elif message.type == "ice-candidate":
        ice_candidate: WebRTCIceCandidate = message

        # Forward the ICE candidate to the other peer
        await send_message(
            user_ids=[ObjectId(ice_candidate.receiver_id)], message_data=ice_candidate
        )

    # Handle user-initiated hangup
    elif message.type == "user_hangup":
        hangup_payload: CallEndedPayLoad = message

        # Update the database and retrive the other participant's ID
        participant_id = await process_call_end(
            user_id=user_id, payload=hangup_payload, db=db
        )

        # Notify both user that the call has ended
        user_ids = [user_id]
        if participant_id:
            user_ids.append(participant_id)
        await send_message(user_ids=user_ids, message_data=hangup_payload)


async def send_message(user_ids: List[ObjectId], message_data: SyncSocketMessage):
    """
    Send message to list of users IDs if online

    Args:
        user_ids : List of IDs to send the message to.
        message_data : The message to send.
    """

    try:
        # logger.error(user_ids)
        for user_id in user_ids:
            # logger.error(f"{message_data.model_dump_json()=}")
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


@router.get("call-log/{call_id}")
async def getCallLog(
    call_id: Annotated[str, Path(title="Call ID")],
    user: UserAuthOut = Depends(get_user_from_access_token_http),
    db: AsyncDatabase = Depends(get_async_database),
):
    call_record = await get_call_record(call_id=ObjectId(call_id), db=db)
    return call_record


@router.get("call-log/{date_after}")
async def getCallLogs(
    date_after: Annotated[datetime, Path(title="Call ID")],
    user: UserAuthOut = Depends(get_user_from_access_token_http),
    db: AsyncDatabase = Depends(get_async_database),
):
    call_record = await list_call_record(user_id=user.id, date_after=date_after, db=db)
    return call_record
