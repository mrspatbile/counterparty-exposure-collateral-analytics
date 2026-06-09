"""Domain models for concentration risk analysis."""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass
class ConcentrationMetric:
    """Concentration data for a single dimension (issuer/asset/rating).

    Attributes:
        dimension_value: The category value (e.g., 'Germany', 'sovereign', 'AAA')
        dimension_type: Type of dimension ('issuer', 'asset_type', 'rating', 'counterparty')
        count: Number of securities/positions in this category
        gross_exposure: Sum of gross exposures
        net_exposure: Sum of net exposures
        adjusted_collateral: Sum of adjusted collateral values
        concentration_ratio: This category's net exposure / total portfolio net exposure
        concentration_percent: concentration_ratio × 100
        rank: Position in ranking (1 = highest concentration)
        herfindahl_contribution: Contribution to portfolio Herfindahl index
        is_flagged: Whether concentration exceeds threshold (threshold-dependent)
        flag_reason: Reason for flag if flagged
        metadata: Additional context
    """

    dimension_value: str
    dimension_type: str
    count: int
    gross_exposure: Decimal
    net_exposure: Decimal
    adjusted_collateral: Decimal
    concentration_ratio: Decimal
    concentration_percent: Decimal
    rank: int = 0
    herfindahl_contribution: Decimal = Decimal("0")
    is_flagged: bool = False
    flag_reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConcentrationAnalysis:
    """Complete concentration risk analysis.

    Attributes:
        by_issuer: List of ConcentrationMetric for each issuer
        by_asset_type: List of ConcentrationMetric for each asset type
        by_rating: List of ConcentrationMetric for each rating
        by_counterparty: List of ConcentrationMetric for each counterparty
        portfolio_herfindahl_index: Sum of squared concentration ratios
        portfolio_net_exposure: Total portfolio net exposure
        top_n_concentration: Sum of top N counterparties (concentration risk)
        num_issuers: Total number of unique issuers
        num_asset_types: Total number of asset types
        num_ratings: Total number of ratings
        num_counterparties: Total number of counterparties
        flagged_count: Number of metrics exceeding thresholds
        success: Whether analysis completed successfully
        errors: Error messages if analysis failed
        warnings: Non-fatal warnings during analysis
    """

    by_issuer: list[ConcentrationMetric] = field(default_factory=list)
    by_asset_type: list[ConcentrationMetric] = field(default_factory=list)
    by_rating: list[ConcentrationMetric] = field(default_factory=list)
    by_counterparty: list[ConcentrationMetric] = field(default_factory=list)
    portfolio_herfindahl_index: Decimal = Decimal("0")
    portfolio_net_exposure: Decimal = Decimal("0")
    top_n_concentration: Decimal = Decimal("0")
    num_issuers: int = 0
    num_asset_types: int = 0
    num_ratings: int = 0
    num_counterparties: int = 0
    flagged_count: int = 0
    success: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
