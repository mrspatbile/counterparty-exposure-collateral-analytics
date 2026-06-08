"""Data manager for orchestrating CSV data loading and validation."""

from dataclasses import dataclass
from pathlib import Path

from collateral_analytics.loaders.csv_loaders import (
    CsvCollateralPositionLoader,
    CsvCounterpartyLoader,
    CsvHaircutScheduleLoader,
    CsvSecurityLoader,
)
from collateral_analytics.models import (
    CollateralPosition,
    Counterparty,
    HaircutSchedule,
    Security,
)
from collateral_analytics.utils.exceptions import DataLoadingError


@dataclass
class AnalyticsDataset:
    """Container for all loaded analytics data.

    Attributes:
        securities: Dictionary of securities by ISIN
        counterparties: Dictionary of counterparties by ID
        positions: List of collateral positions
        haircuts: List of haircut schedule entries
    """

    securities: dict[str, Security]
    counterparties: dict[str, Counterparty]
    positions: list[CollateralPosition]
    haircuts: list[HaircutSchedule]

    def validate_consistency(self) -> None:
        """Validate cross-file data consistency.

        Raises:
            DataLoadingError: If data is inconsistent
        """
        # Check all position ISINs reference valid securities
        missing_securities = set()
        for pos in self.positions:
            if pos.isin not in self.securities:
                missing_securities.add(pos.isin)

        if missing_securities:
            raise DataLoadingError(
                f"Collateral positions reference missing securities: {missing_securities}"
            )

        # Check all position counterparties reference valid counterparties
        missing_counterparties = set()
        for pos in self.positions:
            if pos.counterparty_id not in self.counterparties:
                missing_counterparties.add(pos.counterparty_id)

        if missing_counterparties:
            raise DataLoadingError(
                f"Collateral positions reference missing counterparties: {missing_counterparties}"
            )

    def summary(self) -> str:
        """Return summary of loaded data."""
        return (
            f"AnalyticsDataset: "
            f"{len(self.securities)} securities, "
            f"{len(self.counterparties)} counterparties, "
            f"{len(self.positions)} positions, "
            f"{len(self.haircuts)} haircut rules"
        )


class DataManager:
    """Orchestrates loading and validation of analytics data.

    Loads data from CSV files in a standard data directory.
    Expected file names:
    - securities.csv
    - counterparties.csv
    - collateral_positions.csv
    - haircut_schedule.csv
    """

    def __init__(self, data_dir: Path | str = "data"):
        """Initialize DataManager.

        Args:
            data_dir: Directory containing CSV files (default: 'data')
        """
        self.data_dir = Path(data_dir)
        self.security_loader = CsvSecurityLoader()
        self.counterparty_loader = CsvCounterpartyLoader()
        self.position_loader = CsvCollateralPositionLoader()
        self.haircut_loader = CsvHaircutScheduleLoader()

    def load(self, validate: bool = True) -> AnalyticsDataset:
        """Load all data files and return unified dataset.

        Args:
            validate: Whether to validate cross-file consistency (default: True)

        Returns:
            AnalyticsDataset with all loaded data

        Raises:
            DataLoadingError: If any file cannot be loaded or validation fails
        """
        securities_list = self._load_securities()
        counterparties_list = self._load_counterparties()
        positions = self._load_positions()
        haircuts = self._load_haircuts()

        # Convert lists to dictionaries for O(1) lookup
        securities = {s.isin: s for s in securities_list}
        counterparties = {cp.counterparty_id: cp for cp in counterparties_list}

        dataset = AnalyticsDataset(
            securities=securities,
            counterparties=counterparties,
            positions=positions,
            haircuts=haircuts,
        )

        if validate:
            dataset.validate_consistency()

        return dataset

    def _load_securities(self) -> list[Security]:
        """Load securities from CSV."""
        csv_path = self.data_dir / "securities.csv"
        try:
            return self.security_loader.load(csv_path)
        except DataLoadingError:
            raise
        except Exception as e:
            raise DataLoadingError(f"Failed to load securities: {e}") from e

    def _load_counterparties(self) -> list[Counterparty]:
        """Load counterparties from CSV."""
        csv_path = self.data_dir / "counterparties.csv"
        try:
            return self.counterparty_loader.load(csv_path)
        except DataLoadingError:
            raise
        except Exception as e:
            raise DataLoadingError(f"Failed to load counterparties: {e}") from e

    def _load_positions(self) -> list[CollateralPosition]:
        """Load collateral positions from CSV."""
        csv_path = self.data_dir / "collateral_positions.csv"
        try:
            return self.position_loader.load(csv_path)
        except DataLoadingError:
            raise
        except Exception as e:
            raise DataLoadingError(f"Failed to load collateral positions: {e}") from e

    def _load_haircuts(self) -> list[HaircutSchedule]:
        """Load haircut schedule from CSV."""
        csv_path = self.data_dir / "haircut_schedule.csv"
        try:
            return self.haircut_loader.load(csv_path)
        except DataLoadingError:
            raise
        except Exception as e:
            raise DataLoadingError(f"Failed to load haircut schedule: {e}") from e
