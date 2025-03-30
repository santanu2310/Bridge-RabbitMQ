import logging
from enum import Enum
from typing import Dict, Any
from celery import Task  # type: ignore
from app.core.db import create_sync_client, SyncDatabase
from app.core.message_broker import create_bloking_rabbit_connection
from app.core.config import settings, create_s3_client

logger = logging.getLogger(__name__)


class Dependency(str, Enum):
    db = "db"
    s3_client = "s3_client"
    queue = "queue"


class DependencyManager(Task):
    _instance = None
    _connections: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_connections()
        return cls._instance

    def _initialize_connections(self):
        try:
            self._initialize_mongodb()
            self._initialize_s3()
            self._initialize_rabbitmq()
        except Exception as e:
            logging.error(f"Connection initialization failed: {e}")
            raise

    def _initialize_mongodb(self):
        client = create_sync_client()
        db = SyncDatabase(client, settings.DATABASE_NAME)
        self._connections[Dependency.db.value] = {"client": client, "db": db}

    def _initialize_s3(self):
        self._connections[Dependency.s3_client.value] = create_s3_client()

    def _initialize_rabbitmq(self):
        self._connections[Dependency.queue.value] = create_bloking_rabbit_connection()

    def get_dependency(self, name: Dependency):
        """
        Retrieve a specific dependency connection

        :param name: Name of the dependency (mongodb, s3, rabbitmq)
        :return: Dependency connection details
        """
        if name.value not in self._connections:
            raise ValueError(f"Dependency {name.value} not initialized")

        if name.value == Dependency.db.value:
            return self._connections[Dependency.db.value]["db"]
        return self._connections[name.value]

    def close_connections(self):
        """
        Safely close all connections
        """
        connection_closers = {
            "mongodb": lambda: self._connections[Dependency.db.value]["client"].close(),
            "rabbitmq": lambda: self._connections[Dependency.queue.value].close(),
        }

        for name, closer in connection_closers.items():
            try:
                if name in self._connections:
                    closer()
                    logger.info(f"{name.capitalize()} connection closed")
            except Exception as e:
                logger.error(f"Error closing {name} connection: {e}")

    def __del__(self):
        self.close_connections()
