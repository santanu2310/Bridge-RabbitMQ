import logging
from fastapi import Request, WebSocket
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from pymongo import MongoClient
from app.core.config import settings

logging.basicConfig(level="DEBUG")
logger = logging.getLogger(__name__)


class BaseDatabase:
    def __init__(self, db):
        self.db = db
        self.user_auth = self.db.get_collection("user_auth")
        self.user_profile = self.db.get_collection("user_profile")
        self.friend_request = self.db.get_collection("friend_request")
        self.friends = self.db.get_collection("friends")
        self.conversation = self.db.get_collection("conversation")
        self.message = self.db.get_collection("message")

        self._collection_names = {
            "user_auth",
            "user_profile",
            "friend_request",
            "friends",
            "conversation",
            "message",
        }

    def get_collection(self, name: str) -> AsyncIOMotorCollection:
        """Dynamically fetch a collection by name, if defined."""
        if name not in self._collection_names:
            raise ValueError(f"Collection '{name}' is not defined.")
        return getattr(self, name)


class AsyncDatabase(BaseDatabase):
    def __init__(self, client: AsyncIOMotorClient, db_name: str):
        self.db = client.get_database(db_name)
        super().__init__(self.db)

    async def initialize_indexes(self):
        await self.user_profile.create_index("user_id", unique=True)


class SyncDatabase(BaseDatabase):
    def __init__(self, client: MongoClient, db_name: str):
        self.db = client.get_database(db_name)
        super().__init__(self.db)


def create_async_client() -> AsyncIOMotorClient:
    logger.critical("crate async client is being used")
    return AsyncIOMotorClient(settings.MONGOD_URL)


def get_async_database(request: Request) -> AsyncDatabase:
    return request.state.async_db


def get_async_database_from_socket(websocket: WebSocket) -> AsyncDatabase:
    return websocket.state.async_db


def create_sync_client() -> MongoClient:
    return MongoClient(settings.MONGOD_URL)


def get_sync_database(request: Request) -> SyncDatabase:
    return request.state.sync_db


__all__ = [
    "AsyncIOMotorClient",
    "MongoClient",
    "AsyncDatabase",
    "SyncDatabase",
    "create_async_client",
    "get_async_database",
    "get_async_database_from_socket",
    "create_sync_client",
    "get_sync_database",
]
