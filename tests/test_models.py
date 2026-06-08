"""Tests for domain models."""

from datetime import date
from decimal import Decimal

import pytest

from collateral_analytics.models import (
    CollateralPosition,
    Counterparty,
    HaircutSchedule,
    Security,
)


class TestSecurity:
    """Tests for Security model."""

    def test_valid_security(self) -> None:
        """Create a valid security."""
        s = Security(
            isin="XS1234567890",
            name="Example Bond",
            asset_type="corporate_bond",
            issuer="Example Corp",
            issuer_type="corporate",
            country="DE",
            currency="EUR",
            rating="BBB",
            maturity_date=date(2030, 12, 31),
            market_value=Decimal("1000000.00"),
        )
        assert s.isin == "XS1234567890"
        assert s.market_value == Decimal("1000000.00")

    def test_invalid_isin_length(self) -> None:
        """ISIN must be exactly 12 characters."""
        with pytest.raises(ValueError, match="ISIN must be 12 characters"):
            Security(
                isin="SHORT",
                name="Example Bond",
                asset_type="corporate_bond",
                issuer="Example Corp",
                issuer_type="corporate",
                country="DE",
                currency="EUR",
                rating="BBB",
                maturity_date=date(2030, 12, 31),
                market_value=Decimal("1000000.00"),
            )

    def test_invalid_isin_format(self) -> None:
        """ISIN must have 2 letters followed by 10 digits."""
        with pytest.raises(ValueError, match="ISIN must end with 10 digits"):
            Security(
                isin="XS123456789A",
                name="Example Bond",
                asset_type="corporate_bond",
                issuer="Example Corp",
                issuer_type="corporate",
                country="DE",
                currency="EUR",
                rating="BBB",
                maturity_date=date(2030, 12, 31),
                market_value=Decimal("1000000.00"),
            )

    def test_invalid_currency(self) -> None:
        """Only EUR currency is supported."""
        with pytest.raises(ValueError, match="Only EUR currency supported"):
            Security(
                isin="XS1234567890",
                name="Example Bond",
                asset_type="corporate_bond",
                issuer="Example Corp",
                issuer_type="corporate",
                country="DE",
                currency="USD",
                rating="BBB",
                maturity_date=date(2030, 12, 31),
                market_value=Decimal("1000000.00"),
            )

    def test_invalid_rating(self) -> None:
        """Rating must be valid."""
        with pytest.raises(ValueError, match="Invalid rating"):
            Security(
                isin="XS1234567890",
                name="Example Bond",
                asset_type="corporate_bond",
                issuer="Example Corp",
                issuer_type="corporate",
                country="DE",
                currency="EUR",
                rating="INVALID",
                maturity_date=date(2030, 12, 31),
                market_value=Decimal("1000000.00"),
            )

    def test_maturity_bucket_0_1y(self) -> None:
        """Test 0-1y maturity bucket."""
        s = Security(
            isin="XS1234567890",
            name="Short Bond",
            asset_type="corporate_bond",
            issuer="Example Corp",
            issuer_type="corporate",
            country="DE",
            currency="EUR",
            rating="BBB",
            maturity_date=date(2025, 6, 1),
            market_value=Decimal("1000000.00"),
        )
        ref_date = date(2025, 6, 2)
        assert s.maturity_bucket(ref_date) == "0-1y"

    def test_maturity_bucket_10y_plus(self) -> None:
        """Test 10y+ maturity bucket."""
        s = Security(
            isin="XS1234567890",
            name="Long Bond",
            asset_type="government_bond",
            issuer="Germany",
            issuer_type="sovereign",
            country="DE",
            currency="EUR",
            rating="AAA",
            maturity_date=date(2050, 12, 31),
            market_value=Decimal("1000000.00"),
        )
        ref_date = date(2025, 6, 1)
        assert s.maturity_bucket(ref_date) == "10y+"

    def test_rating_bucket_aaa_aa(self) -> None:
        """Test AAA-AA rating bucket."""
        s = Security(
            isin="XS1234567890",
            name="High Grade Bond",
            asset_type="sovereign",
            issuer="Germany",
            issuer_type="sovereign",
            country="DE",
            currency="EUR",
            rating="AA+",
            maturity_date=date(2030, 12, 31),
            market_value=Decimal("1000000.00"),
        )
        assert s.rating_bucket() == "AAA-AA"

    def test_rating_bucket_nr(self) -> None:
        """Test NR (not rated) rating bucket."""
        s = Security(
            isin="XS1234567890",
            name="Unrated Security",
            asset_type="equity",
            issuer="Example Corp",
            issuer_type="corporate",
            country="DE",
            currency="EUR",
            rating="NR",
            maturity_date=date(2030, 12, 31),
            market_value=Decimal("1000000.00"),
        )
        assert s.rating_bucket() == "NR"

    def test_negative_market_value(self) -> None:
        """Market value must be non-negative."""
        with pytest.raises(ValueError):
            Security(
                isin="XS1234567890",
                name="Example Bond",
                asset_type="corporate_bond",
                issuer="Example Corp",
                issuer_type="corporate",
                country="DE",
                currency="EUR",
                rating="BBB",
                maturity_date=date(2030, 12, 31),
                market_value=Decimal("-1000.00"),
            )


