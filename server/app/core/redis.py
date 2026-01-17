from fastapi import Request
import redis.asyncio as redis
from app.core.config import settings

redis_pool = redis.ConnectionPool.from_url(
    settings.REDIS_URL, max_connections=10, decode_responses=True
)


async def get_redis_client() -> redis.Redis:
    redis_connection = redis.Redis(connection_pool=redis_pool)
    await redis_connection.ping()
    return redis_connection


async def get_redis_conn(request: Request) -> redis.Redis:
    return request.state.redis


async def set_key_value(redis_conn: redis.Redis, key, value, **kwargs):
    await redis_conn.set(key, value, **kwargs)


async def get_value(redis_conn: redis.Redis, key):
    return await redis_conn.get(key)


async def delete_key(redis_conn, key):
    await redis_conn.delete(key)
