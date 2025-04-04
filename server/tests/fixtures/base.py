import httpx
import pytest_asyncio
from fastapi import FastAPI
from collections.abc import AsyncGenerator

from app.main import app as bridge_app
from app.core.db import AsyncDatabase, get_async_database


@pytest_asyncio.fixture
async def app(database_session: AsyncDatabase) -> AsyncGenerator[FastAPI]:
    bridge_app.dependency_overrides[get_async_database] = lambda: database_session

    yield bridge_app

    bridge_app.dependency_overrides.pop(get_async_database)


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncGenerator[httpx.AsyncClient, None]:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
