"""Domain models for collateral coverage and sufficiency assessment."""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass
class CoverageAssessment:
    """Coverage analysis for a single counterparty.

    Attributes:
        counterparty_id: Unique counterparty identifier
        counterparty_name: Counterparty name
        net_exposure: Net exposure amount (post-haircut offset)
        adjusted_collateral_value: Haircut-adjusted collateral value
        coverage_ratio: Ratio of collateral to exposure (adjusted_collateral / net_exposure)
        unsecured_exposure: Exposure not covered by collateral (max(0, net_exposure - collateral))
        excess_collateral: Collateral in excess of exposure (max(0, collateral - net_exposure))
        is_covered: Whether exposure is fully covered (coverage_ratio >= 1.0)
        haircut_impact: Coverage ratio without haircuts (haircut impact analysis)
        haircut_basis_points: Total haircut benefit in basis points
        metadata: Additional context
    """

    counterparty_id: str
    counterparty_name: str
    net_exposure: Decimal
    adjusted_collateral_value: Decimal
    coverage_ratio: Decimal
    unsecured_exposure: Decimal
    excess_collateral: Decimal
    is_covered: bool
    haircut_impact: Decimal = Decimal("0")
    haircut_basis_points: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CoverageReport:
    """Portfolio-level coverage summary.

    Attributes:
        assessments: Dict mapping counterparty_id → CoverageAssessment
        total_counterparties: Number of counterparties assessed
        total_net_exposure: Sum of all net exposures
        total_adjusted_collateral: Sum of all adjusted collateral values
        portfolio_coverage_ratio: Portfolio-level coverage (total collateral / total exposure)
        total_unsecured_exposure: Sum of all unsecured exposures (shortfall)
        total_excess_collateral: Sum of all excess collateral
        counterparties_covered: Count fully covered (ratio >= 1.0)
        counterparties_undercovered: Count with shortfall (ratio < 1.0)
        average_coverage_ratio: Mean coverage across counterparties
        min_coverage_ratio: Lowest coverage ratio
        max_coverage_ratio: Highest coverage ratio
        haircut_benefit: Total benefit from haircuts (bp reduction in coverage gap)
        success: Whether assessment completed successfully
        errors: Error messages if assessment failed
        warnings: Non-fatal warnings during assessment
    """

    assessments: dict[str, CoverageAssessment]
    total_counterparties: int = 0
    total_net_exposure: Decimal = Decimal("0")
    total_adjusted_collateral: Decimal = Decimal("0")
    portfolio_coverage_ratio: Decimal = Decimal("0")
    total_unsecured_exposure: Decimal = Decimal("0")
    total_excess_collateral: Decimal = Decimal("0")
    counterparties_covered: int = 0
    counterparties_undercovered: int = 0
    average_coverage_ratio: Decimal = Decimal("0")
    min_coverage_ratio: Decimal = Decimal("1")
    max_coverage_ratio: Decimal = Decimal("0")
    haircut_benefit: Decimal = Decimal("0")
    success: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
