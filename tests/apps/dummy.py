from spakky.core.mutability import immutable
from spakky.domain.models.event import AbstractDomainEvent
from spakky.stereotype.event_handler import EventHandler, on_event


@immutable
class SampleEvent(AbstractDomainEvent):
    message: str


@EventHandler()
class DummyEventHandler:
    __count: int

    @property
    def count(self) -> int:
        return self.__count

    def __init__(self) -> None:
        self.__count = 0

    @on_event(SampleEvent)
    def handle_sample(self, event: SampleEvent) -> None:
        print(f"Received event: {event}")
        self.__count += 1

    @on_event(SampleEvent)
    async def handle_sample_async(self, event: SampleEvent) -> None:
        print(f"Received event: {event}")
        self.__count += 1
