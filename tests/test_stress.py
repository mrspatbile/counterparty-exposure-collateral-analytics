"""Tests for stress testing module."""

import tempfile
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Iterator

import pytest

from collateral_analytics.engines.exposure import StandardExposureAnalyzer
from collateral_analytics.engines.haircut import ScheduleBasedHaircutEngine
from collateral_analytics.engines.stress import (
    SCENARIO_MARKET_SHOCK,
    SCENARIO_RATE_SHOCK,
    StandardStressEngine,
)
from collateral_analytics.loaders.data_manager import DataManager
from collateral_analytics.models.stress import StressScenario


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


class TestStressScenario:
    """Tests for StressScenario."""

    def test_create_scenario(self) -> None:
        """Create stress scenario."""
        scenario = StressScenario(
            scenario_id="test",
            scenario_name="Test Scenario",
            haircut_shock=Decimal("0.05"),
            spread_shock_bps=100,
        )
        assert scenario.scenario_id == "test"
        assert scenario.haircut_shock == Decimal("0.05")

    def test_predefined_scenarios(self) -> None:
        """Verify predefined scenarios."""
        assert SCENARIO_RATE_SHOCK.scenario_id == "rate_shock"
        assert SCENARIO_MARKET_SHOCK.market_value_shock == Decimal("-0.10")


