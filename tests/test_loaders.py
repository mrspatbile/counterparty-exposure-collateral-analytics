"""Tests for CSV data loaders."""

import tempfile
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from collateral_analytics.loaders.csv_loaders import (
    CsvCollateralPositionLoader,
    CsvCounterpartyLoader,
    CsvHaircutScheduleLoader,
    CsvSecurityLoader,
)
from collateral_analytics.utils.exceptions import DataLoadingError


@pytest.fixture
def temp_data_dir() -> Path:
    """Create temporary directory for test CSVs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestCsvSecurityLoader:
    """Tests for CsvSecurityLoader."""

    def test_load_valid_securities(self, temp_data_dir: Path) -> None:
        """Load valid securities CSV."""
        csv_file = temp_data_dir / "securities.csv"
        csv_file.write_text(
            "isin,name,asset_type,issuer,issuer_type,country,currency,rating,maturity_date,market_value\n"
            "XS1234567890,Test Bond,corporate_bond,Test Corp,corporate,DE,EUR,BBB,2030-12-31,1000000.00\n"
            "XS0987654321,Sovereign Bond,sovereign,Germany,sovereign,DE,EUR,AAA,2035-06-15,500000.00\n"
        )

        loader = CsvSecurityLoader()
        securities = loader.load(csv_file)

        assert len(securities) == 2
        assert securities[0].isin == "XS1234567890"
        assert securities[0].name == "Test Bond"
        assert securities[0].market_value == Decimal("1000000.00")
        assert securities[1].rating == "AAA"

    def test_load_empty_csv(self, temp_data_dir: Path) -> None:
        """Load empty CSV returns empty list."""
        csv_file = temp_data_dir / "empty.csv"
        csv_file.write_text(
            "isin,name,asset_type,issuer,issuer_type,country,currency,rating,maturity_date,market_value\n"
        )

        loader = CsvSecurityLoader()
        securities = loader.load(csv_file)

        assert securities == []

    def test_load_missing_columns(self, temp_data_dir: Path) -> None:
        """Missing required columns raises error."""
        csv_file = temp_data_dir / "securities.csv"
        csv_file.write_text(
            "isin,name,asset_type\n"
            "XS1234567890,Test Bond,corporate_bond\n"
        )

        loader = CsvSecurityLoader()
        with pytest.raises(DataLoadingError, match="Missing columns"):
            loader.load(csv_file)

    def test_load_invalid_rating(self, temp_data_dir: Path) -> None:
        """Invalid rating raises error."""
        csv_file = temp_data_dir / "securities.csv"
        csv_file.write_text(
            "isin,name,asset_type,issuer,issuer_type,country,currency,rating,maturity_date,market_value\n"
            "XS1234567890,Test Bond,corporate_bond,Test Corp,corporate,DE,EUR,INVALID,2030-12-31,1000000.00\n"
        )

        loader = CsvSecurityLoader()
        with pytest.raises(DataLoadingError, match="Failed to parse security"):
            loader.load(csv_file)

    def test_load_file_not_found(self) -> None:
        """Missing file raises error."""
        loader = CsvSecurityLoader()
        with pytest.raises(DataLoadingError, match="File not found"):
            loader.load("nonexistent.csv")


class TestCsvCounterpartyLoader:
    """Tests for CsvCounterpartyLoader."""

    def test_load_valid_counterparties(self, temp_data_dir: Path) -> None:
        """Load valid counterparties CSV."""
        csv_file = temp_data_dir / "counterparties.csv"
        csv_file.write_text(
            "counterparty_id,name,country,rating,exposure,exposure_limit\n"
            "CP001,Bank A,DE,A,5000000.00,10000000.00\n"
            "CP002,Bank B,FR,BBB,3000000.00,5000000.00\n"
        )

        loader = CsvCounterpartyLoader()
        counterparties = loader.load(csv_file)

        assert len(counterparties) == 2
        assert counterparties[0].counterparty_id == "CP001"
        assert counterparties[0].exposure == Decimal("5000000.00")
        assert counterparties[1].rating == "BBB"

    def test_load_empty_csv(self, temp_data_dir: Path) -> None:
        """Load empty CSV returns empty list."""
        csv_file = temp_data_dir / "empty.csv"
        csv_file.write_text(
            "counterparty_id,name,country,rating,exposure,exposure_limit\n"
        )

        loader = CsvCounterpartyLoader()
        counterparties = loader.load(csv_file)

        assert counterparties == []

    def test_load_invalid_exposure_limit(self, temp_data_dir: Path) -> None:
        """Invalid exposure limit (zero) raises error."""
        csv_file = temp_data_dir / "counterparties.csv"
        csv_file.write_text(
            "counterparty_id,name,country,rating,exposure,exposure_limit\n"
            "CP001,Bank A,DE,A,5000000.00,0.00\n"
        )

        loader = CsvCounterpartyLoader()
        with pytest.raises(DataLoadingError, match="Failed to parse counterparty"):
            loader.load(csv_file)


class TestCsvCollateralPositionLoader:
    """Tests for CsvCollateralPositionLoader."""

    def test_load_valid_positions(self, temp_data_dir: Path) -> None:
        """Load valid collateral positions CSV."""
        csv_file = temp_data_dir / "positions.csv"
        csv_file.write_text(
            "counterparty_id,isin,quantity,market_value\n"
            "CP001,XS1234567890,1000.000000,1000000.00\n"
            "CP002,XS0987654321,500.000000,500000.00\n"
        )

        loader = CsvCollateralPositionLoader()
        positions = loader.load(csv_file)

        assert len(positions) == 2
        assert positions[0].counterparty_id == "CP001"
        assert positions[0].quantity == Decimal("1000.000000")
        assert positions[1].market_value == Decimal("500000.00")

    def test_load_empty_csv(self, temp_data_dir: Path) -> None:
        """Load empty CSV returns empty list."""
        csv_file = temp_data_dir / "empty.csv"
        csv_file.write_text("counterparty_id,isin,quantity,market_value\n")

        loader = CsvCollateralPositionLoader()
        positions = loader.load(csv_file)

        assert positions == []

    def test_load_invalid_isin(self, temp_data_dir: Path) -> None:
        """Invalid ISIN raises error."""
        csv_file = temp_data_dir / "positions.csv"
        csv_file.write_text(
            "counterparty_id,isin,quantity,market_value\n"
            "CP001,INVALID,1000.000000,1000000.00\n"
        )

        loader = CsvCollateralPositionLoader()
        with pytest.raises(DataLoadingError, match="Failed to parse collateral position"):
            loader.load(csv_file)


class TestCsvHaircutScheduleLoader:
    """Tests for CsvHaircutScheduleLoader."""

    def test_load_valid_schedules(self, temp_data_dir: Path) -> None:
        """Load valid haircut schedule CSV."""
        csv_file = temp_data_dir / "haircuts.csv"
        csv_file.write_text(
            "asset_type,maturity_bucket,rating_bucket,haircut_rate\n"
            "sovereign,0-1y,AAA-AA,0.0050\n"
            "corporate_bond,1-3y,BBB,0.0500\n"
            "equity,10y+,<B,0.5000\n"
        )

        loader = CsvHaircutScheduleLoader()
        schedules = loader.load(csv_file)

        assert len(schedules) == 3
        assert schedules[0].asset_type == "sovereign"
        assert schedules[0].haircut_rate == Decimal("0.0050")
        assert schedules[2].haircut_rate == Decimal("0.5000")

    def test_load_empty_csv(self, temp_data_dir: Path) -> None:
        """Load empty CSV returns empty list."""
        csv_file = temp_data_dir / "empty.csv"
        csv_file.write_text(
            "asset_type,maturity_bucket,rating_bucket,haircut_rate\n"
        )

        loader = CsvHaircutScheduleLoader()
        schedules = loader.load(csv_file)

        assert schedules == []

    def test_load_invalid_asset_type(self, temp_data_dir: Path) -> None:
        """Invalid asset type raises error."""
        csv_file = temp_data_dir / "haircuts.csv"
        csv_file.write_text(
            "asset_type,maturity_bucket,rating_bucket,haircut_rate\n"
            "invalid_type,0-1y,AAA-AA,0.0050\n"
        )

        loader = CsvHaircutScheduleLoader()
        with pytest.raises(DataLoadingError, match="Failed to parse haircut schedule"):
            loader.load(csv_file)

    def test_load_haircut_rate_out_of_range(self, temp_data_dir: Path) -> None:
        """Haircut rate > 1.0 raises error."""
        csv_file = temp_data_dir / "haircuts.csv"
        csv_file.write_text(
            "asset_type,maturity_bucket,rating_bucket,haircut_rate\n"
            "sovereign,0-1y,AAA-AA,1.5000\n"
        )

        loader = CsvHaircutScheduleLoader()
        with pytest.raises(DataLoadingError, match="Failed to parse haircut schedule"):
            loader.load(csv_file)
