"""Domain model for Haircut Schedule.

All haircut rates stored as decimals: 0.15 = 15% haircut.
See docs/conventions.md for numerical representation standards.
"""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class HaircutSchedule(BaseModel):
    """Defines haircut rates for collateral eligibility assessment.

    Haircuts are tiered by asset type, maturity bucket, and credit rating bucket.
    All rates stored as decimals (0.15 = 15% haircut).

    Attributes:
        asset_type: Type of asset (e.g., 'sovereign', 'corporate_bond', 'equity')
        maturity_bucket: Maturity bucket ('0-1y', '1-3y', '3-5y', '5-10y', '10y+')
        rating_bucket: Rating bucket ('AAA-AA', 'A', 'BBB', 'BB-B', '<B', 'NR')
        haircut_rate: Haircut rate as decimal (0.0 = no haircut, 1.0 = 100% haircut)
    """

    asset_type: str
    maturity_bucket: str
    rating_bucket: str
    haircut_rate: Decimal = Field(..., ge=Decimal("0"), le=Decimal("1"), decimal_places=4)

    @field_validator("asset_type")
    @classmethod
    def validate_asset_type(cls, v: str) -> str:
        """Validate asset type."""
        valid_types = {
            "sovereign",
            "covered_bond",
            "corporate_bond",
            "government_bond",
            "equity",
            "abs",
            "cash",
        }
        if v.lower() not in valid_types:
            raise ValueError(f"Invalid asset_type: {v}")
        return v.lower()

    @field_validator("maturity_bucket")
    @classmethod
    def validate_maturity_bucket(cls, v: str) -> str:
        """Validate maturity bucket."""
        valid_buckets = {"0-1y", "1-3y", "3-5y", "5-10y", "10y+"}
        if v not in valid_buckets:
            raise ValueError(f"Invalid maturity_bucket: {v}")
        return v

    @field_validator("rating_bucket")
    @classmethod
    def validate_rating_bucket(cls, v: str) -> str:
        """Validate rating bucket."""
        valid_buckets = {"AAA-AA", "A", "BBB", "BB-B", "<B", "NR"}
        if v not in valid_buckets:
            raise ValueError(f"Invalid rating_bucket: {v}")
        return v

    model_config = ConfigDict(validate_assignment=True)
