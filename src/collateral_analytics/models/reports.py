"""Domain models for reporting layer.

All monetary values stored as Decimal (natural form).
All rates stored as decimals: 0.05 = 5%, 1.5 = 150%.
See docs/conventions.md for numerical representation standards.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal


@dataclass
class ExposureReportSummary:
    """Summary of counterparty exposures.

    Attributes:
        total_exposure: Sum of all counterparty exposures in EUR
        avg_exposure: Average exposure across counterparties in EUR
        min_exposure: Minimum exposure in EUR
        max_exposure: Maximum exposure in EUR
        top_3_exposures: List of (counterparty_id, exposure) tuples for top 3
        counterparties_at_limit: Count of counterparties at or above limit
    """

    total_exposure: Decimal
    avg_exposure: Decimal
    min_exposure: Decimal
    max_exposure: Decimal
    top_3_exposures: list[tuple[str, Decimal]] = field(default_factory=list)
    counterparties_at_limit: int = 0


@dataclass
class EligibilityReportSummary:
    """Summary of collateral eligibility decisions.

    Attributes:
        total_positions: Total number of collateral positions assessed
        eligible_positions: Count of eligible positions
        rejected_positions: Count of rejected positions
        eligibility_rate: Eligible / total ratio
        rejection_reasons: Dict mapping reason code to count
    """

    total_positions: int
    eligible_positions: int
    rejected_positions: int
    eligibility_rate: Decimal
    rejection_reasons: dict[str, int] = field(default_factory=dict)


@dataclass
class HaircutReportSummary:
    """Summary of haircut application.

    Attributes:
        total_market_value: Sum of all collateral market values
        total_haircut_amount: Total haircut deducted in EUR
        avg_haircut_rate: Average haircut rate across portfolio
        min_haircut_rate: Minimum haircut rate
        max_haircut_rate: Maximum haircut rate
        total_adjusted_value: Total value after haircuts
    """

    total_market_value: Decimal
    total_haircut_amount: Decimal
    avg_haircut_rate: Decimal
    min_haircut_rate: Decimal
    max_haircut_rate: Decimal
    total_adjusted_value: Decimal


@dataclass
class CoverageReportSummary:
    """Summary of collateral coverage.

    Attributes:
        total_exposure: Sum of net exposures
        total_collateral: Sum of adjusted collateral
        portfolio_coverage_ratio: Total collateral / total exposure
        covered_counterparties: Count with coverage >= 1.0
        undercovered_counterparties: Count with coverage < 1.0
        total_shortfall: Sum of unsecured exposures
        total_excess: Sum of excess collateral
    """

    total_exposure: Decimal
    total_collateral: Decimal
    portfolio_coverage_ratio: Decimal
    covered_counterparties: int
    undercovered_counterparties: int
    total_shortfall: Decimal
    total_excess: Decimal


@dataclass
class ConcentrationReportSummary:
    """Summary of concentration risk.

    Attributes:
        issuer_concentration_count: Count of issuer concentrations above 20%
        asset_type_concentration_count: Count of asset type concentrations above 15%
        rating_concentration_count: Count of rating concentrations above 25%
        counterparty_concentration_count: Count of counterparty concentrations above 30%
        herfindahl_index: Overall portfolio concentration index (0-1)
        top_concentration: (dimension, value, ratio) with highest concentration
    """

    issuer_concentration_count: int
    asset_type_concentration_count: int
    rating_concentration_count: int
    counterparty_concentration_count: int
    herfindahl_index: Decimal
    top_concentration: tuple[str, str, Decimal] | None = None


@dataclass
class StressReportSummary:
    """Summary of stress test results.

    Attributes:
        total_scenarios: Number of stress scenarios tested
        coverage_breaches: Count of scenarios causing coverage < 1.0
        worst_case_scenario: Name of scenario with largest coverage impact
        worst_case_coverage_decline: Coverage ratio decline in worst scenario
        avg_coverage_decline: Average coverage decline across all scenarios
    """

    total_scenarios: int
    coverage_breaches: int
    worst_case_scenario: str
    worst_case_coverage_decline: Decimal
    avg_coverage_decline: Decimal


@dataclass
class MonitoringReportSummary:
    """Summary of monitoring findings.

    Attributes:
        num_anomalies: Count of detected anomalies
        num_critical_warnings: Count of critical severity items
        num_early_warnings: Count of early warnings triggered
        has_coverage_risk: Boolean indicating coverage < 1.0 for any counterparty
        has_concentration_risk: Boolean indicating concentration above thresholds
    """

    num_anomalies: int
    num_critical_warnings: int
    num_early_warnings: int
    has_coverage_risk: bool
    has_concentration_risk: bool


@dataclass
class PortfolioSummaryReport:
    """Executive summary across all analytics modules.

    Attributes:
        reference_date: Date for which analytics are calculated
        exposure_summary: Exposure metrics
        eligibility_summary: Collateral eligibility metrics
        haircut_summary: Haircut application metrics
        coverage_summary: Collateral coverage metrics
        concentration_summary: Concentration risk metrics
        stress_summary: Stress test metrics
        monitoring_summary: Monitoring findings
        overall_risk_level: Aggregate risk assessment ('low', 'medium', 'high', 'critical')
        key_findings: List of critical items requiring attention
    """

    reference_date: date
    exposure_summary: ExposureReportSummary
    eligibility_summary: EligibilityReportSummary
    haircut_summary: HaircutReportSummary
    coverage_summary: CoverageReportSummary
    concentration_summary: ConcentrationReportSummary
    stress_summary: StressReportSummary
    monitoring_summary: MonitoringReportSummary
    overall_risk_level: str
    key_findings: list[str] = field(default_factory=list)
