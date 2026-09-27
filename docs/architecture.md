# Phase 1 Architecture

## Execution flow

```text
Proposal -> ExecutionIntent -> RiskManager -> SimulationEnvironment
                                 |              |
                              rejected        approved
                                 |              |
                                 +--> Audit/Event store
                                                |
                                  PortfolioState -> PnLTracker
```

`RiskManager` is owned by the application composition root, not by a strategy or AI component. `SimulationEnvironment.execute()` evaluates the intent immediately before recording a fill; callers cannot provide an approval flag.

## Data and recovery

SQLite migrations are versioned and run before application services are created. Domain-relevant events are appended to `audit_events` as JSON payloads. Migrations are forward-only.

## Boundaries

* `core`: configuration, lifecycle composition, events, logging, and health.
* `data`: SQLite migration and audit repository.
* `domain`: pure portfolio, PnL, treasury, execution, and risk policies.
* `simulation`: deterministic paper-only state transitions.

Secrets are not modelled in Phase 1. Future credential providers must return opaque signing handles and not expose raw secret material to AI or logging code.

## Phase 2 paper-trading boundary

`adapters.dex.DexAdapter` supports quote retrieval only. Its fixed-price
implementation is deterministic and exists for local simulations/tests. The
backtest runner uses its own in-memory `PortfolioState`; it does not use a
wallet, the simulation execution environment, or any transaction sender.

## Automation safety boundary

`AutomationSafetyController` is an execution gate owned by the application
container. The simulation environment evaluates this gate before risk rules
and before any portfolio mutation. It fails closed for reported health issues
and emergency stops; state recovery requires an explicit operator resume.

## Lending analysis boundary

Lending adapters currently expose only `snapshot()`. `LendingAnalyzer` turns a
snapshot into an audited recommendation using health-factor, LTV, debt, and
liquidity limits. No decision itself is a protocol call, and the module has no
signer or transaction submission capability.

## Staking analysis boundary

Staking adapters currently expose only `snapshot()`. `StakingAnalyzer` compares
pending rewards with claim/restake costs and creates an audited recommendation.
There is no protocol mutation or signing code in this module.
