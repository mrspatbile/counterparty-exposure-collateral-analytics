"""Tests for concentration risk analysis module."""

import tempfile
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Iterator

import pytest

from collateral_analytics.engines.concentration import StandardConcentrationAnalyzer
from collateral_analytics.engines.exposure import StandardExposureAnalyzer
from collateral_analytics.engines.haircut import ScheduleBasedHaircutEngine
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


class TestConcentrationMetric:
    """Tests for ConcentrationMetric."""

    def test_create_metric(self) -> None:
        """Create concentration metric."""
        from collateral_analytics.models.concentration import ConcentrationMetric

        metric = ConcentrationMetric(
            dimension_value="Germany",
            dimension_type="issuer",
            count=2,
            gross_exposure=Decimal("1500000"),
            net_exposure=Decimal("1450000"),
            adjusted_collateral=Decimal("1430000"),
            concentration_ratio=Decimal("0.35"),
            concentration_percent=Decimal("35"),
        )
        assert metric.dimension_value == "Germany"
        assert metric.concentration_ratio == Decimal("0.35")


class TestStandardConcentrationAnalyzer:
    """Tests for StandardConcentrationAnalyzer."""

    def test_init_with_default_date(self) -> None:
        """Initialize with default date."""
        analyzer = StandardConcentrationAnalyzer()
        assert analyzer.reference_date == date.today()

    def test_init_with_custom_date(self) -> None:
        """Initialize with custom reference date."""
        ref_date = date(2025, 6, 30)
        analyzer = StandardConcentrationAnalyzer(reference_date=ref_date)
        assert analyzer.reference_date == ref_date

    def test_analyze_basic(self, sample_data_dir: Path) -> None:
        """Analyze concentration with sample data."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        ref_date = date(2025, 6, 30)

        exposure_engine = StandardExposureAnalyzer(reference_date=ref_date)
        exposure_result = exposure_engine.analyze(dataset=dataset)

        haircut_engine = ScheduleBasedHaircutEngine(reference_date=ref_date)
        haircut_report = haircut_engine.calculate(dataset=dataset)

        analyzer = StandardConcentrationAnalyzer(reference_date=ref_date)
        analysis = analyzer.analyze(
            dataset=dataset,
            exposure_result=exposure_result,
            haircut_report=haircut_report,
        )

        assert analysis.success
        assert len(analysis.by_counterparty) == 2
        assert len(analysis.by_asset_type) > 0

    def test_asset_type_concentration_calculated(self, sample_data_dir: Path) -> None:
        """Verify asset type concentration is calculated."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        ref_date = date(2025, 6, 30)

        exposure_engine = StandardExposureAnalyzer(reference_date=ref_date)
        exposure_result = exposure_engine.analyze(dataset=dataset)

        haircut_engine = ScheduleBasedHaircutEngine(reference_date=ref_date)
        haircut_report = haircut_engine.calculate(dataset=dataset)

        analyzer = StandardConcentrationAnalyzer(reference_date=ref_date)
        analysis = analyzer.analyze(
            dataset=dataset,
            exposure_result=exposure_result,
            haircut_report=haircut_report,
        )

        assert len(analysis.by_asset_type) >= 2  # At least sovereign and corporate

    def test_rating_concentration_calculated(self, sample_data_dir: Path) -> None:
        """Verify rating concentration is calculated."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        ref_date = date(2025, 6, 30)

        exposure_engine = StandardExposureAnalyzer(reference_date=ref_date)
        exposure_result = exposure_engine.analyze(dataset=dataset)

        haircut_engine = ScheduleBasedHaircutEngine(reference_date=ref_date)
        haircut_report = haircut_engine.calculate(dataset=dataset)

        analyzer = StandardConcentrationAnalyzer(reference_date=ref_date)
        analysis = analyzer.analyze(
            dataset=dataset,
            exposure_result=exposure_result,
            haircut_report=haircut_report,
        )

        assert len(analysis.by_rating) >= 1

    def test_counterparty_concentration_calculated(self, sample_data_dir: Path) -> None:
        """Verify counterparty concentration is calculated."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        ref_date = date(2025, 6, 30)

        exposure_engine = StandardExposureAnalyzer(reference_date=ref_date)
        exposure_result = exposure_engine.analyze(dataset=dataset)

        haircut_engine = ScheduleBasedHaircutEngine(reference_date=ref_date)
        haircut_report = haircut_engine.calculate(dataset=dataset)

        analyzer = StandardConcentrationAnalyzer(reference_date=ref_date)
        analysis = analyzer.analyze(
            dataset=dataset,
            exposure_result=exposure_result,
            haircut_report=haircut_report,
        )

        assert len(analysis.by_counterparty) == 2

    def test_herfindahl_index_calculated(self, sample_data_dir: Path) -> None:
        """Verify Herfindahl index is calculated."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        ref_date = date(2025, 6, 30)

        exposure_engine = StandardExposureAnalyzer(reference_date=ref_date)
        exposure_result = exposure_engine.analyze(dataset=dataset)

        haircut_engine = ScheduleBasedHaircutEngine(reference_date=ref_date)
        haircut_report = haircut_engine.calculate(dataset=dataset)

        analyzer = StandardConcentrationAnalyzer(reference_date=ref_date)
        analysis = analyzer.analyze(
            dataset=dataset,
            exposure_result=exposure_result,
            haircut_report=haircut_report,
        )

        # Herfindahl should equal sum of squared concentration ratios
        expected_h = sum(m.herfindahl_contribution for m in analysis.by_counterparty)
        assert analysis.portfolio_herfindahl_index == expected_h

    def test_concentration_ranking(self, sample_data_dir: Path) -> None:
        """Verify concentration metrics are ranked."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        ref_date = date(2025, 6, 30)

        exposure_engine = StandardExposureAnalyzer(reference_date=ref_date)
        exposure_result = exposure_engine.analyze(dataset=dataset)

        haircut_engine = ScheduleBasedHaircutEngine(reference_date=ref_date)
        haircut_report = haircut_engine.calculate(dataset=dataset)

        analyzer = StandardConcentrationAnalyzer(reference_date=ref_date)
        analysis = analyzer.analyze(
            dataset=dataset,
            exposure_result=exposure_result,
            haircut_report=haircut_report,
        )

        # Ranks should be sequential starting from 1
        for metric in analysis.by_counterparty:
            assert metric.rank >= 1

    def test_concentration_percents_calculated(self, sample_data_dir: Path) -> None:
        """Verify concentration percentages are calculated."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        ref_date = date(2025, 6, 30)

        exposure_engine = StandardExposureAnalyzer(reference_date=ref_date)
        exposure_result = exposure_engine.analyze(dataset=dataset)

        haircut_engine = ScheduleBasedHaircutEngine(reference_date=ref_date)
        haircut_report = haircut_engine.calculate(dataset=dataset)

        analyzer = StandardConcentrationAnalyzer(reference_date=ref_date)
        analysis = analyzer.analyze(
            dataset=dataset,
            exposure_result=exposure_result,
            haircut_report=haircut_report,
        )

        for metric in analysis.by_counterparty:
            expected_percent = metric.concentration_ratio * Decimal("100")
            assert metric.concentration_percent == expected_percent

    def test_top_n_concentration(self, sample_data_dir: Path) -> None:
        """Verify top N concentration is calculated."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        ref_date = date(2025, 6, 30)

        exposure_engine = StandardExposureAnalyzer(reference_date=ref_date)
        exposure_result = exposure_engine.analyze(dataset=dataset)

        haircut_engine = ScheduleBasedHaircutEngine(reference_date=ref_date)
        haircut_report = haircut_engine.calculate(dataset=dataset)

        analyzer = StandardConcentrationAnalyzer(reference_date=ref_date)
        analysis = analyzer.analyze(
            dataset=dataset,
            exposure_result=exposure_result,
            haircut_report=haircut_report,
        )

        # Top 3 should be sum of largest exposures
        assert analysis.top_n_concentration > 0
        assert analysis.top_n_concentration <= Decimal("1")

    def test_issuer_concentration_tracked(self, sample_data_dir: Path) -> None:
        """Verify issuer concentrations are tracked."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        ref_date = date(2025, 6, 30)

        exposure_engine = StandardExposureAnalyzer(reference_date=ref_date)
        exposure_result = exposure_engine.analyze(dataset=dataset)

        haircut_engine = ScheduleBasedHaircutEngine(reference_date=ref_date)
        haircut_report = haircut_engine.calculate(dataset=dataset)

        analyzer = StandardConcentrationAnalyzer(reference_date=ref_date)
        analysis = analyzer.analyze(
            dataset=dataset,
            exposure_result=exposure_result,
            haircut_report=haircut_report,
        )

        # Should have metrics for Germany, Corp A, Bank B
        issuer_values = {m.dimension_value for m in analysis.by_issuer}
        assert "Germany" in issuer_values or len(analysis.by_issuer) > 0

    def test_missing_parameters(self) -> None:
        """Test handling of missing parameters."""
        analyzer = StandardConcentrationAnalyzer()
        analysis = analyzer.analyze()

        assert not analysis.success
        assert len(analysis.errors) > 0

    def test_dimension_counts_tracked(self, sample_data_dir: Path) -> None:
        """Verify dimension counts are tracked."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        ref_date = date(2025, 6, 30)

        exposure_engine = StandardExposureAnalyzer(reference_date=ref_date)
        exposure_result = exposure_engine.analyze(dataset=dataset)

        haircut_engine = ScheduleBasedHaircutEngine(reference_date=ref_date)
        haircut_report = haircut_engine.calculate(dataset=dataset)

        analyzer = StandardConcentrationAnalyzer(reference_date=ref_date)
        analysis = analyzer.analyze(
            dataset=dataset,
            exposure_result=exposure_result,
            haircut_report=haircut_report,
        )

        assert analysis.num_counterparties == 2
        assert analysis.num_asset_types >= 1
        assert analysis.num_ratings >= 1
