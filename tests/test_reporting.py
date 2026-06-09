"""Tests for reporting layer."""

import tempfile
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Iterator

import pytest

from collateral_analytics.engines.concentration import StandardConcentrationAnalyzer
from collateral_analytics.engines.coverage import StandardCoverageAnalyzer
from collateral_analytics.engines.eligibility import ConfigurableEligibilityEngine
from collateral_analytics.engines.exposure import StandardExposureAnalyzer
from collateral_analytics.engines.haircut import ScheduleBasedHaircutEngine
from collateral_analytics.engines.monitoring import StandardMonitoringEngine
from collateral_analytics.engines.reporting import ReportGenerator
from collateral_analytics.engines.stress import StandardStressEngine
from collateral_analytics.loaders.data_manager import DataManager
from collateral_analytics.models.eligibility import EligibilityRule
from collateral_analytics.models.reports import PortfolioSummaryReport


@pytest.fixture
def sample_data_dir() -> Iterator[Path]:
    """Create temporary directory with sample CSV files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        securities_csv = tmpdir_path / "securities.csv"
        securities_csv.write_text(
            "isin,name,asset_type,issuer,issuer_type,country,currency,rating,maturity_date,market_value\n"
            "XS1111111111,German Bund,sovereign,Germany,sovereign,DE,EUR,AAA,2035-12-31,1000000.00\n"
            "XS2222222222,Corp Bond A,corporate_bond,Corp A,corporate,DE,EUR,BBB,2030-06-30,500000.00\n"
            "XS3333333333,Covered Bond,covered_bond,Bank B,bank,FR,EUR,AA,2032-03-15,750000.00\n"
        )

        counterparties_csv = tmpdir_path / "counterparties.csv"
        counterparties_csv.write_text(
            "counterparty_id,name,country,rating,exposure,exposure_limit\n"
            "CP001,Bank A,DE,A,2000000.00,5000000.00\n"
            "CP002,Bank B,FR,BBB,1500000.00,3000000.00\n"
        )

        positions_csv = tmpdir_path / "collateral_positions.csv"
        positions_csv.write_text(
            "counterparty_id,isin,quantity,market_value\n"
            "CP001,XS1111111111,1000.000000,1000000.00\n"
            "CP001,XS2222222222,500.000000,250000.00\n"
            "CP002,XS3333333333,500.000000,375000.00\n"
        )

        haircuts_csv = tmpdir_path / "haircut_schedule.csv"
        haircuts_csv.write_text(
            "asset_type,maturity_bucket,rating_bucket,haircut_rate\n"
            "sovereign,5-10y,AAA-AA,0.0100\n"
            "sovereign,10y+,AAA-AA,0.0150\n"
            "corporate_bond,5-10y,BBB,0.2000\n"
            "covered_bond,5-10y,AAA-AA,0.0300\n"
        )

        yield tmpdir_path


class TestReportGenerator:
    """Tests for ReportGenerator."""

    def test_init_with_default_date(self) -> None:
        """Initialize with default date."""
        gen = ReportGenerator()
        assert gen.reference_date == date.today()

    def test_init_with_custom_date(self) -> None:
        """Initialize with custom reference date."""
        ref_date = date(2025, 6, 30)
        gen = ReportGenerator(reference_date=ref_date)
        assert gen.reference_date == ref_date

    def test_generate_portfolio_summary(self, sample_data_dir: Path) -> None:
        """Generate portfolio summary from complete analytics pipeline."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        ref_date = date(2025, 6, 30)

        # Run all upstream engines
        exposure_engine = StandardExposureAnalyzer(reference_date=ref_date)
        exposure_result = exposure_engine.analyze(dataset=dataset)

        eligibility_engine = ConfigurableEligibilityEngine(
            rule=EligibilityRule(
                allowed_asset_types={"sovereign", "corporate_bond", "covered_bond"},
                allowed_currencies={"EUR"},
            ),
            reference_date=ref_date,
        )
        eligibility_result = eligibility_engine.assess(dataset=dataset)
        eligibility_data = {
            isin: decision.eligible for isin, decision in eligibility_result.decisions.items()
        }

        haircut_engine = ScheduleBasedHaircutEngine(reference_date=ref_date)
        haircut_report = haircut_engine.calculate(dataset=dataset)

        coverage_engine = StandardCoverageAnalyzer(reference_date=ref_date)
        coverage_report = coverage_engine.assess(
            exposure_result=exposure_result,
            haircut_report=haircut_report,
            dataset=dataset,
        )

        concentration_engine = StandardConcentrationAnalyzer(reference_date=ref_date)
        concentration_analysis = concentration_engine.analyze(
            exposure_result=exposure_result, dataset=dataset
        )

        stress_engine = StandardStressEngine(reference_date=ref_date)
        stress_report = stress_engine.stress(
            exposure_result=exposure_result,
            haircut_report=haircut_report,
            coverage_report=coverage_report,
            dataset=dataset,
        )

        monitoring_engine = StandardMonitoringEngine(reference_date=ref_date)
        monitoring_report = monitoring_engine.monitor(coverage_report=coverage_report)

        # Generate report
        report_gen = ReportGenerator(reference_date=ref_date)
        report = report_gen.generate_portfolio_summary(
            exposure_result=exposure_result,
            eligibility_data=eligibility_data,
            haircut_report=haircut_report,
            coverage_report=coverage_report,
            concentration_analysis=concentration_analysis,
            stress_report=stress_report,
            monitoring_report=monitoring_report,
            dataset=dataset,
        )

        assert isinstance(report, PortfolioSummaryReport)
        assert report.reference_date == ref_date
        assert report.overall_risk_level in ("low", "medium", "high", "critical")

    def test_exposure_summary(self, sample_data_dir: Path) -> None:
        """Verify exposure summary aggregation."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        ref_date = date(2025, 6, 30)
        exposure_engine = StandardExposureAnalyzer(reference_date=ref_date)
        exposure_result = exposure_engine.analyze(dataset=dataset)

        report_gen = ReportGenerator(reference_date=ref_date)
        exposure_summary = report_gen._summarize_exposure(exposure_result, dataset)

        assert exposure_summary.total_exposure > Decimal("0")
        assert exposure_summary.avg_exposure > Decimal("0")
        assert exposure_summary.min_exposure >= Decimal("0")
        assert exposure_summary.max_exposure >= exposure_summary.avg_exposure
        assert len(exposure_summary.top_3_exposures) <= 3

    def test_coverage_summary(self, sample_data_dir: Path) -> None:
        """Verify coverage summary aggregation."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        ref_date = date(2025, 6, 30)

        exposure_engine = StandardExposureAnalyzer(reference_date=ref_date)
        exposure_result = exposure_engine.analyze(dataset=dataset)

        haircut_engine = ScheduleBasedHaircutEngine(reference_date=ref_date)
        haircut_report = haircut_engine.calculate(dataset=dataset)

        coverage_engine = StandardCoverageAnalyzer(reference_date=ref_date)
        coverage_report = coverage_engine.assess(
            exposure_result=exposure_result,
            haircut_report=haircut_report,
            dataset=dataset,
        )

        report_gen = ReportGenerator(reference_date=ref_date)
        coverage_summary = report_gen._summarize_coverage(coverage_report)

        assert coverage_summary.total_exposure > Decimal("0")
        assert coverage_summary.total_collateral >= Decimal("0")
        assert coverage_summary.covered_counterparties >= 0
        assert coverage_summary.undercovered_counterparties >= 0
        assert (
            coverage_summary.covered_counterparties + coverage_summary.undercovered_counterparties
            == len(coverage_report.assessments)
        )

    def test_concentration_summary(self, sample_data_dir: Path) -> None:
        """Verify concentration summary aggregation."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        ref_date = date(2025, 6, 30)

        exposure_engine = StandardExposureAnalyzer(reference_date=ref_date)
        exposure_result = exposure_engine.analyze(dataset=dataset)

        concentration_engine = StandardConcentrationAnalyzer(reference_date=ref_date)
        concentration_analysis = concentration_engine.analyze(
            exposure_result=exposure_result, dataset=dataset
        )

        report_gen = ReportGenerator(reference_date=ref_date)
        concentration_summary = report_gen._summarize_concentration(concentration_analysis)

        assert concentration_summary.issuer_concentration_count >= 0
        assert concentration_summary.herfindahl_index >= Decimal("0")
        assert concentration_summary.herfindahl_index <= Decimal("1")

    def test_stress_summary(self, sample_data_dir: Path) -> None:
        """Verify stress test summary aggregation."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        ref_date = date(2025, 6, 30)

        exposure_engine = StandardExposureAnalyzer(reference_date=ref_date)
        exposure_result = exposure_engine.analyze(dataset=dataset)

        haircut_engine = ScheduleBasedHaircutEngine(reference_date=ref_date)
        haircut_report = haircut_engine.calculate(dataset=dataset)

        coverage_engine = StandardCoverageAnalyzer(reference_date=ref_date)
        coverage_report = coverage_engine.assess(
            exposure_result=exposure_result,
            haircut_report=haircut_report,
            dataset=dataset,
        )

        stress_engine = StandardStressEngine(reference_date=ref_date)
        stress_report = stress_engine.stress(
            exposure_result=exposure_result,
            haircut_report=haircut_report,
            coverage_report=coverage_report,
            dataset=dataset,
        )

        report_gen = ReportGenerator(reference_date=ref_date)
        stress_summary = report_gen._summarize_stress(stress_report)

        assert stress_summary.total_scenarios > 0
        assert stress_summary.coverage_breaches >= 0
        assert stress_summary.worst_case_scenario

    def test_monitoring_summary(self, sample_data_dir: Path) -> None:
        """Verify monitoring summary aggregation."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        ref_date = date(2025, 6, 30)

        exposure_engine = StandardExposureAnalyzer(reference_date=ref_date)
        exposure_result = exposure_engine.analyze(dataset=dataset)

        haircut_engine = ScheduleBasedHaircutEngine(reference_date=ref_date)
        haircut_report = haircut_engine.calculate(dataset=dataset)

        coverage_engine = StandardCoverageAnalyzer(reference_date=ref_date)
        coverage_report = coverage_engine.assess(
            exposure_result=exposure_result,
            haircut_report=haircut_report,
            dataset=dataset,
        )

        monitoring_engine = StandardMonitoringEngine(reference_date=ref_date)
        monitoring_report = monitoring_engine.monitor(coverage_report=coverage_report)

        report_gen = ReportGenerator(reference_date=ref_date)
        monitoring_summary = report_gen._summarize_monitoring(monitoring_report)

        assert monitoring_summary.num_anomalies >= 0
        assert monitoring_summary.num_critical_warnings >= 0
        assert monitoring_summary.num_early_warnings >= 0

    def test_overall_risk_assessment(self, sample_data_dir: Path) -> None:
        """Verify overall risk assessment logic."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        ref_date = date(2025, 6, 30)

        exposure_engine = StandardExposureAnalyzer(reference_date=ref_date)
        exposure_result = exposure_engine.analyze(dataset=dataset)

        haircut_engine = ScheduleBasedHaircutEngine(reference_date=ref_date)
        haircut_report = haircut_engine.calculate(dataset=dataset)

        coverage_engine = StandardCoverageAnalyzer(reference_date=ref_date)
        coverage_report = coverage_engine.assess(
            exposure_result=exposure_result,
            haircut_report=haircut_report,
            dataset=dataset,
        )

        concentration_engine = StandardConcentrationAnalyzer(reference_date=ref_date)
        concentration_analysis = concentration_engine.analyze(
            exposure_result=exposure_result, dataset=dataset
        )

        stress_engine = StandardStressEngine(reference_date=ref_date)
        stress_report = stress_engine.stress(
            exposure_result=exposure_result,
            haircut_report=haircut_report,
            coverage_report=coverage_report,
            dataset=dataset,
        )

        monitoring_engine = StandardMonitoringEngine(reference_date=ref_date)
        monitoring_report = monitoring_engine.monitor(coverage_report=coverage_report)

        report_gen = ReportGenerator(reference_date=ref_date)
        coverage_summary = report_gen._summarize_coverage(coverage_report)
        concentration_summary = report_gen._summarize_concentration(concentration_analysis)
        stress_summary = report_gen._summarize_stress(stress_report)
        monitoring_summary = report_gen._summarize_monitoring(monitoring_report)

        risk_level = report_gen._assess_overall_risk(
            coverage_summary, concentration_summary, stress_summary, monitoring_summary
        )

        assert risk_level in ("low", "medium", "high", "critical")

    def test_key_findings_extraction(self, sample_data_dir: Path) -> None:
        """Verify key findings extraction."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        ref_date = date(2025, 6, 30)

        exposure_engine = StandardExposureAnalyzer(reference_date=ref_date)
        exposure_result = exposure_engine.analyze(dataset=dataset)

        haircut_engine = ScheduleBasedHaircutEngine(reference_date=ref_date)
        haircut_report = haircut_engine.calculate(dataset=dataset)

        coverage_engine = StandardCoverageAnalyzer(reference_date=ref_date)
        coverage_report = coverage_engine.assess(
            exposure_result=exposure_result,
            haircut_report=haircut_report,
            dataset=dataset,
        )

        concentration_engine = StandardConcentrationAnalyzer(reference_date=ref_date)
        concentration_analysis = concentration_engine.analyze(
            exposure_result=exposure_result, dataset=dataset
        )

        stress_engine = StandardStressEngine(reference_date=ref_date)
        stress_report = stress_engine.stress(
            exposure_result=exposure_result,
            haircut_report=haircut_report,
            coverage_report=coverage_report,
            dataset=dataset,
        )

        monitoring_engine = StandardMonitoringEngine(reference_date=ref_date)
        monitoring_report = monitoring_engine.monitor(coverage_report=coverage_report)

        report_gen = ReportGenerator(reference_date=ref_date)
        coverage_summary = report_gen._summarize_coverage(coverage_report)
        concentration_summary = report_gen._summarize_concentration(concentration_analysis)
        stress_summary = report_gen._summarize_stress(stress_report)
        monitoring_summary = report_gen._summarize_monitoring(monitoring_report)

        findings = report_gen._extract_key_findings(
            coverage_summary, concentration_summary, stress_summary, monitoring_summary
        )

        assert isinstance(findings, list)
