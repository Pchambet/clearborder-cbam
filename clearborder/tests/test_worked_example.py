"""The README's worked example agrees with a closed-form calculation."""

import pytest

from scripts import worked_example as we


def test_base_case_matches_hand_calculation():
    # 120 + 850 * 0.60 + 210 * 2.30 = 120 + 510 + 483 = 1113 kg CO2e for 1000 kg
    share_b = we.BASE_CASE_B_KG / we.COIL_KG
    assert we.estimated_emission_share(share_b) == pytest.approx(483 / 1113, abs=1e-4)


def test_breach_point_matches_closed_form():
    # estimated share = 2.3 * C * x / (120 + C * (0.6 + 1.7 x)) = 0.2 with C = 1060
    c = we.COIL_KG
    closed_form = (
        0.2
        * (we.DIRECT_EMISSIONS + c * we.SEE_SUPPLIER_A)
        / (c * (we.SEE_SUPPLIER_B - 0.2 * (we.SEE_SUPPLIER_B - we.SEE_SUPPLIER_A)))
    )
    assert we.breach_point() == pytest.approx(closed_form, abs=1e-3)
