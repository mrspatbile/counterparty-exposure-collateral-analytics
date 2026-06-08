"""Sample data generator for analytics platform.

Generates realistic but synthetic data for testing and demonstration.
Uses business day logic (Mon-Fri) for snapshots.
"""

import random
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Literal

import pandas as pd

from collateral_analytics.utils.logging import configure_logging

logger = configure_logging(__name__)


class SampleDataGenerator:
    """Generate realistic sample data across multiple time periods.

    Supports multiple modes:
    - "new": Create new versioned directory
    - "refresh": Overwrite current version
    - "reset": Delete all and start fresh
    """

    # Realistic counterparty data
    COUNTERPARTIES = [
        {"id": "CP001", "name": "Deutsche Bank", "country": "DE", "rating": "A"},
        {"id": "CP002", "name": "BNP Paribas", "country": "FR", "rating": "A"},
        {"id": "CP003", "name": "ING Groep", "country": "NL", "rating": "A-"},
        {"id": "CP004", "name": "Santander Bank", "country": "ES", "rating": "A"},
        {"id": "CP005", "name": "UniCredit", "country": "IT", "rating": "BBB+"},
        {"id": "CP006", "name": "Commerzbank", "country": "DE", "rating": "BBB"},
    ]

    # Realistic security data
    SECURITIES = [
        # Sovereign bonds
        {
            "isin": "DE0001102309",
            "name": "German Bund 2.5% 2035",
            "asset_type": "sovereign",
            "issuer": "Germany",
            "issuer_type": "sovereign",
            "country": "DE",
            "rating": "AAA",
        },
        {
            "isin": "FR0000188468",
            "name": "French OAT 1.75% 2032",
            "asset_type": "sovereign",
            "issuer": "France",
            "issuer_type": "sovereign",
            "country": "FR",
            "rating": "AA",
        },
        {
            "isin": "NL0000109833",
            "name": "Dutch Bond 2.0% 2036",
            "asset_type": "sovereign",
            "issuer": "Netherlands",
            "issuer_type": "sovereign",
            "country": "NL",
            "rating": "AAA",
        },
        # Corporate bonds
        {
            "isin": "XS1234567890",
            "name": "Siemens Senior Bond 2% 2030",
            "asset_type": "corporate_bond",
            "issuer": "Siemens AG",
            "issuer_type": "corporate",
            "country": "DE",
            "rating": "A",
        },
        {
            "isin": "XS0987654321",
            "name": "SAP SE Bond 1.5% 2032",
            "asset_type": "corporate_bond",
            "issuer": "SAP SE",
            "issuer_type": "corporate",
            "country": "DE",
            "rating": "A+",
        },
        {
            "isin": "XS2111111111",
            "name": "Airbus Bond 2.25% 2030",
            "asset_type": "corporate_bond",
            "issuer": "Airbus SE",
            "issuer_type": "corporate",
            "country": "NL",
            "rating": "BBB+",
        },
        {
            "isin": "XS2222222222",
            "name": "LVMH Bond 1.875% 2033",
            "asset_type": "corporate_bond",
            "issuer": "LVMH Moët Hennessy",
            "issuer_type": "corporate",
            "country": "FR",
            "rating": "A",
        },
        {
            "isin": "XS2333333333",
            "name": "Shell PLC Bond 3.5% 2029",
            "asset_type": "corporate_bond",
            "issuer": "Shell PLC",
            "issuer_type": "corporate",
            "country": "NL",
            "rating": "A",
        },
        # Covered bonds
        {
            "isin": "XS2444444444",
            "name": "Deutsche Bank Covered Bond 1.75% 2031",
            "asset_type": "covered_bond",
            "issuer": "Deutsche Bank",
            "issuer_type": "bank",
            "country": "DE",
            "rating": "AA-",
        },
        {
            "isin": "XS2555555555",
            "name": "BNP Paribas Covered Bond 2.0% 2032",
            "asset_type": "covered_bond",
            "issuer": "BNP Paribas",
            "issuer_type": "bank",
            "country": "FR",
            "rating": "AA",
        },
    ]

    def __init__(
        self,
        start_date: str | date = "2025-01-01",
        months: int = 6,
        seed: int | None = None,
    ):
        """Initialize generator.

        Args:
            start_date: Start date for data generation (ISO format or date object)
            months: Number of months to generate
            seed: Random seed for reproducibility
        """
        if isinstance(start_date, str):
            self.start_date = datetime.fromisoformat(start_date).date()
        else:
            self.start_date = start_date

        self.months = months
        self.seed = seed

        if seed is not None:
            random.seed(seed)

        logger.info(f"SampleDataGenerator initialized: {self.start_date} for {months} months")

    def _last_business_day_of_month(self, target_date: date) -> date:
        """Get last business day (Mon-Fri) of month.

        Args:
            target_date: Any date in the target month

        Returns:
            Last business day of that month
        """
        # Get last day of month
        if target_date.month == 12:
            last_day = date(target_date.year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = date(target_date.year, target_date.month + 1, 1) - timedelta(days=1)

        # Back up to last business day (Mon-Fri)
        while last_day.weekday() > 4:  # 5=Saturday, 6=Sunday
            last_day -= timedelta(days=1)

        return last_day

    def _generate_market_value(self, base_value: float = 1000000.0) -> Decimal:
        """Generate realistic market value with variation.

        Args:
            base_value: Base market value in EUR

        Returns:
            Market value as Decimal
        """
        variance = random.uniform(0.8, 1.2)  # ±20% variance
        value = base_value * variance
        return Decimal(str(round(value, 2)))

    def _generate_securities_for_month(self, snapshot_date: date) -> pd.DataFrame:
        """Generate securities for a month.

        Args:
            snapshot_date: Date for this snapshot

        Returns:
            DataFrame with securities
        """
        rows = []
        for sec in self.SECURITIES:
            # Vary market value slightly month-to-month
            market_value = self._generate_market_value(1000000.0)

            # Set maturity 5-10 years in future
            maturity_years = random.randint(5, 10)
            maturity_date = snapshot_date + timedelta(days=365 * maturity_years)

            rows.append(
                {
                    "isin": sec["isin"],
                    "name": sec["name"],
                    "asset_type": sec["asset_type"],
                    "issuer": sec["issuer"],
                    "issuer_type": sec["issuer_type"],
                    "country": sec["country"],
                    "currency": "EUR",
                    "rating": sec["rating"],
                    "maturity_date": maturity_date.isoformat(),
                    "market_value": str(market_value),
                }
            )

        return pd.DataFrame(rows)

    def _generate_counterparties_for_month(self, snapshot_date: date) -> pd.DataFrame:
        """Generate counterparties with time-varying exposure.

        Args:
            snapshot_date: Date for this snapshot

        Returns:
            DataFrame with counterparties
        """
        rows = []
        for cp in self.COUNTERPARTIES:
            # Exposure varies month-to-month (±15%)
            base_exposure = Decimal("5000000.00")
            variance = Decimal(str(random.uniform(0.85, 1.15)))
            exposure = base_exposure * variance

            # Limit is 2x exposure
            limit = exposure * Decimal("2")

            rows.append(
                {
                    "counterparty_id": cp["id"],
                    "name": cp["name"],
                    "country": cp["country"],
                    "rating": cp["rating"],
                    "exposure": str(round(exposure, 2)),
                    "exposure_limit": str(round(limit, 2)),
                }
            )

        return pd.DataFrame(rows)

    def _generate_positions_for_month(
        self, snapshot_date: date, securities_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Generate collateral positions.

        Args:
            snapshot_date: Date for this snapshot
            securities_df: Securities DataFrame for reference

        Returns:
            DataFrame with collateral positions
        """
        rows = []
        securities_list = securities_df["isin"].tolist()

        # Each counterparty holds 2-4 securities
        for cp in self.COUNTERPARTIES:
            num_securities = random.randint(2, 4)
            selected_isins = random.sample(securities_list, num_securities)

            for isin in selected_isins:
                quantity = Decimal(str(random.randint(100, 5000)))
                market_value = self._generate_market_value(500000.0)

                rows.append(
                    {
                        "counterparty_id": cp["id"],
                        "isin": isin,
                        "quantity": str(quantity),
                        "market_value": str(market_value),
                    }
                )

        return pd.DataFrame(rows)

    def _generate_haircut_schedule(self) -> pd.DataFrame:
        """Generate haircut schedule (fixed across all months).

        Returns:
            DataFrame with haircut rates
        """
        schedule = []

        asset_types = ["sovereign", "corporate_bond", "covered_bond"]

        # Define haircut rates (realistic)
        haircut_matrix = {
            "sovereign": {
                "AAA-AA": {"0-1y": 0.005, "1-3y": 0.01, "3-5y": 0.015, "5-10y": 0.02, "10y+": 0.03},
                "A": {"0-1y": 0.01, "1-3y": 0.015, "3-5y": 0.02, "5-10y": 0.025, "10y+": 0.035},
                "BBB": {"0-1y": 0.025, "1-3y": 0.035, "3-5y": 0.045, "5-10y": 0.055, "10y+": 0.07},
            },
            "corporate_bond": {
                "AAA-AA": {
                    "0-1y": 0.025,
                    "1-3y": 0.035,
                    "3-5y": 0.045,
                    "5-10y": 0.055,
                    "10y+": 0.07,
                },
                "A": {"0-1y": 0.05, "1-3y": 0.065, "3-5y": 0.08, "5-10y": 0.095, "10y+": 0.12},
                "BBB": {"0-1y": 0.10, "1-3y": 0.125, "3-5y": 0.15, "5-10y": 0.175, "10y+": 0.20},
            },
            "covered_bond": {
                "AA": {"0-1y": 0.015, "1-3y": 0.025, "3-5y": 0.035, "5-10y": 0.045, "10y+": 0.06},
                "A": {"0-1y": 0.04, "1-3y": 0.055, "3-5y": 0.07, "5-10y": 0.085, "10y+": 0.10},
            },
        }

        for asset_type in asset_types:
            if asset_type not in haircut_matrix:
                continue
            for rating_bucket, maturity_map in haircut_matrix[asset_type].items():
                for maturity_bucket, rate in maturity_map.items():
                    schedule.append(
                        {
                            "asset_type": asset_type,
                            "maturity_bucket": maturity_bucket,
                            "rating_bucket": rating_bucket,
                            "haircut_rate": str(Decimal(str(rate))),
                        }
                    )

        return pd.DataFrame(schedule)

    def generate(
        self, output_dir: Path | str = "data", mode: Literal["new", "refresh", "reset"] = "new"
    ) -> Path:
        """Generate sample data and save to CSV files.

        Args:
            output_dir: Base output directory
            mode: Generation mode
                  "new": Create new versioned directory
                  "refresh": Overwrite current version
                  "reset": Delete all and regenerate

        Returns:
            Path to generated data directory
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Determine target directory
        if mode == "reset":
            # Delete all existing sample data
            for item in output_dir.glob("sample_v*"):
                if item.is_dir():
                    import shutil

                    shutil.rmtree(item)
                    logger.info(f"Deleted {item}")
            target_dir = output_dir / "sample_v1"
        elif mode == "new":
            # Find next version number
            existing = [d for d in output_dir.glob("sample_v*") if d.is_dir()]
            next_version = len(existing) + 1
            target_dir = output_dir / f"sample_v{next_version}"
        else:  # refresh
            # Use existing version_v1 or latest
            existing = sorted(output_dir.glob("sample_v*"))
            target_dir = existing[-1] if existing else output_dir / "sample_v1"

        target_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Generating data to {target_dir}")

        # Generate haircut schedule (same for all months)
        haircuts_df = self._generate_haircut_schedule()
        haircuts_df.to_csv(target_dir / "haircut_schedule.csv", index=False)
        logger.info(f"Generated haircut schedule: {len(haircuts_df)} rules")

        # Generate data for each month
        current_date = self.start_date
        for month_idx in range(self.months):
            snapshot_date = self._last_business_day_of_month(current_date)

            securities_df = self._generate_securities_for_month(snapshot_date)
            counterparties_df = self._generate_counterparties_for_month(snapshot_date)
            positions_df = self._generate_positions_for_month(snapshot_date, securities_df)

            # Save CSVs (overwrite month-to-month in refresh mode)
            securities_df.to_csv(target_dir / "securities.csv", index=False)
            counterparties_df.to_csv(target_dir / "counterparties.csv", index=False)
            positions_df.to_csv(target_dir / "collateral_positions.csv", index=False)

            logger.info(
                f"Month {month_idx + 1} ({snapshot_date}): "
                f"{len(securities_df)} securities, {len(counterparties_df)} counterparties, "
                f"{len(positions_df)} positions"
            )

            # Advance to next month
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)

        logger.info(f"Sample data generated successfully to {target_dir}")
        return target_dir

    def list_versions(self, data_dir: Path | str = "data") -> list[str]:
        """List all existing sample data versions.

        Args:
            data_dir: Data directory

        Returns:
            List of version directory names
        """
        data_dir = Path(data_dir)
        versions = sorted([d.name for d in data_dir.glob("sample_v*") if d.is_dir()])
        return versions

    def clean(self, data_dir: Path | str = "data", keep_latest: int = 2) -> None:
        """Delete old sample data versions, keeping latest N.

        Args:
            data_dir: Data directory
            keep_latest: Number of latest versions to keep
        """
        data_dir = Path(data_dir)
        versions = sorted(data_dir.glob("sample_v*"))

        to_delete = versions[:-keep_latest] if len(versions) > keep_latest else []
        for version_dir in to_delete:
            import shutil

            shutil.rmtree(version_dir)
            logger.info(f"Deleted {version_dir}")
