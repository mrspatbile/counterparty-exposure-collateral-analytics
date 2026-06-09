"""Tests for exposure analysis module."""

import tempfile
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Iterator

import pytest

from collateral_analytics.engines.exposure import StandardExposureAnalyzer
from collateral_analytics.loaders.data_manager import DataManager
from collateral_analytics.models.exposure import ExposureSnapshot


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
            "CP003,Bank C,IT,BBB,500000.00,1000000.00\n"
        )

        positions_csv = tmpdir_path / "collateral_positions.csv"
        positions_csv.write_text(
            "counterparty_id,isin,quantity,market_value\n"
            "CP001,XS1111111111,1000.000000,1000000.00\n"
            "CP001,XS2222222222,500.000000,250000.00\n"
            "CP002,XS2222222222,1000.000000,500000.00\n"
            "CP002,XS3333333333,500.000000,375000.00\n"
            "CP003,XS1111111111,200.000000,200000.00\n"
        )

        haircuts_csv = tmpdir_path / "haircut_schedule.csv"
        haircuts_csv.write_text(
            "asset_type,maturity_bucket,rating_bucket,haircut_rate\n"
            "sovereign,5-10y,AAA-AA,0.0100\n"
            "sovereign,10y+,AAA-AA,0.0150\n"
            "corporate_bond,3-5y,BBB,0.1500\n"
            "corporate_bond,5-10y,BBB,0.2000\n"
            "covered_bond,5-10y,AAA-AA,0.0300\n"
            "covered_bond,10y+,AAA-AA,0.0400\n"
        )

        yield tmpdir_path


class TestExposureSnapshot:
    """Tests for ExposureSnapshot."""

    def test_create_snapshot(self) -> None:
        """Create valid exposure snapshot."""
        snapshot = ExposureSnapshot(
            counterparty_id="CP001",
            counterparty_name="Bank A",
            gross_exposure=Decimal("1000000"),
            adjusted_collateral_value=Decimal("900000"),
            net_exposure=Decimal("100000"),
            utilisation_ratio=Decimal("0.1"),
            unsecured_exposure=Decimal("100000"),
            concentration_ratio=Decimal("0.15"),
            exposure_limit=Decimal("1000000"),
            available_capacity=Decimal("900000"),
        )
        assert snapshot.counterparty_id == "CP001"

    def test_is_at_limit(self) -> None:
        """Test is_at_limit method."""
        snapshot = ExposureSnapshot(
            counterparty_id="CP001",
            counterparty_name="Bank A",
            gross_exposure=Decimal("1000000"),
            adjusted_collateral_value=Decimal("0"),
            net_exposure=Decimal("1000000"),
            utilisation_ratio=Decimal("1.0"),
            unsecured_exposure=Decimal("1000000"),
            concentration_ratio=Decimal("0.5"),
            exposure_limit=Decimal("1000000"),
            available_capacity=Decimal("0"),
        )
        assert snapshot.is_at_limit()

    def test_is_over_limit(self) -> None:
        """Test is_over_limit method."""
        snapshot = ExposureSnapshot(
            counterparty_id="CP001",
            counterparty_name="Bank A",
            gross_exposure=Decimal("1100000"),
            adjusted_collateral_value=Decimal("0"),
            net_exposure=Decimal("1100000"),
            utilisation_ratio=Decimal("1.1"),
            unsecured_exposure=Decimal("1100000"),
            concentration_ratio=Decimal("0.5"),
            exposure_limit=Decimal("1000000"),
            available_capacity=Decimal("-100000"),
        )
        assert snapshot.is_over_limit()

    def test_has_capacity(self) -> None:
        """Test has_capacity method."""
        snap_with = ExposureSnapshot(
            counterparty_id="CP001",
            counterparty_name="Bank A",
            gross_exposure=Decimal("500000"),
            adjusted_collateral_value=Decimal("0"),
            net_exposure=Decimal("500000"),
            utilisation_ratio=Decimal("0.5"),
            unsecured_exposure=Decimal("500000"),
            concentration_ratio=Decimal("0.2"),
            exposure_limit=Decimal("1000000"),
            available_capacity=Decimal("500000"),
        )
        assert snap_with.has_capacity()