class TestStandardStressEngine:
    """Tests for StandardStressEngine."""

    def test_init_with_default_date(self) -> None:
        """Initialize with default date."""
        engine = StandardStressEngine()
        assert engine.reference_date == date.today()

    def test_init_with_custom_date(self) -> None:
        """Initialize with custom reference date."""
        ref_date = date(2025, 6, 30)
        engine = StandardStressEngine(reference_date=ref_date)
        assert engine.reference_date == ref_date

    def test_stress_basic(self, sample_data_dir: Path) -> None:
        """Run stress test with sample data."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        ref_date = date(2025, 6, 30)

        exposure_engine = StandardExposureAnalyzer(reference_date=ref_date)
        exposure_result = exposure_engine.analyze(dataset=dataset)

        haircut_engine = ScheduleBasedHaircutEngine(reference_date=ref_date)
        haircut_report = haircut_engine.calculate(dataset=dataset)

        stress_engine = StandardStressEngine(reference_date=ref_date)
        report = stress_engine.stress(
            exposure_result=exposure_result,
            haircut_report=haircut_report,
        )

        assert report.success
        assert len(report.scenarios) > 0
        assert len(report.results) > 0

    def test_stress_coverage_impact(self, sample_data_dir: Path) -> None:
        """Verify stress impacts coverage ratios."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        ref_date = date(2025, 6, 30)

        exposure_engine = StandardExposureAnalyzer(reference_date=ref_date)
        exposure_result = exposure_engine.analyze(dataset=dataset)

        haircut_engine = ScheduleBasedHaircutEngine(reference_date=ref_date)
        haircut_report = haircut_engine.calculate(dataset=dataset)

        stress_engine = StandardStressEngine(reference_date=ref_date)
        report = stress_engine.stress(
            exposure_result=exposure_result,
            haircut_report=haircut_report,
        )

        for result in report.results.values():
            # Stress should reduce coverage (haircut shock reduces collateral)
            assert result.coverage_ratio_delta <= Decimal("0")

    def test_stress_unsecured_exposure_impact(self, sample_data_dir: Path) -> None:
        """Verify stress increases unsecured exposure."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        ref_date = date(2025, 6, 30)

        exposure_engine = StandardExposureAnalyzer(reference_date=ref_date)
        exposure_result = exposure_engine.analyze(dataset=dataset)

        haircut_engine = ScheduleBasedHaircutEngine(reference_date=ref_date)
        haircut_report = haircut_engine.calculate(dataset=dataset)

        stress_engine = StandardStressEngine(reference_date=ref_date)
        report = stress_engine.stress(
            exposure_result=exposure_result,
            haircut_report=haircut_report,
        )

        for result in report.results.values():
            # Stress should increase unsecured exposure (reduced collateral)
            assert result.unsecured_exposure_delta >= Decimal("0")

    def test_breach_detection(self, sample_data_dir: Path) -> None:
        """Detect coverage breaches under stress."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        ref_date = date(2025, 6, 30)

        exposure_engine = StandardExposureAnalyzer(reference_date=ref_date)
        exposure_result = exposure_engine.analyze(dataset=dataset)

        haircut_engine = ScheduleBasedHaircutEngine(reference_date=ref_date)
        haircut_report = haircut_engine.calculate(dataset=dataset)

        stress_engine = StandardStressEngine(reference_date=ref_date)
        report = stress_engine.stress(
            exposure_result=exposure_result,
            haircut_report=haircut_report,
        )

        # Verify breach detection matches coverage < 1.0
        for result in report.results.values():
            expected_breach = result.stress_coverage_ratio < Decimal("1")
            assert result.coverage_breached == expected_breach

    def test_worst_case_tracking(self, sample_data_dir: Path) -> None:
        """Verify worst case scenario is tracked."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        ref_date = date(2025, 6, 30)

        exposure_engine = StandardExposureAnalyzer(reference_date=ref_date)
        exposure_result = exposure_engine.analyze(dataset=dataset)

        haircut_engine = ScheduleBasedHaircutEngine(reference_date=ref_date)
        haircut_report = haircut_engine.calculate(dataset=dataset)

        stress_engine = StandardStressEngine(reference_date=ref_date)
        report = stress_engine.stress(
            exposure_result=exposure_result,
            haircut_report=haircut_report,
        )

        assert report.worst_case_scenario
        assert report.worst_case_impact < Decimal("0")  # Coverage declines

    def test_custom_scenarios(self, sample_data_dir: Path) -> None:
        """Apply custom scenarios."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        ref_date = date(2025, 6, 30)

        exposure_engine = StandardExposureAnalyzer(reference_date=ref_date)
        exposure_result = exposure_engine.analyze(dataset=dataset)

        haircut_engine = ScheduleBasedHaircutEngine(reference_date=ref_date)
        haircut_report = haircut_engine.calculate(dataset=dataset)

        custom_scenario = StressScenario(
            scenario_id="custom",
            scenario_name="Custom Test",
            haircut_shock=Decimal("0.15"),
        )

        stress_engine = StandardStressEngine(reference_date=ref_date)
        report = stress_engine.stress(
            exposure_result=exposure_result,
            haircut_report=haircut_report,
            scenarios=[custom_scenario],
        )

        assert len(report.scenarios) == 1
        assert report.scenarios[0].scenario_id == "custom"

    def test_aggregated_unsecured_impact(self, sample_data_dir: Path) -> None:
        """Verify total unsecured impact is aggregated."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        ref_date = date(2025, 6, 30)

        exposure_engine = StandardExposureAnalyzer(reference_date=ref_date)
        exposure_result = exposure_engine.analyze(dataset=dataset)

        haircut_engine = ScheduleBasedHaircutEngine(reference_date=ref_date)
        haircut_report = haircut_engine.calculate(dataset=dataset)

        stress_engine = StandardStressEngine(reference_date=ref_date)
        report = stress_engine.stress(
            exposure_result=exposure_result,
            haircut_report=haircut_report,
        )

        expected_total = sum(r.unsecured_exposure_delta for r in report.results.values())
        assert report.total_unsecured_impact == expected_total

    def test_average_coverage_decline(self, sample_data_dir: Path) -> None:
        """Verify average coverage decline is calculated."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        ref_date = date(2025, 6, 30)

        exposure_engine = StandardExposureAnalyzer(reference_date=ref_date)
        exposure_result = exposure_engine.analyze(dataset=dataset)

        haircut_engine = ScheduleBasedHaircutEngine(reference_date=ref_date)
        haircut_report = haircut_engine.calculate(dataset=dataset)

        stress_engine = StandardStressEngine(reference_date=ref_date)
        report = stress_engine.stress(
            exposure_result=exposure_result,
            haircut_report=haircut_report,
        )

        if report.results:
            # Average should be close to calculated average (float precision)
            assert report.average_coverage_decline < Decimal("0")  # Should be negative
            assert abs(report.average_coverage_decline) > Decimal("1")  # Sanity check

    def test_missing_exposure_result(self) -> None:
        """Test handling of missing exposure_result."""
        engine = StandardStressEngine()
        report = engine.stress()

        assert not report.success
        assert len(report.errors) > 0

    def test_missing_haircut_report(self, sample_data_dir: Path) -> None:
        """Test handling of missing haircut_report."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        ref_date = date(2025, 6, 30)

        exposure_engine = StandardExposureAnalyzer(reference_date=ref_date)
        exposure_result = exposure_engine.analyze(dataset=dataset)

        engine = StandardStressEngine()
        report = engine.stress(exposure_result=exposure_result)

        assert not report.success
        assert len(report.errors) > 0
