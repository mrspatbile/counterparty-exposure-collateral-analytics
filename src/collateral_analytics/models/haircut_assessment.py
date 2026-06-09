"""Domain models for haircut calculation and assessment."""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass
class HaircutAssessment:
    """Haircut calculation for a single security.

    Attributes:
        isin: International Securities Identification Number
        asset_type: Type of asset (e.g., 'sovereign', 'corporate_bond')
        maturity_bucket: Maturity bracket (e.g., '5-10y', '10y+')
        rating_bucket: Credit quality bracket (e.g., 'AAA-AA', 'BBB')
        market_value: Original market value in EUR
        haircut_rate: Applied haircut as decimal (0.15 = 15% haircut)
        haircut_amount: Absolute haircut amount (market_value × haircut_rate)
        adjusted_value: Post-haircut value (market_value × (1 - haircut_rate))
        metadata: Additional context (lookup results, warnings)
    """

    isin: str
    asset_type: str
    maturity_bucket: str
    rating_bucket: str
    market_value: Decimal
    haircut_rate: Decimal
    haircut_amount: Decimal
    adjusted_value: Decimal
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class HaircutReport:
    """Portfolio-level haircut summary.

    Attributes:
        assessments: Dict mapping ISIN → HaircutAssessment
        total_securities: Number of securities assessed
        total_market_value: Sum of all market values
        total_haircut_amount: Sum of all haircuts applied
        total_adjusted_value: Sum of all adjusted values
        average_haircut_rate: Weighted average haircut (haircuts / market_value)
        min_haircut_rate: Minimum haircut applied
        max_haircut_rate: Maximum haircut applied
        securities_with_zero_haircut: Count of securities with no haircut
        missing_schedule_entries: Count where no schedule rule found
        success: Whether calculation completed successfully
        errors: Error messages if calculation failed
        warnings: Non-fatal warnings (missing schedule entries, etc.)
    """

    assessments: dict[str, HaircutAssessment]
    total_securities: int = 0
    total_market_value: Decimal = Decimal("0")
    total_haircut_amount: Decimal = Decimal("0")
    total_adjusted_value: Decimal = Decimal("0")
    average_haircut_rate: Decimal = Decimal("0")
    min_haircut_rate: Decimal = Decimal("1")
    max_haircut_rate: Decimal = Decimal("0")
    securities_with_zero_haircut: int = 0
    missing_schedule_entries: int = 0
    success: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
