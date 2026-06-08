"""Tests for DataManager and AnalyticsDataset."""

import tempfile
from pathlib import Path

import pytest

from collateral_analytics.loaders.data_manager import DataManager
from collateral_analytics.utils.exceptions import DataLoadingError


@pytest.fixture
def sample_data_dir() -> Path:
    """Create temporary directory with sample CSV files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create securities.csv
        securities_csv = tmpdir_path / "securities.csv"
        securities_csv.write_text(
            "isin,name,asset_type,issuer,issuer_type,country,currency,rating,maturity_date,market_value\n"
            "XS1234567890,Bond A,corporate_bond,Corp A,corporate,DE,EUR,BBB,2030-12-31,1000000.00\n"
            "XS0987654321,Bond B,sovereign,Germany,sovereign,DE,EUR,AAA,2035-06-15,500000.00\n"
        )

        # Create counterparties.csv
        counterparties_csv = tmpdir_path / "counterparties.csv"
        counterparties_csv.write_text(
            "counterparty_id,name,country,rating,exposure,exposure_limit\n"
            "CP001,Bank A,DE,A,5000000.00,10000000.00\n"
            "CP002,Bank B,FR,BBB,3000000.00,5000000.00\n"
        )

        # Create collateral_positions.csv
        positions_csv = tmpdir_path / "collateral_positions.csv"
        positions_csv.write_text(
            "counterparty_id,isin,quantity,market_value\n"
            "CP001,XS1234567890,1000.000000,1000000.00\n"
            "CP002,XS0987654321,500.000000,500000.00\n"
        )

        # Create haircut_schedule.csv
        haircuts_csv = tmpdir_path / "haircut_schedule.csv"
        haircuts_csv.write_text(
            "asset_type,maturity_bucket,rating_bucket,haircut_rate\n"
            "corporate_bond,0-1y,BBB,0.0500\n"
            "sovereign,0-1y,AAA-AA,0.0050\n"
        )

        yield tmpdir_path


class TestAnalyticsDataset:
    """Tests for AnalyticsDataset."""

    def test_summary(self, sample_data_dir: Path) -> None:
        """Test summary generation."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load()

        summary = dataset.summary()
        assert "2 securities" in summary
        assert "2 counterparties" in summary
        assert "2 positions" in summary
        assert "2 haircut rules" in summary

    def test_validate_consistency_valid(self, sample_data_dir: Path) -> None:
        """Valid data passes consistency check."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        # Should not raise
        dataset.validate_consistency()

    def test_validate_consistency_missing_security(
        self, sample_data_dir: Path
    ) -> None:
        """Missing security referenced in position raises error."""
        # Modify positions to reference non-existent security
        positions_csv = sample_data_dir / "collateral_positions.csv"
        positions_csv.write_text(
            "counterparty_id,isin,quantity,market_value\n"
            "CP001,XS9999999999,1000.000000,1000000.00\n"
        )

        manager = DataManager(sample_data_dir)
        with pytest.raises(DataLoadingError, match="missing securities"):
            manager.load(validate=True)

    def test_validate_consistency_missing_counterparty(
        self, sample_data_dir: Path
    ) -> None:
        """Missing counterparty referenced in position raises error."""
        # Modify positions to reference non-existent counterparty
        positions_csv = sample_data_dir / "collateral_positions.csv"
        positions_csv.write_text(
            "counterparty_id,isin,quantity,market_value\n"
            "CP999,XS1234567890,1000.000000,1000000.00\n"
        )

        manager = DataManager(sample_data_dir)
        with pytest.raises(DataLoadingError, match="missing counterparties"):
            manager.load(validate=True)


class TestDataManager:
    """Tests for DataManager."""

    def test_load_all_files(self, sample_data_dir: Path) -> None:
        """Load all data files successfully."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load()

        assert len(dataset.securities) == 2
        assert len(dataset.counterparties) == 2
        assert len(dataset.positions) == 2
        assert len(dataset.haircuts) == 2

    def test_securities_indexed_by_isin(self, sample_data_dir: Path) -> None:
        """Securities are indexed by ISIN for O(1) lookup."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load()

        assert "XS1234567890" in dataset.securities
        assert dataset.securities["XS1234567890"].name == "Bond A"

    def test_counterparties_indexed_by_id(self, sample_data_dir: Path) -> None:
        """Counterparties are indexed by ID for O(1) lookup."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load()

        assert "CP001" in dataset.counterparties
        assert dataset.counterparties["CP001"].name == "Bank A"

    def test_load_with_validation_disabled(self, sample_data_dir: Path) -> None:
        """Load without validation skips consistency checks."""
        # Create invalid data
        positions_csv = sample_data_dir / "collateral_positions.csv"
        positions_csv.write_text(
            "counterparty_id,isin,quantity,market_value\n"
            "CP999,XS9999999999,1000.000000,1000000.00\n"
        )

        manager = DataManager(sample_data_dir)
        # Should not raise when validate=False
        dataset = manager.load(validate=False)
        assert len(dataset.positions) == 1

    def test_missing_file(self) -> None:
        """Missing data directory raises error."""
        manager = DataManager("nonexistent/path")
        with pytest.raises(DataLoadingError):
            manager.load()

    def test_custom_data_dir(self, sample_data_dir: Path) -> None:
        """Initialize with custom data directory."""
        manager = DataManager(data_dir=sample_data_dir)
        dataset = manager.load()

        assert len(dataset.securities) == 2

    def test_positions_reference_valid_data(self, sample_data_dir: Path) -> None:
        """Loaded positions reference valid securities and counterparties."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load()

        for pos in dataset.positions:
            # Check security exists
            assert pos.isin in dataset.securities
            # Check counterparty exists
            assert pos.counterparty_id in dataset.counterparties
