"""Standard implementation of counterparty exposure analysis."""

from datetime import date
from decimal import Decimal
from typing import Any

from collateral_analytics.engines.base import BaseExposureAnalyzer
from collateral_analytics.loaders.data_manager import AnalyticsDataset
from collateral_analytics.models.exposure import (
    ExposureAnalysisResult,
    ExposureMetrics,
    ExposureSnapshot,
    RankingResult,
)
from collateral_analytics.utils.logging import configure_logging

logger = configure_logging(__name__)


class StandardExposureAnalyzer(BaseExposureAnalyzer):
    """Standard implementation of counterparty exposure analysis."""

    def __init__(self, reference_date: date | None = None):
        """Initialize analyzer."""
        self.reference_date = reference_date or date.today()
        logger.info(f"StandardExposureAnalyzer initialized for {self.reference_date}")

    def analyze(self, **kwargs: Any) -> ExposureAnalysisResult:
        """Perform complete exposure analysis."""
        dataset = kwargs.get("dataset")
        if not isinstance(dataset, AnalyticsDataset):
            return ExposureAnalysisResult(
                snapshots={},
                metrics=ExposureMetrics(
                    portfolio_gross_exposure=Decimal("0"),
                    portfolio_adjusted_collateral=Decimal("0"),
                    portfolio_net_exposure=Decimal("0"),
                    total_collateral_value=Decimal("0"),
                    total_counterparties=0,
                    average_utilisation=Decimal("0"),
                    max_utilisation=Decimal("0"),
                    counterparties_at_limit=0,
                    counterparties_over_limit=0,
                    herfindahl_index=Decimal("0"),
                    largest_counterparty_concentration=Decimal("0"),
                ),
                rankings_by_gross_exposure=[],
                rankings_by_net_exposure=[],
                rankings_by_utilisation=[],
                rankings_by_concentration=[],
                success=False,
                errors=["dataset parameter required"],
            )

        try:
            snapshots = {}
            total_gross = Decimal("0")
            total_collateral = Decimal("0")
            total_net = Decimal("0")
            total_posted_collateral = Decimal("0")

            for cp_id, counterparty in dataset.counterparties.items():
                gross_exposure = self._calculate_gross_exposure(cp_id, dataset)
                adjusted_collateral = self._calculate_adjusted_collateral(cp_id, dataset)
                posted_collateral = self._calculate_total_collateral(cp_id, dataset)
                net_exposure = max(Decimal("0"), gross_exposure - adjusted_collateral)
                unsecured_exposure = net_exposure

                utilisation = (
                    (net_exposure / counterparty.exposure_limit)
                    if counterparty.exposure_limit > 0
                    else Decimal("0")
                )

                available_capacity = max(
                    Decimal("0"),
                    counterparty.exposure_limit - net_exposure,
                )

                snapshot = ExposureSnapshot(
                    counterparty_id=cp_id,
                    counterparty_name=counterparty.name,
                    gross_exposure=gross_exposure,
                    adjusted_collateral_value=adjusted_collateral,
                    net_exposure=net_exposure,
                    utilisation_ratio=utilisation,
                    unsecured_exposure=unsecured_exposure,
                    concentration_ratio=Decimal("0"),
                    exposure_limit=counterparty.exposure_limit,
                    available_capacity=available_capacity,
                )

                snapshots[cp_id] = snapshot
                total_gross += gross_exposure
                total_collateral += adjusted_collateral
                total_net += net_exposure
                total_posted_collateral += posted_collateral

            for snapshot in snapshots.values():
                if total_net > 0:
                    snapshot.concentration_ratio = snapshot.net_exposure / total_net
                else:
                    snapshot.concentration_ratio = Decimal("0")

            metrics = self._calculate_metrics(
                snapshots, total_gross, total_collateral, total_net, total_posted_collateral
            )

            rankings_gross = self._rank_by_metric(snapshots, "gross_exposure", "gross_exposure")
            rankings_net = self._rank_by_metric(snapshots, "net_exposure", "net_exposure")
            rankings_util = self._rank_by_metric(
                snapshots, "utilisation_ratio", "utilisation_ratio"
            )
            rankings_conc = self._rank_by_metric(
                snapshots, "concentration_ratio", "concentration_ratio"
            )

            logger.info(f"Exposure analysis completed: {len(snapshots)} counterparties")

            return ExposureAnalysisResult(
                snapshots=snapshots,
                metrics=metrics,
                rankings_by_gross_exposure=rankings_gross,
                rankings_by_net_exposure=rankings_net,
                rankings_by_utilisation=rankings_util,
                rankings_by_concentration=rankings_conc,
                success=True,
            )

        except Exception as e:
            logger.error(f"Exposure analysis failed: {e}")
            return ExposureAnalysisResult(
                snapshots={},
                metrics=ExposureMetrics(
                    portfolio_gross_exposure=Decimal("0"),
                    portfolio_adjusted_collateral=Decimal("0"),
                    portfolio_net_exposure=Decimal("0"),
                    total_collateral_value=Decimal("0"),
                    total_counterparties=0,
                    average_utilisation=Decimal("0"),
                    max_utilisation=Decimal("0"),
                    counterparties_at_limit=0,
                    counterparties_over_limit=0,
                    herfindahl_index=Decimal("0"),
                    largest_counterparty_concentration=Decimal("0"),
                ),
                rankings_by_gross_exposure=[],
                rankings_by_net_exposure=[],
                rankings_by_utilisation=[],
                rankings_by_concentration=[],
                success=False,
                errors=[str(e)],
            )

    def _calculate_gross_exposure(self, counterparty_id: str, dataset: AnalyticsDataset) -> Decimal:
        """Calculate gross exposure (sum of collateral positions)."""
        gross = Decimal("0")
        for position in dataset.positions:
            if position.counterparty_id == counterparty_id:
                gross += position.market_value
        return gross

    def _calculate_total_collateral(
        self, counterparty_id: str, dataset: AnalyticsDataset
    ) -> Decimal:
        """Calculate total collateral posted (before haircuts)."""
        total = Decimal("0")
        for position in dataset.positions:
            if position.counterparty_id == counterparty_id:
                total += position.market_value
        return total

    def _calculate_adjusted_collateral(
        self, counterparty_id: str, dataset: AnalyticsDataset
    ) -> Decimal:
        """Calculate adjusted collateral value (after haircuts)."""
        adjusted = Decimal("0")
        for position in dataset.positions:
            if position.counterparty_id == counterparty_id:
                if position.isin in dataset.securities:
                    security = dataset.securities[position.isin]
                    haircut_rate = self._get_haircut_rate(security, dataset)
                    position_adjusted = position.market_value * (Decimal("1") - haircut_rate)
                    adjusted += position_adjusted
        return adjusted

    def _get_haircut_rate(self, security: Any, dataset: AnalyticsDataset) -> Decimal:
        """Get haircut rate for a security from the schedule."""
        maturity_bucket = security.maturity_bucket(self.reference_date)
        rating_bucket = security.rating_bucket()

        for haircut_rule in dataset.haircuts:
            if (
                haircut_rule.asset_type == security.asset_type
                and haircut_rule.maturity_bucket == maturity_bucket
                and haircut_rule.rating_bucket == rating_bucket
            ):
                return haircut_rule.haircut_rate

        logger.warning(f"No haircut rule found for {security.isin}")
        return Decimal("0")

    def _calculate_metrics(
        self,
        snapshots: dict[str, ExposureSnapshot],
        total_gross: Decimal,
        total_collateral: Decimal,
        total_net: Decimal,
        total_posted_collateral: Decimal,
    ) -> ExposureMetrics:
        """Calculate aggregated portfolio metrics."""
        num_counterparties = len(snapshots)
        at_limit = sum(1 for s in snapshots.values() if s.is_at_limit())
        over_limit = sum(1 for s in snapshots.values() if s.is_over_limit())

        avg_util = Decimal("0")
        if num_counterparties > 0:
            total_util = sum(s.utilisation_ratio for s in snapshots.values())
            avg_util = total_util / Decimal(str(num_counterparties))

        max_util = (
            max(s.utilisation_ratio for s in snapshots.values()) if snapshots else Decimal("0")
        )

        herfindahl = Decimal("0")
        for snapshot in snapshots.values():
            herfindahl += snapshot.concentration_ratio**2

        largest_conc = (
            max(s.concentration_ratio for s in snapshots.values()) if snapshots else Decimal("0")
        )

        return ExposureMetrics(
            portfolio_gross_exposure=total_gross,
            portfolio_adjusted_collateral=total_collateral,
            portfolio_net_exposure=total_net,
            total_collateral_value=total_posted_collateral,
            total_counterparties=num_counterparties,
            average_utilisation=avg_util,
            max_utilisation=max_util,
            counterparties_at_limit=at_limit,
            counterparties_over_limit=over_limit,
            herfindahl_index=herfindahl,
            largest_counterparty_concentration=largest_conc,
        )

    def _rank_by_metric(
        self,
        snapshots: dict[str, ExposureSnapshot],
        metric_attr: str,
        metric_name: str,
    ) -> list[RankingResult]:
        """Generate ranking for a specific metric."""
        ranking_tuples = [
            (cp_id, snapshot, getattr(snapshot, metric_attr))
            for cp_id, snapshot in snapshots.items()
        ]

        ranking_tuples.sort(key=lambda x: x[2], reverse=True)

        results = []
        total = len(ranking_tuples)
        for rank, (cp_id, snapshot, value) in enumerate(ranking_tuples, start=1):
            percentile = Decimal(str(1.0 - (rank - 1) / total)) if total > 0 else Decimal("0")
            results.append(
                RankingResult(
                    rank=rank,
                    counterparty_id=cp_id,
                    counterparty_name=snapshot.counterparty_name,
                    metric_value=value,
                    metric_name=metric_name,
                    percentile=percentile,
                )
            )

        return results
