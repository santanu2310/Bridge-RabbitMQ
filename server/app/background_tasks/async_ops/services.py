import json
from typing import List
import logging
from bson import ObjectId
from aio_pika.abc import AbstractIncomingMessage
from app.core.db import AsyncDatabase
from app.core.schemas import OnlineStatusMessage, ProfileMediaUpdate
from app.api.sync_socket.router import send_message as send_sync_message

logger = logging.getLogger(__name__)


async def distribute_online_status_update(
    message: AbstractIncomingMessage, db: AsyncDatabase
) -> None:
    data = json.loads(message.body.decode("utf-8"))
    user_id = data["user_id"]
    user_list: List[ObjectId] = []

    logger.info(f"{data=}")
    # Retrive the conversations with the user
    async for document in db.conversation.find(
        {"participants": {"$all": [ObjectId(user_id)]}}
    ):
        # Add the firend id to the list
        user_list.extend(
            ObjectId(userid)
            for userid in document["participants"]
            if str(userid) != user_id
        )

    # Prepare the date and sending it to the list of user
    msg_data = OnlineStatusMessage(user_id=user_id, status=data["status"])
    await send_sync_message(user_ids=user_list, message_data=msg_data)


async def send_profilemedia_update_confirmation(
    data: AbstractIncomingMessage, *args, **kwargs
):
    decoded_data = json.loads(data.body.decode("utf-8"))
    message = ProfileMediaUpdate.model_validate_json(decoded_data)

    await send_sync_message(user_ids=[message.user_id], message_data=message)
