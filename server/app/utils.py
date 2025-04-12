import os
import uuid
from typing import Optional
from fastapi import HTTPException, status
from passlib.context import CryptContext  # type: ignore
import boto3  # type: ignore
from botocore.client import Config  # type: ignore
from botocore.exceptions import ClientError  # type: ignore

from app.core.config import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def generate_salt() -> str:
    return os.urandom(10).hex()


def hash_password(password: str, salt: str) -> str:
    hashed_password = pwd_context.hash(password + salt)
    return hashed_password


def verify_password(password_hash: str, password_plain: str, salt: str):
    return pwd_context.verify(password_plain + salt, password_hash)


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
