"""Standard implementation of collateral eligibility assessment."""

from datetime import date
from decimal import Decimal
from typing import Any

from collateral_analytics.engines.base import BaseEligibilityEngine
from collateral_analytics.loaders.data_manager import AnalyticsDataset
from collateral_analytics.models.eligibility import (
    EligibilityAssessmentResult,
    EligibilityDecision,
    EligibilityRule,
)
from collateral_analytics.utils.logging import configure_logging

logger = configure_logging(__name__)

REASON_CODES = {
    "ELIGIBLE": "Collateral meets all eligibility criteria",
    "MISSING_MARKET_VALUE": "Market value is missing or zero",
    "UNSUPPORTED_ASSET_TYPE": "Asset type not in allowed list",
    "RATING_BELOW_THRESHOLD": "Credit rating below minimum acceptable",
    "CURRENCY_NOT_ALLOWED": "Currency not in allowed list",
    "MATURITY_EXCEEDS_LIMIT": "Maturity exceeds maximum allowed",
    "INELIGIBLE": "Does not meet eligibility criteria",
}


class ConfigurableEligibilityEngine(BaseEligibilityEngine):
    """Configurable eligibility assessment engine."""

    def __init__(self, rule: EligibilityRule | None = None, reference_date: date | None = None):
        """Initialize engine with eligibility rule.

        Args:
            rule: EligibilityRule to apply (uses default if None)
            reference_date: Date for maturity calculations (defaults to today)
        """
        self.rule = rule or self._default_rule()
        self.reference_date = reference_date or date.today()
        logger.info(f"ConfigurableEligibilityEngine initialized: {self.rule.description}")

    @staticmethod
    def _default_rule() -> EligibilityRule:
        """Create default eligibility rule."""
        return EligibilityRule(
            allowed_asset_types={
                "sovereign",
                "covered_bond",
                "corporate_bond",
                "government_bond",
                "abs",
            },
            allowed_currencies={"EUR"},
            allowed_ratings={"AAA", "AA+", "AA", "AA-", "A+", "A", "A-", "BBB+", "BBB", "BBB-"},
            max_maturity_years=10,
            require_market_value=True,
            min_market_value=Decimal("0"),
            description="Default: EUR denominated, investment grade or better, max 10y maturity",
        )

    def assess(self, **kwargs: Any) -> EligibilityAssessmentResult:
        """Perform eligibility assessment on all securities in dataset."""
        dataset = kwargs.get("dataset")
        if not isinstance(dataset, AnalyticsDataset):
            return EligibilityAssessmentResult(
                decisions={},
                success=False,
                errors=["dataset parameter required"],
            )

        try:
            decisions = {}
            eligible_count = 0
            ineligible_count = 0

            for isin, security in dataset.securities.items():
                decision = self._assess_security(security)
                decisions[isin] = decision

                if decision.eligible:
                    eligible_count += 1
                else:
                    ineligible_count += 1

            logger.info(
                f"Eligibility assessment completed: {eligible_count} eligible, "
                f"{ineligible_count} ineligible"
            )

            return EligibilityAssessmentResult(
                decisions=decisions,
                eligible_count=eligible_count,
                ineligible_count=ineligible_count,
                total_assessed=len(decisions),
                success=True,
            )

        except Exception as e:
            logger.error(f"Eligibility assessment failed: {e}")
            return EligibilityAssessmentResult(
                decisions={},
                success=False,
                errors=[str(e)],
            )

    def _assess_security(self, security: Any) -> EligibilityDecision:
        """Assess a single security against the rule."""
        # Check market value
        if security.market_value is None or security.market_value <= 0:
            return EligibilityDecision(
                isin=security.isin,
                eligible=False,
                reason_code="MISSING_MARKET_VALUE",
                explanation=REASON_CODES["MISSING_MARKET_VALUE"],
                rule_applied="market_value requirement",
                metadata={"market_value": security.market_value},
            )

        # Check asset type
        if not self.rule.allows_asset_type(security.asset_type):
            return EligibilityDecision(
                isin=security.isin,
                eligible=False,
                reason_code="UNSUPPORTED_ASSET_TYPE",
                explanation=f"Asset type '{security.asset_type}' not allowed. "
                f"Allowed: {self.rule.allowed_asset_types}",
                rule_applied="asset_type filter",
                metadata={"asset_type": security.asset_type},
            )

        # Check currency
        if not self.rule.allows_currency(security.currency):
            return EligibilityDecision(
                isin=security.isin,
                eligible=False,
                reason_code="CURRENCY_NOT_ALLOWED",
                explanation=f"Currency '{security.currency}' not allowed. "
                f"Allowed: {self.rule.allowed_currencies}",
                rule_applied="currency filter",
                metadata={"currency": security.currency},
            )

        # Check rating
        if not self.rule.allows_rating(security.rating):
            return EligibilityDecision(
                isin=security.isin,
                eligible=False,
                reason_code="RATING_BELOW_THRESHOLD",
                explanation=f"Rating '{security.rating}' not in allowed list. "
                f"Allowed: {self.rule.allowed_ratings}",
                rule_applied="rating filter",
                metadata={"rating": security.rating},
            )

        # Check maturity
        days_to_maturity = security.days_to_maturity(self.reference_date)
        maturity_years = days_to_maturity / 365.25
        if not self.rule.allows_maturity(int(maturity_years)):
            return EligibilityDecision(
                isin=security.isin,
                eligible=False,
                reason_code="MATURITY_EXCEEDS_LIMIT",
                explanation=f"Maturity {maturity_years:.1f}y exceeds maximum {self.rule.max_maturity_years}y",
                rule_applied="maturity filter",
                metadata={"maturity_years": maturity_years, "days_to_maturity": days_to_maturity},
            )

        return EligibilityDecision(
            isin=security.isin,
            eligible=True,
            reason_code="ELIGIBLE",
            explanation="Collateral meets all eligibility criteria",
            rule_applied=self.rule.description,
            metadata={
                "asset_type": security.asset_type,
                "currency": security.currency,
                "rating": security.rating,
                "maturity_years": maturity_years,
                "market_value": float(security.market_value),
            },
        )