class TestCounterparty:
    """Tests for Counterparty model."""

    def test_valid_counterparty(self) -> None:
        """Create a valid counterparty."""
        cp = Counterparty(
            counterparty_id="CP001",
            name="Example Bank",
            country="DE",
            rating="A",
            exposure=Decimal("5000000.00"),
            exposure_limit=Decimal("10000000.00"),
        )
        assert cp.counterparty_id == "CP001"
        assert cp.utilisation() == Decimal("0.5")

    def test_utilisation_calculation(self) -> None:
        """Test utilisation ratio calculation."""
        cp = Counterparty(
            counterparty_id="CP001",
            name="Example Bank",
            country="DE",
            rating="A",
            exposure=Decimal("7500000.00"),
            exposure_limit=Decimal("10000000.00"),
        )
        assert cp.utilisation() == Decimal("0.75")

    def test_available_capacity(self) -> None:
        """Test available capacity calculation."""
        cp = Counterparty(
            counterparty_id="CP001",
            name="Example Bank",
            country="DE",
            rating="A",
            exposure=Decimal("3000000.00"),
            exposure_limit=Decimal("10000000.00"),
        )
        assert cp.available_capacity() == Decimal("7000000.00")

    def test_is_at_limit(self) -> None:
        """Test is_at_limit check."""
        cp_over = Counterparty(
            counterparty_id="CP001",
            name="Example Bank",
            country="DE",
            rating="A",
            exposure=Decimal("11000000.00"),
            exposure_limit=Decimal("10000000.00"),
        )
        assert cp_over.is_at_limit() is True

        cp_under = Counterparty(
            counterparty_id="CP002",
            name="Another Bank",
            country="FR",
            rating="BBB",
            exposure=Decimal("5000000.00"),
            exposure_limit=Decimal("10000000.00"),
        )
        assert cp_under.is_at_limit() is False

    def test_invalid_exposure_limit(self) -> None:
        """Exposure limit must be positive."""
        with pytest.raises(ValueError, match="exposure_limit must be positive"):
            Counterparty(
                counterparty_id="CP001",
                name="Example Bank",
                country="DE",
                rating="A",
                exposure=Decimal("5000000.00"),
                exposure_limit=Decimal("0.00"),
            )

    def test_invalid_country(self) -> None:
        """Country must be 2-letter ISO code."""
        with pytest.raises(ValueError, match="2-letter ISO 3166 code"):
            Counterparty(
                counterparty_id="CP001",
                name="Example Bank",
                country="INVALID",
                rating="A",
                exposure=Decimal("5000000.00"),
                exposure_limit=Decimal("10000000.00"),
            )


class TestCollateralPosition:
    """Tests for CollateralPosition model."""

    def test_valid_position(self) -> None:
        """Create a valid collateral position."""
        pos = CollateralPosition(
            counterparty_id="CP001",
            isin="XS1234567890",
            quantity=Decimal("1000.000000"),
            market_value=Decimal("1000000.00"),
        )
        assert pos.counterparty_id == "CP001"
        assert pos.isin == "XS1234567890"

    def test_position_value_per_unit(self) -> None:
        """Test per-unit value calculation."""
        pos = CollateralPosition(
            counterparty_id="CP001",
            isin="XS1234567890",
            quantity=Decimal("1000.000000"),
            market_value=Decimal("1000000.00"),
        )
        assert pos.position_value_per_unit() == Decimal("1000.00")

    def test_invalid_isin(self) -> None:
        """ISIN must be valid."""
        with pytest.raises(ValueError, match="ISIN must be 12 characters"):
            CollateralPosition(
                counterparty_id="CP001",
                isin="INVALID",
                quantity=Decimal("1000.000000"),
                market_value=Decimal("1000000.00"),
            )

    def test_zero_quantity(self) -> None:
        """Quantity must be positive."""
        with pytest.raises(ValueError):
            CollateralPosition(
                counterparty_id="CP001",
                isin="XS1234567890",
                quantity=Decimal("0.000000"),
                market_value=Decimal("1000000.00"),
            )


class TestHaircutSchedule:
    """Tests for HaircutSchedule model."""

    def test_valid_haircut(self) -> None:
        """Create a valid haircut schedule entry."""
        hc = HaircutSchedule(
            asset_type="sovereign",
            maturity_bucket="0-1y",
            rating_bucket="AAA-AA",
            haircut_rate=Decimal("0.0050"),
        )
        assert hc.haircut_rate == Decimal("0.0050")

    def test_invalid_asset_type(self) -> None:
        """Asset type must be valid."""
        with pytest.raises(ValueError, match="Invalid asset_type"):
            HaircutSchedule(
                asset_type="invalid_type",
                maturity_bucket="0-1y",
                rating_bucket="AAA-AA",
                haircut_rate=Decimal("0.0050"),
            )

    def test_invalid_maturity_bucket(self) -> None:
        """Maturity bucket must be valid."""
        with pytest.raises(ValueError, match="Invalid maturity_bucket"):
            HaircutSchedule(
                asset_type="sovereign",
                maturity_bucket="invalid_bucket",
                rating_bucket="AAA-AA",
                haircut_rate=Decimal("0.0050"),
            )

    def test_invalid_rating_bucket(self) -> None:
        """Rating bucket must be valid."""
        with pytest.raises(ValueError, match="Invalid rating_bucket"):
            HaircutSchedule(
                asset_type="sovereign",
                maturity_bucket="0-1y",
                rating_bucket="INVALID",
                haircut_rate=Decimal("0.0050"),
            )

    def test_haircut_rate_out_of_range(self) -> None:
        """Haircut rate must be between 0 and 1."""
        with pytest.raises(ValueError):
            HaircutSchedule(
                asset_type="sovereign",
                maturity_bucket="0-1y",
                rating_bucket="AAA-AA",
                haircut_rate=Decimal("1.5000"),
            )
