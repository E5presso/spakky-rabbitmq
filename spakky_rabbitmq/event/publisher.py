from aio_pika import Message, connect_robust  # type: ignore
from jsons import dumps  # type: ignore
from pika import BlockingConnection, URLParameters
from spakky.domain.models.event import AbstractDomainEvent
from spakky.domain.ports.event.event_publisher import (
    IAsyncEventPublisher,
    IEventPublisher,
)
from spakky.pod.annotations.pod import Pod

from spakky_rabbitmq.event.config import RabbitMQConnectionConfig


@Pod()
class RabbitMQEventPublisher(IEventPublisher):
    connection_string: str
    exchange_name: str | None

    def __init__(self, config: RabbitMQConnectionConfig) -> None:
        self.connection_string = config.connection_string
        self.exchange_name = config.exchange_name

    def publish(self, event: AbstractDomainEvent) -> None:
        connection = BlockingConnection(URLParameters(self.connection_string))
        channel = connection.channel()
        channel.queue_declare(event.event_name)
        if self.exchange_name is not None:
            channel.exchange_declare(self.exchange_name)
            channel.queue_bind(event.event_name, self.exchange_name, event.event_name)
        channel.basic_publish(
            self.exchange_name if self.exchange_name is not None else "",
            event.event_name,
            dumps(event).encode(),
        )
        channel.close()
        connection.close()


@Pod()
class AsyncRabbitMQEventPublisher(IAsyncEventPublisher):
    connection_string: str
    exchange_name: str | None

    def __init__(self, config: RabbitMQConnectionConfig) -> None:
        self.connection_string = config.connection_string
        self.exchange_name = config.exchange_name

    async def publish(self, event: AbstractDomainEvent) -> None:
        async with await connect_robust(self.connection_string) as connection:
            channel = await connection.channel()
            exchange = (
                await channel.declare_exchange(self.exchange_name)
                if self.exchange_name is not None
                else channel.default_exchange
            )
            queue = await channel.declare_queue(event.event_name)
            if self.exchange_name is not None:
                await queue.bind(exchange, event.event_name)
            await exchange.publish(
                Message(body=dumps(event).encode()),
                routing_key=event.event_name,
            )
            await channel.close()
