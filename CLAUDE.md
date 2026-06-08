# CLAUDE.md

## Project overview

This repository is a counterparty exposure and collateral analytics platform built as a
professional risk application. The full specification is in docs/project_spec.md -- read it
before starting any module.

The implementation is inspired by practices used by central banks, CCPs, and treasury
functions. It is not intended to replicate regulatory frameworks or production systems.

---

## Commit rules

- Do not add co-author attribution in commit messages
- Do not add any Claude or AI references in commit messages
- Use only the repository author identity configured in git
- Commit messages should reflect the domain reasoning behind the change, not just the code change
- do not commit anything. I will ask you eventually to give me bash commands to stage files and to the commit messages.

Good commit message examples:
- `add cashflow coverage ratio calculation for soft bullet structures`
- `fix haircut schedule lookup -- was matching on asset type only, now includes maturity bucket`
- `add rating downgrade scenario to stress engine`

---

## How we work together

### Session start
At the start of every session, state which module you are working on.
Do not jump to another module unless explicitly instructed.
Confirm the current state of the repo before adding new files.

1. Understand the task first
2. Explain proposed changes before implementing anything
3. Wait for approval
4. Implement in small steps
5. After each step explain what changed and why

### Module sequencing
Build in this order unless instructed otherwise:

1. Domain models and data layer
2. Module 1 -- Counterparty Exposure Analytics
3. Module 2 -- Collateral Eligibility
4. Module 3 -- Haircut Framework
5. Module 4 -- Collateral Sufficiency
6. Module 5 -- Concentration Risk
7. Module 6 -- Stress Testing
8. Module 7 -- AI-Assisted Monitoring
9. Reporting layer
10. Streamlit dashboard
11. Tests (written alongside each module, not deferred to the end)
12. Documentation

### Commit with linear issues referenced

MRS-120 Streamlit dashboard

MRS-119 Reporting layer

MRS-118 Module 7 -- AI Assisted Monitoring

MRS-117 Module 6 -- Stress Testing

MRS-116 Module 5 -- Concentration Risk

MRS-115 Module 4 -- Collateral Sufficiency Monitoring

MRS-114 Module 3 -- Haircut Framework

MRS-113 Module 2 -- Collateral Eligibility Engine

MRS-112 Module 1 -- Counterparty Exposure Analytics

MRS-111 Sample data generation

MRS-110 Domain models and data layer

MRS-109 Set up repository structure and base architecture


### Before creating new files
If a pattern already exists in the repo (a base class, a loader, a report format),
follow that pattern. Ask before introducing a new pattern.

### When stuck
If a design decision is ambiguous, ask. Do not invent business logic that is not in the spec
or already present in the codebase.

---

## Code standards

- Python 3.13.3
- Type hints throughout -- no untyped functions
- Pydantic or dataclasses for all domain objects
- pathlib for all file paths -- no string path concatenation
- pytest for all tests -- use fixtures
- logging for all runtime messages -- no print statements in production code
- No `from __future__ import annotations`
- No hardcoded datasets -- everything loads from CSV files in data/
- No business logic inside dashboard code
- Custom exceptions for domain errors (see spec for the full list)

---

## Architecture rules

- Abstract base classes for all engines and loaders
- Concrete implementations via dependency injection
- Calculations must be independent from visualisation
- Business logic operates on domain entities, not raw DataFrames where practical
- Prefer composition over deep inheritance hierarchies

---

## What AI monitoring is and is not

AI is used only for surveillance and commentary generation:
- anomaly detection (Isolation Forest, LOF, or statistical methods)
- automated risk commentary from KPIs
- early warning indicators

AI is not used for:
- eligibility decisions
- haircut assignment
- regulatory classification

These remain rule-based. Do not blur this boundary.

---

## Sample data rules

- All sample data must be realistic -- no placeholder names like "Counterparty A"
- Data must cover at least January through June (monthly snapshots)
- Multiple counterparties, issuers, asset classes, ratings
- Concentrations should be realistic enough to trigger alerts in some scenarios

---

## Disclaimer to include in README and docs

> This repository is a simplified analytical implementation inspired by collateral and
> counterparty risk practices used by financial institutions and central banks. It is not
> intended to replicate regulatory frameworks or production systems.
