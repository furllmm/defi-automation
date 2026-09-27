from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from defi_manager.core.config import Settings
from defi_manager.core.container import Container
from defi_manager.domain.models import ExecutionIntent

def main() -> int:
    with TemporaryDirectory() as directory:
        app = Container.build(Settings(database_path=Path(directory) / "selftest.sqlite3"))
        app.portfolio.cash_usd = Decimal("1000")
        decision = app.simulation.execute(ExecutionIntent("ETH", "buy", Decimal("0.1"), Decimal("2000"), 20, Decimal("1")))
        assert decision.allowed
        assert app.portfolio.cash_usd == Decimal("799")
        assert app.portfolio.positions["ETH"].quantity == Decimal("0.1")
        assert len(app.audit.all()) == 2
    print("self-test passed")
    return 0

