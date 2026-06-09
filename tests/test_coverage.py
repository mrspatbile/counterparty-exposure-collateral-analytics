"""Tests for collateral coverage assessment module."""

import tempfile
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from collateral_analytics.engines.coverage import StandardCoverageAnalyzer
from collateral_analytics.engines.exposure import StandardExposureAnalyzer
from collateral_analytics.engines.haircut import ScheduleBasedHaircutEngine
from collateral_analytics.loaders.data_manager import DataManager


@pytest.fixture
def sample_data_dir() -> Path:
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


class TestCoverageAssessment:
    """Tests for CoverageAssessment."""

    def test_create_covered_assessment(self) -> None:
        """Create coverage assessment for fully covered counterparty."""
        from collateral_analytics.models.coverage import CoverageAssessment

        assessment = CoverageAssessment(
            counterparty_id="CP001",
            counterparty_name="Bank A",
            net_exposure=Decimal("1000000"),
            adjusted_collateral_value=Decimal("1200000"),
            coverage_ratio=Decimal("1.2"),
            unsecured_exposure=Decimal("0"),
            excess_collateral=Decimal("200000"),
            is_covered=True,
        )
        assert assessment.is_covered
        assert assessment.excess_collateral == Decimal("200000")

    def test_create_undercovered_assessment(self) -> None:
        """Create coverage assessment for undercovered counterparty."""
        from collateral_analytics.models.coverage import CoverageAssessment

        assessment = CoverageAssessment(
            counterparty_id="CP002",
            counterparty_name="Bank B",
            net_exposure=Decimal("1000000"),
            adjusted_collateral_value=Decimal("800000"),
            coverage_ratio=Decimal("0.8"),
            unsecured_exposure=Decimal("200000"),
            excess_collateral=Decimal("0"),
            is_covered=False,
        )
        assert not assessment.is_covered
        assert assessment.unsecured_exposure == Decimal("200000")


