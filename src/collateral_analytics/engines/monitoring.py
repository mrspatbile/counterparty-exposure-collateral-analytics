"""AI-assisted monitoring engine with anomaly detection and commentary generation."""

from datetime import date
from decimal import Decimal
from statistics import mean, stdev
from typing import Any

from collateral_analytics.engines.base import BaseEngine
from collateral_analytics.models.coverage import CoverageReport
from collateral_analytics.models.monitoring import (
    AnomalyScore,
    EarlyWarning,
    MonitoringReport,
    RiskCommentary,
)
from collateral_analytics.utils.logging import configure_logging

logger = configure_logging(__name__)

# Anomaly detection thresholds
ANOMALY_SCORE_THRESHOLD = Decimal("0.7")
Z_SCORE_THRESHOLD = Decimal("2.5")
COVERAGE_WARNING_THRESHOLD = Decimal("1.0")
CONCENTRATION_WARNING_THRESHOLD = Decimal("0.25")
UTILISATION_WARNING_THRESHOLD = Decimal("0.8")


class StandardMonitoringEngine(BaseEngine):
    """AI-assisted monitoring with statistical anomaly detection."""

    def __init__(self, reference_date: date | None = None):
        """Initialize monitoring engine.

        Args:
            reference_date: Date for calculations (defaults to today)
        """
        self.reference_date = reference_date or date.today()
        logger.info(f"StandardMonitoringEngine initialized for {self.reference_date}")

    def monitor(self, **kwargs: Any) -> MonitoringReport:
        """Perform AI-assisted monitoring.

        Args:
            coverage_report: CoverageReport with coverage metrics

        Returns:
            MonitoringReport with anomalies, commentaries, and early warnings
        """
        coverage_report = kwargs.get("coverage_report")

        if not isinstance(coverage_report, CoverageReport):
            return MonitoringReport(
                anomalies=[],
                commentaries=[],
                early_warnings=[],
                success=False,
                errors=["coverage_report parameter required"],
            )

        try:
            anomalies: list[AnomalyScore] = []
            commentaries = []
            early_warnings = []

            # Detect anomalies in coverage ratios
            coverage_anomalies = self._detect_coverage_anomalies(coverage_report)
            anomalies.extend(coverage_anomalies)

            # Generate commentary on coverage
            coverage_commentary = self._generate_coverage_commentary(coverage_report)
            commentaries.extend(coverage_commentary)

            # Detect early warning indicators
            warnings = self._detect_early_warnings(coverage_report)
            early_warnings.extend(warnings)

            # Count critical items
            critical_count = sum(1 for c in commentaries if c.severity == "critical")
            critical_count += sum(1 for w in early_warnings if w.confidence > Decimal("0.8"))

            logger.info(
                f"Monitoring completed: {len(anomalies)} anomalies, "
                f"{len(commentaries)} commentaries, {len(early_warnings)} warnings"
            )

            return MonitoringReport(
                anomalies=anomalies,
                commentaries=commentaries,
                early_warnings=early_warnings,
                num_anomalies=len(anomalies),
                num_warnings=len(commentaries) + len(early_warnings),
                critical_count=critical_count,
                success=True,
            )

        except Exception as e:
            logger.error(f"Monitoring failed: {e}")
            return MonitoringReport(
                anomalies=[],
                commentaries=[],
                early_warnings=[],
                success=False,
                errors=[str(e)],
            )

    def _detect_coverage_anomalies(self, coverage_report: CoverageReport) -> list[AnomalyScore]:
        """Detect anomalies in coverage ratios using z-score method."""
        anomalies: list[AnomalyScore] = []

        if not coverage_report.assessments:
            return anomalies

        # Calculate z-scores for coverage ratios
        coverage_values = [float(a.coverage_ratio) for a in coverage_report.assessments.values()]

        if len(coverage_values) < 2:
            return anomalies

        mean_coverage = Decimal(str(mean(coverage_values)))
        std_coverage = Decimal(str(stdev(coverage_values)))

        for cp_id, assessment in coverage_report.assessments.items():
            if std_coverage > 0:
                z_score = (assessment.coverage_ratio - mean_coverage) / std_coverage
            else:
                z_score = Decimal("0")

            # Flag as anomaly if |z_score| > threshold
            is_anomaly = abs(z_score) > Z_SCORE_THRESHOLD

            if is_anomaly:
                anomaly_score = min(Decimal("1"), abs(z_score) / Z_SCORE_THRESHOLD)
                deviation_type = "high" if z_score > 0 else "low"

                anomaly = AnomalyScore(
                    counterparty_id=cp_id,
                    dimension="coverage_ratio",
                    dimension_value=assessment.coverage_ratio,
                    anomaly_score=anomaly_score,
                    is_anomaly=True,
                    deviation_type=deviation_type,
                    z_score=z_score,
                    metadata={
                        "mean": str(mean_coverage),
                        "std": str(std_coverage),
                        "z_score": str(z_score),
                    },
                )
                anomalies.append(anomaly)

        return anomalies

    def _generate_coverage_commentary(
        self, coverage_report: CoverageReport
    ) -> list[RiskCommentary]:
        """Generate automated commentary based on coverage metrics."""
        commentaries = []

        for cp_id, assessment in coverage_report.assessments.items():
            # Critical: coverage below 1.0
            if not assessment.is_covered:
                commentary = RiskCommentary(
                    counterparty_id=cp_id,
                    category="coverage",
                    text=(
                        f"Exposure undercovered: {assessment.unsecured_exposure:,.0f} EUR "
                        f"shortfall. Coverage ratio {assessment.coverage_ratio:.2f}x."
                    ),
                    severity="critical",
                    triggered_by="coverage_ratio < 1.0",
                    suggested_action="Increase collateral or reduce exposure immediately",
                )
                commentaries.append(commentary)

            # Warning: coverage between 1.0 and 1.2
            elif assessment.coverage_ratio < Decimal("1.2"):
                commentary = RiskCommentary(
                    counterparty_id=cp_id,
                    category="coverage",
                    text=(
                        f"Low coverage margin: {assessment.coverage_ratio:.2f}x coverage. "
                        f"Minimal buffer for adverse moves."
                    ),
                    severity="warning",
                    triggered_by="coverage_ratio < 1.2",
                    suggested_action="Monitor closely; consider additional collateral",
                )
                commentaries.append(commentary)

            # Info: high utilisation despite adequate coverage
            if assessment.coverage_ratio > Decimal("1.5"):
                commentary = RiskCommentary(
                    counterparty_id=cp_id,
                    category="coverage",
                    text=f"Excellent coverage: {assessment.coverage_ratio:.2f}x. Low liquidation risk.",
                    severity="info",
                    triggered_by="coverage_ratio > 1.5",
                )
                commentaries.append(commentary)

        return commentaries

    def _detect_early_warnings(self, coverage_report: CoverageReport) -> list[EarlyWarning]:
        """Detect early warning indicators."""
        warnings = []

        for cp_id, assessment in coverage_report.assessments.items():
            # Warning: approaching critical threshold
            if (
                Decimal("0.95") < assessment.coverage_ratio < Decimal("1.05")
                and not assessment.is_covered
            ):
                warning = EarlyWarning(
                    counterparty_id=cp_id,
                    warning_type="threshold_breach",
                    indicator_name="coverage_ratio_approaching_1x",
                    current_value=assessment.coverage_ratio,
                    threshold_value=Decimal("1.0"),
                    confidence=Decimal("0.85"),
                    metadata={"unsecured_exposure": str(assessment.unsecured_exposure)},
                )
                warnings.append(warning)

            # Warning: high unsecured exposure
            if assessment.unsecured_exposure > Decimal("500000"):
                warning = EarlyWarning(
                    counterparty_id=cp_id,
                    warning_type="concentration_spike",
                    indicator_name="unsecured_exposure_high",
                    current_value=assessment.unsecured_exposure,
                    threshold_value=Decimal("500000"),
                    confidence=Decimal("0.9"),
                    metadata={"coverage_ratio": str(assessment.coverage_ratio)},
                )
                warnings.append(warning)

        return warnings
