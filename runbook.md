Here is the content:

```markdown
# runbook.md

## Environment

```bash
# Activate venv
source .venv/bin/activate

# Install everything after defining dependencies
pip install -e '.[dev]'
```

## Code quality

See at end of this page references to ruff

```bash
# Check linting
ruff check src tests

# Auto-fix what ruff can
ruff check --fix src tests

# Check formatting
ruff format --check src tests

# Fix formatting
ruff format src tests

# Type check
mypy src
```

## Before every push

```bash
ruff format src tests
ruff check --fix src tests
ruff check src tests
pytest tests/
```

## Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ -v --cov=src --cov-report=term-missing
```

## Common ruff errors

- F401 unused import -- remove it
- F841 assigned but unused variable -- remove it
- I001 import order -- run `ruff check --fix` to auto-sort

## Mock data

<!-- Add the command to generate mock data for this project once defined -->
```


# Ref: All code must pass ruff checks:

### Import Rules
- Imports must be sorted alphabetically within groups
- Local imports should be grouped together and sorted
- Remove all unused imports immediately (F401)
- Correct sort order: stdlib → third-party → local imports

### Variable Rules
- Do NOT assign variables that are never used (F841)
- Remove assigned-but-unused variables from loops, conditionals, etc.
- OK to import and re-export in __init__.py files (even if not directly used)

### Common Fixes
- Remove unused imports: `from typing import Any` (if not used in file)
- Remove unused loop variables: don't collect data you don't use
- Sort imports: local imports in __init__.py should be alphabetical
  Example: base → csv_loaders → data_manager (not data_manager → base)

### Before Committing
Run: `python3 -m ruff check src tests`
All output should be "All checks passed!"

### Files with Common Issues
- `__init__.py` files: watch for unsorted imports (ruff will fix with --fix)
- Test files: remove imports used only for type hints if not explicitly needed
- Generator/utility files: don't define variables used only in comments
## Running the Dashboard

```bash
# Activate virtual environment
source .venv/bin/activate

# Generate sample data first (if not already generated)
python3 -c "from collateral_analytics.sample_data.generator import SampleDataGenerator; gen = SampleDataGenerator(); gen.generate()"

# Run the Streamlit dashboard
streamlit run dashboard/app.py
```

The dashboard will open in your default browser at `http://localhost:8501`

### Dashboard Features

- **Portfolio Overview**: Executive summary with KPIs and key findings
- **Exposure Analytics**: Counterparty exposure rankings and utilization
- **Collateral Eligibility**: Acceptance rates and rejection reasons
- **Haircut Analysis**: Haircut application and distribution
- **Coverage Monitoring**: Collateral coverage ratios and shortfalls
- **Concentration Risk**: Herfindahl index and top concentrations
- **Stress Testing**: Scenario impacts and breach detection
- **Monitoring & Alerts**: Anomalies, risk commentary, and early warnings
- **Data Export**: Download reports and position data as CSV

### Troubleshooting

If you encounter import errors, make sure:
1. Virtual environment is activated: `source .venv/bin/activate`
2. Dependencies are installed: `uv sync`
3. You're running from the project root directory
