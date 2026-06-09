"""Streamlit dashboard for counterparty exposure and collateral analytics."""

from datetime import date
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.utils import (
    format_currency,
    format_percentage,
    format_ratio,
    generate_portfolio_report,
    list_available_datasets,
    load_dataset,
    run_concentration_analysis,
    run_coverage_assessment,
    run_eligibility_assessment,
    run_exposure_analysis,
    run_haircut_calculation,
    run_monitoring,
    run_stress_testing,
)

st.set_page_config(
    page_title="Counterparty Exposure Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📊 Counterparty Exposure & Collateral Analytics")

# Sidebar configuration
st.sidebar.header("Configuration")

available_datasets = list_available_datasets()
if available_datasets:
    selected_dataset = st.sidebar.selectbox(
        "Select Data Version",
        available_datasets,
        index=len(available_datasets) - 1,
    )
    data_dir = Path("data") / selected_dataset
else:
    st.sidebar.warning("No data versions found. Generate sample data first.")
    st.stop()

reference_date = st.sidebar.date_input(
    "Reference Date",
    value=date.today(),
    min_value=date(2025, 1, 1),
    max_value=date.today(),
)

# Load data
try:
    dataset = load_dataset(str(data_dir))
except Exception as e:
    st.error(f"Failed to load dataset: {e}")
    st.stop()

# Run all analytics
with st.spinner("Running analytics engines..."):
    exposure_result = run_exposure_analysis(dataset, reference_date)
    eligibility_result = run_eligibility_assessment(dataset, reference_date)
    haircut_report = run_haircut_calculation(dataset, reference_date)
    coverage_report = run_coverage_assessment(
        exposure_result, haircut_report, dataset, reference_date
    )
    concentration_analysis = run_concentration_analysis(exposure_result, dataset, reference_date)
    stress_report = run_stress_testing(
        exposure_result, haircut_report, coverage_report, dataset, reference_date
    )
    monitoring_report = run_monitoring(coverage_report, reference_date)
    portfolio_report = generate_portfolio_report(
        exposure_result,
        eligibility_result,
        haircut_report,
        coverage_report,
        concentration_analysis,
        stress_report,
        monitoring_report,
        dataset,
        reference_date,
    )

# Main tabs
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs(
    [
        "📈 Overview",
        "💼 Exposure",
        "✅ Eligibility",
        "📉 Haircuts",
        "🛡️ Coverage",
        "🎯 Concentration",
        "⚡ Stress",
        "🚨 Monitoring",
        "📥 Data",
    ]
)

# ============================================================================
# TAB 1: PORTFOLIO OVERVIEW
# ============================================================================
with tab1:
    st.header("Portfolio Overview")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total Exposure",
            format_currency(portfolio_report.exposure_summary.total_exposure),
            delta=None,
        )

    with col2:
        st.metric(
            "Portfolio Coverage",
            format_ratio(portfolio_report.coverage_summary.portfolio_coverage_ratio),
            delta="✓ Covered"
            if portfolio_report.coverage_summary.undercovered_counterparties == 0
            else "⚠️ Undercovered",
        )

    with col3:
        st.metric(
            "Risk Level",
            portfolio_report.overall_risk_level.upper(),
            delta=None,
        )

    with col4:
        st.metric(
            "Stress Breaches",
            portfolio_report.stress_summary.coverage_breaches,
            delta=f"of {portfolio_report.stress_summary.total_scenarios} scenarios",
        )

    st.markdown("---")

    # Key findings
    st.subheader("🔑 Key Findings")
    if portfolio_report.key_findings:
        for finding in portfolio_report.key_findings:
            st.info(finding)
    else:
        st.success("No critical findings. Portfolio in healthy state.")

    # Executive summary metrics
    st.subheader("Executive Summary")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.write("**Exposure Metrics**")
        st.write(f"• Counterparties: {len(dataset.counterparties)}")
        st.write(
            f"• Avg Exposure: {format_currency(portfolio_report.exposure_summary.avg_exposure)}"
        )
        st.write(
            f"• Max Exposure: {format_currency(portfolio_report.exposure_summary.max_exposure)}"
        )

    with col2:
        st.write("**Coverage Status**")
        st.write(f"• Covered: {portfolio_report.coverage_summary.covered_counterparties}")
        st.write(f"• Undercovered: {portfolio_report.coverage_summary.undercovered_counterparties}")
        st.write(
            f"• Shortfall: {format_currency(portfolio_report.coverage_summary.total_shortfall)}"
        )

    with col3:
        st.write("**Risk Indicators**")
        st.write(f"• Anomalies: {portfolio_report.monitoring_summary.num_anomalies}")
        st.write(f"• Critical Alerts: {portfolio_report.monitoring_summary.num_critical_warnings}")
        st.write(
            f"• Herfindahl Index: {format_ratio(portfolio_report.concentration_summary.herfindahl_index)}"
        )


