"""Abstract base classes for analytics engines."""

from abc import ABC, abstractmethod
from typing import Any


class BaseEngine(ABC):
    """Base class for all analytics engines."""

    pass


class BaseExposureAnalyzer(BaseEngine):
    """Abstract base class for counterparty exposure analysis.

    Calculates gross/net exposure, utilisation, concentration, and rankings.
    """

    @abstractmethod
    def analyze(self, **kwargs: Any) -> Any:
        """Perform exposure analysis.

        Returns:
            Analysis results (structure depends on implementation)
        """
        pass


class BaseEligibilityEngine(BaseEngine):
    """Abstract base class for collateral eligibility assessment.

    Determines whether collateral is eligible based on configurable rules.
    """

    @abstractmethod
    def assess(self, **kwargs: Any) -> Any:
        """Assess collateral eligibility.

        Returns:
            Eligibility assessment results
        """
        pass


class BaseHaircutEngine(BaseEngine):
    """Abstract base class for haircut calculation.

    Applies haircuts based on asset type, maturity, and credit quality.
    """

    @abstractmethod
    def calculate(self, **kwargs: Any) -> Any:
        """Calculate haircuts and adjusted collateral values.

        Returns:
            Haircut calculation results
        """
        pass


class BaseConcentrationAnalyzer(BaseEngine):
    """Abstract base class for concentration analysis.

    Analyzes issuer, asset type, and rating concentrations.
    """

    @abstractmethod
    def analyze(self, **kwargs: Any) -> Any:
        """Perform concentration analysis.

        Returns:
            Concentration analysis results
        """
        pass


class BaseStressEngine(BaseEngine):
    """Abstract base class for stress testing.

    Applies stress scenarios (rate shock, spread shock, downgrade, etc.)
    and recalculates coverage metrics.
    """

    @abstractmethod
    def stress(self, **kwargs: Any) -> Any:
        """Run stress testing scenarios.

        Returns:
            Stress test results
        """
        pass


class BaseReportGenerator(BaseEngine):
    """Abstract base class for report generation.

    Generates structured reports in various formats (Excel, CSV).
    """

    @abstractmethod
    def generate(self, **kwargs: Any) -> Any:
        """Generate report from analysis results.

        Returns:
            Report output (path, bytes, or structured data)
        """
        pass
