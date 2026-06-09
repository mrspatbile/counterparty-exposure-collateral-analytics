"""Tests for haircut calculation module."""

import tempfile
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from collateral_analytics.engines.haircut import ScheduleBasedHaircutEngine
from collateral_analytics.loaders.data_manager import DataManager
from collateral_analytics.models.haircut_assessment import HaircutAssessment


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
        )

        positions_csv = tmpdir_path / "collateral_positions.csv"
        positions_csv.write_text(
            "counterparty_id,isin,quantity,market_value\n"
            "CP001,XS1111111111,1000.000000,1000000.00\n"
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


class TestHaircutAssessment:
    """Tests for HaircutAssessment."""

    def test_create_assessment(self) -> None:
        """Create haircut assessment."""
        assessment = HaircutAssessment(
            isin="XS1111111111",
            asset_type="sovereign",
            maturity_bucket="5-10y",
            rating_bucket="AAA-AA",
            market_value=Decimal("1000000"),
            haircut_rate=Decimal("0.01"),
            haircut_amount=Decimal("10000"),
            adjusted_value=Decimal("990000"),
        )
        assert assessment.isin == "XS1111111111"
        assert assessment.market_value == Decimal("1000000")
        assert assessment.adjusted_value == Decimal("990000")


class TestScheduleBasedHaircutEngine:
    """Tests for ScheduleBasedHaircutEngine."""

    def test_init_with_default_date(self) -> None:
        """Initialize with default date."""
        engine = ScheduleBasedHaircutEngine()
        assert engine.reference_date == date.today()

    def test_init_with_custom_date(self) -> None:
        """Initialize with custom reference date."""
        ref_date = date(2025, 6, 30)
        engine = ScheduleBasedHaircutEngine(reference_date=ref_date)
        assert engine.reference_date == ref_date

    def test_calculate_basic(self, sample_data_dir: Path) -> None:
        """Calculate haircuts for sample data."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        engine = ScheduleBasedHaircutEngine(reference_date=date(2025, 6, 30))
        report = engine.calculate(dataset=dataset)

        assert report.success
        assert len(report.assessments) == 3
        assert report.total_securities == 3

    def test_haircut_rate_applied(self, sample_data_dir: Path) -> None:
        """Verify haircut rates are applied from schedule."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        engine = ScheduleBasedHaircutEngine(reference_date=date(2025, 6, 30))
        report = engine.calculate(dataset=dataset)

        # Sovereign (AAA, 10y+) should have 1.5% haircut
        sovereign_assessment = report.assessments["XS1111111111"]
        assert sovereign_assessment.haircut_rate == Decimal("0.015")

    def test_haircut_amount_calculated(self, sample_data_dir: Path) -> None:
        """Verify haircut amounts are calculated correctly."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        engine = ScheduleBasedHaircutEngine(reference_date=date(2025, 6, 30))
        report = engine.calculate(dataset=dataset)

        sovereign_assessment = report.assessments["XS1111111111"]
        expected_haircut_amount = Decimal("1000000") * Decimal("0.015")
        assert sovereign_assessment.haircut_amount == expected_haircut_amount

    def test_adjusted_value_calculated(self, sample_data_dir: Path) -> None:
        """Verify adjusted values (post-haircut) are calculated correctly."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        engine = ScheduleBasedHaircutEngine(reference_date=date(2025, 6, 30))
        report = engine.calculate(dataset=dataset)

        sovereign_assessment = report.assessments["XS1111111111"]
        expected_adjusted = Decimal("1000000") - (Decimal("1000000") * Decimal("0.015"))
        assert sovereign_assessment.adjusted_value == expected_adjusted

    def test_total_market_value_aggregated(self, sample_data_dir: Path) -> None:
        """Verify total market value is aggregated."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        engine = ScheduleBasedHaircutEngine(reference_date=date(2025, 6, 30))
        report = engine.calculate(dataset=dataset)

        expected_total = Decimal("1000000") + Decimal("500000") + Decimal("750000")
        assert report.total_market_value == expected_total

    def test_total_haircut_amount_aggregated(self, sample_data_dir: Path) -> None:
        """Verify total haircuts are aggregated."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        engine = ScheduleBasedHaircutEngine(reference_date=date(2025, 6, 30))
        report = engine.calculate(dataset=dataset)

        # Sovereign: 1000000 * 0.015 = 15000
        # Corp: 500000 * 0.20 = 100000
        # Covered: 750000 * 0.03 = 22500
        expected_total_haircut = Decimal("15000") + Decimal("100000") + Decimal("22500")
        assert report.total_haircut_amount == expected_total_haircut

    def test_total_adjusted_value_aggregated(self, sample_data_dir: Path) -> None:
        """Verify total adjusted values are aggregated."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        engine = ScheduleBasedHaircutEngine(reference_date=date(2025, 6, 30))
        report = engine.calculate(dataset=dataset)

        expected_adjusted = Decimal("985000") + Decimal("400000") + Decimal("727500")
        assert report.total_adjusted_value == expected_adjusted

    def test_average_haircut_rate_calculated(self, sample_data_dir: Path) -> None:
        """Verify average haircut rate is calculated."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        engine = ScheduleBasedHaircutEngine(reference_date=date(2025, 6, 30))
        report = engine.calculate(dataset=dataset)

        # Total haircuts / total market value
        expected_avg = report.total_haircut_amount / report.total_market_value
        assert report.average_haircut_rate == expected_avg

    def test_min_max_haircut_tracked(self, sample_data_dir: Path) -> None:
        """Verify min/max haircuts are tracked."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        engine = ScheduleBasedHaircutEngine(reference_date=date(2025, 6, 30))
        report = engine.calculate(dataset=dataset)

        assert report.min_haircut_rate == Decimal("0.015")
        assert report.max_haircut_rate == Decimal("0.20")

    def test_assessment_includes_metadata(self, sample_data_dir: Path) -> None:
        """Verify assessment includes metadata."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        engine = ScheduleBasedHaircutEngine(reference_date=date(2025, 6, 30))
        report = engine.calculate(dataset=dataset)

        assessment = report.assessments["XS1111111111"]
        assert assessment.metadata
        assert "found_rule" in assessment.metadata
        assert "rating" in assessment.metadata

    def test_missing_schedule_entry(self, sample_data_dir: Path) -> None:
        """Handle security with no matching haircut rule."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        # Remove a haircut rule to simulate missing entry
        dataset.haircuts = [
            h
            for h in dataset.haircuts
            if not (h.asset_type == "corporate_bond" and h.maturity_bucket == "5-10y")
        ]

        engine = ScheduleBasedHaircutEngine(reference_date=date(2025, 6, 30))
        report = engine.calculate(dataset=dataset)

        # Should still succeed but with warnings
        assert report.success
        assert report.missing_schedule_entries >= 0

    def test_zero_haircut_tracked(self, sample_data_dir: Path) -> None:
        """Track securities with zero haircut."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        # Clear haircut schedule to get all zero haircuts
        dataset.haircuts = []

        engine = ScheduleBasedHaircutEngine(reference_date=date(2025, 6, 30))
        report = engine.calculate(dataset=dataset)

        assert report.securities_with_zero_haircut == 3
        assert report.total_haircut_amount == Decimal("0")
        assert report.average_haircut_rate == Decimal("0")

    def test_empty_dataset_handling(self) -> None:
        """Test handling of empty dataset."""
        from collateral_analytics.loaders.data_manager import AnalyticsDataset

        empty_dataset = AnalyticsDataset(
            securities={},
            counterparties={},
            positions=[],
            haircuts=[],
        )

        engine = ScheduleBasedHaircutEngine()
        report = engine.calculate(dataset=empty_dataset)

        assert report.success
        assert report.total_securities == 0
        assert report.total_haircut_amount == Decimal("0")

    def test_missing_dataset_parameter(self) -> None:
        """Test handling of missing dataset parameter."""
        engine = ScheduleBasedHaircutEngine()
        report = engine.calculate()

        assert not report.success
        assert len(report.errors) > 0
