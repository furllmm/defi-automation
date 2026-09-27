from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from defi_manager.core.events import Event, EventBus


class PauseReason(StrEnum):
    BATTERY = "battery"
    NETWORK = "network"
    RPC = "rpc"
    AI = "ai"
    CLOCK = "clock"
    RESOURCE = "resource"
    MANUAL = "manual"


@dataclass(frozen=True)
class SafetyDecision:
    allowed: bool
    reason: str


class AutomationSafetyController:
    """Fail-closed automation gate for simulated execution.

    An unhealthy required dependency pauses automation. Recovery is explicit:
    clearing an issue only makes resumption possible; an operator must resume.
    Emergency stop additionally requires explicit recovery.
    """

    def __init__(self, events: EventBus) -> None:
        self._events = events
        self._active_issues: set[PauseReason] = set()
        self._manual_paused = False
        self._health_recovery_required = False
        self._emergency_stopped = False

    @property
    def paused(self) -> bool:
        return self._manual_paused or self._health_recovery_required or bool(self._active_issues) or self._emergency_stopped

    def observe(self, reason: PauseReason, healthy: bool, detail: str = "") -> None:
        was_paused = self.paused
        if healthy:
            self._active_issues.discard(reason)
            self._events.publish(Event("safety.health_restored", {"reason": reason, "detail": detail}))
        else:
            self._active_issues.add(reason)
            self._health_recovery_required = True
            self._events.publish(Event("safety.pause_requested", {"reason": reason, "detail": detail}))
        if not was_paused and self.paused:
            self._events.publish(Event("automation.paused", {"reason": reason, "detail": detail}))
        elif was_paused and not self._active_issues and self._health_recovery_required:
            self._events.publish(Event("automation.resume_available", {"detail": "all health checks restored"}))

    def pause(self, detail: str = "manual pause") -> None:
        self._manual_paused = True
        self._events.publish(Event("automation.paused", {"reason": PauseReason.MANUAL, "detail": detail}))

    def resume(self) -> SafetyDecision:
        if self._emergency_stopped:
            return SafetyDecision(False, "emergency stop must be recovered first")
        if self._active_issues:
            return SafetyDecision(False, "health checks are not restored")
        if not self._manual_paused and not self._health_recovery_required:
            return SafetyDecision(True, "already running")
        self._manual_paused = False
        self._health_recovery_required = False
        self._events.publish(Event("automation.resumed", {}))
        return SafetyDecision(True, "resumed")

    def emergency_stop(self, detail: str) -> None:
        self._emergency_stopped = True
        self._events.publish(Event("automation.emergency_stop", {"detail": detail}))

    def recover_emergency(self, detail: str) -> SafetyDecision:
        if self._active_issues:
            return SafetyDecision(False, "health checks are not restored")
        self._emergency_stopped = False
        self._manual_paused = True
        self._health_recovery_required = False
        self._events.publish(Event("automation.recovery_required", {"detail": detail}))
        return SafetyDecision(True, "emergency cleared; manual resume required")

    def execution_decision(self) -> SafetyDecision:
        if self._emergency_stopped:
            return SafetyDecision(False, "emergency stop active")
        if self._manual_paused:
            return SafetyDecision(False, "automation manually paused")
        if self._health_recovery_required:
            return SafetyDecision(False, "operator resume required after health recovery")
        if self._active_issues:
            return SafetyDecision(False, f"automation paused: {sorted(reason.value for reason in self._active_issues)}")
        return SafetyDecision(True, "automation running")
