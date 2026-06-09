"""Domain models for counterparty exposure analysis."""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass
class ExposureSnapshot:
    """Point-in-time exposure view for a single counterparty."""

    counterparty_id: str
    counterparty_name: str
    gross_exposure: Decimal
    adjusted_collateral_value: Decimal
    net_exposure: Decimal
    utilisation_ratio: Decimal
    unsecured_exposure: Decimal
    concentration_ratio: Decimal
    exposure_limit: Decimal
    available_capacity: Decimal
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_at_limit(self) -> bool:
        """Check if counterparty is at or above exposure limit."""
        return self.net_exposure >= self.exposure_limit

    def is_over_limit(self) -> bool:
        """Check if counterparty exceeds exposure limit."""
        return self.net_exposure > self.exposure_limit

    def has_capacity(self) -> bool:
        """Check if counterparty has available capacity."""
        return self.available_capacity > 0


@dataclass
class ExposureMetrics:
    """Aggregated exposure metrics across entire portfolio."""

    portfolio_gross_exposure: Decimal
    portfolio_adjusted_collateral: Decimal
    portfolio_net_exposure: Decimal
    total_collateral_value: Decimal
    total_counterparties: int
    average_utilisation: Decimal
    max_utilisation: Decimal
    counterparties_at_limit: int
    counterparties_over_limit: int
    herfindahl_index: Decimal
    largest_counterparty_concentration: Decimal
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RankingResult:
    """Exposure ranking result."""

    rank: int
    counterparty_id: str
    counterparty_name: str
    metric_value: Decimal
    metric_name: str
    percentile: Decimal = Decimal("0")


@dataclass
class ExposureAnalysisResult:
    """Complete exposure analysis output."""

    snapshots: dict[str, ExposureSnapshot]
    metrics: ExposureMetrics
    rankings_by_gross_exposure: list[RankingResult]
    rankings_by_net_exposure: list[RankingResult]
    rankings_by_utilisation: list[RankingResult]
    rankings_by_concentration: list[RankingResult]
    success: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
