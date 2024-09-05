from logging import Logger

from spakky.application.interfaces.pluggable import IPluggable
from spakky.application.interfaces.registry import IPodRegistry
from spakky_rabbitmq.event.consumer import (
    AsyncRabbitMQEventConsumer,
    RabbitMQEventConsumer,
)
from spakky_rabbitmq.event.publisher import (
    AsyncRabbitMQEventPublisher,
    RabbitMQEventPublisher,
)
from spakky_rabbitmq.post_processor import RabbitMQPostProcessor


class RabbitMQPlugin(IPluggable):
    logger: Logger

    def __init__(self, logger: Logger) -> None:
        self.logger = logger

    def register(self, registry: IPodRegistry) -> None:
        registry.register(RabbitMQEventConsumer)
        registry.register(AsyncRabbitMQEventConsumer)
        registry.register(RabbitMQEventPublisher)
        registry.register(AsyncRabbitMQEventPublisher)
        registry.register_post_processor(RabbitMQPostProcessor(self.logger))
