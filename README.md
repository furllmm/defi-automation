# AI DeFi Manager

Safety-first, local-first foundation for an automated DeFi manager. It implements the Phase 1 foundation (configuration, persistence, event auditing, deterministic simulation, portfolio/PnL, treasury allocation, and a non-bypassable rule-based risk gate) plus Phase 2 paper-trading primitives.

> **No live trading is implemented.** The project does not store seed phrases or private keys, does not sign transactions, and must not be treated as financial advice.

## Quick start

Requires Python 3.11 or later.

```bash
cp .env.example .env
python -m venv .venv
. .venv/bin/activate
pip install -e .
defi-manager selftest
PYTHONPATH=src python -m unittest discover -s tests -v
```

The self-test creates an isolated SQLite database, submits a simulated trade, and verifies that the risk gate, PnL, portfolio state, and audit event work together.

## Safety model

All execution intents must pass through `RiskManager.evaluate()` before simulation mutates portfolio state. A rejected intent cannot be executed. Future AI components can propose intents but cannot receive secrets, alter risk limits, or sign transactions.

## Configuration

Copy `.env.example` to `.env`. Environment variables use the `DEFI_MANAGER_` prefix. The default mode is `simulation`; `live` is rejected because no live executor exists.

## Development containers

```bash
docker compose run --rm app
# or: podman compose run --rm app
```

## Phase 2 paper trading

Phase 2 provides a read-only DEX quote contract, deterministic fixed-price
and market-data adapters for local use, a strategy registry, MA-crossover
strategy, and a RSI strategy, plus a long-only backtest runner with optional stop-loss,
take-profit, cooldown, fee/slippage, drawdown, win-rate, and profit-factor
metrics. Paper execution is routed through the same safety and risk gate as
simulation, while market-data providers remain strictly read-only. They are
deliberately paper-only: no adapter has a
transaction-submission method and the backtest owns isolated in-memory state.

Lending, staking, liquidity mining, AI, wallets, and live execution remain
deliberately out of scope until their dedicated safety layers are approved.

## Automation safety controls

The simulation gate fails closed when network, RPC, AI, clock, battery, or
resource health checks report a problem. An emergency stop blocks all new
simulated execution. Health recovery does not silently resume a manually
paused or emergency-stopped system: an operator must explicitly resume after
recovery.

## Scheduled paper automation and notifications

`Scheduler` provides deterministic `run_due()` ticks and an optional daemon
thread for local/headless use. Every scheduled task is blocked by the same
automation safety gate. Failed tasks and safety events are recorded in the
audit store and routed through a notification sink. The bundled in-memory sink
is test-only; desktop, webhook, Telegram, and email integrations remain future
adapter work.

## Lending analysis (read-only)

The lending module accepts protocol snapshots through a read-only adapter
contract and calculates LTV, health factor, and annual net yield. Its policy
engine can only emit `monitor`, `block_new_debt`, `deleveraging_required`, or
`emergency_repay_required` recommendations. It does not supply, borrow, repay,
or sign transactions.

## Staking analysis (read-only)

The staking module evaluates pending rewards against claim/restake gas, APR/APY,
lock periods, and unstaking delays. It can recommend `defer_claim`,
`claim_rewards`, or `claim_and_restake`; these are audit-logged recommendations
only. The module cannot stake, unstake, claim, restake, or sign transactions.

## Liquidity mining analysis (read-only)

Pool snapshots are evaluated using TVL, available liquidity, volatility, fees,
rewards, impermanent-loss estimate, gas, and insurance costs. The analyzer only
recommends `consider_liquidity`, `avoid_pool`, or `monitor`; it cannot add,
remove, rebalance, claim, or sign transactions.
