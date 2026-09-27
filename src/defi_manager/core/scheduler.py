from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from threading import Event as ThreadEvent, Thread
from time import monotonic

from defi_manager.core.events import Event, EventBus
from defi_manager.core.safety import AutomationSafetyController


@dataclass
class ScheduledTask:
    name: str
    interval_seconds: float
    action: Callable[[], None]
    last_run_at: float | None = None


class Scheduler:
    """Periodic scheduler that honours the automation safety gate.

    The run_due API accepts a supplied time for deterministic tests. Start is
    optional and creates one daemon thread for local/headless operation.
    """

    def __init__(self, safety: AutomationSafetyController, events: EventBus) -> None:
        self._safety = safety
        self._events = events
        self._tasks: dict[str, ScheduledTask] = {}
        self._stop_event = ThreadEvent()
        self._thread: Thread | None = None

    def register(self, name: str, interval_seconds: float, action: Callable[[], None]) -> None:
        if not name:
            raise ValueError("task name cannot be empty")
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        if name in self._tasks:
            raise ValueError(f"task already registered: {name}")
        self._tasks[name] = ScheduledTask(name, interval_seconds, action)

    def run_due(self, now: float | None = None) -> None:
        current = monotonic() if now is None else now
        for task in self._tasks.values():
            if task.last_run_at is not None and current - task.last_run_at < task.interval_seconds:
                continue
            decision = self._safety.execution_decision()
            if not decision.allowed:
                self._events.publish(Event("scheduler.task_skipped", {"task": task.name, "reason": decision.reason}))
                continue
            try:
                task.action()
            except Exception as exc:
                self._events.publish(Event("scheduler.task_failed", {"task": task.name, "error": str(exc)}))
            else:
                task.last_run_at = current
                self._events.publish(Event("scheduler.task_completed", {"task": task.name}))

    def start(self, poll_interval_seconds: float = 1.0) -> None:
        if poll_interval_seconds <= 0:
            raise ValueError("poll_interval_seconds must be positive")
        if self._thread is not None and self._thread.is_alive():
            raise RuntimeError("scheduler already running")
        self._stop_event.clear()
        self._thread = Thread(target=self._loop, args=(poll_interval_seconds,), daemon=True, name="defi-manager-scheduler")
        self._thread.start()

    def stop(self, timeout_seconds: float = 5.0) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout_seconds)

    def _loop(self, poll_interval_seconds: float) -> None:
        while not self._stop_event.is_set():
            self.run_due()
            self._stop_event.wait(poll_interval_seconds)

