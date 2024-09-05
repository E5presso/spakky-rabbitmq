import logging
from typing import Any, Generator
from logging import Logger, Formatter, StreamHandler, getLogger

import pytest
from spakky.application.application_context import ApplicationContext
from spakky.plugins.aspect import AspectPlugin
from spakky.plugins.logging import LoggingPlugin
from spakky.pod.pod import Pod
from spakky.threading.interface import IAsyncManagedThreadAction, IManagedThreadAction
from spakky.threading.managed_thread import AsyncManagedThread, ManagedThread
from spakky_rabbitmq.event.config import RabbitMQConnectionConfig
from spakky_rabbitmq.plugins.rabbitmq import RabbitMQPlugin

from tests import apps


@pytest.fixture(name="config", scope="session")
def get_config_fixture() -> Generator[RabbitMQConnectionConfig, Any, None]:
    config = RabbitMQConnectionConfig(
        host="localhost",
        port=5672,
        user="test",
        password="test",
        exchange_name=None,
    )
    yield config


@pytest.fixture(name="logger", scope="session")
def get_logger_fixture() -> Generator[Logger, Any, None]:
    logger: Logger = getLogger("debug")
    logger.setLevel(logging.DEBUG)
    console = StreamHandler()
    console.setLevel(level=logging.DEBUG)
    console.setFormatter(Formatter("[%(levelname)s] (%(asctime)s) : %(message)s"))
    logger.addHandler(console)

    yield logger

    logger.removeHandler(console)


@pytest.fixture(name="context", scope="function")
def get_application_context_fixture(
    logger: Logger,
    config: RabbitMQConnectionConfig,
) -> Generator[ApplicationContext, Any, None]:
    @Pod()
    def get_logger() -> Logger:
        return logger

    @Pod()
    def get_config() -> RabbitMQConnectionConfig:
        return config

    context: ApplicationContext = ApplicationContext(package=apps)

    context.register_plugin(LoggingPlugin())
    context.register_plugin(RabbitMQPlugin(logger))
    context.register_plugin(AspectPlugin(logger))

    context.register(get_logger)
    context.register(get_config)

    context.start()

    yield context


@pytest.fixture(name="managed_thread", scope="function", autouse=True)
def get_managed_thread_fixture(
    context: ApplicationContext,
) -> Generator[ManagedThread, Any, None]:
    thread: ManagedThread = ManagedThread(
        context.get(IManagedThreadAction),
        "RabbitMQ Sync Thread",
    )
    thread.start()
    yield thread
    thread.stop()


@pytest.fixture(name="async_managed_thread", scope="function", autouse=True)
def get_async_managed_thread_fixture(
    context: ApplicationContext,
) -> Generator[AsyncManagedThread, Any, None]:
    thread: AsyncManagedThread = AsyncManagedThread(
        context.get(IAsyncManagedThreadAction),
        "RabbitMQ Async Thread",
    )
    thread.start()
    yield thread
    thread.stop()
