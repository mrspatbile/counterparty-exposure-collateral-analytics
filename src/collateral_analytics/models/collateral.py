"""Domain model for Collateral Positions.

All monetary values stored as Decimal (natural form).
See docs/conventions.md for numerical representation standards.
"""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CollateralPosition(BaseModel):
    """Represents a collateral position held against a counterparty.

    Links a security held as collateral to a counterparty.
    All monetary values in EUR as Decimal.

    Attributes:
        counterparty_id: ID of the counterparty (e.g., 'CP001')
        isin: ISIN of the security (e.g., 'XS1234567890')
        quantity: Quantity of security units held
        market_value: Current market value in EUR
    """

    counterparty_id: str
    isin: str
    quantity: Decimal = Field(..., gt=Decimal("0"), decimal_places=6)
    market_value: Decimal = Field(..., ge=Decimal("0"), decimal_places=2)

    @field_validator("counterparty_id")
    @classmethod
    def validate_counterparty_id(cls, v: str) -> str:
        """Validate counterparty ID is non-empty."""
        if not v or not v.strip():
            raise ValueError("counterparty_id must not be empty")
        return v.upper()

    @field_validator("isin")
    @classmethod
    def validate_isin(cls, v: str) -> str:
        """Validate ISIN format: 2 letters + 9 digits + 1 check digit."""
        if not isinstance(v, str) or len(v) != 12:
            raise ValueError("ISIN must be 12 characters")
        if not v[:2].isalpha():
            raise ValueError("ISIN must start with 2 letters")
        if not v[2:].isdigit():
            raise ValueError("ISIN must end with 10 digits")
        return v.upper()

    def position_value_per_unit(self) -> Decimal:
        """Calculate market value per unit (market_value / quantity)."""
        if self.quantity == 0:
            return Decimal("0")
        return self.market_value / self.quantity

    model_config = ConfigDict(validate_assignment=True)
