from time import sleep
from asyncio import sleep as asleep

import pytest
from spakky.application.application_context import ApplicationContext
from spakky.domain.ports.event.event_publisher import (
    IAsyncEventPublisher,
    IEventPublisher,
)
from spakky.threading.managed_thread import AsyncManagedThread, ManagedThread

from tests.apps.dummy import DummyEventHandler, SampleEvent


def test_synchronous_event_publish_and_consume(
    context: ApplicationContext, managed_thread: ManagedThread
) -> None:
    managed_thread.start()
    publisher = context.get(IEventPublisher)
    publisher.publish(SampleEvent(message="Hello, World!"))
    publisher.publish(SampleEvent(message="Goodbye, World!"))
    sleep(0.1)
    handler = context.get(DummyEventHandler)
    assert handler.count == 2


@pytest.mark.asyncio
async def test_asynchronous_event_publish_and_consume(
    context: ApplicationContext, async_managed_thread: AsyncManagedThread
) -> None:
    async_managed_thread.start()
    publisher = context.get(IAsyncEventPublisher)
    await publisher.publish(SampleEvent(message="Hello, World!"))
    await publisher.publish(SampleEvent(message="Goodbye, World!"))
    await asleep(0.1)
    handler = context.get(DummyEventHandler)
    assert handler.count == 2
