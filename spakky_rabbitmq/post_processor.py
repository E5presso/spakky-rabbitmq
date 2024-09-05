from inspect import ismethod, getmembers, iscoroutinefunction
from logging import Logger

from spakky.application.interfaces.container import IPodContainer
from spakky.application.interfaces.post_processor import IPodPostProcessor
from spakky.domain.models.event import DomainEvent
from spakky.domain.ports.event.event_consumer import IAsyncEventConsumer, IEventConsumer
from spakky.pod.order import Order
from spakky.stereotype.event_handler import EventHandler, EventRoute


@Order(1)
class RabbitMQPostProcessor(IPodPostProcessor):
    __logger: Logger

    def __init__(self, logger: Logger) -> None:
        super().__init__()
        self.__logger = logger

    def post_process(self, container: IPodContainer, pod: object) -> object:
        if not EventHandler.exists(pod):
            return pod
        consumer = container.get(IEventConsumer)
        async_consumer = container.get(IAsyncEventConsumer)
        for _, method in getmembers(pod, ismethod):
            route: EventRoute[DomainEvent] | None = EventRoute.get_or_none(method)
            if route is None:
                continue
            # pylint: disable=line-too-long
            self.__logger.info(
                f"[{type(self).__name__}] {route.event_type.__name__} -> {method.__qualname__}"
            )
            if iscoroutinefunction(method):
                async_consumer.register(route.event_type, method)
                continue
            consumer.register(route.event_type, method)
        return pod
