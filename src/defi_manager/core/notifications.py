from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from defi_manager.core.events import Event, EventBus


class NotificationSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True)
class Notification:
    title: str
    body: str
    severity: NotificationSeverity


class NotificationSink(Protocol):
    def send(self, notification: Notification) -> None: ...


class InMemoryNotificationSink:
    """Test/local sink; external sinks can implement the same contract."""

    def __init__(self) -> None:
        self.sent: list[Notification] = []

    def send(self, notification: Notification) -> None:
        self.sent.append(notification)


class NotificationDispatcher:
    _EVENTS: dict[str, tuple[str, NotificationSeverity]] = {
        "automation.paused": ("Automation paused", NotificationSeverity.WARNING),
        "automation.emergency_stop": ("Emergency stop", NotificationSeverity.CRITICAL),
        "safety.execution_rejected": ("Execution blocked", NotificationSeverity.WARNING),
        "scheduler.task_failed": ("Scheduled task failed", NotificationSeverity.WARNING),
    }

    def __init__(self, events: EventBus, sink: NotificationSink) -> None:
        self._sink = sink
        events.subscribe("*", self.handle)

    def handle(self, event: Event) -> None:
        definition = self._EVENTS.get(event.name)
        if definition is None:
            return
        title, severity = definition
        details = ", ".join(f"{key}={value}" for key, value in sorted(event.payload.items()))
        self._sink.send(Notification(title, details or event.name, severity))

