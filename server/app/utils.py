import os
import uuid
from typing import Optional
from fastapi import HTTPException, status
import bcrypt
import boto3  # type: ignore
from botocore.client import Config  # type: ignore
from botocore.exceptions import ClientError  # type: ignore

from app.core.config import settings


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed_password.decode("utf-8")


def verify_password(password_hash: str, password_plain: str):
    return bcrypt.checkpw(password_plain.encode("utf-8"), password_hash.encode("utf-8"))


def get_file_extension(filename: str) -> str:
    _, ext = os.path.splitext(filename)
    return ext[1:].lower() if ext else ""


def create_presigned_upload_url():
    conditions = [
        ["content-length-range", 0, 20971520],  # 20 MB limit
    ]

    unique_id = str(uuid.uuid4())

    # Generate a presigned S3 POST URL
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY,
        aws_secret_access_key=settings.AWS_SECRET_KEY,
        region_name="ap-south-1",
        config=Config(signature_version="s3v4"),
    )

    try:
        response = s3_client.generate_presigned_post(
            settings.BUCKET_NAME,
            f"temp/{unique_id}",
            Conditions=conditions,
            ExpiresIn=360,
        )

    except ClientError as e:
        print(f"{e=}")
        return None

    # The response contains the presigned URL and required fields
    s3_client.close()
    return response


def create_presigned_download_url(
    key: Optional[str],
):
    if not key:
        return

    # Generate a S3 Slient
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY,
        aws_secret_access_key=settings.AWS_SECRET_KEY,
        region_name="ap-south-1",
        config=Config(signature_version="s3v4"),
    )

    try:
        # Generate a presigned GET URL
        response = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.BUCKET_NAME, "Key": key},
            ExpiresIn=600,
        )

        return response

    except ClientError as e:
        print(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

