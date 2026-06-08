"""Domain model for Counterparties.

All monetary values stored as Decimal (natural form).
All rates stored as decimals: 0.05 = 5%, 1.5 = 150%.
See docs/conventions.md for numerical representation standards.
"""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Counterparty(BaseModel):
    """Represents a counterparty in the exposure framework.

    All monetary values in EUR. Exposure values as Decimal (natural form).

    Attributes:
        counterparty_id: Unique identifier (e.g., 'CP001')
        name: Counterparty name
        country: Country (ISO 3166 code, e.g., 'DE', 'FR')
        rating: Credit rating (e.g., 'AAA', 'AA+', 'BBB-')
        exposure: Current exposure amount in EUR
        exposure_limit: Maximum allowed exposure in EUR
    """

    counterparty_id: str
    name: str
    country: str
    rating: str
    exposure: Decimal = Field(..., ge=Decimal("0"), decimal_places=2)
    exposure_limit: Decimal = Field(..., ge=Decimal("0"), decimal_places=2)

    @field_validator("counterparty_id")
    @classmethod
    def validate_counterparty_id(cls, v: str) -> str:
        """Validate counterparty ID is non-empty and uppercase."""
        if not v or not v.strip():
            raise ValueError("counterparty_id must not be empty")
        return v.upper()

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v: str) -> str:
        """Validate rating format."""
        valid_ratings = {
            "AAA", "AA+", "AA", "AA-",
            "A+", "A", "A-",
            "BBB+", "BBB", "BBB-",
            "BB+", "BB", "BB-",
            "B+", "B", "B-",
            "CCC+", "CCC", "CCC-",
            "CC", "C", "D", "NR"
        }
        if v not in valid_ratings:
            raise ValueError(f"Invalid rating: {v}")
        return v

    @field_validator("country")
    @classmethod
    def validate_country(cls, v: str) -> str:
        """Validate country is 2-letter ISO code."""
        if not v or len(v) != 2 or not v.isalpha():
            raise ValueError("Country must be 2-letter ISO 3166 code")
        return v.upper()

    @field_validator("exposure_limit")
    @classmethod
    def validate_exposure_limit(cls, v: Decimal, info) -> Decimal:
        """Ensure exposure limit is positive."""
        if v <= 0:
            raise ValueError("exposure_limit must be positive")
        return v

    def utilisation(self) -> Decimal:
        """Calculate exposure utilisation as ratio (exposure / limit).

        Returns: Decimal (0.75 = 75% utilisation)
        """
        if self.exposure_limit == 0:
            return Decimal("0")
        return self.exposure / self.exposure_limit

    def available_capacity(self) -> Decimal:
        """Calculate remaining available capacity (limit - exposure)."""
        return max(Decimal("0"), self.exposure_limit - self.exposure)

    def is_at_limit(self) -> bool:
        """Check if counterparty is at or above limit."""
        return self.exposure >= self.exposure_limit

    model_config = ConfigDict(validate_assignment=True)
