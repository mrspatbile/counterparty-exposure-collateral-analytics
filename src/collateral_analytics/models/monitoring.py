"""Domain models for AI-assisted monitoring and anomaly detection."""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass
class AnomalyScore:
    """Anomaly detection result for a single dimension.

    Attributes:
        counterparty_id: Counterparty identifier
        dimension: Dimension being analyzed (e.g., 'coverage_ratio', 'concentration')
        dimension_value: The value being assessed
        anomaly_score: Score 0-1 (0=normal, 1=highly anomalous)
        is_anomaly: Whether score exceeds threshold
        deviation_type: Direction of deviation ('high', 'low', 'normal')
        z_score: Standard deviations from mean (for z-score method)
        metadata: Detection method, thresholds used, etc.
    """

    counterparty_id: str
    dimension: str
    dimension_value: Decimal
    anomaly_score: Decimal
    is_anomaly: bool
    deviation_type: str  # 'high', 'low', 'normal'
    z_score: Decimal = Decimal("0")
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RiskCommentary:
    """Generated automated risk commentary.

    Attributes:
        counterparty_id: Counterparty identifier
        category: Commentary category ('coverage', 'concentration', 'utilisation', 'trend')
        text: Human-readable commentary
        severity: Severity level ('info', 'warning', 'critical')
        triggered_by: Which KPI triggered this commentary
        suggested_action: Optional recommended action
        metadata: Additional context
    """

    counterparty_id: str
    category: str
    text: str
    severity: str  # 'info', 'warning', 'critical'
    triggered_by: str = ""
    suggested_action: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EarlyWarning:
    """Early warning indicator for risk escalation.

    Attributes:
        counterparty_id: Counterparty identifier
        warning_type: Type of warning ('trend', 'threshold_breach', 'concentration_spike')
        indicator_name: Name of the indicator
        current_value: Current value of indicator
        threshold_value: Threshold that triggered warning
        days_to_breach: Estimated days until breach if trend continues
        confidence: Confidence in the warning (0-1)
        metadata: Supporting data
    """

    counterparty_id: str
    warning_type: str
    indicator_name: str
    current_value: Decimal
    threshold_value: Decimal
    days_to_breach: int = 0
    confidence: Decimal = Decimal("0.5")
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MonitoringReport:
    """Complete AI-assisted monitoring output.

    Attributes:
        anomalies: List of detected anomalies
        commentaries: List of generated commentaries
        early_warnings: List of early warning indicators
        num_anomalies: Count of anomalies detected
        num_warnings: Count of warnings generated
        critical_count: Count of critical-severity items
        success: Whether monitoring completed successfully
        errors: Error messages if monitoring failed
        warnings: Non-fatal warnings during monitoring
    """

    anomalies: list[AnomalyScore]
    commentaries: list[RiskCommentary]
    early_warnings: list[EarlyWarning]
    num_anomalies: int = 0
    num_warnings: int = 0
    critical_count: int = 0
    success: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
