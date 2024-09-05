from typing import Any
from asyncio import Lock as AsyncLock, Event as AsyncEvent
from threading import Lock as ThreadLock, Event as ThreadEvent

from aio_pika import connect_robust
from aio_pika.abc import AbstractIncomingMessage
from jsons import loads  # type: ignore
from pika import URLParameters
from pika.adapters.blocking_connection import BlockingChannel, BlockingConnection
from pika.spec import Basic, BasicProperties
from spakky.domain.models.event import DomainEvent
from spakky.domain.ports.event.event_consumer import (
    DomainEventT,
    IAsyncEventConsumer,
    IAsyncEventHandlerCallback,
    IEventConsumer,
    IEventHandlerCallback,
)
from spakky.pod.pod import Pod
from spakky.threading.interface import IAsyncManagedThreadAction, IManagedThreadAction
from spakky_rabbitmq.event.config import RabbitMQConnectionConfig


@Pod()
class RabbitMQEventConsumer(IEventConsumer, IManagedThreadAction):
    connection_string: str
    type_lookup: dict[str, type[DomainEvent]]
    handlers: dict[type[DomainEvent], IEventHandlerCallback[Any]]

    def __init__(self, config: RabbitMQConnectionConfig) -> None:
        self.connection_string = config.connection_string
        self.type_lookup = {}
        self.handlers = {}

    def _route_event_handler(
        self,
        channel: BlockingChannel,
        method_frame: Basic.Deliver,
        _: BasicProperties,
        body: bytes,
    ) -> None:
        assert method_frame.delivery_tag is not None
        assert method_frame.consumer_tag is not None
        event_type = self.type_lookup[method_frame.consumer_tag]
        handler = self.handlers[event_type]
        event = loads(body.decode(), event_type)
        handler(event)
        channel.basic_ack(method_frame.delivery_tag)

    def register(
        self,
        event: type[DomainEventT],
        handler: IEventHandlerCallback[DomainEventT],
    ) -> None:
        self.handlers[event] = handler

    def __call__(self, event: ThreadEvent, lock: ThreadLock) -> None:
        connection = BlockingConnection(parameters=URLParameters(self.connection_string))
        channel = connection.channel()

        for event_type in self.handlers:
            channel.queue_declare(event_type.__name__)
            consumer_tag = channel.basic_consume(
                event_type.__name__,
                self._route_event_handler,
            )
            self.type_lookup[consumer_tag] = event_type

        def stop() -> None:
            if event.is_set():
                channel.stop_consuming()
                channel.close()
                connection.close()
                return
            connection.add_callback_threadsafe(stop)

        connection.add_callback_threadsafe(stop)
        channel.start_consuming()


@Pod()
class AsyncRabbitMQEventConsumer(IAsyncEventConsumer, IAsyncManagedThreadAction):
    connection_string: str
    type_lookup: dict[str, type[DomainEvent]]
    handlers: dict[type[DomainEvent], IAsyncEventHandlerCallback[Any]]

    def __init__(self, config: RabbitMQConnectionConfig) -> None:
        self.connection_string = config.connection_string
        self.type_lookup = {}
        self.handlers = {}

    async def _route_event_handler(self, message: AbstractIncomingMessage) -> None:
        assert message.delivery_tag is not None
        assert message.consumer_tag is not None
        event_type = self.type_lookup[message.consumer_tag]
        handler = self.handlers[event_type]
        event = loads(message.body.decode(), event_type)
        await handler(event)
        await message.ack()

    def register(
        self,
        event: type[DomainEventT],
        handler: IAsyncEventHandlerCallback[DomainEventT],
    ) -> None:
        self.handlers[event] = handler

    async def __call__(self, event: AsyncEvent, lock: AsyncLock) -> None:
        async with await connect_robust(self.connection_string) as connection:
            channel = await connection.channel()
            for event_type in self.handlers:
                queue = await channel.declare_queue(event_type.__name__)  # type: ignore
                # pylint: disable=line-too-long
                consumer_tag = await queue.consume(self._route_event_handler)  # type: ignore
                self.type_lookup[consumer_tag] = event_type
            await event.wait()
        return
