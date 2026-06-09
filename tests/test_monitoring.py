"""Tests for AI-assisted monitoring module."""

import tempfile
from datetime import date
from pathlib import Path
from typing import Iterator

import pytest

from collateral_analytics.engines.coverage import StandardCoverageAnalyzer
from collateral_analytics.engines.exposure import StandardExposureAnalyzer
from collateral_analytics.engines.haircut import ScheduleBasedHaircutEngine
from collateral_analytics.engines.monitoring import StandardMonitoringEngine
from collateral_analytics.loaders.data_manager import DataManager


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


class TestStandardMonitoringEngine:
    """Tests for StandardMonitoringEngine."""

    def test_init_with_default_date(self) -> None:
        """Initialize with default date."""
        engine = StandardMonitoringEngine()
        assert engine.reference_date == date.today()

    def test_init_with_custom_date(self) -> None:
        """Initialize with custom reference date."""
        ref_date = date(2025, 6, 30)
        engine = StandardMonitoringEngine(reference_date=ref_date)
        assert engine.reference_date == ref_date

    def test_monitor_basic(self, sample_data_dir: Path) -> None:
        """Run monitoring with sample data."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        ref_date = date(2025, 6, 30)

        # Run upstream analysis
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

        # Monitor
        monitor_engine = StandardMonitoringEngine(reference_date=ref_date)
        report = monitor_engine.monitor(coverage_report=coverage_report)

        assert report.success
        assert report.num_anomalies >= 0
        assert report.num_warnings >= 0

    def test_anomaly_detection(self, sample_data_dir: Path) -> None:
        """Verify anomaly detection runs."""
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

        monitor_engine = StandardMonitoringEngine(reference_date=ref_date)
        report = monitor_engine.monitor(coverage_report=coverage_report)

        assert isinstance(report.anomalies, list)

    def test_commentary_generation(self, sample_data_dir: Path) -> None:
        """Verify commentary generation runs."""
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

        monitor_engine = StandardMonitoringEngine(reference_date=ref_date)
        report = monitor_engine.monitor(coverage_report=coverage_report)

        assert isinstance(report.commentaries, list)

    def test_early_warning_detection(self, sample_data_dir: Path) -> None:
        """Verify early warning detection runs."""
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

        monitor_engine = StandardMonitoringEngine(reference_date=ref_date)
        report = monitor_engine.monitor(coverage_report=coverage_report)

        assert isinstance(report.early_warnings, list)

    def test_critical_count_tracking(self, sample_data_dir: Path) -> None:
        """Verify critical count is tracked."""
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

        monitor_engine = StandardMonitoringEngine(reference_date=ref_date)
        report = monitor_engine.monitor(coverage_report=coverage_report)

        assert report.critical_count >= 0

    def test_missing_coverage_report(self) -> None:
        """Test handling of missing coverage_report."""
        engine = StandardMonitoringEngine()
        report = engine.monitor()

        assert not report.success
        assert len(report.errors) > 0
