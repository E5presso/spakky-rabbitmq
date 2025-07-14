from typing import Any

from aio_pika import connect_robust  # type: ignore
from aio_pika.abc import AbstractIncomingMessage, AbstractRobustConnection
from jsons import loads  # type: ignore
from pika import URLParameters
from pika.adapters.blocking_connection import BlockingChannel, BlockingConnection
from pika.spec import Basic, BasicProperties
from spakky.domain.models.event import AbstractDomainEvent
from spakky.domain.ports.event.event_consumer import (
    DomainEventT,
    IAsyncEventConsumer,
    IAsyncEventHandlerCallback,
    IEventConsumer,
    IEventHandlerCallback,
)
from spakky.pod.annotations.pod import Pod
from spakky.service.background import (
    AbstractAsyncBackgroundService,
    AbstractBackgroundService,
)

from spakky_rabbitmq.event.config import RabbitMQConnectionConfig


@Pod()
class RabbitMQEventConsumer(IEventConsumer, AbstractBackgroundService):
    connection_string: str
    type_lookup: dict[str, type[AbstractDomainEvent]]
    handlers: dict[type[AbstractDomainEvent], IEventHandlerCallback[Any]]
    connection: BlockingConnection
    channel: BlockingChannel

    def __init__(self, config: RabbitMQConnectionConfig) -> None:
        super().__init__()
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

    def _check_if_event_set(self) -> None:
        if self._stop_event.is_set():
            self.channel.stop_consuming()
        self.connection.add_callback_threadsafe(self._check_if_event_set)

    def register(
        self,
        event: type[DomainEventT],
        handler: IEventHandlerCallback[DomainEventT],
    ) -> None:
        self.handlers[event] = handler

    def initialize(self) -> None:
        self.connection = BlockingConnection(
            parameters=URLParameters(self.connection_string)
        )
        self.channel = self.connection.channel()

        for event_type in self.handlers:
            self.channel.queue_declare(event_type.__name__)
            consumer_tag = self.channel.basic_consume(
                event_type.__name__,
                self._route_event_handler,
            )
            self.type_lookup[consumer_tag] = event_type

    def dispose(self) -> None:
        self.channel.close()
        self.connection.close()
        return

    def run(self) -> None:
        self.connection.add_callback_threadsafe(self._check_if_event_set)
        self.channel.start_consuming()


@Pod()
class AsyncRabbitMQEventConsumer(IAsyncEventConsumer, AbstractAsyncBackgroundService):
    connection_string: str
    type_lookup: dict[str, type[AbstractDomainEvent]]
    handlers: dict[type[AbstractDomainEvent], IAsyncEventHandlerCallback[Any]]
    connection: AbstractRobustConnection

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

    async def initialize_async(self) -> None:
        self.connection = await connect_robust(self.connection_string)
        self.channel = await self.connection.channel()

        for event_type in self.handlers:
            queue = await self.channel.declare_queue(event_type.__name__)
            consumer_tag = await queue.consume(self._route_event_handler)
            self.type_lookup[consumer_tag] = event_type

    async def dispose_async(self) -> None:
        await self.channel.close()
        await self.connection.close()
        return

    async def run_async(self) -> None:
        await self._stop_event.wait()
