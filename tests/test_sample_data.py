"""Tests for sample data generator."""

import tempfile
from datetime import date
from pathlib import Path
from typing import Iterator

import pytest

from collateral_analytics.sample_data.generator import SampleDataGenerator


@pytest.fixture
def temp_data_dir() -> Iterator[Path]:
    """Create temporary directory for generated data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestSampleDataGenerator:
    """Tests for SampleDataGenerator."""

    def test_init_with_string_date(self) -> None:
        """Initialize with ISO format date string."""
        gen = SampleDataGenerator(start_date="2025-01-15", months=3)
        assert gen.start_date == date(2025, 1, 15)
        assert gen.months == 3

    def test_init_with_date_object(self) -> None:
        """Initialize with date object."""
        start = date(2025, 1, 1)
        gen = SampleDataGenerator(start_date=start, months=6)
        assert gen.start_date == start

    def test_last_business_day_of_month(self) -> None:
        """Test business day calculation."""
        gen = SampleDataGenerator()

        # January 2025: last day is Friday 31st (business day)
        result = gen._last_business_day_of_month(date(2025, 1, 15))
        assert result == date(2025, 1, 31)
        assert result.weekday() < 5  # Mon-Fri

        # February 2025: last day is Friday 28th (business day)
        result = gen._last_business_day_of_month(date(2025, 2, 15))
        assert result == date(2025, 2, 28)

    def test_generate_with_new_mode(self, temp_data_dir: Path) -> None:
        """Generate with 'new' mode creates versioned directory."""
        gen = SampleDataGenerator(start_date="2025-01-01", months=2, seed=42)
        output = gen.generate(output_dir=temp_data_dir, mode="new")

        assert output.exists()
        assert "sample_v" in output.name
        assert (output / "securities.csv").exists()
        assert (output / "counterparties.csv").exists()
        assert (output / "collateral_positions.csv").exists()
        assert (output / "haircut_schedule.csv").exists()

    def test_generate_creates_valid_csvs(self, temp_data_dir: Path) -> None:
        """Generated CSV files contain valid data."""
        gen = SampleDataGenerator(start_date="2025-01-01", months=1, seed=42)
        output = gen.generate(output_dir=temp_data_dir)

        import pandas as pd

        securities = pd.read_csv(output / "securities.csv")
        assert len(securities) > 0
        assert "isin" in securities.columns
        assert "market_value" in securities.columns

        counterparties = pd.read_csv(output / "counterparties.csv")
        assert len(counterparties) > 0
        assert "counterparty_id" in counterparties.columns

        positions = pd.read_csv(output / "collateral_positions.csv")
        assert len(positions) > 0
        assert "quantity" in positions.columns

        haircuts = pd.read_csv(output / "haircut_schedule.csv")
        assert len(haircuts) > 0
        assert "haircut_rate" in haircuts.columns

    def test_generate_multiple_versions(self, temp_data_dir: Path) -> None:
        """Generate multiple versions with 'new' mode."""
        gen = SampleDataGenerator(start_date="2025-01-01", months=1, seed=42)

        output1 = gen.generate(output_dir=temp_data_dir, mode="new")
        output2 = gen.generate(output_dir=temp_data_dir, mode="new")

        assert output1 != output2
        assert "sample_v1" in output1.name
        assert "sample_v2" in output2.name

    def test_list_versions(self, temp_data_dir: Path) -> None:
        """List existing versions."""
        gen = SampleDataGenerator(start_date="2025-01-01", months=1, seed=42)
        gen.generate(output_dir=temp_data_dir, mode="new")
        gen.generate(output_dir=temp_data_dir, mode="new")

        versions = gen.list_versions(temp_data_dir)
        assert len(versions) == 2
        assert "sample_v1" in versions
        assert "sample_v2" in versions

    def test_refresh_mode_overwrites(self, temp_data_dir: Path) -> None:
        """Refresh mode overwrites existing version."""
        gen1 = SampleDataGenerator(start_date="2025-01-01", months=1, seed=42)
        output1 = gen1.generate(output_dir=temp_data_dir, mode="new")

        # Refresh with different seed
        gen2 = SampleDataGenerator(start_date="2025-01-01", months=1, seed=99)
        output2 = gen2.generate(output_dir=temp_data_dir, mode="refresh")

        # Same directory after refresh
        assert output1 == output2

    def test_reset_mode_deletes_all(self, temp_data_dir: Path) -> None:
        """Reset mode deletes existing versions."""
        gen = SampleDataGenerator(start_date="2025-01-01", months=1, seed=42)
        gen.generate(output_dir=temp_data_dir, mode="new")
        gen.generate(output_dir=temp_data_dir, mode="new")

        versions_before = gen.list_versions(temp_data_dir)
        assert len(versions_before) == 2

        # Reset
        gen.generate(output_dir=temp_data_dir, mode="reset")

        versions_after = gen.list_versions(temp_data_dir)
        assert len(versions_after) == 1
        assert "sample_v1" in versions_after

    def test_clean_keeps_latest(self, temp_data_dir: Path) -> None:
        """Clean keeps only latest N versions."""
        gen = SampleDataGenerator(start_date="2025-01-01", months=1, seed=42)
        gen.generate(output_dir=temp_data_dir, mode="new")
        gen.generate(output_dir=temp_data_dir, mode="new")
        gen.generate(output_dir=temp_data_dir, mode="new")

        assert len(gen.list_versions(temp_data_dir)) == 3

        gen.clean(temp_data_dir, keep_latest=1)

        versions = gen.list_versions(temp_data_dir)
        assert len(versions) == 1
        assert "sample_v3" in versions

    def test_reproducibility_with_seed(self, temp_data_dir: Path) -> None:
        """Same seed produces same data."""
        gen1 = SampleDataGenerator(start_date="2025-01-01", months=1, seed=42)
        output1 = gen1.generate(output_dir=temp_data_dir, mode="new")

        import pandas as pd

        df1 = pd.read_csv(output1 / "counterparties.csv")

        # Generate again with same seed in different directory
        with tempfile.TemporaryDirectory() as tmpdir2:
            gen2 = SampleDataGenerator(start_date="2025-01-01", months=1, seed=42)
            output2 = gen2.generate(output_dir=tmpdir2, mode="new")
            df2 = pd.read_csv(output2 / "counterparties.csv")

            # Should be identical
            assert df1.equals(df2)