# ============================================================================
# TAB 2: EXPOSURE ANALYTICS
# ============================================================================
with tab2:
    st.header("Counterparty Exposure Analysis")

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "Total Exposure", format_currency(portfolio_report.exposure_summary.total_exposure)
        )
        st.metric(
            "Average Exposure", format_currency(portfolio_report.exposure_summary.avg_exposure)
        )

    with col2:
        st.metric("Min Exposure", format_currency(portfolio_report.exposure_summary.min_exposure))
        st.metric("Max Exposure", format_currency(portfolio_report.exposure_summary.max_exposure))

    st.markdown("---")

    # Top exposures
    st.subheader("Top Counterparty Exposures")
    if portfolio_report.exposure_summary.top_3_exposures:
        top_data = []
        for cp_id, exposure in portfolio_report.exposure_summary.top_3_exposures:
            cp_name = (
                dataset.counterparties.get(cp_id, {}).name
                if cp_id in dataset.counterparties
                else cp_id
            )
            utilisation = (
                (exposure / dataset.counterparties[cp_id].exposure_limit)
                if cp_id in dataset.counterparties
                else 0
            )
            top_data.append(
                {
                    "Counterparty": cp_name,
                    "Exposure": float(exposure),
                    "Utilisation": float(utilisation),
                }
            )

        df_top = pd.DataFrame(top_data)
        fig = px.bar(df_top, x="Counterparty", y="Exposure", title="Top 3 Exposures")
        st.plotly_chart(fig, use_container_width=True)

    # Utilisation
    st.subheader("Counterparty Utilisation")
    utilisation_data = []
    for cp_id, cp in dataset.counterparties.items():
        utilisation = float(cp.utilisation())
        utilisation_data.append(
            {
                "Counterparty": cp.name,
                "Utilisation": utilisation * 100,
                "At Limit": cp.is_at_limit(),
            }
        )

    df_util = pd.DataFrame(utilisation_data).sort_values("Utilisation", ascending=False)
    fig = px.bar(
        df_util,
        x="Counterparty",
        y="Utilisation",
        color="At Limit",
        title="Exposure Utilisation (%)",
        color_discrete_map={True: "red", False: "green"},
    )
    st.plotly_chart(fig, use_container_width=True)


# ============================================================================
# TAB 3: COLLATERAL ELIGIBILITY
# ============================================================================
with tab3:
    st.header("Collateral Eligibility Assessment")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Positions", portfolio_report.eligibility_summary.total_positions)

    with col2:
        st.metric("Eligible", portfolio_report.eligibility_summary.eligible_positions)

    with col3:
        st.metric("Rejected", portfolio_report.eligibility_summary.rejected_positions)

    st.markdown("---")

    # Eligibility rate
    st.subheader("Eligibility Rate")
    fig = go.Figure(
        data=[
            go.Pie(
                labels=["Eligible", "Rejected"],
                values=[
                    portfolio_report.eligibility_summary.eligible_positions,
                    portfolio_report.eligibility_summary.rejected_positions,
                ],
                marker=dict(colors=["green", "red"]),
            )
        ]
    )
    st.plotly_chart(fig, use_container_width=True)

    # Eligibility by asset type
    st.subheader("Collateral by Asset Type")
    asset_data = []
    for sec_id, sec in dataset.securities.items():
        is_eligible = (
            eligibility_result.decisions.get(sec_id).eligible
            if sec_id in eligibility_result.decisions
            else False
        )
        asset_data.append(
            {
                "Asset Type": sec.asset_type,
                "ISIN": sec_id,
                "Rating": sec.rating,
                "Eligible": "✓" if is_eligible else "✗",
            }
        )

    df_assets = pd.DataFrame(asset_data)
    st.dataframe(df_assets, use_container_width=True, hide_index=True)


