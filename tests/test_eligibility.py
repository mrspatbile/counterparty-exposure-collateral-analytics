"""Tests for collateral eligibility assessment module."""

import tempfile
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Iterator

import pytest

from collateral_analytics.engines.eligibility import ConfigurableEligibilityEngine
from collateral_analytics.loaders.data_manager import DataManager
from collateral_analytics.models.eligibility import EligibilityRule


@pytest.fixture
def sample_data_dir() -> Iterator[Path]:
    """Create temporary directory with sample CSV files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        securities_csv = tmpdir_path / "securities.csv"
        securities_csv.write_text(
            "isin,name,asset_type,issuer,issuer_type,country,currency,rating,maturity_date,market_value\n"
            "XS1111111111,German Bund,sovereign,Germany,sovereign,DE,EUR,AAA,2035-12-31,1000000.00\n"
            "XS2222222222,Corp Bond A,corporate_bond,Corp A,corporate,DE,EUR,BBB,2030-06-30,500000.00\n"
            "XS3333333333,High Yield Bond,corporate_bond,Corp B,corporate,DE,EUR,B,2028-03-15,250000.00\n"
            "XS4444444444,Long Maturity Bond,sovereign,Germany,sovereign,DE,EUR,AAA,2045-06-30,1000000.00\n"
        )

        counterparties_csv = tmpdir_path / "counterparties.csv"
        counterparties_csv.write_text(
            "counterparty_id,name,country,rating,exposure,exposure_limit\n"
            "CP001,Bank A,DE,A,2000000.00,5000000.00\n"
        )

        positions_csv = tmpdir_path / "collateral_positions.csv"
        positions_csv.write_text(
            "counterparty_id,isin,quantity,market_value\n"
            "CP001,XS1111111111,1000.000000,1000000.00\n"
        )

        haircuts_csv = tmpdir_path / "haircut_schedule.csv"
        haircuts_csv.write_text(
            "asset_type,maturity_bucket,rating_bucket,haircut_rate\n"
            "sovereign,5-10y,AAA-AA,0.0100\n"
            "sovereign,10y+,AAA-AA,0.0150\n"
            "corporate_bond,5-10y,BBB,0.2000\n"
        )

        yield tmpdir_path


class TestEligibilityRule:
    """Tests for EligibilityRule."""

    def test_create_default_rule(self) -> None:
        """Create rule with default settings."""
        rule = EligibilityRule()
        assert rule.description == "Default eligibility rule"
        assert rule.require_market_value is True

    def test_allows_asset_type_with_list(self) -> None:
        """Test asset type filtering."""
        rule = EligibilityRule(allowed_asset_types={"sovereign", "covered_bond"})
        assert rule.allows_asset_type("sovereign")
        assert rule.allows_asset_type("SOVEREIGN")
        assert not rule.allows_asset_type("equity")

    def test_allows_asset_type_with_none(self) -> None:
        """Test asset type with no restriction."""
        rule = EligibilityRule(allowed_asset_types=None)
        assert rule.allows_asset_type("sovereign")
        assert rule.allows_asset_type("equity")
        assert rule.allows_asset_type("anything")

    def test_allows_currency(self) -> None:
        """Test currency filtering."""
        rule = EligibilityRule(allowed_currencies={"EUR", "GBP"})
        assert rule.allows_currency("EUR")
        assert rule.allows_currency("eur")
        assert not rule.allows_currency("USD")

    def test_allows_rating(self) -> None:
        """Test rating filtering."""
        rule = EligibilityRule(allowed_ratings={"AAA", "AA", "A", "BBB"})
        assert rule.allows_rating("AAA")
        assert not rule.allows_rating("BB")

    def test_allows_maturity(self) -> None:
        """Test maturity limits."""
        rule = EligibilityRule(max_maturity_years=10)
        assert rule.allows_maturity(5)
        assert rule.allows_maturity(10)
        assert not rule.allows_maturity(11)

    def test_allows_market_value_positive(self) -> None:
        """Test market value requirement."""
        rule = EligibilityRule(require_market_value=True)
        assert rule.allows_market_value(Decimal("1000"))
        assert not rule.allows_market_value(Decimal("0"))
        assert not rule.allows_market_value(Decimal("-1000"))

    def test_allows_market_value_no_requirement(self) -> None:
        """Test with no market value requirement."""
        rule = EligibilityRule(require_market_value=False)
        assert rule.allows_market_value(Decimal("1000"))
        assert rule.allows_market_value(Decimal("0"))

    def test_allows_market_value_minimum(self) -> None:
        """Test minimum market value threshold."""
        rule = EligibilityRule(min_market_value=Decimal("500000"))
        assert rule.allows_market_value(Decimal("500000"))
        assert rule.allows_market_value(Decimal("1000000"))
        assert not rule.allows_market_value(Decimal("250000"))


class TestConfigurableEligibilityEngine:
    """Tests for ConfigurableEligibilityEngine."""

    def test_init_with_default_rule(self) -> None:
        """Initialize with default rule."""
        engine = ConfigurableEligibilityEngine()
        assert engine.rule is not None
        assert engine.reference_date == date.today()

    def test_init_with_custom_rule(self) -> None:
        """Initialize with custom rule."""
        custom_rule = EligibilityRule(
            description="Test rule",
            allowed_asset_types={"sovereign"},
        )
        engine = ConfigurableEligibilityEngine(rule=custom_rule)
        assert engine.rule.description == "Test rule"

    def test_init_with_custom_date(self) -> None:
        """Initialize with custom reference date."""
        ref_date = date(2025, 6, 30)
        engine = ConfigurableEligibilityEngine(reference_date=ref_date)
        assert engine.reference_date == ref_date

    def test_assess_valid_security(self, sample_data_dir: Path) -> None:
        """Assess eligible security."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        engine = ConfigurableEligibilityEngine(reference_date=date(2025, 6, 30))
        result = engine.assess(dataset=dataset)

        assert result.success
        decision = result.decisions["XS1111111111"]
        assert decision.eligible
        assert decision.reason_code == "ELIGIBLE"

    def test_assess_rating_below_threshold(self, sample_data_dir: Path) -> None:
        """Reject security with rating below threshold."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        rule = EligibilityRule(
            allowed_ratings={"AAA", "AA", "A", "BBB"},
            description="BBB minimum",
        )
        engine = ConfigurableEligibilityEngine(rule=rule, reference_date=date(2025, 6, 30))
        result = engine.assess(dataset=dataset)

        decision = result.decisions["XS3333333333"]
        assert not decision.eligible
        assert decision.reason_code == "RATING_BELOW_THRESHOLD"

    def test_assess_unsupported_asset_type(self, sample_data_dir: Path) -> None:
        """Reject security with unsupported asset type."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        rule = EligibilityRule(
            allowed_asset_types={"sovereign"},
            description="Sovereigns only",
        )
        engine = ConfigurableEligibilityEngine(rule=rule, reference_date=date(2025, 6, 30))
        result = engine.assess(dataset=dataset)

        decision = result.decisions["XS2222222222"]
        assert not decision.eligible
        assert decision.reason_code == "UNSUPPORTED_ASSET_TYPE"

    def test_assess_maturity_exceeds_limit(self, sample_data_dir: Path) -> None:
        """Reject security with maturity beyond limit."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        rule = EligibilityRule(
            max_maturity_years=5,
            description="Max 5y maturity",
        )
        engine = ConfigurableEligibilityEngine(rule=rule, reference_date=date(2025, 6, 30))
        result = engine.assess(dataset=dataset)

        decision = result.decisions["XS4444444444"]
        assert not decision.eligible
        assert decision.reason_code == "MATURITY_EXCEEDS_LIMIT"

    def test_assess_missing_market_value(self, sample_data_dir: Path) -> None:
        """Reject security with zero market value."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        dataset.securities["XS1111111111"].market_value = Decimal("0")

        rule = EligibilityRule(require_market_value=True)
        engine = ConfigurableEligibilityEngine(rule=rule)
        result = engine.assess(dataset=dataset)

        decision = result.decisions["XS1111111111"]
        assert not decision.eligible
        assert decision.reason_code == "MISSING_MARKET_VALUE"

    def test_assess_all_securities(self, sample_data_dir: Path) -> None:
        """Assess all securities in dataset."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        engine = ConfigurableEligibilityEngine(reference_date=date(2025, 6, 30))
        result = engine.assess(dataset=dataset)

        assert result.total_assessed == 4
        assert result.eligible_count > 0
        assert result.ineligible_count > 0
        assert result.eligible_count + result.ineligible_count == 4

    def test_decision_has_explanation(self, sample_data_dir: Path) -> None:
        """Verify decisions include explanations."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        rule = EligibilityRule(allowed_currencies={"EUR"})
        engine = ConfigurableEligibilityEngine(rule=rule)
        result = engine.assess(dataset=dataset)

        for decision in result.decisions.values():
            assert decision.explanation
            assert len(decision.explanation) > 0

    def test_decision_has_metadata(self, sample_data_dir: Path) -> None:
        """Verify decisions include metadata."""
        manager = DataManager(sample_data_dir)
        dataset = manager.load(validate=True)

        engine = ConfigurableEligibilityEngine(reference_date=date(2025, 6, 30))
        result = engine.assess(dataset=dataset)

        eligible_decision = result.decisions["XS1111111111"]
        assert eligible_decision.metadata
        assert "rating" in eligible_decision.metadata

    def test_empty_dataset_handling(self) -> None:
        """Test handling of empty dataset."""
        from collateral_analytics.loaders.data_manager import AnalyticsDataset

        empty_dataset = AnalyticsDataset(
            securities={},
            counterparties={},
            positions=[],
            haircuts=[],
        )

        engine = ConfigurableEligibilityEngine()
        result = engine.assess(dataset=empty_dataset)

        assert result.success
        assert result.total_assessed == 0
        assert result.eligible_count == 0
        assert result.ineligible_count == 0

    def test_missing_dataset_parameter(self) -> None:
        """Test handling of missing dataset parameter."""
        engine = ConfigurableEligibilityEngine()
        result = engine.assess()

        assert not result.success
        assert len(result.errors) > 0
