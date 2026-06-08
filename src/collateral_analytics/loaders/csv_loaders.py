"""CSV data loaders for domain objects.

All loaders inherit from BaseDataLoader and parse CSV files into domain models.
Monetary values are converted to Decimal. Dates are parsed as ISO 8601.
"""

from decimal import Decimal
from pathlib import Path

import pandas as pd
from pydantic import ValidationError

from collateral_analytics.loaders.base import BaseDataLoader
from collateral_analytics.models import (
    CollateralPosition,
    Counterparty,
    HaircutSchedule,
    Security,
)
from collateral_analytics.utils.exceptions import DataLoadingError


class CsvSecurityLoader(BaseDataLoader[Security]):
    """Load securities from CSV file.

    Expected columns: isin, name, asset_type, issuer, issuer_type, country,
                     currency, rating, maturity_date, market_value
    """

    def load(self, source: Path | str) -> list[Security]:
        """Load securities from CSV.

        Args:
            source: Path to CSV file

        Returns:
            List of Security objects

        Raises:
            DataLoadingError: If CSV is malformed or validation fails
        """
        try:
            source_path = Path(source)
            df = pd.read_csv(source_path)
        except FileNotFoundError as e:
            raise DataLoadingError(f"File not found: {source}") from e
        except pd.errors.ParserError as e:
            raise DataLoadingError(f"Failed to parse CSV: {e}") from e

        if df.empty:
            return []

        required_columns = {
            "isin", "name", "asset_type", "issuer", "issuer_type",
            "country", "currency", "rating", "maturity_date", "market_value"
        }
        missing = required_columns - set(df.columns)
        if missing:
            raise DataLoadingError(f"Missing columns: {missing}")

        securities: list[Security] = []
        for idx, row in df.iterrows():
            try:
                security = Security(
                    isin=str(row["isin"]).strip(),
                    name=str(row["name"]).strip(),
                    asset_type=str(row["asset_type"]).strip(),
                    issuer=str(row["issuer"]).strip(),
                    issuer_type=str(row["issuer_type"]).strip(),
                    country=str(row["country"]).strip(),
                    currency=str(row["currency"]).strip(),
                    rating=str(row["rating"]).strip(),
                    maturity_date=pd.to_datetime(row["maturity_date"]).date(),
                    market_value=Decimal(str(row["market_value"])),
                )
                securities.append(security)
            except (ValueError, ValidationError) as e:
                raise DataLoadingError(
                    f"Row {idx + 2}: Failed to parse security: {e}"
                ) from e

        return securities


class CsvCounterpartyLoader(BaseDataLoader[Counterparty]):
    """Load counterparties from CSV file.

    Expected columns: counterparty_id, name, country, rating, exposure, exposure_limit
    """

    def load(self, source: Path | str) -> list[Counterparty]:
        """Load counterparties from CSV.

        Args:
            source: Path to CSV file

        Returns:
            List of Counterparty objects

        Raises:
            DataLoadingError: If CSV is malformed or validation fails
        """
        try:
            source_path = Path(source)
            df = pd.read_csv(source_path)
        except FileNotFoundError as e:
            raise DataLoadingError(f"File not found: {source}") from e
        except pd.errors.ParserError as e:
            raise DataLoadingError(f"Failed to parse CSV: {e}") from e

        if df.empty:
            return []

        required_columns = {
            "counterparty_id", "name", "country", "rating",
            "exposure", "exposure_limit"
        }
        missing = required_columns - set(df.columns)
        if missing:
            raise DataLoadingError(f"Missing columns: {missing}")

        counterparties: list[Counterparty] = []
        for idx, row in df.iterrows():
            try:
                counterparty = Counterparty(
                    counterparty_id=str(row["counterparty_id"]).strip(),
                    name=str(row["name"]).strip(),
                    country=str(row["country"]).strip(),
                    rating=str(row["rating"]).strip(),
                    exposure=Decimal(str(row["exposure"])),
                    exposure_limit=Decimal(str(row["exposure_limit"])),
                )
                counterparties.append(counterparty)
            except (ValueError, ValidationError) as e:
                raise DataLoadingError(
                    f"Row {idx + 2}: Failed to parse counterparty: {e}"
                ) from e

        return counterparties


class CsvCollateralPositionLoader(BaseDataLoader[CollateralPosition]):
    """Load collateral positions from CSV file.

    Expected columns: counterparty_id, isin, quantity, market_value
    """

    def load(self, source: Path | str) -> list[CollateralPosition]:
        """Load collateral positions from CSV.

        Args:
            source: Path to CSV file

        Returns:
            List of CollateralPosition objects

        Raises:
            DataLoadingError: If CSV is malformed or validation fails
        """
        try:
            source_path = Path(source)
            df = pd.read_csv(source_path)
        except FileNotFoundError as e:
            raise DataLoadingError(f"File not found: {source}") from e
        except pd.errors.ParserError as e:
            raise DataLoadingError(f"Failed to parse CSV: {e}") from e

        if df.empty:
            return []

        required_columns = {"counterparty_id", "isin", "quantity", "market_value"}
        missing = required_columns - set(df.columns)
        if missing:
            raise DataLoadingError(f"Missing columns: {missing}")

        positions: list[CollateralPosition] = []
        for idx, row in df.iterrows():
            try:
                position = CollateralPosition(
                    counterparty_id=str(row["counterparty_id"]).strip(),
                    isin=str(row["isin"]).strip(),
                    quantity=Decimal(str(row["quantity"])),
                    market_value=Decimal(str(row["market_value"])),
                )
                positions.append(position)
            except (ValueError, ValidationError) as e:
                raise DataLoadingError(
                    f"Row {idx + 2}: Failed to parse collateral position: {e}"
                ) from e

        return positions


class CsvHaircutScheduleLoader(BaseDataLoader[HaircutSchedule]):
    """Load haircut schedule from CSV file.

    Expected columns: asset_type, maturity_bucket, rating_bucket, haircut_rate
    """

    def load(self, source: Path | str) -> list[HaircutSchedule]:
        """Load haircut schedule from CSV.

        Args:
            source: Path to CSV file

        Returns:
            List of HaircutSchedule objects

        Raises:
            DataLoadingError: If CSV is malformed or validation fails
        """
        try:
            source_path = Path(source)
            df = pd.read_csv(source_path)
        except FileNotFoundError as e:
            raise DataLoadingError(f"File not found: {source}") from e
        except pd.errors.ParserError as e:
            raise DataLoadingError(f"Failed to parse CSV: {e}") from e

        if df.empty:
            return []

        required_columns = {
            "asset_type", "maturity_bucket", "rating_bucket", "haircut_rate"
        }
        missing = required_columns - set(df.columns)
        if missing:
            raise DataLoadingError(f"Missing columns: {missing}")

        schedules: list[HaircutSchedule] = []
        for idx, row in df.iterrows():
            try:
                schedule = HaircutSchedule(
                    asset_type=str(row["asset_type"]).strip(),
                    maturity_bucket=str(row["maturity_bucket"]).strip(),
                    rating_bucket=str(row["rating_bucket"]).strip(),
                    haircut_rate=Decimal(str(row["haircut_rate"])),
                )
                schedules.append(schedule)
            except (ValueError, ValidationError) as e:
                raise DataLoadingError(
                    f"Row {idx + 2}: Failed to parse haircut schedule: {e}"
                ) from e

        return schedules