# ============================================================================
# TAB 4: HAIRCUT ANALYSIS
# ============================================================================
with tab4:
    st.header("Haircut Analysis")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total Market Value",
            format_currency(portfolio_report.haircut_summary.total_market_value),
        )

    with col2:
        st.metric(
            "Total Haircut Amount",
            format_currency(portfolio_report.haircut_summary.total_haircut_amount),
        )

    with col3:
        st.metric(
            "Avg Haircut Rate", format_percentage(portfolio_report.haircut_summary.avg_haircut_rate)
        )

    with col4:
        st.metric(
            "Adjusted Value", format_currency(portfolio_report.haircut_summary.total_adjusted_value)
        )

    st.markdown("---")

    # Haircut distribution
    st.subheader("Haircut Rate Distribution")
    haircut_data = []
    for assessment in haircut_report.assessments.values():
        haircut_data.append(
            {
                "ISIN": assessment.isin,
                "Haircut Rate": float(assessment.haircut_rate) * 100,
                "Market Value": float(assessment.market_value),
            }
        )

    df_haircuts = pd.DataFrame(haircut_data)
    fig = px.scatter(
        df_haircuts,
        x="Haircut Rate",
        y="Market Value",
        size="Market Value",
        hover_data=["ISIN"],
        title="Haircut Rates vs Market Value",
    )
    st.plotly_chart(fig, use_container_width=True)


# ============================================================================
# TAB 5: COVERAGE MONITORING
# ============================================================================
with tab5:
    st.header("Collateral Coverage Monitoring")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Portfolio Coverage Ratio",
            format_ratio(portfolio_report.coverage_summary.portfolio_coverage_ratio),
        )

    with col2:
        st.metric(
            "Covered Counterparties",
            f"{portfolio_report.coverage_summary.covered_counterparties} / {len(coverage_report.assessments)}",
        )

    with col3:
        st.metric(
            "Total Shortfall", format_currency(portfolio_report.coverage_summary.total_shortfall)
        )

    st.markdown("---")

    # Coverage by counterparty
    st.subheader("Coverage Ratios by Counterparty")
    coverage_data = []
    for cp_id, assessment in coverage_report.assessments.items():
        cp_name = (
            dataset.counterparties.get(cp_id).name if cp_id in dataset.counterparties else cp_id
        )
        coverage_data.append(
            {
                "Counterparty": cp_name,
                "Coverage Ratio": float(assessment.coverage_ratio),
                "Is Covered": assessment.is_covered,
            }
        )

    df_coverage = pd.DataFrame(coverage_data).sort_values("Coverage Ratio")
    fig = px.bar(
        df_coverage,
        x="Counterparty",
        y="Coverage Ratio",
        color="Is Covered",
        title="Coverage Ratio by Counterparty",
        color_discrete_map={True: "green", False: "red"},
    )
    st.plotly_chart(fig, use_container_width=True)

    # Shortfall/Excess
    st.subheader("Shortfall / Excess Collateral")
    shortfall_data = []
    for cp_id, assessment in coverage_report.assessments.items():
        cp_name = (
            dataset.counterparties.get(cp_id).name if cp_id in dataset.counterparties else cp_id
        )
        shortfall_data.append(
            {
                "Counterparty": cp_name,
                "Shortfall": float(assessment.unsecured_exposure),
                "Excess": float(assessment.excess_collateral),
            }
        )

    df_shortfall = pd.DataFrame(shortfall_data)
    fig = px.bar(
        df_shortfall,
        x="Counterparty",
        y=["Shortfall", "Excess"],
        title="Shortfall vs Excess Collateral",
        barmode="group",
    )
    st.plotly_chart(fig, use_container_width=True)


