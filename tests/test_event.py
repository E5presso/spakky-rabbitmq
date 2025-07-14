from asyncio import sleep as asleep  # type: ignore
from time import sleep

import pytest
from spakky.application.application import SpakkyApplication
from spakky.domain.ports.event.event_publisher import (
    IAsyncEventPublisher,
    IEventPublisher,
)

from tests.apps.dummy import DummyEventHandler, SampleEvent


def test_synchronous_event(app: SpakkyApplication) -> None:
    publisher = app.container.get(IEventPublisher)
    publisher.publish(SampleEvent(message="Hello, World!"))
    publisher.publish(SampleEvent(message="Goodbye, World!"))
    sleep(0.1)
    handler = app.container.get(DummyEventHandler)
    assert handler.count == 2


@pytest.mark.asyncio
async def test_asynchronous_event(app: SpakkyApplication) -> None:
    publisher = app.container.get(IAsyncEventPublisher)
    await publisher.publish(SampleEvent(message="Hello, World!"))
    await publisher.publish(SampleEvent(message="Goodbye, World!"))
    await asleep(0.1)
    handler = app.container.get(DummyEventHandler)
    assert handler.count == 2
