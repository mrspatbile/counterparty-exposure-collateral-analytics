"""Domain models for stress testing and scenario analysis."""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass
class StressScenario:
    """Stress test scenario definition.

    Attributes:
        scenario_id: Unique scenario identifier
        scenario_name: Human-readable name
        description: Scenario description and assumptions
        haircut_shock: Additional haircut to apply (0.05 = +5%)
        spread_shock_bps: Spread shock in basis points (100 = +100bps)
        rating_downgrade_notches: Number of rating notches to downgrade
        market_value_shock: Market value change as decimal (-0.10 = -10% market value)
        metadata: Additional scenario parameters
    """

    scenario_id: str
    scenario_name: str
    description: str = ""
    haircut_shock: Decimal = Decimal("0")
    spread_shock_bps: int = 0
    rating_downgrade_notches: int = 0
    market_value_shock: Decimal = Decimal("0")
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class StressResult:
    """Impact of a single stress scenario on a counterparty.

    Attributes:
        counterparty_id: Counterparty identifier
        scenario_id: Scenario applied
        base_coverage_ratio: Original coverage ratio (pre-stress)
        stress_coverage_ratio: Coverage ratio under stress
        coverage_ratio_delta: Change in coverage ratio
        base_unsecured_exposure: Original unsecured exposure
        stress_unsecured_exposure: Unsecured exposure under stress
        unsecured_exposure_delta: Change in unsecured exposure
        base_excess_collateral: Original excess collateral
        stress_excess_collateral: Excess collateral under stress
        excess_collateral_delta: Change in excess collateral
        coverage_breached: Whether coverage ratio falls below 1.0 under stress
        metadata: Additional context (individual shock impacts)
    """

    counterparty_id: str
    scenario_id: str
    base_coverage_ratio: Decimal
    stress_coverage_ratio: Decimal
    coverage_ratio_delta: Decimal
    base_unsecured_exposure: Decimal
    stress_unsecured_exposure: Decimal
    unsecured_exposure_delta: Decimal
    base_excess_collateral: Decimal
    stress_excess_collateral: Decimal
    excess_collateral_delta: Decimal
    coverage_breached: bool
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class StressTestReport:
    """Portfolio-level stress test results.

    Attributes:
        scenarios: Applied stress scenarios
        results: Dict mapping (counterparty_id, scenario_id) → StressResult
        worst_case_scenario: Scenario with largest portfolio impact
        worst_case_impact: Largest coverage ratio decline across all combinations
        num_counterparties_breached: Count where coverage drops below 1.0 in any scenario
        total_unsecured_impact: Total increase in unsecured exposure across all scenarios
        average_coverage_decline: Mean coverage ratio change across all counterparties/scenarios
        success: Whether stress test completed successfully
        errors: Error messages if test failed
        warnings: Non-fatal warnings during testing
    """

    scenarios: list[StressScenario]
    results: dict[tuple[str, str], StressResult]
    worst_case_scenario: str = ""
    worst_case_impact: Decimal = Decimal("0")
    num_counterparties_breached: int = 0
    total_unsecured_impact: Decimal = Decimal("0")
    average_coverage_decline: Decimal = Decimal("0")
    success: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