class TestStandardExposureAnalyzer:
    """Tests for StandardExposureAnalyzer."""

    def test_init_with_default_date(self) -> None:
        """Initialize with default date."""
        analyzer = StandardExposureAnalyzer()
        assert analyzer.reference_date == date.today()

    def test_init_with_custom_date(self) -> None:
        """Initialize with custom reference date."""
        ref_date = date(2025, 6, 30)
        analyzer = StandardExposureAnalyzer(reference_date=ref_date)
        assert analyzer.reference_date == ref_date

    def test_analyze_basic(self, sample_data_dir: Path) -> None:
        """Analyze exposure with sample data."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        analyzer = StandardExposureAnalyzer(reference_date=date(2025, 6, 30))
        result = analyzer.analyze(dataset=dataset)

        assert result.success
        assert len(result.snapshots) == 3
        assert "CP001" in result.snapshots

    def test_gross_exposure_calculated(self, sample_data_dir: Path) -> None:
        """Verify gross exposure is sum of positions."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        analyzer = StandardExposureAnalyzer(reference_date=date(2025, 6, 30))
        result = analyzer.analyze(dataset=dataset)

        assert result.snapshots["CP001"].gross_exposure == Decimal("1250000.00")
        assert result.snapshots["CP002"].gross_exposure == Decimal("875000.00")
        assert result.snapshots["CP003"].gross_exposure == Decimal("200000.00")

    def test_adjusted_collateral_applies_haircuts(self, sample_data_dir: Path) -> None:
        """Verify adjusted collateral applies haircuts."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        analyzer = StandardExposureAnalyzer(reference_date=date(2025, 6, 30))
        result = analyzer.analyze(dataset=dataset)

        expected_adj_cp001 = Decimal("985000.00") + Decimal("200000.00")
        assert result.snapshots["CP001"].adjusted_collateral_value == expected_adj_cp001

    def test_net_exposure_calculated(self, sample_data_dir: Path) -> None:
        """Verify net exposure = gross - adjusted_collateral."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        analyzer = StandardExposureAnalyzer(reference_date=date(2025, 6, 30))
        result = analyzer.analyze(dataset=dataset)

        snapshot = result.snapshots["CP001"]
        expected_net = snapshot.gross_exposure - snapshot.adjusted_collateral_value
        assert snapshot.net_exposure == expected_net

    def test_utilisation_ratio_calculated(self, sample_data_dir: Path) -> None:
        """Verify utilisation ratio = net_exposure / limit."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        analyzer = StandardExposureAnalyzer(reference_date=date(2025, 6, 30))
        result = analyzer.analyze(dataset=dataset)

        snapshot = result.snapshots["CP001"]
        expected_util = snapshot.net_exposure / snapshot.exposure_limit
        assert snapshot.utilisation_ratio == expected_util

    def test_concentration_ratios_sum_to_one(self, sample_data_dir: Path) -> None:
        """Verify concentration ratios sum to 1.0."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        analyzer = StandardExposureAnalyzer(reference_date=date(2025, 6, 30))
        result = analyzer.analyze(dataset=dataset)

        total_conc = sum(s.concentration_ratio for s in result.snapshots.values())
        assert abs(total_conc - Decimal("1.0")) < Decimal("0.0001")

    def test_metrics_aggregated_correctly(self, sample_data_dir: Path) -> None:
        """Verify aggregated metrics."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        analyzer = StandardExposureAnalyzer(reference_date=date(2025, 6, 30))
        result = analyzer.analyze(dataset=dataset)

        metrics = result.metrics
        assert metrics.total_counterparties == 3
        expected_gross = Decimal("1250000") + Decimal("875000") + Decimal("200000")
        assert metrics.portfolio_gross_exposure == expected_gross

    def test_rankings_ordered_by_metric(self, sample_data_dir: Path) -> None:
        """Verify rankings ordered correctly."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        analyzer = StandardExposureAnalyzer(reference_date=date(2025, 6, 30))
        result = analyzer.analyze(dataset=dataset)

        rankings = result.rankings_by_gross_exposure
        for i in range(len(rankings) - 1):
            assert rankings[i].metric_value >= rankings[i + 1].metric_value
            assert rankings[i].rank == i + 1

    def test_empty_dataset_handling(self) -> None:
        """Test handling of empty dataset."""
        from collateral_analytics.loaders.data_manager import AnalyticsDataset

        empty_dataset = AnalyticsDataset(
            securities={},
            counterparties={},
            positions=[],
            haircuts=[],
        )

        analyzer = StandardExposureAnalyzer()
        result = analyzer.analyze(dataset=empty_dataset)

        assert result.success
        assert len(result.snapshots) == 0
        assert result.metrics.total_counterparties == 0
