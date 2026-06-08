"""Domain model for Securities.

All monetary values stored as Decimal (natural form).
All rates stored as decimals: 0.05 = 5%, 1.5 = 150%.
See docs/conventions.md for numerical representation standards.
"""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Security(BaseModel):
    """Represents a security used as collateral.

    All monetary values in EUR. All rates as decimals (0.05 = 5%).

    Attributes:
        isin: International Securities Identification Number (e.g., 'XS1234567890')
        name: Security name
        asset_type: Type of asset (e.g., 'sovereign', 'corporate', 'covered_bond', 'equity')
        issuer: Name of issuer
        issuer_type: Type of issuer (e.g., 'sovereign', 'corporate', 'bank')
        country: Issuer country (ISO 3166 code, e.g., 'DE')
        currency: Currency (ISO 4217 code, currently 'EUR' only)
        rating: Credit rating (e.g., 'AAA', 'AA+', 'BBB-')
        maturity_date: Security maturity date (ISO 8601)
        market_value: Current market value in EUR (stored as Decimal)
    """

    isin: str
    name: str
    asset_type: str
    issuer: str
    issuer_type: str
    country: str
    currency: str = Field(default="EUR")
    rating: str
    maturity_date: date
    market_value: Decimal = Field(..., ge=Decimal("0"), decimal_places=2)

    @field_validator("isin")
    @classmethod
    def validate_isin(cls, v: str) -> str:
        """Validate ISIN format: 2 letters + 9 digits + 1 check digit."""
        if not isinstance(v, str) or len(v) != 12:
            raise ValueError("ISIN must be 12 characters")
        if not v[:2].isalpha():
            raise ValueError("ISIN must start with 2 letters (country code)")
        if not v[2:].isdigit():
            raise ValueError("ISIN must end with 10 digits")
        return v.upper()

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Validate currency is EUR."""
        if v != "EUR":
            raise ValueError("Only EUR currency supported")
        return v

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v: str) -> str:
        """Validate rating format (e.g., AAA, AA+, BBB-)."""
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

    @field_validator("asset_type")
    @classmethod
    def validate_asset_type(cls, v: str) -> str:
        """Validate asset type."""
        valid_types = {
            "sovereign", "covered_bond", "corporate_bond", "government_bond",
            "equity", "abs", "cash"
        }
        if v.lower() not in valid_types:
            raise ValueError(f"Invalid asset_type: {v}")
        return v.lower()

    def days_to_maturity(self, reference_date: date) -> int:
        """Calculate days remaining until maturity."""
        delta = self.maturity_date - reference_date
        return max(0, delta.days)

    def maturity_bucket(self, reference_date: date) -> str:
        """Assign maturity bucket: '0-1y', '1-3y', '3-5y', '5-10y', '10y+'."""
        days = self.days_to_maturity(reference_date)
        if days <= 365:
            return "0-1y"
        elif days <= 365 * 3:
            return "1-3y"
        elif days <= 365 * 5:
            return "3-5y"
        elif days <= 365 * 10:
            return "5-10y"
        else:
            return "10y+"

    def rating_bucket(self) -> str:
        """Assign rating bucket: 'AAA-AA', 'A', 'BBB', 'BB-B', '<B', 'NR'."""
        if self.rating in {"AAA", "AA+", "AA", "AA-"}:
            return "AAA-AA"
        elif self.rating in {"A+", "A", "A-"}:
            return "A"
        elif self.rating in {"BBB+", "BBB", "BBB-"}:
            return "BBB"
        elif self.rating in {"BB+", "BB", "BB-", "B+", "B", "B-"}:
            return "BB-B"
        elif self.rating in {"CCC+", "CCC", "CCC-", "CC", "C"}:
            return "<B"
        else:
            return "NR"

    model_config = ConfigDict(validate_assignment=True)
