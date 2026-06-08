# Conventions and Standards

## Numerical Representation

### Core Rule
All numerical values are stored in their **natural decimal form** to ensure accuracy and avoid rounding errors.

### Rate and Ratio Storage

| Type | Storage | Range | Example |
|------|---------|-------|---------|
| Haircut rate | Decimal | 0.0 — 1.0 | 0.15 = 15% haircut |
| Coverage ratio | Decimal | 0.0 — ∞ | 1.25 = 125% coverage |
| Interest rate | Decimal | per annum | 0.05 = 5% p.a. |
| Spread/Yield | Integer (bps) | basis points | 150 = 150 bps = 1.5% |
| Concentration % | Decimal | 0.0 — 1.0 | 0.35 = 35% concentration |

### Basis Points (bps)

Use integer basis points only when:
- Data is sourced in bps (market data, credit spreads)
- Precision below 1 bps is not needed

**Conversion:**
- 1 bps = 0.0001 as decimal = 0.01%
- 150 bps = 0.015 as decimal = 1.5%

### Percentage Values

**Never store raw percentages.** Always convert:
- 5% → 0.05 (as Decimal)
- 150 bps → as integer 150

### Examples

```python
# Haircut
haircut_rate = Decimal("0.15")  # 15% haircut, not 15 or 0.0015

# Coverage ratio
coverage_ratio = Decimal("1.25")  # 125%, not 125 or 1.25%

# Spread (in basis points)
spread_bps = 150  # 150 bps, convert to 0.015 if needed as decimal

# Interest rate
interest_rate = Decimal("0.05")  # 5% p.a., not 5
```

## Field Naming Conventions

Make the unit explicit in field names:

- `haircut_rate` — implicit decimal (0-1 range)
- `coverage_ratio` — implicit decimal
- `spread_bps` — explicit basis points
- `market_value` — implicit currency (EUR)
- `days_to_maturity` — implicit days
- `maturity_date` — implicit ISO date

## Validation Rules

All models enforce:
- Non-negative monetary values
- Haircut rates: 0 ≤ x ≤ 1
- Ratios: x ≥ 0
- Dates: valid ISO 8601 format
- Currency: EUR only (for now)
- ISIN: valid format (2-letter country + 9 digits + 1 check digit)

## Module Documentation

Each module includes:
- Module-level docstring explaining unit conventions
- Field-level docstrings for non-obvious fields
- Examples in comments where values appear
