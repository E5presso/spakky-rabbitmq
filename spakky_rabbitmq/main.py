from spakky.application.application import SpakkyApplication

from spakky_rabbitmq.event.consumer import (
    AsyncRabbitMQEventConsumer,
    RabbitMQEventConsumer,
)
from spakky_rabbitmq.event.publisher import (
    AsyncRabbitMQEventPublisher,
    RabbitMQEventPublisher,
)
from spakky_rabbitmq.post_processor import RabbitMQPostProcessor


def initialize(app: SpakkyApplication) -> None:
    app.add(RabbitMQPostProcessor)

    app.add(RabbitMQEventConsumer)
    app.add(RabbitMQEventPublisher)

    app.add(AsyncRabbitMQEventConsumer)
    app.add(AsyncRabbitMQEventPublisher)