class TestStandardCoverageAnalyzer:
    """Tests for StandardCoverageAnalyzer."""

    def test_init_with_default_date(self) -> None:
        """Initialize with default date."""
        analyzer = StandardCoverageAnalyzer()
        assert analyzer.reference_date == date.today()

    def test_init_with_custom_date(self) -> None:
        """Initialize with custom reference date."""
        ref_date = date(2025, 6, 30)
        analyzer = StandardCoverageAnalyzer(reference_date=ref_date)
        assert analyzer.reference_date == ref_date

    def test_assess_with_exposure_and_haircut(self, sample_data_dir: Path) -> None:
        """Assess coverage using exposure and haircut results."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        ref_date = date(2025, 6, 30)

        # Generate exposure analysis
        exposure_engine = StandardExposureAnalyzer(reference_date=ref_date)
        exposure_result = exposure_engine.analyze(dataset=dataset)

        # Generate haircut analysis
        haircut_engine = ScheduleBasedHaircutEngine(reference_date=ref_date)
        haircut_report = haircut_engine.calculate(dataset=dataset)

        # Assess coverage
        coverage_analyzer = StandardCoverageAnalyzer(reference_date=ref_date)
        report = coverage_analyzer.assess(
            exposure_result=exposure_result,
            haircut_report=haircut_report,
            dataset=dataset,
        )

        assert report.success
        assert report.total_counterparties == 2

    def test_coverage_ratio_calculated(self, sample_data_dir: Path) -> None:
        """Verify coverage ratio is calculated correctly."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        ref_date = date(2025, 6, 30)

        exposure_engine = StandardExposureAnalyzer(reference_date=ref_date)
        exposure_result = exposure_engine.analyze(dataset=dataset)

        haircut_engine = ScheduleBasedHaircutEngine(reference_date=ref_date)
        haircut_report = haircut_engine.calculate(dataset=dataset)

        coverage_analyzer = StandardCoverageAnalyzer(reference_date=ref_date)
        report = coverage_analyzer.assess(
            exposure_result=exposure_result,
            haircut_report=haircut_report,
            dataset=dataset,
        )

        for assessment in report.assessments.values():
            expected_ratio = (
                assessment.adjusted_collateral_value / assessment.net_exposure
                if assessment.net_exposure > 0
                else Decimal("0")
            )
            assert assessment.coverage_ratio == expected_ratio

    def test_covered_counterparty_detection(self, sample_data_dir: Path) -> None:
        """Detect fully covered counterparties (coverage >= 1.0)."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        ref_date = date(2025, 6, 30)

        exposure_engine = StandardExposureAnalyzer(reference_date=ref_date)
        exposure_result = exposure_engine.analyze(dataset=dataset)

        haircut_engine = ScheduleBasedHaircutEngine(reference_date=ref_date)
        haircut_report = haircut_engine.calculate(dataset=dataset)

        coverage_analyzer = StandardCoverageAnalyzer(reference_date=ref_date)
        report = coverage_analyzer.assess(
            exposure_result=exposure_result,
            haircut_report=haircut_report,
            dataset=dataset,
        )

        for assessment in report.assessments.values():
            if assessment.coverage_ratio >= Decimal("1.0"):
                assert assessment.is_covered
            else:
                assert not assessment.is_covered

    def test_unsecured_exposure_calculated(self, sample_data_dir: Path) -> None:
        """Verify unsecured exposure (shortfall) is calculated."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        ref_date = date(2025, 6, 30)

        exposure_engine = StandardExposureAnalyzer(reference_date=ref_date)
        exposure_result = exposure_engine.analyze(dataset=dataset)

        haircut_engine = ScheduleBasedHaircutEngine(reference_date=ref_date)
        haircut_report = haircut_engine.calculate(dataset=dataset)

        coverage_analyzer = StandardCoverageAnalyzer(reference_date=ref_date)
        report = coverage_analyzer.assess(
            exposure_result=exposure_result,
            haircut_report=haircut_report,
            dataset=dataset,
        )

        for assessment in report.assessments.values():
            expected_unsecured = max(
                Decimal("0"),
                assessment.net_exposure - assessment.adjusted_collateral_value,
            )
            assert assessment.unsecured_exposure == expected_unsecured

    def test_excess_collateral_calculated(self, sample_data_dir: Path) -> None:
        """Verify excess collateral is calculated."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        ref_date = date(2025, 6, 30)

        exposure_engine = StandardExposureAnalyzer(reference_date=ref_date)
        exposure_result = exposure_engine.analyze(dataset=dataset)

        haircut_engine = ScheduleBasedHaircutEngine(reference_date=ref_date)
        haircut_report = haircut_engine.calculate(dataset=dataset)

        coverage_analyzer = StandardCoverageAnalyzer(reference_date=ref_date)
        report = coverage_analyzer.assess(
            exposure_result=exposure_result,
            haircut_report=haircut_report,
            dataset=dataset,
        )

        for assessment in report.assessments.values():
            expected_excess = max(
                Decimal("0"),
                assessment.adjusted_collateral_value - assessment.net_exposure,
            )
            assert assessment.excess_collateral == expected_excess

    def test_portfolio_coverage_ratio_aggregated(self, sample_data_dir: Path) -> None:
        """Verify portfolio coverage is aggregated correctly."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        ref_date = date(2025, 6, 30)

        exposure_engine = StandardExposureAnalyzer(reference_date=ref_date)
        exposure_result = exposure_engine.analyze(dataset=dataset)

        haircut_engine = ScheduleBasedHaircutEngine(reference_date=ref_date)
        haircut_report = haircut_engine.calculate(dataset=dataset)

        coverage_analyzer = StandardCoverageAnalyzer(reference_date=ref_date)
        report = coverage_analyzer.assess(
            exposure_result=exposure_result,
            haircut_report=haircut_report,
            dataset=dataset,
        )

        expected_ratio = (
            report.total_adjusted_collateral / report.total_net_exposure
            if report.total_net_exposure > 0
            else Decimal("0")
        )
        assert report.portfolio_coverage_ratio == expected_ratio

    def test_coverage_statistics_tracked(self, sample_data_dir: Path) -> None:
        """Verify coverage statistics are tracked (min, max, average)."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        ref_date = date(2025, 6, 30)

        exposure_engine = StandardExposureAnalyzer(reference_date=ref_date)
        exposure_result = exposure_engine.analyze(dataset=dataset)

        haircut_engine = ScheduleBasedHaircutEngine(reference_date=ref_date)
        haircut_report = haircut_engine.calculate(dataset=dataset)

        coverage_analyzer = StandardCoverageAnalyzer(reference_date=ref_date)
        report = coverage_analyzer.assess(
            exposure_result=exposure_result,
            haircut_report=haircut_report,
            dataset=dataset,
        )

        assert report.min_coverage_ratio <= report.average_coverage_ratio
        assert report.average_coverage_ratio <= report.max_coverage_ratio

    def test_shortfall_and_coverage_counts(self, sample_data_dir: Path) -> None:
        """Verify covered/undercovered counts are accurate."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        ref_date = date(2025, 6, 30)

        exposure_engine = StandardExposureAnalyzer(reference_date=ref_date)
        exposure_result = exposure_engine.analyze(dataset=dataset)

        haircut_engine = ScheduleBasedHaircutEngine(reference_date=ref_date)
        haircut_report = haircut_engine.calculate(dataset=dataset)

        coverage_analyzer = StandardCoverageAnalyzer(reference_date=ref_date)
        report = coverage_analyzer.assess(
            exposure_result=exposure_result,
            haircut_report=haircut_report,
            dataset=dataset,
        )

        expected_covered = sum(1 for a in report.assessments.values() if a.is_covered)
        expected_undercovered = sum(1 for a in report.assessments.values() if not a.is_covered)

        assert report.counterparties_covered == expected_covered
        assert report.counterparties_undercovered == expected_undercovered

    def test_total_shortfall_aggregated(self, sample_data_dir: Path) -> None:
        """Verify total unsecured exposure is aggregated."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        ref_date = date(2025, 6, 30)

        exposure_engine = StandardExposureAnalyzer(reference_date=ref_date)
        exposure_result = exposure_engine.analyze(dataset=dataset)

        haircut_engine = ScheduleBasedHaircutEngine(reference_date=ref_date)
        haircut_report = haircut_engine.calculate(dataset=dataset)

        coverage_analyzer = StandardCoverageAnalyzer(reference_date=ref_date)
        report = coverage_analyzer.assess(
            exposure_result=exposure_result,
            haircut_report=haircut_report,
            dataset=dataset,
        )

        expected_shortfall = sum(a.unsecured_exposure for a in report.assessments.values())
        assert report.total_unsecured_exposure == expected_shortfall

    def test_missing_exposure_result_parameter(self) -> None:
        """Test handling of missing exposure_result parameter."""
        analyzer = StandardCoverageAnalyzer()
        report = analyzer.assess()

        assert not report.success
        assert len(report.errors) > 0

    def test_missing_haircut_report_parameter(self, sample_data_dir: Path) -> None:
        """Test handling of missing haircut_report parameter."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        exposure_engine = StandardExposureAnalyzer()
        exposure_result = exposure_engine.analyze(dataset=dataset)

        analyzer = StandardCoverageAnalyzer()
        report = analyzer.assess(exposure_result=exposure_result)

        assert not report.success
        assert len(report.errors) > 0
