"""Reporting engine that aggregates analytics across all modules."""

from datetime import date
from decimal import Decimal

from collateral_analytics.engines.base import BaseEngine
from collateral_analytics.loaders.data_manager import AnalyticsDataset
from collateral_analytics.models.concentration import ConcentrationAnalysis
from collateral_analytics.models.coverage import CoverageReport
from collateral_analytics.models.exposure import ExposureAnalysisResult
from collateral_analytics.models.haircut_assessment import HaircutReport
from collateral_analytics.models.monitoring import MonitoringReport
from collateral_analytics.models.reports import (
    ConcentrationReportSummary,
    CoverageReportSummary,
    EligibilityReportSummary,
    ExposureReportSummary,
    HaircutReportSummary,
    MonitoringReportSummary,
    PortfolioSummaryReport,
    StressReportSummary,
)
from collateral_analytics.models.stress import StressTestReport
from collateral_analytics.utils.logging import configure_logging

logger = configure_logging(__name__)


class ReportGenerator(BaseEngine):
    """Orchestrates all analytics engines and produces structured reports."""

    def __init__(self, reference_date: date | None = None):
        """Initialize report generator.

        Args:
            reference_date: Date for calculations (defaults to today)
        """
        self.reference_date = reference_date or date.today()
        logger.info(f"ReportGenerator initialized for {self.reference_date}")

    def generate_portfolio_summary(
        self,
        exposure_result: ExposureAnalysisResult,
        eligibility_data: dict[str, bool],
        haircut_report: HaircutReport,
        coverage_report: CoverageReport,
        concentration_analysis: ConcentrationAnalysis,
        stress_report: StressTestReport,
        monitoring_report: MonitoringReport,
        dataset: AnalyticsDataset,
    ) -> PortfolioSummaryReport:
        """Generate comprehensive portfolio summary across all modules.

        Args:
            exposure_result: Counterparty exposure analysis
            eligibility_data: Dict mapping isin to eligible boolean
            haircut_report: Haircut application summary
            coverage_report: Collateral coverage metrics
            concentration_analysis: Concentration risk analysis
            stress_report: Stress test results
            monitoring_report: Monitoring findings
            dataset: Analytics dataset with securities and counterparties

        Returns:
            PortfolioSummaryReport with all aggregated metrics
        """
        try:
            exposure_summary = self._summarize_exposure(exposure_result, dataset)
            eligibility_summary = self._summarize_eligibility(eligibility_data, dataset)
            haircut_summary = self._summarize_haircuts(haircut_report)
            coverage_summary = self._summarize_coverage(coverage_report)
            concentration_summary = self._summarize_concentration(concentration_analysis)
            stress_summary = self._summarize_stress(stress_report)
            monitoring_summary = self._summarize_monitoring(monitoring_report)

            overall_risk_level = self._assess_overall_risk(
                coverage_summary, concentration_summary, stress_summary, monitoring_summary
            )

            key_findings = self._extract_key_findings(
                coverage_summary, concentration_summary, stress_summary, monitoring_summary
            )

            report = PortfolioSummaryReport(
                reference_date=self.reference_date,
                exposure_summary=exposure_summary,
                eligibility_summary=eligibility_summary,
                haircut_summary=haircut_summary,
                coverage_summary=coverage_summary,
                concentration_summary=concentration_summary,
                stress_summary=stress_summary,
                monitoring_summary=monitoring_summary,
                overall_risk_level=overall_risk_level,
                key_findings=key_findings,
            )

            logger.info(f"Portfolio summary generated: risk_level={overall_risk_level}")
            return report

        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            raise

    def _summarize_exposure(
        self, result: ExposureAnalysisResult, dataset: AnalyticsDataset
    ) -> ExposureReportSummary:
        """Summarize counterparty exposures."""
        if not result.snapshots:
            return ExposureReportSummary(
                total_exposure=Decimal("0"),
                avg_exposure=Decimal("0"),
                min_exposure=Decimal("0"),
                max_exposure=Decimal("0"),
            )

        exposures = [s.gross_exposure for s in result.snapshots.values()]
        total = sum(exposures, Decimal("0"))
        avg = total / Decimal(len(exposures)) if exposures else Decimal("0")

        top_3 = sorted(
            [(cp_id, s.gross_exposure) for cp_id, s in result.snapshots.items()],
            key=lambda x: x[1],
            reverse=True,
        )[:3]

        counterparties_at_limit = sum(
            1
            for cp_id in result.snapshots.keys()
            if cp_id in dataset.counterparties and dataset.counterparties[cp_id].is_at_limit()
        )

        return ExposureReportSummary(
            total_exposure=total,
            avg_exposure=avg,
            min_exposure=min(exposures) if exposures else Decimal("0"),
            max_exposure=max(exposures) if exposures else Decimal("0"),
            top_3_exposures=top_3,
            counterparties_at_limit=counterparties_at_limit,
        )

    def _summarize_eligibility(
        self, eligibility_data: dict[str, bool], dataset: AnalyticsDataset
    ) -> EligibilityReportSummary:
        """Summarize collateral eligibility."""
        total = len(eligibility_data)
        eligible = sum(1 for v in eligibility_data.values() if v)
        rejected = total - eligible
        rate = Decimal(eligible) / Decimal(total) if total > 0 else Decimal("0")

        return EligibilityReportSummary(
            total_positions=total,
            eligible_positions=eligible,
            rejected_positions=rejected,
            eligibility_rate=rate,
        )

    def _summarize_haircuts(self, report: HaircutReport) -> HaircutReportSummary:
        """Summarize haircut application."""
        assessments = list(report.assessments.values())

        if not assessments:
            return HaircutReportSummary(
                total_market_value=Decimal("0"),
                total_haircut_amount=Decimal("0"),
                avg_haircut_rate=Decimal("0"),
                min_haircut_rate=Decimal("0"),
                max_haircut_rate=Decimal("0"),
                total_adjusted_value=Decimal("0"),
            )

        total_market = sum((a.market_value for a in assessments), Decimal("0"))
        total_haircut = sum((a.haircut_amount for a in assessments), Decimal("0"))
        total_adjusted = sum((a.adjusted_value for a in assessments), Decimal("0"))

        haircut_rates = [a.haircut_rate for a in assessments]
        avg_rate = sum(haircut_rates, Decimal("0")) / Decimal(len(haircut_rates))

        return HaircutReportSummary(
            total_market_value=total_market,
            total_haircut_amount=total_haircut,
            avg_haircut_rate=avg_rate,
            min_haircut_rate=min(haircut_rates) if haircut_rates else Decimal("0"),
            max_haircut_rate=max(haircut_rates) if haircut_rates else Decimal("0"),
            total_adjusted_value=total_adjusted,
        )

    def _summarize_coverage(self, report: CoverageReport) -> CoverageReportSummary:
        """Summarize collateral coverage."""
        assessments = list(report.assessments.values())

        if not assessments:
            return CoverageReportSummary(
                total_exposure=Decimal("0"),
                total_collateral=Decimal("0"),
                portfolio_coverage_ratio=Decimal("0"),
                covered_counterparties=0,
                undercovered_counterparties=0,
                total_shortfall=Decimal("0"),
                total_excess=Decimal("0"),
            )

        total_exposure = sum((a.net_exposure for a in assessments), Decimal("0"))
        total_collateral = sum((a.adjusted_collateral_value for a in assessments), Decimal("0"))
        portfolio_ratio = (
            total_collateral / total_exposure if total_exposure > Decimal("0") else Decimal("0")
        )

        covered = sum(1 for a in assessments if a.is_covered)
        undercovered = len(assessments) - covered
        total_shortfall = sum((a.unsecured_exposure for a in assessments), Decimal("0"))
        total_excess = sum((a.excess_collateral for a in assessments), Decimal("0"))

        return CoverageReportSummary(
            total_exposure=total_exposure,
            total_collateral=total_collateral,
            portfolio_coverage_ratio=portfolio_ratio,
            covered_counterparties=covered,
            undercovered_counterparties=undercovered,
            total_shortfall=total_shortfall,
            total_excess=total_excess,
        )

    def _summarize_concentration(
        self, analysis: ConcentrationAnalysis
    ) -> ConcentrationReportSummary:
        """Summarize concentration risk."""
        issuer_count = sum(1 for m in analysis.by_issuer if m.concentration_percent > Decimal("20"))
        asset_type_count = sum(
            1 for m in analysis.by_asset_type if m.concentration_percent > Decimal("15")
        )
        rating_count = sum(1 for m in analysis.by_rating if m.concentration_percent > Decimal("25"))
        counterparty_count = sum(
            1 for m in analysis.by_counterparty if m.concentration_percent > Decimal("30")
        )

        top_concentration = None
        if analysis.by_issuer:
            top = sorted(analysis.by_issuer, key=lambda x: x.concentration_ratio, reverse=True)[0]
            top_concentration = ("issuer", top.dimension_value, top.concentration_ratio)

        return ConcentrationReportSummary(
            issuer_concentration_count=issuer_count,
            asset_type_concentration_count=asset_type_count,
            rating_concentration_count=rating_count,
            counterparty_concentration_count=counterparty_count,
            herfindahl_index=analysis.portfolio_herfindahl_index,
            top_concentration=top_concentration,
        )

    def _summarize_stress(self, report: StressTestReport) -> StressReportSummary:
        """Summarize stress test results."""
        total_scenarios = len(report.results)
        coverage_breaches = sum(1 for r in report.results.values() if r.coverage_breached)

        worst_scenario = report.worst_case_scenario or "N/A"
        worst_decline = Decimal("0")
        avg_decline = Decimal("0")

        if report.results:
            declines = [
                r.coverage_ratio_delta
                for r in report.results.values()
                if r.coverage_ratio_delta is not None
            ]
            if declines:
                avg_decline = sum(declines, Decimal("0")) / Decimal(len(declines))
                worst_decline = min(declines)

        return StressReportSummary(
            total_scenarios=total_scenarios,
            coverage_breaches=coverage_breaches,
            worst_case_scenario=worst_scenario,
            worst_case_coverage_decline=worst_decline,
            avg_coverage_decline=avg_decline,
        )

    def _summarize_monitoring(self, report: MonitoringReport) -> MonitoringReportSummary:
        """Summarize monitoring findings."""
        critical_warnings = sum(1 for c in report.commentaries if c.severity == "critical")
        has_coverage_risk = any(c.severity == "critical" for c in report.commentaries)
        has_concentration_risk = any(
            "concentration" in c.category.lower() for c in report.commentaries
        )

        return MonitoringReportSummary(
            num_anomalies=len(report.anomalies),
            num_critical_warnings=critical_warnings,
            num_early_warnings=len(report.early_warnings),
            has_coverage_risk=has_coverage_risk,
            has_concentration_risk=has_concentration_risk,
        )

    def _assess_overall_risk(
        self,
        coverage: CoverageReportSummary,
        concentration: ConcentrationReportSummary,
        stress: StressReportSummary,
        monitoring: MonitoringReportSummary,
    ) -> str:
        """Assess overall portfolio risk level."""
        if (
            monitoring.num_critical_warnings > 0
            or coverage.undercovered_counterparties > 0
            or stress.coverage_breaches > 0
        ):
            return "critical"
        elif (
            monitoring.has_coverage_risk
            or concentration.herfindahl_index > Decimal("0.25")
            or concentration.issuer_concentration_count > 2
        ):
            return "high"
        elif (
            coverage.portfolio_coverage_ratio < Decimal("1.2") or monitoring.has_concentration_risk
        ):
            return "medium"
        else:
            return "low"

    def _extract_key_findings(
        self,
        coverage: CoverageReportSummary,
        concentration: ConcentrationReportSummary,
        stress: StressReportSummary,
        monitoring: MonitoringReportSummary,
    ) -> list[str]:
        """Extract key findings requiring attention."""
        findings = []

        if coverage.undercovered_counterparties > 0:
            findings.append(
                f"{coverage.undercovered_counterparties} counterparties undercovered (coverage < 1.0)"
            )

        if coverage.total_shortfall > Decimal("0"):
            findings.append(f"Total uncovered exposure: {coverage.total_shortfall:,.0f} EUR")

        if stress.coverage_breaches > 0:
            findings.append(f"{stress.coverage_breaches} stress scenarios trigger coverage breach")

        if monitoring.num_critical_warnings > 0:
            findings.append(f"{monitoring.num_critical_warnings} critical alerts generated")

        if concentration.issuer_concentration_count > 2:
            findings.append(
                f"High issuer concentration: {concentration.issuer_concentration_count} issuers above 20%"
            )

        return findings
