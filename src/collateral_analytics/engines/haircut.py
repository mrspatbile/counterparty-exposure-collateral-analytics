"""Standard implementation of haircut calculation engine."""

from datetime import date
from decimal import Decimal
from typing import Any

from collateral_analytics.engines.base import BaseHaircutEngine
from collateral_analytics.loaders.data_manager import AnalyticsDataset
from collateral_analytics.models.haircut_assessment import (
    HaircutAssessment,
    HaircutReport,
)
from collateral_analytics.utils.logging import configure_logging

logger = configure_logging(__name__)


class ScheduleBasedHaircutEngine(BaseHaircutEngine):
    """Haircut calculation using schedule-based lookup."""

    def __init__(self, reference_date: date | None = None):
        """Initialize engine.

        Args:
            reference_date: Date for maturity bucket calculations (defaults to today)
        """
        self.reference_date = reference_date or date.today()
        logger.info(f"ScheduleBasedHaircutEngine initialized for {self.reference_date}")

    def calculate(self, **kwargs: Any) -> HaircutReport:
        """Calculate haircuts for all securities in dataset.

        Args:
            dataset: AnalyticsDataset containing securities and haircut schedule

        Returns:
            HaircutReport with individual assessments and portfolio summary
        """
        dataset = kwargs.get("dataset")
        if not isinstance(dataset, AnalyticsDataset):
            return HaircutReport(
                assessments={},
                success=False,
                errors=["dataset parameter required"],
            )

        try:
            assessments = {}
            total_market_value = Decimal("0")
            total_haircut_amount = Decimal("0")
            total_adjusted_value = Decimal("0")
            min_haircut = Decimal("1")
            max_haircut = Decimal("0")
            zero_haircut_count = 0
            missing_schedule_count = 0

            for isin, security in dataset.securities.items():
                # Get maturity and rating buckets
                maturity_bucket = security.maturity_bucket(self.reference_date)
                rating_bucket = security.rating_bucket()

                # Lookup haircut rate
                haircut_rate, found_rule = self._lookup_haircut_rate(
                    security.asset_type, maturity_bucket, rating_bucket, dataset
                )

                if not found_rule:
                    missing_schedule_count += 1
                    logger.warning(
                        f"No haircut rule found for {isin} "
                        f"({security.asset_type}, {maturity_bucket}, {rating_bucket})"
                    )

                # Calculate haircut amounts
                market_value = security.market_value
                haircut_amount = market_value * haircut_rate
                adjusted_value = market_value - haircut_amount

                # Track statistics
                total_market_value += market_value
                total_haircut_amount += haircut_amount
                total_adjusted_value += adjusted_value

                if haircut_rate == 0:
                    zero_haircut_count += 1
                else:
                    min_haircut = min(min_haircut, haircut_rate)
                    max_haircut = max(max_haircut, haircut_rate)

                assessment = HaircutAssessment(
                    isin=isin,
                    asset_type=security.asset_type,
                    maturity_bucket=maturity_bucket,
                    rating_bucket=rating_bucket,
                    market_value=market_value,
                    haircut_rate=haircut_rate,
                    haircut_amount=haircut_amount,
                    adjusted_value=adjusted_value,
                    metadata={
                        "found_rule": found_rule,
                        "rating": security.rating,
                        "days_to_maturity": security.days_to_maturity(self.reference_date),
                    },
                )
                assessments[isin] = assessment

            # Calculate average haircut rate
            average_haircut = (
                (total_haircut_amount / total_market_value)
                if total_market_value > 0
                else Decimal("0")
            )

            # Handle min/max for zero haircut cases
            if min_haircut == Decimal("1"):
                min_haircut = Decimal("0")

            logger.info(
                f"Haircut calculation completed: {len(assessments)} securities, "
                f"total haircut {total_haircut_amount}"
            )

            warnings = []
            if missing_schedule_count > 0:
                warnings.append(f"{missing_schedule_count} securities missing haircut rules")

            return HaircutReport(
                assessments=assessments,
                total_securities=len(assessments),
                total_market_value=total_market_value,
                total_haircut_amount=total_haircut_amount,
                total_adjusted_value=total_adjusted_value,
                average_haircut_rate=average_haircut,
                min_haircut_rate=min_haircut,
                max_haircut_rate=max_haircut,
                securities_with_zero_haircut=zero_haircut_count,
                missing_schedule_entries=missing_schedule_count,
                success=True,
                warnings=warnings,
            )

        except Exception as e:
            logger.error(f"Haircut calculation failed: {e}")
            return HaircutReport(
                assessments={},
                success=False,
                errors=[str(e)],
            )

    def _lookup_haircut_rate(
        self, asset_type: str, maturity_bucket: str, rating_bucket: str, dataset: AnalyticsDataset
    ) -> tuple[Decimal, bool]:
        """Lookup haircut rate from schedule.

        Returns:
            Tuple of (haircut_rate, found_rule)
        """
        for haircut_rule in dataset.haircuts:
            if (
                haircut_rule.asset_type == asset_type
                and haircut_rule.maturity_bucket == maturity_bucket
                and haircut_rule.rating_bucket == rating_bucket
            ):
                return (haircut_rule.haircut_rate, True)

        # No rule found, return 0% haircut
        return (Decimal("0"), False)
