# CLAUDE.md

## Project overview

This repository is a counterparty exposure and collateral analytics platform built as a
professional risk application. The full specification is in meta/project_spec.md. Read it before starting any module. Also read meta/conventions.md before implementing any business logic.

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

Before implementing anything:

- state which module is being worked on
- confirm the current state of the repository
- explain the proposed approach
- identify affected files
- wait for approval

Do not jump to another module unless explicitly instructed.

Implementation should be done in small steps. After each step, explain what changed and why.

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
11. Documentation

Tests must be written alongside each module and are never deferred to the end of the project.

### Linear issue mapping

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

### Conventions

Follow all conventions defined in:

- meta/conventions.md

Do not introduce new numerical representations, units, naming conventions,
or validation rules without approval.

---

## Code standards

- Python 3.13
- Type hints throughout -- no untyped functions
- Pydantic or dataclasses for all domain objects
- pathlib for all file paths -- no string path concatenation
- pytest for all tests -- use fixtures
- logging for all runtime messages -- no print statements in production code
- No `from __future__ import annotations`
- No hardcoded datasets -- everything loads from CSV files in data/
- No business logic inside dashboard code
- Custom exceptions for domain errors (see spec for the full list)
- Use Decimal for financial calculations unless the conventions explicitly state otherwise
- Do not run repository-wide test suites, type checks, or expensive validation commands unless explicitly instructed.

---

## Architecture rules

- Abstract base classes for all engines and loaders
- Concrete implementations via dependency injection
- Calculations must be independent from visualisation
- Business logic operates on domain entities, not raw DataFrames where practical
- Prefer composition over deep inheritance hierarchies
- Business rules must be traceable to the specification or documented assumptions

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

## Environment and tooling

This repository uses uv.

Use:

- `uv sync` to install project dependencies
- `uv add <package>` for runtime dependencies
- `uv add --dev <package>` for development dependencies
- `uv run <command>` to execute tools inside the project environment

---

## Disclaimer to include in README and docs

> This repository is a simplified analytical implementation inspired by collateral and
> counterparty risk practices used by financial institutions and central banks. It is not
> intended to replicate regulatory frameworks or production systems.
