# Counterparty Exposure and Collateral Analytics Platform

## Overview

A Python-based analytics platform for measuring counterparty exposure, assessing collateral quality, monitoring coverage, analysing concentration risk, stress testing portfolios, and generating risk commentary.

The platform follows a modular architecture where each analytical component can be executed independently or as part of a complete workflow.

---

## Dashboard

### Overview Dashboard

![Overview Dashboard](docs/images/dashboard-overview.png)

### Risk Analytics Dashboard

![Risk Analytics Dashboard](docs/images/dashboard-risk.png)

For a complete walkthrough of all dashboard pages and functionality:

**See:** `docs/dashboard_showcase.pdf`

---

## Key Features

### Counterparty Exposure Analytics
- Gross and net exposure calculation
- Utilisation monitoring
- Counterparty ranking and aggregation
- Exposure limit monitoring

### Collateral Analytics
- Eligibility assessment engine
- Schedule-based haircut framework
- Adjusted collateral valuation
- Coverage and shortfall monitoring

### Risk Analytics
- Concentration analysis
- Herfindahl Index calculation
- Scenario-based stress testing
- Portfolio risk summaries

### Monitoring and Reporting
- Statistical anomaly detection
- Automated risk commentary
- Early warning indicators
- Executive reporting layer

---

## Architecture

```text
CSV Data
   ↓
Exposure Analytics
   ↓
Eligibility Assessment
   ↓
Haircut Framework
   ↓
Coverage Monitoring
   ↓
Concentration Analysis
   ↓
Stress Testing
   ↓
Monitoring
   ↓
Reporting
   ↓
Streamlit Dashboard
```

---

## Technology Stack

- Python 3.13
- Pandas
- Pydantic / Dataclasses
- Streamlit
- Pytest
- Ruff
- Mypy
- UV

---

## Quick Start

```bash
git clone <repository-url>
cd counterparty-exposure-collateral-analytics
uv sync
streamlit run dashboard/app.py
```

### Run Tests

```bash
uv run pytest tests/
```

---

## Sample Data

The repository includes realistic sample datasets covering:

- Multiple counterparties
- Multiple issuers
- Different credit ratings
- Multiple asset classes
- Several monthly snapshots

---

## Repository Structure

```text
.
├── dashboard/
├── data/
├── src/
│   └── collateral_analytics/
├── tests/
├── meta/
├── README.md
├── runbook.md
├── CLAUDE.md
└── pyproject.toml
```

---

## Documentation

- Project Dossier
- Methodology Documentation
- Dashboard Showcase
- Project Specification
- Conventions and Standards
- Runbook

---

## Future Enhancements

- Multi-currency support
- Database persistence layer
- API interfaces
- Additional stress scenarios
- Scheduled reporting workflows

---

## Disclaimer

This repository is a simplified analytical implementation inspired by collateral and counterparty risk practices used by financial institutions and central banks. It is not intended to replicate regulatory frameworks or production systems.
