from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from defi_manager.core.config import Settings
from defi_manager.core.container import Container
from defi_manager.core.safety import PauseReason


class OperationsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.app = Container.build(Settings(database_path=Path(self.temporary_directory.name) / "manager.sqlite3"))
        self.addCleanup(self.app.database.connection.close)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_scheduler_runs_only_when_automation_is_allowed(self) -> None:
        calls: list[str] = []
        self.app.scheduler.register("scan", 10, lambda: calls.append("scan"))
        self.app.scheduler.run_due(now=0)
        self.app.scheduler.run_due(now=5)
        self.assertEqual(calls, ["scan"])

        self.app.safety.observe(PauseReason.RPC, healthy=False, detail="unavailable")
        self.app.scheduler.run_due(now=10)
        self.assertEqual(calls, ["scan"])
        self.assertEqual(self.app.notifications.sent[-1].title, "Automation paused")

    def test_task_failure_generates_notification_and_audit_event(self) -> None:
        def fail() -> None:
            raise RuntimeError("simulated task failure")

        self.app.scheduler.register("failing", 1, fail)
        self.app.scheduler.run_due(now=0)
        self.assertEqual(self.app.notifications.sent[-1].title, "Scheduled task failed")
        self.assertIn("simulated task failure", self.app.notifications.sent[-1].body)
        self.assertEqual(self.app.audit.all()[-1]["name"], "scheduler.task_failed")
