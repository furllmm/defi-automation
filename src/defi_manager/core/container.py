from dataclasses import dataclass
from decimal import Decimal
from defi_manager.core.config import Settings
from defi_manager.core.events import EventBus
from defi_manager.core.notifications import InMemoryNotificationSink, NotificationDispatcher
from defi_manager.core.safety import AutomationSafetyController
from defi_manager.core.scheduler import Scheduler
from defi_manager.data.sqlite import AuditRepository, Database
from defi_manager.domain.models import PnLTracker, PortfolioState
from defi_manager.domain.risk import RiskManager, RiskPolicy
from defi_manager.domain.treasury import Treasury
from defi_manager.lending.analyzer import LendingAnalyzer
from defi_manager.lending.models import LendingPolicy
from defi_manager.liquidity.analyzer import LiquidityAnalyzer
from defi_manager.liquidity.models import LiquidityPolicy
from defi_manager.staking.analyzer import StakingAnalyzer
from defi_manager.staking.models import StakingPolicy
from defi_manager.simulation.environment import SimulationEnvironment

@dataclass
class Container:
    settings: Settings
    database: Database
    events: EventBus
    audit: AuditRepository
    portfolio: PortfolioState
    pnl: PnLTracker
    treasury: Treasury
    risk: RiskManager
    safety: AutomationSafetyController
    scheduler: Scheduler
    notifications: InMemoryNotificationSink
    lending: LendingAnalyzer
    staking: StakingAnalyzer
    liquidity: LiquidityAnalyzer
    simulation: SimulationEnvironment

    @classmethod
    def build(cls, settings: Settings) -> "Container":
        database = Database(settings.database_path)
        database.migrate()
        events = EventBus()
        audit = AuditRepository(database)
        events.subscribe("*", audit.record)
        portfolio, pnl, treasury = PortfolioState(), PnLTracker(), Treasury.default()
        treasury.validate()
        risk = RiskManager(RiskPolicy(settings.max_trade_notional_usd, settings.max_daily_loss_usd, settings.max_slippage_bps))
        safety = AutomationSafetyController(events)
        scheduler = Scheduler(safety, events)
        notifications = InMemoryNotificationSink()
        NotificationDispatcher(events, notifications)
        lending = LendingAnalyzer(LendingPolicy(Decimal("0.70"), Decimal("1.50"), Decimal("1.15"), Decimal("1000"), Decimal("100")), events)
        staking = StakingAnalyzer(StakingPolicy(Decimal("1"), True, Decimal("1")), events)
        liquidity = LiquidityAnalyzer(LiquidityPolicy(Decimal("10000"), Decimal("5000"), Decimal("0.50"), Decimal("1")), events)
        simulation = SimulationEnvironment(portfolio, pnl, risk, events, safety)
        return cls(settings, database, events, audit, portfolio, pnl, treasury, risk, safety, scheduler, notifications, lending, staking, liquidity, simulation)
