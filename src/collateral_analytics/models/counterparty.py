"""Domain model for Counterparties."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass
class Counterparty:
    """Represents a counterparty in the exposure framework.

    Attributes:
        counterparty_id: Unique identifier
        name: Counterparty name
        country: Country (ISO 3166 code)
        rating: Credit rating (e.g., 'AAA', 'BBB')
        exposure: Total exposure to this counterparty
        exposure_limit: Maximum allowed exposure
    """

    counterparty_id: str
    name: str
    country: str
    rating: str
    exposure: Decimal
    exposure_limit: Decimal
