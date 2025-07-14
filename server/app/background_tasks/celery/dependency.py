import logging
import threading
from enum import Enum
from typing import Any, Dict

from app.core.config import create_s3_client, settings
from app.core.db import SyncDatabase, create_sync_client
from app.core.message_broker import create_bloking_rabbit_connection
from celery import Task  # type: ignore

logger = logging.getLogger(__name__)


class Dependency(str, Enum):
    db = "db"
    s3_client = "s3_client"
    queue = "queue"


class DependencyManager(Task):
    _connections: Dict[str, Any] = {}
    _initialized = False
    _lock = threading.Lock()

    def __new__(cls):
        logger.critical("New Instance of DependencyManager created")
        if not hasattr(cls, "_instance"):
            with cls._lock:
                if not hasattr(cls, "_instance"):
                    cls._instance = super().__new__(cls)
        return cls._instance

    def initialize(self):
        if self._initialized:
            return
        try:
            # MongoDB connection
            client = create_sync_client()
            self._connections[Dependency.db] = SyncDatabase(
                client, settings.DATABASE_NAME
            )

            # S3 client
            self._connections[Dependency.s3_client] = create_s3_client()

            # RabbitMq
            self._connections[Dependency.queue] = create_bloking_rabbit_connection()

            self._initialized = True

        except Exception as e:
            logging.error(f"Connection initialization failed: {e}")
            raise

    def get_dependency(self, name: Dependency):
        """Retrieve a dependency with lazy initialization"""
        if not self._initialized:
            self.initialize()

        if name not in self._connections:
            raise ValueError(f"Unknown dependency: {name}")

        return self._connections[name]

    def close_connections(self):
        """Safely close all connections"""
        try:
            if db := self._connections.get(Dependency.db):
                db.client.close()
                logger.info("MongoDB connection closed")
        except Exception as e:
            logger.error(f"Error closing MongoDB: {e}")

        try:
            if queue := self._connections.get(Dependency.queue):
                queue.close()
                logger.info("RabbitMQ connection closed")
        except Exception as e:
            logger.error(f"Error closing RabbitMQ: {e}")

        self._connections.clear()
        self._initialized = False
