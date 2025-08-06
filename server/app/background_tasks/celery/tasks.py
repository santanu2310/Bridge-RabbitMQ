import logging
from bson import ObjectId
from datetime import datetime, timezone
from pymongo import ReturnDocument
from pymongo.errors import ServerSelectionTimeoutError, NetworkTimeout
from pika.exceptions import AMQPConnectionError, ConnectionClosed
from app.background_tasks.celery.dependency import get_dependency_manager, Dependency
from app.core.config import create_celery_client, settings
from app.core.message_broker import publish_bloking_message
from app.core.schemas import (
    MediaType,
    Message,
    ProfileMediaUpdate,
    UserProfile,
    FriendUpdateMessage,
    BrodcastMessage,
)
from app.utils import get_file_extension
from botocore.exceptions import ClientError, NoCredentialsError  # type: ignore

from .services import process_image_to_aspect
from .utils import list_friends_id

celery_app = create_celery_client()


logger = logging.getLogger(__name__)
logging.basicConfig(level="DEBUG")


@celery_app.task(
    autoretry_for=(
        ClientError,
        ServerSelectionTimeoutError,
        NetworkTimeout,
        AMQPConnectionError,
        ConnectionClosed,
        ConnectionError,
    ),
    retry_kwargs={"max_retries": 3, "countdown": 60},
)
def process_media_message(message_id: str):
    dep_manager = get_dependency_manager()
    try:
        with dep_manager.get_dependency_context(Dependency.db) as db:
            # Getting the message from message from id and maping it
            message_response = db.message.find_one({"_id": ObjectId(message_id)})
            if not message_response:
                logger.error(f"Message not found for id: {message_id}")
                return

            message = Message.model_validate(message_response)
            if not message.attachment:
                logger.error(f"No attachment found in db for the msg_id: {message_id}")
                return

        with dep_manager.get_dependency_context(Dependency.s3_client) as s3:
            # Generating the key
            present_time = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
            key = "attachment/Bridge_Atachment_" + present_time

            # Transfereing the data
            s3.copy_object(
                Bucket=settings.BUCKET_NAME,
                CopySource={
                    "Bucket": settings.BUCKET_NAME,
                    "Key": message.attachment.temp_file_id,
                },
                Key=key,
            )

            # Geting the file
            size = s3.head_object(
                Bucket=settings.BUCKET_NAME,
                Key=key,
            ).get("ContentLength", 0)

        # Updating the message data related to attachment
        message.attachment.name = (
            "Bridge_Atachment "
            + present_time
            + "."
            + get_file_extension(message.attachment.name)
        )
        message.attachment.size = size
        message.attachment.key = key

        with dep_manager.get_dependency_context(Dependency.db) as db:
            # Updating the message in database
            db.message.update_one(
                {"_id": message.id},
                {"$set": {"attachment": message.attachment.model_dump()}},
            )

            # Update the conversation last_message_date
            db.conversation.find_one_and_update(
                {"_id": message.conversation_id},
                {
                    "$set": {"last_message_date": message.sending_time},
                },
            )

        with dep_manager.get_dependency_context(Dependency.queue) as queue:
            data = message.model_dump_json(by_alias=True)
            publish_bloking_message(
                connection=queue,
                exchange_name=settings.EXCHANGES.sync_message.value,
                topic=settings.TOPICS.message.value,
                data=data,
            )
    except Exception as e:
        logger.exception(f"Task failed for message {message_id}: {e}")

        # Reset connections based on exception type
        if isinstance(e, (ServerSelectionTimeoutError, NetworkTimeout)):
            logger.warning("Resetting database connection due to error")
            dep_manager.reset_connection(Dependency.db)

        elif isinstance(e, (AMQPConnectionError, ConnectionClosed)):
            logger.warning("Resetting queue connection due to error")
            dep_manager.reset_connection(Dependency.queue)

        elif isinstance(e, (ClientError, NoCredentialsError)):
            logger.warning("Resetting S3 connection due to error")
            dep_manager.reset_connection(Dependency.s3_client)

        raise


@celery_app.task
def process_profile_media(file_id: str, user_id: str, media_type: str):
    dep_manager = get_dependency_manager()

    try:
        with dep_manager.get_dependency_context(Dependency.s3_client) as s3:
            # Getting the image from S3
            obj = s3.get_object(
                Bucket=settings.BUCKET_NAME,
                Key=file_id,
            )
        image_data = obj["Body"].read()

        target_size = (0, 0)
        if media_type == MediaType.profile_picture.value:
            target_size = (480, 480)
        elif media_type == MediaType.banner_picture.value:
            target_size = (855, 360)
        else:
            logger.critical(f"Invalid media_type : {media_type}")
            return

        output_buffer = process_image_to_aspect(
            image_data=image_data, target_size=target_size
        )

        present_time = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        new_key = f"{media_type}/{user_id}{present_time}"

        with dep_manager.get_dependency_context(Dependency.s3_client) as s3:
            # Reupload the processed image back to S3.
            s3.upload_fileobj(
                output_buffer,
                settings.BUCKET_NAME,
                new_key,
                ExtraArgs={"ContentType": "image/webp"},
            )

        with dep_manager.get_dependency_context(Dependency.db) as db:
            # Add the new image key to database
            user_profile_response = db.user_profile.find_one_and_update(
                {"auth_id": ObjectId(user_id)},
                {
                    "$set": {
                        media_type: new_key,
                    }
                },
                return_document=ReturnDocument.BEFORE,
            )

            friends_list = list_friends_id(user_id=ObjectId(user_id), db=db)

        user_profile: UserProfile = UserProfile.model_validate(user_profile_response)

        message = ProfileMediaUpdate(
            user_id=ObjectId(user_id), media_type=media_type, media_id=new_key
        )

        data = message.model_dump_json(by_alias=True)
        with dep_manager.get_dependency_context(Dependency.s3_client) as s3:
            s3.delete_object(
                Bucket=settings.BUCKET_NAME, Key=user_profile.profile_picture
            )
            s3.delete_object(Bucket=settings.BUCKET_NAME, Key=file_id)

        with dep_manager.get_dependency_context(Dependency.queue) as queue:
            publish_bloking_message(
                connection=queue,
                exchange_name=settings.EXCHANGES.task_updates.value,
                topic=settings.TOPICS.media_update,
                data=data,
            )

            # Send the updated user data to all friends
            data = FriendUpdateMessage(**{"id": ObjectId(user_id), media_type: new_key})
            payload = BrodcastMessage(ids=friends_list, data=data)

            publish_bloking_message(
                connection=queue,
                exchange_name=settings.EXCHANGES.sync_message.value,
                topic=settings.TOPICS.chat_broadcast_selected.value,
                data=payload.model_dump_json(),
            )

            logger.error(f"{payload=}")
    except Exception as e:
        logger.exception(
            f"Infrastructure error processing media for user {user_id}: {e}"
        )

        # Reset connections on specific errors
        if isinstance(e, (ClientError, NoCredentialsError)):
            dep_manager.reset_connection(Dependency.s3_client)

        elif isinstance(e, (ServerSelectionTimeoutError, NetworkTimeout)):
            dep_manager.reset_connection(Dependency.db)

        elif isinstance(e, (AMQPConnectionError, ConnectionClosed)):
            dep_manager.reset_connection(Dependency.queue)

        raise
