import asyncio
import json
import logging
from functools import wraps
from typing import Awaitable, Callable, Dict
from pydantic import BaseModel

from aio_pika import Message, connect_robust
from aio_pika.abc import (
    AbstractChannel,
    AbstractExchange,
    AbstractQueue,
    AbstractRobustConnection,
    ExchangeType,
)
from aio_pika.exceptions import AMQPConnectionError
from fastapi import WebSocket
from pika import BlockingConnection, URLParameters  # type: ignore
from pika.exceptions import UnroutableError  # type: ignore

from app.core.config import settings

logger = logging.getLogger(__name__)


async def create_rabbit_connection() -> AbstractRobustConnection:
    return await connect_robust(
        url=settings.CELERY_BROKER_URL,
        ssl=True,
    )


def create_bloking_rabbit_connection() -> BlockingConnection:
    parameters = URLParameters(settings.CELERY_BROKER_URL)
    parameters.heartbeat = 30
    return BlockingConnection(parameters)


def get_rabbit_connection(websocket: WebSocket) -> AbstractRobustConnection:
    return websocket.state.queue_connection


async def create_rabbit_exchanges(connection: AbstractRobustConnection):
    channel = None
    try:
        channel = await connection.channel()
        await channel.declare_exchange(
            name=settings.EXCHANGES.sync_message.value,
            type=ExchangeType.TOPIC,
            durable=True,
        )
        await channel.declare_exchange(
            name=settings.EXCHANGES.task_updates.value,
            type=ExchangeType.TOPIC,
            durable=True,
        )

        logger.info("Exchange created successfully")
    except Exception as e:
        logger.error(f"Error creating exchange : {e}")
    finally:
        if channel:
            await channel.close()


async def publish_message(
    connection: AbstractRobustConnection,
    exchange_name: str,
    topic: str,
    data: BaseModel,
):
    channel: AbstractChannel = await connection.channel()
    try:
        exchange: AbstractExchange = await channel.get_exchange(name=exchange_name)

        await exchange.publish(
            Message(body=data.model_dump_json().encode("utf-8")),
            routing_key=topic,
        )

    except Exception as e:
        logger.error(f"Failed to publish message: {e}")
    finally:
        await channel.close()


def publish_bloking_message(
    connection: BlockingConnection, exchange_name: str, topic: str, data: str
):
    channel = None
    try:
        channel = connection.channel()
        body = data.encode("utf-8")
        channel.basic_publish(
            exchange=exchange_name, routing_key=topic, body=body, mandatory=True
        )

    except UnroutableError as e:
        logger.error(f"Message was returned [Unroutable] : {e}")
    except Exception as e:
        logger.error(f"Failed to publish message: {e}")


def rabbit_consumer(
    topic_name: str,
    exchange_name: str,
    max_retries: int = 10,
    initial_delay: float = 2.0,
):
    def decorator(func: Callable[..., Awaitable[None]]):
        @wraps(func)
        async def wrapper(*args, **kwargs) -> None:
            attempt = 0
            while attempt < max_retries:
                connection = await connect_robust(url=settings.CELERY_BROKER_URL)

                async with connection:
                    try:
                        channel: AbstractChannel = await connection.channel()
                        await channel.set_qos(prefetch_count=5)

                        exchange: AbstractExchange = await channel.get_exchange(
                            name=exchange_name
                        )

                        queue: AbstractQueue = await channel.declare_queue(
                            exclusive=True
                        )

                        await queue.bind(exchange, routing_key=topic_name)

                        async with queue.iterator() as queue_iter:
                            async for message in queue_iter:
                                async with message.process():
                                    try:
                                        await func(message, *args, **kwargs)
                                    except Exception as e:
                                        logger.error(
                                            f"Error processing {topic_name} message, {message=} error : {e}"
                                        )
                    except AMQPConnectionError as e:
                        logger.error(f"RabbitMQ connection failed : {e}")
                        attempt += 1

                        if attempt >= max_retries:
                            logger.critical(
                                f"Max retries ({max_retries}) reached. Giving up."
                            )
                            break

                        sleep_time = initial_delay * attempt

                        await asyncio.sleep(sleep_time)

        return wrapper

    return decorator
