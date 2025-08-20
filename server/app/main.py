import asyncio
import time
import logging
import contextlib
from typing import TypedDict
from collections.abc import AsyncIterator
from aio_pika.abc import AbstractRobustConnection
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.api import router

from app.background_tasks.async_ops.tasks import (
    watch_user_updates,
    handle_online_status_update,
    watch_message_updates,
    distribute_published_messages,
    watch_friend_requests,
    profile_media_update_confirmation,
)

from app.core.message_broker import create_rabbit_connection, create_rabbit_exchanges

from app.core.db import (
    AsyncDatabase,
    SyncDatabase,
    create_async_client,
    create_sync_client,
)
from app.core.config import settings


class State(TypedDict):
    async_db: AsyncDatabase
    sync_db: SyncDatabase
    queue_connection: AbstractRobustConnection


logger = logging.getLogger(__name__)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[State]:
    async_cleint = create_async_client()
    sync_client = create_sync_client()
    queue_connection = await create_rabbit_connection()

    await create_rabbit_exchanges(connection=queue_connection)

    async_db = AsyncDatabase(async_cleint, settings.DATABASE_NAME)

    app.state.background_tasks = [
        asyncio.create_task(watch_friend_requests()),
        asyncio.create_task(watch_user_updates()),
        asyncio.create_task(handle_online_status_update(db=async_db)),
        asyncio.create_task(watch_message_updates()),
        asyncio.create_task(distribute_published_messages(db=async_db)),
        asyncio.create_task(profile_media_update_confirmation()),
    ]

    yield {
        "async_db": async_db,
        "sync_db": SyncDatabase(sync_client, settings.DATABASE_NAME),
        "queue_connection": queue_connection,
    }

    for task in app.state.background_tasks:
        task.cancel()

    await asyncio.gather(*app.state.background_tasks, return_exceptions=True)

    async_cleint.close()
    sync_client.close()
    await queue_connection.close()


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)

    app.include_router(router=router)
    logger.error(f"{settings.ALLOW_ORIGINS=}")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.ALLOW_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app


app = create_app()


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    logger.info(f"Request: {request.method} {request.url}")
    response = await call_next(request)
    duration = time.time() - start_time
    logger.info(f"Response: {response.status_code} completed in {duration:.3f}s")
    return response
