"""Replaceable event bus used for SSE notifications and workers."""
from abc import ABC, abstractmethod
from queue import Queue


class MessageBus(ABC):
    """Abstract event transport so tests do not require Redis."""
    @abstractmethod
    def publish(self, channel: str, payload: dict): ...
    @abstractmethod
    def subscribe(self, channel: str): ...


class InMemoryBus(MessageBus):
    """Small process-local bus for development and tests."""
    def __init__(self):
        self.queues: dict[str, list[Queue]] = {}

    def publish(self, channel, payload):
        for queue in self.queues.get(channel, []):
            queue.put(payload)

    def subscribe(self, channel):
        queue = Queue()
        self.queues.setdefault(channel, []).append(queue)
        return queue
