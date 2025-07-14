from functools import wraps
from inspect import getmembers, iscoroutinefunction, ismethod
from logging import Logger
from typing import Any

from spakky.domain.models.event import AbstractDomainEvent
from spakky.domain.ports.event.event_consumer import IAsyncEventConsumer, IEventConsumer
from spakky.pod.annotations.order import Order
from spakky.pod.annotations.pod import Pod
from spakky.pod.interfaces.aware.container_aware import IContainerAware
from spakky.pod.interfaces.aware.logger_aware import ILoggerAware
from spakky.pod.interfaces.container import IContainer
from spakky.pod.interfaces.post_processor import IPostProcessor
from spakky.stereotype.event_handler import EventHandler, EventRoute


@Order(1)
@Pod()
class RabbitMQPostProcessor(IPostProcessor, ILoggerAware, IContainerAware):
    __logger: Logger
    __container: IContainer

    def set_logger(self, logger: Logger) -> None:
        self.__logger = logger

    def set_container(self, container: IContainer) -> None:
        self.__container = container

    def post_process(self, pod: object) -> object:
        if not EventHandler.exists(pod):
            return pod
        handler: EventHandler = EventHandler.get(pod)
        consumer = self.__container.get(IEventConsumer)
        async_consumer = self.__container.get(IAsyncEventConsumer)
        for name, method in getmembers(pod, ismethod):
            route: EventRoute[AbstractDomainEvent] | None = EventRoute[
                AbstractDomainEvent
            ].get_or_none(method)
            if route is None:
                continue
            # pylint: disable=line-too-long
            self.__logger.info(
                f"[{type(self).__name__}] {route.event_type.__name__} -> {method.__qualname__}"
            )

            if iscoroutinefunction(method):

                @wraps(method)
                async def async_endpoint(
                    *args: Any,
                    method_name: str = name,
                    controller_type: type[object] = handler.type_,
                    context: IContainer = self.__container,
                    **kwargs: Any,
                ) -> Any:
                    controller_instance = context.get(controller_type)
                    method_to_call = getattr(controller_instance, method_name)
                    return await method_to_call(*args, **kwargs)

                async_consumer.register(route.event_type, async_endpoint)
                continue

            @wraps(method)
            def endpoint(
                *args: Any,
                method_name: str = name,
                controller_type: type[object] = handler.type_,
                context: IContainer = self.__container,
                **kwargs: Any,
            ) -> Any:
                controller_instance = context.get(controller_type)
                method_to_call = getattr(controller_instance, method_name)
                return method_to_call(*args, **kwargs)

            consumer.register(route.event_type, endpoint)
        return pod
