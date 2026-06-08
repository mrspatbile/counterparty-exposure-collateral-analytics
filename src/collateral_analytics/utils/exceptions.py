"""Custom exceptions for counterparty exposure and collateral analytics."""


class AnalyticsError(Exception):
    """Base exception for all analytics errors."""

    pass


class DataLoadingError(AnalyticsError):
    """Raised when data loading from CSV fails."""

    pass


class ValidationError(AnalyticsError):
    """Raised when data validation fails."""

    pass


class EligibilityError(AnalyticsError):
    """Raised when eligibility assessment fails."""

    pass


class HaircutError(AnalyticsError):
    """Raised when haircut calculation fails."""

    pass


class ExposureError(AnalyticsError):
    """Raised when exposure calculation fails."""

    pass


class CollateralError(AnalyticsError):
    """Raised when collateral-related calculations fail."""

    pass


class ConcentrationError(AnalyticsError):
    """Raised when concentration analysis fails."""

    pass


class StressTestError(AnalyticsError):
    """Raised when stress testing fails."""

    pass
