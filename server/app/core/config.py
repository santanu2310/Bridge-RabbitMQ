import logging
import logging.config
from enum import Enum
from pathlib import Path
import boto3  # type: ignore
from botocore.config import Config  # type: ignore
from celery import Celery  # type: ignore
from pydantic_settings import BaseSettings, SettingsConfigDict

env_path = Path(__file__).parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=env_path, env_file_encoding="utf-8")

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    ALLOW_ORIGINS: str = "http://localhost:5173"

    # JWT secrets
    JWT_ACCESS_SECRET_KEY: str = ""
    JWT_REFRESH_SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"

    class TOPICS(str, Enum):
        online_status = "online_status"
        media_update = "media_update"
        message = "message"

    class EXCHANGES(str, Enum):
        sync_message = "sync_message"
        task_updates = "task_updates"

    # AWS
    AWS_ACCESS_KEY: str = ""
    AWS_SECRET_KEY: str = ""
    BUCKET_NAME: str = ""
    RABBITMQ_USER_NAME: str = ""
    RABBITMQ_USER_PASSWORD: str = ""

    # Mongodb
    MONGOD_URL: str = ""
    DATABASE_NAME: str = "bridge"

    # RABBITMQ_URL: str = "amqps://b-553fe81b-63b6-4ace-bd15-186c6428c97c.mq.ap-south-1.amazonaws.com:5671"
    # RABBITMQ_HOST: str = (
    #     "b-553fe81b-63b6-4ace-bd15-186c6428c97c.mq.ap-south-1.amazonaws.com"
    # )
    RABBITMQ_PORT: str = "5671"
    CELERY_BROKER_URL: str = "amqp://bridge-bot:Mybridge1936@rabbitmq:5672"


settings = Settings()
logger = logging.getLogger(__name__)


def create_celery_client() -> Celery:
    return Celery("tasks", broker=settings.CELERY_BROKER_URL)


def create_s3_client():
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY,
        aws_secret_access_key=settings.AWS_SECRET_KEY,
        region_name="ap-south-1",
        config=Config(signature_version="s3v4"),
    )

    return s3_client


LOGGING_CONFIG = {
    "version": 1,
    "formatters": {
        "standard": {"format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "standard",
            "filename": "app.log",
            "maxBytes": 1024 * 1024 * 5,  # 5 MB per file
            "backupCount": 3,
        },
    },
    "loggers": {
        # Custom logger for your app
        "root": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        # Optionally configure uvicorn's loggers:
        # "uvicorn.error": {
        #     "handlers": ["console", "file"],
        #     "level": "INFO",
        #     "propagate": False,
        # },
        # "uvicorn.access": {
        #     "handlers": ["console", "file"],
        #     "level": "INFO",
        #     "propagate": False,
        # },
    },
}

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger()
logger.info("Logger initialized for production")


__all__ = [
    "settings",
    "create_celery_client",
]
