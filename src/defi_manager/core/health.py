from dataclasses import dataclass

@dataclass(frozen=True)
class HealthStatus:
    healthy: bool
    detail: str

class HealthMonitor:
    def database_status(self, database: object) -> HealthStatus:
        try:
            database.connection.execute("SELECT 1")  # type: ignore[attr-defined]
        except Exception as exc:
            return HealthStatus(False, f"database unavailable: {exc}")
        return HealthStatus(True, "database reachable")

