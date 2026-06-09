"""Standard implementation of collateral coverage assessment."""

from datetime import date
from decimal import Decimal
from typing import Any

from collateral_analytics.engines.base import BaseEngine
from collateral_analytics.models.coverage import CoverageAssessment, CoverageReport
from collateral_analytics.models.exposure import ExposureAnalysisResult
from collateral_analytics.models.haircut_assessment import HaircutReport
from collateral_analytics.utils.logging import configure_logging

logger = configure_logging(__name__)


class StandardCoverageAnalyzer(BaseEngine):
    """Standard implementation of coverage assessment.

    Integrates exposure analysis with haircut application to calculate
    collateral sufficiency metrics per counterparty and portfolio.
    """

    def __init__(self, reference_date: date | None = None):
        """Initialize analyzer.

        Args:
            reference_date: Date for calculations (defaults to today)
        """
        self.reference_date = reference_date or date.today()
        logger.info(f"StandardCoverageAnalyzer initialized for {self.reference_date}")

    def assess(self, **kwargs: Any) -> CoverageReport:
        """Assess collateral coverage for counterparties.

        Args:
            exposure_result: ExposureAnalysisResult from StandardExposureAnalyzer
            haircut_report: HaircutReport from ScheduleBasedHaircutEngine
            dataset: AnalyticsDataset for reference data

        Returns:
            CoverageReport with per-counterparty and portfolio-level metrics
        """
        exposure_result = kwargs.get("exposure_result")
        haircut_report = kwargs.get("haircut_report")
        dataset = kwargs.get("dataset")

        if not isinstance(exposure_result, ExposureAnalysisResult):
            return CoverageReport(
                assessments={},
                success=False,
                errors=["exposure_result parameter required"],
            )

        if not isinstance(haircut_report, HaircutReport):
            return CoverageReport(
                assessments={},
                success=False,
                errors=["haircut_report parameter required"],
            )

        try:
            assessments = {}
            total_net_exposure = Decimal("0")
            total_adjusted_collateral = Decimal("0")
            total_unsecured = Decimal("0")
            total_excess = Decimal("0")
            covered_count = 0
            undercovered_count = 0
            min_coverage = Decimal("1")
            max_coverage = Decimal("0")
            coverage_ratios = []

            for cp_id, snapshot in exposure_result.snapshots.items():
                net_exposure = snapshot.net_exposure
                adjusted_collateral = snapshot.adjusted_collateral_value

                # Calculate coverage ratio
                coverage_ratio = (
                    (adjusted_collateral / net_exposure) if net_exposure > 0 else Decimal("0")
                )

                # Calculate shortfall/excess
                unsecured = max(Decimal("0"), net_exposure - adjusted_collateral)
                excess = max(Decimal("0"), adjusted_collateral - net_exposure)

                # Determine coverage status
                is_covered = coverage_ratio >= Decimal("1")

                # Calculate haircut impact (coverage without haircuts)
                gross_collateral = self._calculate_gross_collateral(cp_id, dataset)
                haircut_impact = (
                    (gross_collateral / net_exposure) if net_exposure > 0 else Decimal("0")
                )

                # Haircut benefit in basis points
                haircut_bp = 0
                if haircut_impact > 0:
                    haircut_benefit = haircut_impact - coverage_ratio
                    haircut_bp = int(haircut_benefit * Decimal("10000"))

                # Aggregate metrics
                total_net_exposure += net_exposure
                total_adjusted_collateral += adjusted_collateral
                total_unsecured += unsecured
                total_excess += excess
                coverage_ratios.append(coverage_ratio)

                if is_covered:
                    covered_count += 1
                else:
                    undercovered_count += 1

                min_coverage = min(min_coverage, coverage_ratio)
                max_coverage = max(max_coverage, coverage_ratio)

                assessment = CoverageAssessment(
                    counterparty_id=cp_id,
                    counterparty_name=snapshot.counterparty_name,
                    net_exposure=net_exposure,
                    adjusted_collateral_value=adjusted_collateral,
                    coverage_ratio=coverage_ratio,
                    unsecured_exposure=unsecured,
                    excess_collateral=excess,
                    is_covered=is_covered,
                    haircut_impact=haircut_impact,
                    haircut_basis_points=haircut_bp,
                    metadata={
                        "utilisation_ratio": float(snapshot.utilisation_ratio),
                        "available_capacity": float(snapshot.available_capacity),
                    },
                )
                assessments[cp_id] = assessment

            # Portfolio metrics
            portfolio_coverage = (
                (total_adjusted_collateral / total_net_exposure)
                if total_net_exposure > 0
                else Decimal("0")
            )

            avg_coverage: Decimal = (
                Decimal(str(float(sum(coverage_ratios) / len(coverage_ratios))))
                if coverage_ratios
                else Decimal("0")
            )

            if min_coverage == Decimal("1"):
                min_coverage = Decimal("0")

            # Haircut benefit (total reduction in coverage gap)
            total_haircut_benefit = (
                (haircut_report.total_market_value - haircut_report.total_adjusted_value)
                / total_net_exposure
                if total_net_exposure > 0
                else Decimal("0")
            )

            logger.info(
                f"Coverage assessment completed: {covered_count} covered, "
                f"{undercovered_count} undercovered, portfolio coverage {portfolio_coverage}"
            )

            return CoverageReport(
                assessments=assessments,
                total_counterparties=len(assessments),
                total_net_exposure=total_net_exposure,
                total_adjusted_collateral=total_adjusted_collateral,
                portfolio_coverage_ratio=portfolio_coverage,
                total_unsecured_exposure=total_unsecured,
                total_excess_collateral=total_excess,
                counterparties_covered=covered_count,
                counterparties_undercovered=undercovered_count,
                average_coverage_ratio=avg_coverage,
                min_coverage_ratio=min_coverage,
                max_coverage_ratio=max_coverage,
                haircut_benefit=total_haircut_benefit,
                success=True,
            )

        except Exception as e:
            logger.error(f"Coverage assessment failed: {e}")
            return CoverageReport(
                assessments={},
                success=False,
                errors=[str(e)],
            )

    def _calculate_gross_collateral(self, counterparty_id: str, dataset: Any) -> Decimal:
        """Calculate total collateral posted (before haircuts) for a counterparty."""
        if dataset is None:
            return Decimal("0")

        total = Decimal("0")
        for position in dataset.positions:
            if position.counterparty_id == counterparty_id:
                total += position.market_value
        return total
