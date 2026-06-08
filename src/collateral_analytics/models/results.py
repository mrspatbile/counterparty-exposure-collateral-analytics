"""Domain models for analysis results."""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass
class AnalysisResult:
    """Base class for analysis results."""

    success: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EligibilityAssessment(AnalysisResult):
    """Result of eligibility assessment for a security."""

    isin: str = ""
    eligible: bool = False
    reason_code: str = ""
    explanation: str = ""


@dataclass
class HaircutResult(AnalysisResult):
    """Result of haircut calculation."""

    isin: str = ""
    market_value: Decimal = Decimal("0")
    haircut_rate: Decimal = Decimal("0")
    adjusted_value: Decimal = Decimal("0")


@dataclass
class CoverageMetrics(AnalysisResult):
    """Coverage ratio and related metrics."""

    counterparty_id: str = ""
    adjusted_collateral_value: Decimal = Decimal("0")
    exposure: Decimal = Decimal("0")
    coverage_ratio: Decimal = Decimal("0")
    unsecured_exposure: Decimal = Decimal("0")
    excess_collateral: Decimal = Decimal("0")
