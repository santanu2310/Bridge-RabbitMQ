import io
from typing import Union
from datetime import datetime
from bson import ObjectId
import logging
from botocore.exceptions import ClientError  # type: ignore
from PIL import Image
from app.core.config import create_celery_client, settings
from app.core.schemas import Message, MediaType, UserProfile, ProfileMediaUpdate
from app.core.db import create_sync_client, SyncDatabase
from app.core.message_broker import (
    publish_bloking_message,
)
from app.utils import get_file_extension
from pymongo import ReturnDocument
from app.background_tasks.celery.dependency import DependencyManager, Dependency


dependency = DependencyManager()

celery_app = create_celery_client()

logging.basicConfig(level="DEBUG")
logger = logging.getLogger(__name__)


@celery_app.task
def process_media_message(message_id: str):
    with create_sync_client() as sync_client:
        db = SyncDatabase(sync_client, settings.DATABASE_NAME)
        try:
            # Getting the message from message from id and maping it
            message_response = db.message.find_one({"_id": ObjectId(message_id)})
            message = Message.model_validate(message_response)

            if not message.attachment:
                raise
            # Creating a s3 client
            s3_client = dependency.get_dependency(Dependency.s3_client)

            # Generating the key
            present_time = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
            key = "attachment/Bridge_Atachment_" + present_time

            # Transfereing the data
            s3_client.copy_object(
                Bucket=settings.BUCKET_NAME,
                CopySource={
                    "Bucket": settings.BUCKET_NAME,
                    "Key": message.attachment.temp_file_id,
                },
                Key=key,
            )

            # Geting the file
            size = s3_client.head_object(
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

            data = message.model_dump_json(by_alias=True)

            publish_bloking_message(
                connection=dependency.get_dependency(Dependency.queue),
                exchange_name=settings.EXCHANGES.sync_message.value,
                topic=settings.TOPICS.message.value,
                data=data,
            )
        except ClientError as e:
            print(f"Error copying object: {e}")


@celery_app.task
def process_profile_media(file_id: str, user_id: str, media_type: MediaType):
    db = dependency.get_dependency(Dependency.db)

    test_db = dependency.get_dependency(Dependency.queue)
    logger.critical(f"form process media message {test_db=}")

    s3_client = dependency.get_dependency(Dependency.s3_client)

    try:
        # Getting the image from S3
        obj = s3_client.get_object(
            Bucket=settings.BUCKET_NAME,
            Key=file_id,
        )
        image_data = obj["Body"].read()

        # Open the image using PIL.
        image: Union[Image.Image] = Image.open(io.BytesIO(image_data))
        width, height = image.size

        if width != height:
            # Crop image to a square aspect ratio if the original is rectangular.
            square_size = min(width, height)

            left = (width - square_size) // 2
            top = (height - square_size) // 2
            right = left + square_size
            bottom = top + square_size

            image = image.crop((left, top, right, bottom))

        # Change the resolution
        target_size = (480, 480)
        image.thumbnail(target_size)

        output_buffer = io.BytesIO()
        image.convert("RGB").save(output_buffer, format="WebP")

        output_buffer.seek(0)
        # image_bytes = output_buffer.read()

        present_time = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
        new_key = f"{media_type}/{user_id}{present_time}"
        # Step 3: Reupload the processed image back to S3.
        s3_client.upload_fileobj(
            output_buffer,
            settings.BUCKET_NAME,
            new_key,
            ExtraArgs={"ContentType": "image/webp"},
        )

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

        user_profile: UserProfile = UserProfile.model_validate(user_profile_response)

        message = ProfileMediaUpdate(
            user_id=ObjectId(user_id), media_type=media_type, media_id=new_key
        )

        data = message.model_dump_json(by_alias=True)

        publish_bloking_message(
            connection=dependency.get_dependency(Dependency.queue),
            exchange_name=settings.EXCHANGES.task_updates.value,
            topic=settings.TOPICS.media_update,
            data=data,
        )

        s3_client.delete_object(
            Bucket=settings.BUCKET_NAME, Key=user_profile.profile_picture
        )

    except Exception as e:
        logger.critical(e)

    # Delete the old image from S3.
    s3_client.delete_object(Bucket=settings.BUCKET_NAME, Key=file_id)
    # producer.close()
