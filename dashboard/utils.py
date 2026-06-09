"""Dashboard utilities for caching and data loading."""

from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import streamlit as st

from collateral_analytics.engines.concentration import StandardConcentrationAnalyzer
from collateral_analytics.engines.coverage import StandardCoverageAnalyzer
from collateral_analytics.engines.eligibility import ConfigurableEligibilityEngine
from collateral_analytics.engines.exposure import StandardExposureAnalyzer
from collateral_analytics.engines.haircut import ScheduleBasedHaircutEngine
from collateral_analytics.engines.monitoring import StandardMonitoringEngine
from collateral_analytics.engines.reporting import ReportGenerator
from collateral_analytics.engines.stress import StandardStressEngine
from collateral_analytics.loaders.data_manager import AnalyticsDataset, DataManager
from collateral_analytics.models.eligibility import EligibilityRule
from collateral_analytics.models.reports import PortfolioSummaryReport
from collateral_analytics.sample_data.generator import SampleDataGenerator


@st.cache_resource
def get_data_manager(data_dir: str) -> DataManager:
    """Get DataManager instance with caching."""
    return DataManager(Path(data_dir))


@st.cache_data
def load_dataset(data_dir: str) -> AnalyticsDataset:
    """Load and cache analytics dataset."""
    manager = get_data_manager(data_dir)
    return manager.load(validate=True)


@st.cache_data
def list_available_datasets(base_dir: str = "data") -> list[str]:
    """List available sample data versions."""
    gen = SampleDataGenerator()
    versions = gen.list_versions(base_dir)
    return list(versions) if versions else []


@st.cache_data
def run_exposure_analysis(dataset: AnalyticsDataset, reference_date: date) -> Any:
    """Run exposure analysis with caching."""
    engine = StandardExposureAnalyzer(reference_date=reference_date)
    return engine.analyze(dataset=dataset)


@st.cache_data
def run_eligibility_assessment(dataset: AnalyticsDataset, reference_date: date) -> Any:
    """Run eligibility assessment with caching."""
    engine = ConfigurableEligibilityEngine(
        rule=EligibilityRule(
            allowed_asset_types={"sovereign", "corporate_bond", "covered_bond"},
            allowed_currencies={"EUR"},
        ),
        reference_date=reference_date,
    )
    return engine.assess(dataset=dataset)


@st.cache_data
def run_haircut_calculation(dataset: AnalyticsDataset, reference_date: date) -> Any:
    """Run haircut calculation with caching."""
    engine = ScheduleBasedHaircutEngine(reference_date=reference_date)
    return engine.calculate(dataset=dataset)


@st.cache_data
def run_coverage_assessment(
    exposure_result: Any, haircut_report: Any, dataset: AnalyticsDataset, reference_date: date
) -> Any:
    """Run coverage assessment with caching."""
    engine = StandardCoverageAnalyzer(reference_date=reference_date)
    return engine.assess(
        exposure_result=exposure_result,
        haircut_report=haircut_report,
        dataset=dataset,
    )


@st.cache_data
def run_concentration_analysis(
    exposure_result: Any, dataset: AnalyticsDataset, reference_date: date
) -> Any:
    """Run concentration analysis with caching."""
    engine = StandardConcentrationAnalyzer(reference_date=reference_date)
    return engine.analyze(exposure_result=exposure_result, dataset=dataset)


@st.cache_data
def run_stress_testing(
    exposure_result: Any,
    haircut_report: Any,
    coverage_report: Any,
    dataset: AnalyticsDataset,
    reference_date: date,
) -> Any:
    """Run stress testing with caching."""
    engine = StandardStressEngine(reference_date=reference_date)
    return engine.stress(
        exposure_result=exposure_result,
        haircut_report=haircut_report,
        coverage_report=coverage_report,
        dataset=dataset,
    )


@st.cache_data
def run_monitoring(coverage_report: Any, reference_date: date) -> Any:
    """Run monitoring with caching."""
    engine = StandardMonitoringEngine(reference_date=reference_date)
    return engine.monitor(coverage_report=coverage_report)


@st.cache_data
def generate_portfolio_report(
    exposure_result: Any,
    eligibility_result: Any,
    haircut_report: Any,
    coverage_report: Any,
    concentration_analysis: Any,
    stress_report: Any,
    monitoring_report: Any,
    dataset: AnalyticsDataset,
    reference_date: date,
) -> PortfolioSummaryReport:
    """Generate portfolio summary report with caching."""
    gen = ReportGenerator(reference_date=reference_date)
    eligibility_data = {
        isin: decision.eligible for isin, decision in eligibility_result.decisions.items()
    }
    return gen.generate_portfolio_summary(
        exposure_result=exposure_result,
        eligibility_data=eligibility_data,
        haircut_report=haircut_report,
        coverage_report=coverage_report,
        concentration_analysis=concentration_analysis,
        stress_report=stress_report,
        monitoring_report=monitoring_report,
        dataset=dataset,
    )


def decimal_to_float(value: Decimal) -> float:
    """Convert Decimal to float for plotting."""
    return float(value)


def format_currency(value: Decimal | float) -> str:
    """Format value as currency string."""
    if isinstance(value, Decimal):
        value = float(value)
    return f"€{value:,.0f}"


def format_percentage(value: Decimal | float) -> str:
    """Format value as percentage string."""
    if isinstance(value, Decimal):
        value = float(value)
    return f"{value * 100:.2f}%"


def format_ratio(value: Decimal | float) -> str:
    """Format value as ratio string."""
    if isinstance(value, Decimal):
        value = float(value)
    return f"{value:.2f}x"
