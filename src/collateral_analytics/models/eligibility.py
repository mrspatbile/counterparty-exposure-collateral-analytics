"""Domain models for collateral eligibility assessment."""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass
class EligibilityRule:
    """Configurable eligibility rule for collateral assessment.

    Attributes:
        allowed_asset_types: Set of eligible asset types (None = all allowed)
        allowed_currencies: Set of eligible currencies (None = all allowed)
        allowed_ratings: Set of eligible ratings (None = all allowed)
        min_rating: Minimum acceptable rating (None = no minimum)
        max_maturity_years: Maximum maturity in years (None = no limit)
        require_market_value: Whether market_value must be positive
        min_market_value: Minimum acceptable market value (None = no minimum)
        description: Human-readable rule description
    """

    allowed_asset_types: set[str] | None = None
    allowed_currencies: set[str] | None = None
    allowed_ratings: set[str] | None = None
    min_rating: str | None = None
    max_maturity_years: int | None = None
    require_market_value: bool = True
    min_market_value: Decimal | None = None
    description: str = "Default eligibility rule"
    metadata: dict[str, Any] = field(default_factory=dict)

    def allows_asset_type(self, asset_type: str) -> bool:
        """Check if asset type is allowed."""
        if self.allowed_asset_types is None:
            return True
        return asset_type.lower() in self.allowed_asset_types

    def allows_currency(self, currency: str) -> bool:
        """Check if currency is allowed."""
        if self.allowed_currencies is None:
            return True
        return currency.upper() in self.allowed_currencies

    def allows_rating(self, rating: str) -> bool:
        """Check if rating is allowed."""
        if self.allowed_ratings is None:
            return True
        return rating in self.allowed_ratings

    def allows_maturity(self, maturity_years: int) -> bool:
        """Check if maturity is within limits."""
        if self.max_maturity_years is None:
            return True
        return maturity_years <= self.max_maturity_years

    def allows_market_value(self, market_value: Decimal) -> bool:
        """Check if market value meets requirements."""
        if self.require_market_value and market_value <= 0:
            return False
        if self.min_market_value is not None and market_value < self.min_market_value:
            return False
        return True


@dataclass
class EligibilityDecision:
    """Result of eligibility assessment for a single security.

    Attributes:
        isin: International Securities Identification Number
        eligible: Whether collateral is eligible
        reason_code: Code explaining decision (e.g., ELIGIBLE, RATING_BELOW_THRESHOLD)
        explanation: Human-readable explanation
        rule_applied: Description of which rule triggered decision
        metadata: Additional context (failing checks, etc.)
    """

    isin: str
    eligible: bool
    reason_code: str
    explanation: str
    rule_applied: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EligibilityAssessmentResult:
    """Complete eligibility assessment output.

    Attributes:
        decisions: Dict mapping ISIN → EligibilityDecision
        eligible_count: Number of eligible securities
        ineligible_count: Number of ineligible securities
        total_assessed: Total securities assessed
        success: Whether assessment completed successfully
        errors: Error messages if assessment failed
        warnings: Non-fatal warnings during assessment
    """

    decisions: dict[str, EligibilityDecision]
    eligible_count: int = 0
    ineligible_count: int = 0
    total_assessed: int = 0
    success: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
