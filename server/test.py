import asyncio
from aio_pika import connect_robust
from app.core.message_broker import create_rabbit_exchanges


async def create_rabbit_connection():
    connection = await connect_robust(
        url="amqps://bridgebot:bdgbot212014@b-553fe81b-63b6-4ace-bd15-186c6428c97c.mq.ap-south-1.amazonaws.com:5671",
        ssl=True,
    )
    channel = await connection.channel()
    await create_rabbit_exchanges(connection=connection)
    print(channel)


if __name__ == "__main__":
    asyncio.run(create_rabbit_connection())
