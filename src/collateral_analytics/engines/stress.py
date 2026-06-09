"""Standard implementation of stress testing engine."""

from datetime import date
from decimal import Decimal
from typing import Any

from collateral_analytics.engines.base import BaseStressEngine
from collateral_analytics.models.exposure import ExposureAnalysisResult
from collateral_analytics.models.haircut_assessment import HaircutReport
from collateral_analytics.models.stress import (
    StressResult,
    StressScenario,
    StressTestReport,
)
from collateral_analytics.utils.logging import configure_logging

logger = configure_logging(__name__)

# Predefined scenarios
SCENARIO_RATE_SHOCK = StressScenario(
    scenario_id="rate_shock",
    scenario_name="Interest Rate Shock",
    description="Market interest rates increase by 100 basis points",
    haircut_shock=Decimal("0.03"),
    spread_shock_bps=100,
)

SCENARIO_SPREAD_SHOCK = StressScenario(
    scenario_id="spread_shock",
    scenario_name="Credit Spread Widening",
    description="Credit spreads widen by 200 basis points",
    haircut_shock=Decimal("0.05"),
    spread_shock_bps=200,
)

SCENARIO_DOWNGRADE = StressScenario(
    scenario_id="downgrade",
    scenario_name="Single Notch Downgrade",
    description="All counterparties downgraded 1 rating notch",
    rating_downgrade_notches=1,
    haircut_shock=Decimal("0.10"),
)

SCENARIO_MARKET_SHOCK = StressScenario(
    scenario_id="market_shock",
    scenario_name="Market Value Decline",
    description="Market values decline by 10%",
    market_value_shock=Decimal("-0.10"),
)

DEFAULT_SCENARIOS = [
    SCENARIO_RATE_SHOCK,
    SCENARIO_SPREAD_SHOCK,
    SCENARIO_DOWNGRADE,
    SCENARIO_MARKET_SHOCK,
]


class StandardStressEngine(BaseStressEngine):
    """Standard implementation of stress testing."""

    def __init__(self, reference_date: date | None = None):
        """Initialize stress engine.

        Args:
            reference_date: Date for calculations (defaults to today)
        """
        self.reference_date = reference_date or date.today()
        logger.info(f"StandardStressEngine initialized for {self.reference_date}")

    def stress(self, **kwargs: Any) -> StressTestReport:
        """Run stress tests on portfolio.

        Args:
            exposure_result: ExposureAnalysisResult with base case exposures
            haircut_report: HaircutReport with base case haircuts
            scenarios: List of StressScenario (defaults to predefined scenarios)

        Returns:
            StressTestReport with scenario results
        """
        exposure_result = kwargs.get("exposure_result")
        haircut_report = kwargs.get("haircut_report")
        scenarios = kwargs.get("scenarios", DEFAULT_SCENARIOS)

        if not isinstance(exposure_result, ExposureAnalysisResult):
            return StressTestReport(
                scenarios=[],
                results={},
                success=False,
                errors=["exposure_result parameter required"],
            )

        if not isinstance(haircut_report, HaircutReport):
            return StressTestReport(
                scenarios=[],
                results={},
                success=False,
                errors=["haircut_report parameter required"],
            )

        try:
            results: dict[tuple[str, str], StressResult] = {}
            worst_scenario = ""
            worst_impact = Decimal("0")
            breached_count = 0
            total_unsecured_delta = Decimal("0")
            impact_deltas = []

            for scenario in scenarios:
                for cp_id, snapshot in exposure_result.snapshots.items():
                    # Calculate base coverage ratio
                    base_coverage = (
                        (snapshot.adjusted_collateral_value / snapshot.net_exposure)
                        if snapshot.net_exposure > 0
                        else Decimal("0")
                    )

                    # Calculate stressed haircut
                    base_haircut = (
                        (haircut_report.total_haircut_amount / haircut_report.total_market_value)
                        if haircut_report.total_market_value > 0
                        else Decimal("0")
                    )
                    stressed_haircut = min(Decimal("1"), base_haircut + scenario.haircut_shock)

                    # Calculate stressed collateral value
                    base_collateral = snapshot.adjusted_collateral_value
                    market_value_adjustment = Decimal("1") + scenario.market_value_shock
                    stressed_collateral = base_collateral * market_value_adjustment
                    stressed_collateral *= Decimal("1") - stressed_haircut

                    # Calculate stressed exposure (simplified: assume exposure unchanged)
                    stressed_exposure = snapshot.net_exposure

                    # Calculate stressed coverage ratio
                    stressed_coverage = (
                        (stressed_collateral / stressed_exposure)
                        if stressed_exposure > 0
                        else Decimal("0")
                    )

                    # Calculate deltas
                    coverage_delta = stressed_coverage - base_coverage

                    # Base case unsecured/excess
                    unsecured_base = max(
                        Decimal("0"), snapshot.net_exposure - snapshot.adjusted_collateral_value
                    )
                    excess_base = max(
                        Decimal("0"), snapshot.adjusted_collateral_value - snapshot.net_exposure
                    )

                    # Stressed case
                    unsecured_stressed = max(Decimal("0"), stressed_exposure - stressed_collateral)
                    excess_stressed = max(Decimal("0"), stressed_collateral - stressed_exposure)
                    unsecured_delta = unsecured_stressed - unsecured_base
                    excess_delta = excess_stressed - excess_base

                    breached = stressed_coverage < Decimal("1")

                    result = StressResult(
                        counterparty_id=cp_id,
                        scenario_id=scenario.scenario_id,
                        base_coverage_ratio=base_coverage,
                        stress_coverage_ratio=stressed_coverage,
                        coverage_ratio_delta=coverage_delta,
                        base_unsecured_exposure=unsecured_base,
                        stress_unsecured_exposure=unsecured_stressed,
                        unsecured_exposure_delta=unsecured_delta,
                        base_excess_collateral=excess_base,
                        stress_excess_collateral=excess_stressed,
                        excess_collateral_delta=excess_delta,
                        coverage_breached=breached,
                    )

                    results[(cp_id, scenario.scenario_id)] = result
                    impact_deltas.append(coverage_delta)
                    total_unsecured_delta += unsecured_delta

                    if breached:
                        breached_count += 1

                    # Track worst case
                    if abs(coverage_delta) > abs(worst_impact):
                        worst_impact = coverage_delta
                        worst_scenario = scenario.scenario_id

            # Calculate average coverage decline
            avg_decline: Decimal = (
                Decimal(str(float(sum(impact_deltas) / len(impact_deltas))))
                if impact_deltas
                else Decimal("0")
            )

            logger.info(
                f"Stress test completed: {len(scenarios)} scenarios, worst impact {worst_impact}"
            )

            return StressTestReport(
                scenarios=scenarios,
                results=results,
                worst_case_scenario=worst_scenario,
                worst_case_impact=worst_impact,
                num_counterparties_breached=breached_count,
                total_unsecured_impact=total_unsecured_delta,
                average_coverage_decline=avg_decline,
                success=True,
            )

        except Exception as e:
            logger.error(f"Stress test failed: {e}")
            return StressTestReport(
                scenarios=scenarios,
                results={},
                success=False,
                errors=[str(e)],
            )
