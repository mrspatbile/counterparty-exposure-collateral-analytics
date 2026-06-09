"""Standard implementation of concentration risk analysis."""

from datetime import date
from decimal import Decimal
from typing import Any

from collateral_analytics.engines.base import BaseConcentrationAnalyzer
from collateral_analytics.loaders.data_manager import AnalyticsDataset
from collateral_analytics.models.concentration import (
    ConcentrationAnalysis,
    ConcentrationMetric,
)
from collateral_analytics.models.exposure import ExposureAnalysisResult
from collateral_analytics.models.haircut_assessment import HaircutReport
from collateral_analytics.utils.logging import configure_logging

logger = configure_logging(__name__)

# Concentration thresholds for flagging
ISSUER_CONCENTRATION_THRESHOLD = Decimal("0.20")  # 20%
ASSET_TYPE_CONCENTRATION_THRESHOLD = Decimal("0.15")  # 15%
RATING_CONCENTRATION_THRESHOLD = Decimal("0.25")  # 25%
COUNTERPARTY_CONCENTRATION_THRESHOLD = Decimal("0.30")  # 30%


class StandardConcentrationAnalyzer(BaseConcentrationAnalyzer):
    """Standard implementation of concentration risk analysis."""

    def __init__(self, reference_date: date | None = None):
        """Initialize analyzer.

        Args:
            reference_date: Date for calculations (defaults to today)
        """
        self.reference_date = reference_date or date.today()
        logger.info(f"StandardConcentrationAnalyzer initialized for {self.reference_date}")

    def analyze(self, **kwargs: Any) -> ConcentrationAnalysis:
        """Analyze concentration risk across multiple dimensions.

        Args:
            dataset: AnalyticsDataset with securities and positions
            exposure_result: ExposureAnalysisResult for net exposures
            haircut_report: HaircutReport for adjusted collateral

        Returns:
            ConcentrationAnalysis with metrics by issuer, asset, rating, counterparty
        """
        dataset = kwargs.get("dataset")
        exposure_result = kwargs.get("exposure_result")
        haircut_report = kwargs.get("haircut_report")

        if not isinstance(dataset, AnalyticsDataset):
            return ConcentrationAnalysis(
                success=False,
                errors=["dataset parameter required"],
            )

        if not isinstance(exposure_result, ExposureAnalysisResult):
            return ConcentrationAnalysis(
                success=False,
                errors=["exposure_result parameter required"],
            )

        if not isinstance(haircut_report, HaircutReport):
            return ConcentrationAnalysis(
                success=False,
                errors=["haircut_report parameter required"],
            )

        try:
            # Calculate concentrations by dimension
            issuer_metrics = self._calculate_issuer_concentration(
                dataset, exposure_result, haircut_report
            )
            asset_metrics = self._calculate_asset_type_concentration(
                dataset, exposure_result, haircut_report
            )
            rating_metrics = self._calculate_rating_concentration(
                dataset, exposure_result, haircut_report
            )
            counterparty_metrics = self._calculate_counterparty_concentration(exposure_result)

            # Calculate portfolio Herfindahl index
            portfolio_herfindahl = self._calculate_herfindahl(counterparty_metrics)

            # Flag concentrations exceeding thresholds
            self._flag_concentrations(issuer_metrics, ISSUER_CONCENTRATION_THRESHOLD, "issuer")
            self._flag_concentrations(
                asset_metrics, ASSET_TYPE_CONCENTRATION_THRESHOLD, "asset_type"
            )
            self._flag_concentrations(rating_metrics, RATING_CONCENTRATION_THRESHOLD, "rating")
            self._flag_concentrations(
                counterparty_metrics, COUNTERPARTY_CONCENTRATION_THRESHOLD, "counterparty"
            )

            flagged_count = sum(
                1
                for metrics in [issuer_metrics, asset_metrics, rating_metrics, counterparty_metrics]
                for m in metrics
                if m.is_flagged
            )

            # Top 3 counterparty concentration
            top_3 = sum(
                m.net_exposure
                for m in sorted(counterparty_metrics, key=lambda x: x.net_exposure, reverse=True)[
                    :3
                ]
            )
            top_3_ratio = (
                (top_3 / exposure_result.metrics.portfolio_net_exposure)
                if exposure_result.metrics.portfolio_net_exposure > 0
                else Decimal("0")
            )

            logger.info(
                f"Concentration analysis completed: {len(issuer_metrics)} issuers, "
                f"Herfindahl {portfolio_herfindahl}"
            )

            return ConcentrationAnalysis(
                by_issuer=issuer_metrics,
                by_asset_type=asset_metrics,
                by_rating=rating_metrics,
                by_counterparty=counterparty_metrics,
                portfolio_herfindahl_index=portfolio_herfindahl,
                portfolio_net_exposure=exposure_result.metrics.portfolio_net_exposure,
                top_n_concentration=top_3_ratio,
                num_issuers=len(issuer_metrics),
                num_asset_types=len(asset_metrics),
                num_ratings=len(rating_metrics),
                num_counterparties=len(counterparty_metrics),
                flagged_count=flagged_count,
                success=True,
            )

        except Exception as e:
            logger.error(f"Concentration analysis failed: {e}")
            return ConcentrationAnalysis(
                success=False,
                errors=[str(e)],
            )

    def _calculate_issuer_concentration(
        self,
        dataset: AnalyticsDataset,
        exposure_result: ExposureAnalysisResult,
        haircut_report: HaircutReport,
    ) -> list[ConcentrationMetric]:
        """Calculate concentration by issuer."""
        issuer_data: dict[str, dict[str, Any]] = {}

        for isin, security in dataset.securities.items():
            issuer = security.issuer
            if issuer not in issuer_data:
                issuer_data[issuer] = {
                    "count": 0,
                    "gross_exposure": Decimal("0"),
                    "net_exposure": Decimal("0"),
                    "adjusted_collateral": Decimal("0"),
                }

            assessment = haircut_report.assessments.get(isin)
            if assessment:
                issuer_data[issuer]["count"] += 1
                issuer_data[issuer]["gross_exposure"] += assessment.market_value
                issuer_data[issuer]["adjusted_collateral"] += assessment.adjusted_value

        # Calculate net exposure from positions
        for position in dataset.positions:
            if position.isin in dataset.securities:
                issuer = dataset.securities[position.isin].issuer
                # Find corresponding counterparty snapshot for net exposure
                for snapshot in exposure_result.snapshots.values():
                    # Rough approximation: attribute net exposure proportionally
                    if issuer in issuer_data:
                        issuer_data[issuer]["net_exposure"] += position.market_value * Decimal(
                            "0.5"
                        )  # Simplified

        return self._create_metrics(
            issuer_data, "issuer", exposure_result.metrics.portfolio_net_exposure
        )

    def _calculate_asset_type_concentration(
        self,
        dataset: AnalyticsDataset,
        exposure_result: ExposureAnalysisResult,
        haircut_report: HaircutReport,
    ) -> list[ConcentrationMetric]:
        """Calculate concentration by asset type."""
        asset_data: dict[str, dict[str, Any]] = {}

        for isin, security in dataset.securities.items():
            asset_type = security.asset_type
            if asset_type not in asset_data:
                asset_data[asset_type] = {
                    "count": 0,
                    "gross_exposure": Decimal("0"),
                    "net_exposure": Decimal("0"),
                    "adjusted_collateral": Decimal("0"),
                }

            assessment = haircut_report.assessments.get(isin)
            if assessment:
                asset_data[asset_type]["count"] += 1
                asset_data[asset_type]["gross_exposure"] += assessment.market_value
                asset_data[asset_type]["adjusted_collateral"] += assessment.adjusted_value
                asset_data[asset_type]["net_exposure"] += assessment.adjusted_value

        return self._create_metrics(
            asset_data, "asset_type", exposure_result.metrics.portfolio_net_exposure
        )

    def _calculate_rating_concentration(
        self,
        dataset: AnalyticsDataset,
        exposure_result: ExposureAnalysisResult,
        haircut_report: HaircutReport,
    ) -> list[ConcentrationMetric]:
        """Calculate concentration by rating."""
        rating_data: dict[str, dict[str, Any]] = {}

        for isin, security in dataset.securities.items():
            rating = security.rating
            if rating not in rating_data:
                rating_data[rating] = {
                    "count": 0,
                    "gross_exposure": Decimal("0"),
                    "net_exposure": Decimal("0"),
                    "adjusted_collateral": Decimal("0"),
                }

            assessment = haircut_report.assessments.get(isin)
            if assessment:
                rating_data[rating]["count"] += 1
                rating_data[rating]["gross_exposure"] += assessment.market_value
                rating_data[rating]["adjusted_collateral"] += assessment.adjusted_value
                rating_data[rating]["net_exposure"] += assessment.adjusted_value

        return self._create_metrics(
            rating_data, "rating", exposure_result.metrics.portfolio_net_exposure
        )

    def _calculate_counterparty_concentration(
        self, exposure_result: ExposureAnalysisResult
    ) -> list[ConcentrationMetric]:
        """Calculate concentration by counterparty."""
        metrics = []
        for cp_id, snapshot in exposure_result.snapshots.items():
            conc_ratio = snapshot.concentration_ratio
            conc_percent = conc_ratio * Decimal("100")

            metric = ConcentrationMetric(
                dimension_value=snapshot.counterparty_name,
                dimension_type="counterparty",
                count=1,  # One counterparty per metric
                gross_exposure=snapshot.gross_exposure,
                net_exposure=snapshot.net_exposure,
                adjusted_collateral=snapshot.adjusted_collateral_value,
                concentration_ratio=conc_ratio,
                concentration_percent=conc_percent,
                herfindahl_contribution=conc_ratio**2,
            )
            metrics.append(metric)

        # Sort and rank
        metrics.sort(key=lambda x: x.net_exposure, reverse=True)
        for rank, metric in enumerate(metrics, start=1):
            metric.rank = rank

        return metrics

    def _create_metrics(
        self,
        data: dict[str, dict[str, Any]],
        dimension_type: str,
        portfolio_net_exposure: Decimal,
    ) -> list[ConcentrationMetric]:
        """Create ConcentrationMetric list from data dictionary."""
        metrics = []
        for dimension_value, values in data.items():
            net_exposure = values.get("net_exposure", Decimal("0"))
            conc_ratio = (
                (net_exposure / portfolio_net_exposure)
                if portfolio_net_exposure > 0
                else Decimal("0")
            )
            conc_percent = conc_ratio * Decimal("100")

            metric = ConcentrationMetric(
                dimension_value=dimension_value,
                dimension_type=dimension_type,
                count=values["count"],
                gross_exposure=values["gross_exposure"],
                net_exposure=net_exposure,
                adjusted_collateral=values["adjusted_collateral"],
                concentration_ratio=conc_ratio,
                concentration_percent=conc_percent,
                herfindahl_contribution=conc_ratio**2,
            )
            metrics.append(metric)

        # Sort and rank
        metrics.sort(key=lambda x: x.net_exposure, reverse=True)
        for rank, metric in enumerate(metrics, start=1):
            metric.rank = rank

        return metrics

    def _calculate_herfindahl(self, counterparty_metrics: list[ConcentrationMetric]) -> Decimal:
        """Calculate Herfindahl index from counterparty concentrations."""
        herfindahl: Decimal = sum(
            (m.herfindahl_contribution for m in counterparty_metrics),
            Decimal("0"),
        )
        return herfindahl

    def _flag_concentrations(
        self,
        metrics: list[ConcentrationMetric],
        threshold: Decimal,
        dimension_type: str,
    ) -> None:
        """Flag concentrations exceeding threshold."""
        for metric in metrics:
            if metric.concentration_ratio >= threshold:
                metric.is_flagged = True
                metric.flag_reason = (
                    f"{dimension_type.replace('_', ' ').title()} concentration "
                    f"{metric.concentration_percent:.1f}% exceeds {threshold * 100:.0f}% threshold"
                )