# ============================================================================
# TAB 6: CONCENTRATION RISK
# ============================================================================
with tab6:
    st.header("Concentration Risk Analysis")

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "Herfindahl Index",
            format_ratio(portfolio_report.concentration_summary.herfindahl_index),
        )

    with col2:
        st.metric(
            "Issuer Concentrations > 20%",
            portfolio_report.concentration_summary.issuer_concentration_count,
        )

    st.markdown("---")

    # Top concentrations
    st.subheader("Top Concentrations by Dimension")
    col1, col2 = st.columns(2)

    with col1:
        st.write("**By Issuer**")
        issuer_data = [
            {"Issuer": m.dimension_value, "Concentration": float(m.concentration_percent)}
            for m in concentration_analysis.by_issuer[:5]
        ]
        if issuer_data:
            df_issuer = pd.DataFrame(issuer_data)
            st.dataframe(df_issuer, use_container_width=True, hide_index=True)

    with col2:
        st.write("**By Asset Type**")
        asset_data = [
            {"Asset Type": m.dimension_value, "Concentration": float(m.concentration_percent)}
            for m in concentration_analysis.by_asset_type[:5]
        ]
        if asset_data:
            df_asset = pd.DataFrame(asset_data)
            st.dataframe(df_asset, use_container_width=True, hide_index=True)

    # Concentration charts
    st.subheader("Concentration Distribution")
    col1, col2 = st.columns(2)

    with col1:
        issuer_chart_data = [
            {"Dimension": m.dimension_value, "Concentration": float(m.concentration_percent)}
            for m in concentration_analysis.by_issuer
        ]
        if issuer_chart_data:
            df_issuer_chart = (
                pd.DataFrame(issuer_chart_data)
                .sort_values("Concentration", ascending=False)
                .head(10)
            )
            fig = px.bar(
                df_issuer_chart, x="Dimension", y="Concentration", title="Top Issuer Concentrations"
            )
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        asset_chart_data = [
            {"Dimension": m.dimension_value, "Concentration": float(m.concentration_percent)}
            for m in concentration_analysis.by_asset_type
        ]
        if asset_chart_data:
            df_asset_chart = pd.DataFrame(asset_chart_data).sort_values(
                "Concentration", ascending=False
            )
            fig = px.pie(
                df_asset_chart,
                names="Dimension",
                values="Concentration",
                title="Asset Type Distribution",
            )
            st.plotly_chart(fig, use_container_width=True)


# ============================================================================
# TAB 7: STRESS TESTING
# ============================================================================
with tab7:
    st.header("Stress Testing")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Scenarios", portfolio_report.stress_summary.total_scenarios)

    with col2:
        st.metric("Coverage Breaches", portfolio_report.stress_summary.coverage_breaches)

    with col3:
        st.metric(
            "Worst Case Decline",
            format_ratio(abs(portfolio_report.stress_summary.worst_case_coverage_decline)),
        )

    st.markdown("---")

    st.subheader(f"Worst Case Scenario: {portfolio_report.stress_summary.worst_case_scenario}")

    # Stress results by scenario
    st.subheader("Scenario Impact on Coverage")
    stress_data = []
    for scenario_name, result in stress_report.results.items():
        stress_data.append(
            {
                "Scenario": scenario_name,
                "Base Coverage": float(result.base_coverage_ratio)
                if result.base_coverage_ratio
                else 0,
                "Stress Coverage": float(result.coverage_ratio) if result.coverage_ratio else 0,
                "Coverage Breach": result.coverage_breached,
            }
        )

    df_stress = pd.DataFrame(stress_data)
    fig = px.bar(
        df_stress,
        x="Scenario",
        y=["Base Coverage", "Stress Coverage"],
        title="Coverage Before and After Stress",
        barmode="group",
    )
    st.plotly_chart(fig, use_container_width=True)

    # Scenario details table
    st.subheader("Scenario Details")
    st.dataframe(df_stress, use_container_width=True, hide_index=True)


