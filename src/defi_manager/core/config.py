from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
import os
from pathlib import Path

class ConfigurationError(ValueError):
    """Raised when application configuration is unsafe or invalid."""

@dataclass(frozen=True)
class Settings:
    mode: str = "simulation"
    database_path: Path = Path("data/defi-manager.sqlite3")
    log_level: str = "INFO"
    max_trade_notional_usd: Decimal = Decimal("1000")
    max_daily_loss_usd: Decimal = Decimal("100")
    max_slippage_bps: int = 100
    max_module_exposure_usd: Decimal = Decimal("10000")
    max_leverage: Decimal = Decimal("1")
    max_price_impact_bps: int = 500
    max_gas_usd: Decimal = Decimal("100")
    max_asset_exposure_usd: Decimal = Decimal("5000")

    @classmethod
    def from_environment(cls) -> "Settings":
        prefix = "DEFI_MANAGER_"
        mode = os.getenv(f"{prefix}MODE", "simulation").lower()
        if mode != "simulation":
            raise ConfigurationError("Only simulation mode is available in Phase 1")
        try:
            settings = cls(
                mode=mode,
                database_path=Path(os.getenv(f"{prefix}DATABASE_PATH", str(cls.database_path))),
                log_level=os.getenv(f"{prefix}LOG_LEVEL", "INFO").upper(),
                max_trade_notional_usd=Decimal(os.getenv(f"{prefix}MAX_TRADE_NOTIONAL_USD", "1000")),
                max_daily_loss_usd=Decimal(os.getenv(f"{prefix}MAX_DAILY_LOSS_USD", "100")),
                max_slippage_bps=int(os.getenv(f"{prefix}MAX_SLIPPAGE_BPS", "100")),
                max_module_exposure_usd=Decimal(os.getenv(f"{prefix}MAX_MODULE_EXPOSURE_USD", "10000")),
                max_leverage=Decimal(os.getenv(f"{prefix}MAX_LEVERAGE", "1")),
                max_price_impact_bps=int(os.getenv(f"{prefix}MAX_PRICE_IMPACT_BPS", "500")),
                max_gas_usd=Decimal(os.getenv(f"{prefix}MAX_GAS_USD", "100")),
                max_asset_exposure_usd=Decimal(os.getenv(f"{prefix}MAX_ASSET_EXPOSURE_USD", "5000")),
            )
        except (ValueError, ArithmeticError) as exc:
            raise ConfigurationError("Configuration values must be numeric where required") from exc
        if min(settings.max_trade_notional_usd, settings.max_daily_loss_usd, settings.max_module_exposure_usd, settings.max_gas_usd, settings.max_asset_exposure_usd) < 0:
            raise ConfigurationError("Risk limits cannot be negative")
        if settings.max_leverage <= 0:
            raise ConfigurationError("MAX_LEVERAGE must be greater than 0")
        if not 0 <= settings.max_slippage_bps <= 10_000:
            raise ConfigurationError("MAX_SLIPPAGE_BPS must be between 0 and 10000")
        if not 0 <= settings.max_price_impact_bps <= 10_000:
            raise ConfigurationError("MAX_PRICE_IMPACT_BPS must be between 0 and 10000")
        return settings

