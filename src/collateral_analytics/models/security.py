"""Domain model for Securities."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass
class Security:
    """Represents a security used as collateral.

    Attributes:
        isin: International Securities Identification Number
        name: Security name
        asset_type: Type of asset (e.g., 'sovereign', 'corporate', 'covered_bond')
        issuer: Name of issuer
        issuer_type: Type of issuer (e.g., 'sovereign', 'corporate')
        country: Issuer country (ISO 3166 code)
        currency: Currency (ISO 4217 code)
        rating: Credit rating (e.g., 'AAA', 'BBB')
        maturity_date: Security maturity date
        market_value: Current market value
    """

    isin: str
    name: str
    asset_type: str
    issuer: str
    issuer_type: str
    country: str
    currency: str
    rating: str
    maturity_date: date
    market_value: Decimal