# ============================================================================
# TAB 8: MONITORING & ALERTS
# ============================================================================
with tab8:
    st.header("Anomalies & Risk Alerts")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Detected Anomalies", len(monitoring_report.anomalies))

    with col2:
        st.metric("Risk Commentaries", len(monitoring_report.commentaries))

    with col3:
        st.metric("Early Warnings", len(monitoring_report.early_warnings))

    st.markdown("---")

    # Risk commentaries
    st.subheader("Risk Commentary")
    for commentary in monitoring_report.commentaries:
        severity_emoji = (
            "🔴"
            if commentary.severity == "critical"
            else "🟡"
            if commentary.severity == "warning"
            else "🟢"
        )
        st.warning(f"{severity_emoji} **{commentary.severity.upper()}**: {commentary.text}")

    # Early warnings
    st.subheader("Early Warnings")
    if monitoring_report.early_warnings:
        for warning in monitoring_report.early_warnings:
            confidence = float(warning.confidence) * 100 if warning.confidence else 0
            st.info(
                f"⚠️ **{warning.warning_type}**: {warning.indicator_name} (Confidence: {confidence:.0f}%)"
            )
    else:
        st.success("No early warnings detected.")

    # Anomalies table
    st.subheader("Anomaly Scores")
    if monitoring_report.anomalies:
        anomaly_data = [
            {
                "Counterparty": a.counterparty_id,
                "Dimension": a.dimension,
                "Anomaly Score": float(a.anomaly_score),
                "Z-Score": float(a.z_score) if a.z_score else 0,
                "Deviation": a.deviation_type,
            }
            for a in monitoring_report.anomalies
        ]
        df_anomalies = pd.DataFrame(anomaly_data).sort_values("Anomaly Score", ascending=False)
        st.dataframe(df_anomalies, use_container_width=True, hide_index=True)


# ============================================================================
# TAB 9: DATA EXPORT
# ============================================================================
with tab9:
    st.header("Data Export")

    st.subheader("Portfolio Summary Report")
    summary_data = {
        "Metric": [
            "Total Exposure",
            "Portfolio Coverage Ratio",
            "Overall Risk Level",
            "Eligible Collateral",
            "Total Haircut Amount",
            "Covered Counterparties",
            "Herfindahl Index",
            "Stress Test Breaches",
            "Detected Anomalies",
            "Critical Alerts",
        ],
        "Value": [
            f"{portfolio_report.exposure_summary.total_exposure:,.2f}",
            f"{portfolio_report.coverage_summary.portfolio_coverage_ratio:.2f}x",
            portfolio_report.overall_risk_level.upper(),
            f"{portfolio_report.eligibility_summary.eligible_positions}",
            f"{portfolio_report.haircut_summary.total_haircut_amount:,.2f}",
            f"{portfolio_report.coverage_summary.covered_counterparties} / {len(coverage_report.assessments)}",
            f"{portfolio_report.concentration_summary.herfindahl_index:.4f}",
            f"{portfolio_report.stress_summary.coverage_breaches} / {portfolio_report.stress_summary.total_scenarios}",
            f"{portfolio_report.monitoring_summary.num_anomalies}",
            f"{portfolio_report.monitoring_summary.num_critical_warnings}",
        ],
    }
    df_summary = pd.DataFrame(summary_data)
    st.dataframe(df_summary, use_container_width=True, hide_index=True)

    # Download buttons
    csv_summary = df_summary.to_csv(index=False)
    st.download_button(
        label="Download Summary Report (CSV)",
        data=csv_summary,
        file_name=f"portfolio_summary_{reference_date}.csv",
        mime="text/csv",
    )

    st.subheader("Detailed Position Data")
    if st.checkbox("Show all positions"):
        position_data = []
        for pos in dataset.positions:
            assessment = coverage_report.assessments.get(pos.counterparty_id)
            haircut = haircut_report.assessments.get(pos.isin)
            if assessment and haircut:
                position_data.append(
                    {
                        "Counterparty": pos.counterparty_id,
                        "ISIN": pos.isin,
                        "Quantity": float(pos.quantity),
                        "Market Value": float(pos.market_value),
                        "Haircut Rate": float(haircut.haircut_rate) if haircut else 0,
                        "Adjusted Value": float(haircut.adjusted_value)
                        if haircut
                        else float(pos.market_value),
                    }
                )

        if position_data:
            df_positions = pd.DataFrame(position_data)
            st.dataframe(df_positions, use_container_width=True, hide_index=True)

            csv_positions = df_positions.to_csv(index=False)
            st.download_button(
                label="Download Position Data (CSV)",
                data=csv_positions,
                file_name=f"positions_{reference_date}.csv",
                mime="text/csv",
            )
