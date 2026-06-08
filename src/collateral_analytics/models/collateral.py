"""Domain model for Collateral Positions."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass
class CollateralPosition:
    """Represents a collateral position held against a counterparty.

    Attributes:
        counterparty_id: ID of the counterparty
        isin: ISIN of the security
        quantity: Quantity of the security held
        market_value: Current market value of position
    """

    counterparty_id: str
    isin: str
    quantity: Decimal
    market_value: Decimal
