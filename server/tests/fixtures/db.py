import logging
from collections.abc import AsyncGenerator
import pytest_asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.db import AsyncDatabase

logging.basicConfig(level="DEBUG")
logger = logging.getLogger(__name__)

db_name = "TestDb"

TEST_DB = "mongodb://localhost:27017/?directConnection=true"
# TEST_DB = "mongodb://localhost:27017,localhost:27018,localhost:27019/?replicaSet=rs0"


def create_async_client() -> AsyncIOMotorClient:
    return AsyncIOMotorClient(TEST_DB)


@pytest_asyncio.fixture
async def database_session() -> AsyncGenerator[AsyncDatabase]:
    client = create_async_client()
    logger.critical(f"{client=}")

    yield AsyncDatabase(client=client, db_name=db_name)

    await client.drop_database(db_name)
    client.close()
