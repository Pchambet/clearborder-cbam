"""Unit tests for the CBAM engine: SEE arithmetic, cap on estimates, nested BOMs.

Every expected value is computed by hand in the comment next to it.
"""

import pytest

from app.cbam_engine import (
    PrecursorData,
    ProductEmissionData,
    calculate_ee_inp_mat,
    calculate_see,
    calculate_see_recursive,
    validate_80_20_rule,
)


class TestCalculateEeInpMat:
    """EE_InpMat = sum(M_i * SEE_i), split by data quality."""

    def test_empty_precursors(self):
        assert calculate_ee_inp_mat([]) == (0.0, 0.0, 0.0)

    def test_single_precursor_real(self):
        precursors = [PrecursorData(mass_kg=100, see_per_kg=1.5, is_real_data=True)]
        assert calculate_ee_inp_mat(precursors) == (150.0, 150.0, 0.0)

    def test_multiple_precursors_mixed(self):
        precursors = [
            PrecursorData(mass_kg=500, see_per_kg=1.6, is_real_data=True),
            PrecursorData(mass_kg=200, see_per_kg=2.0, is_real_data=False),
        ]
        total, actual, estimated = calculate_ee_inp_mat(precursors)
        assert total == pytest.approx(1200.0)  # 500*1.6 + 200*2.0
        assert actual == pytest.approx(800.0)
        assert estimated == pytest.approx(400.0)


class TestValidate8020Rule:
    """At least 80 % of embedded emissions must come from actual data."""

    def test_zero_emissions_is_compliant(self):
        assert validate_80_20_rule(0, 0) == (True, 1.0)

    def test_100_percent_actual(self):
        assert validate_80_20_rule(100, 100) == (True, 1.0)

    def test_exactly_80_percent_is_compliant(self):
        assert validate_80_20_rule(80, 100) == (True, 0.8)

    def test_79_percent_is_not(self):
        assert validate_80_20_rule(79, 100) == (False, 0.79)


class TestCalculateSee:
    """SEE_g = (AttrEm_g + EE_InpMat) / AL_g."""

    def test_simple_good_no_precursors(self):
        result = calculate_see(ProductEmissionData(attr_em=100, activity_level=1000))
        assert result["see_per_kg"] == pytest.approx(0.1)
        assert result["ee_inp_mat"] == 0
        assert result["rule_80_20_compliant"] is True
        assert result["warnings"] == []

    def test_good_with_precursor(self):
        data = ProductEmissionData(
            attr_em=50,
            activity_level=1000,
            precursors=[PrecursorData(mass_kg=1050, see_per_kg=1.6, is_real_data=True)],
        )
        result = calculate_see(data)
        # EE_InpMat = 1050 * 1.6 = 1680; (50 + 1680) / 1000 = 1.73
        assert result["see_per_kg"] == pytest.approx(1.73)
        assert result["ee_inp_mat"] == pytest.approx(1680.0)
        assert result["total_emissions_kg_co2e"] == pytest.approx(1730.0)
        assert result["rule_80_20_compliant"] is True

    def test_activity_level_zero_raises(self):
        with pytest.raises(ValueError, match="strictly positive"):
            calculate_see(ProductEmissionData(attr_em=100, activity_level=0))

    def test_violation_produces_warning(self):
        data = ProductEmissionData(
            attr_em=0,
            activity_level=1000,
            precursors=[
                PrecursorData(mass_kg=200, see_per_kg=1.0, is_real_data=True),
                PrecursorData(mass_kg=800, see_per_kg=1.5, is_real_data=False),
            ],
        )
        result = calculate_see(data)
        # actual 200 / total (200 + 1200) = 0.142857
        assert result["rule_80_20_compliant"] is False
        assert result["real_data_ratio"] == pytest.approx(0.1429)
        assert "80/20" in result["warnings"][0]

    def test_cap_is_on_emissions_not_mass(self):
        """A light precursor with a high default SEE breaches the cap on its own."""
        data = ProductEmissionData(
            attr_em=0,
            activity_level=1000,
            precursors=[
                PrecursorData(mass_kg=900, see_per_kg=0.1, is_real_data=True),
                PrecursorData(mass_kg=100, see_per_kg=10.0, is_real_data=False),
            ],
        )
        result = calculate_see(data)
        # by mass 90 % actual (would pass); by emissions 90 / (90 + 1000) = 8.3 % (fails)
        assert result["real_data_ratio"] == pytest.approx(0.0826, abs=1e-4)
        assert result["rule_80_20_compliant"] is False

    def test_heavy_low_carbon_estimate_can_pass(self):
        """Conversely, a heavy estimated precursor with a tiny SEE stays under the cap."""
        data = ProductEmissionData(
            attr_em=0,
            activity_level=1000,
            precursors=[
                PrecursorData(mass_kg=100, see_per_kg=10.0, is_real_data=True),
                PrecursorData(mass_kg=900, see_per_kg=0.01, is_real_data=False),
            ],
        )
        result = calculate_see(data)
        # by mass 10 % actual (would fail); by emissions 1000 / 1009 = 99.1 % (passes)
        assert result["real_data_ratio"] == pytest.approx(0.9911, abs=1e-4)
        assert result["rule_80_20_compliant"] is True

    def test_direct_emissions_count_as_actual_data(self):
        data = ProductEmissionData(
            attr_em=900,
            activity_level=1000,
            precursors=[PrecursorData(mass_kg=100, see_per_kg=1.0, is_real_data=False)],
        )
        result = calculate_see(data)
        # actual 900 / total 1000 = 0.9
        assert result["real_data_ratio"] == pytest.approx(0.9)
        assert result["rule_80_20_compliant"] is True


class TestCalculateSeeRecursive:
    """Nested bills of materials."""

    def test_flat_bom(self):
        bom = {
            "attr_em": 50,
            "activity_level": 1000,
            "precursors": [{"mass_kg": 1050, "see_per_kg": 1.6, "is_real_data": True}],
        }
        assert calculate_see_recursive(bom)["see_per_kg"] == pytest.approx(1.73)

    def test_nested_bom(self):
        bom = {
            "attr_em": 0,
            "activity_level": 100,
            "precursors": [
                {
                    "mass_kg": 100,
                    "see_per_kg": None,
                    "is_real_data": True,
                    "nested_bom": {"attr_em": 10, "activity_level": 100, "precursors": []},
                },
            ],
        }
        # nested SEE = 10/100 = 0.1; EE_InpMat = 100*0.1 = 10; SEE = 10/100 = 0.1
        assert calculate_see_recursive(bom)["see_per_kg"] == pytest.approx(0.1)

    def test_precursor_without_see_or_bom_raises(self):
        """Missing data must fail loudly, not be dropped from embedded emissions."""
        bom = {
            "attr_em": 20,
            "activity_level": 10,
            "precursors": [{"mass_kg": 5, "see_per_kg": None, "is_real_data": False}],
        }
        with pytest.raises(ValueError, match="neither see_per_kg nor nested_bom"):
            calculate_see_recursive(bom)
