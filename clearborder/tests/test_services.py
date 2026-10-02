"""
Service-layer tests: persistence, report computation, classification.
"""

from decimal import Decimal

import pytest

from app.schemas import (
    CBAMReportRequest,
    InstallationCreate,
    PrecursorInput,
    ProductCreate,
    ProductReportItem,
)
from app.services import (
    calculate_cbam_report,
    calculate_product_see,
    classify_product,
    create_installation,
    create_product,
    get_installation,
    list_cn_codes,
    list_installations,
)


class TestInstallationServices:
    """Installations."""

    def test_create_and_get_installation(self, db_session):
        data = InstallationCreate(
            name="Steel mill TR",
            country_code="TR",
            sector="iron_steel",
            emissions_per_tonne=Decimal("1.65"),
        )
        inst = create_installation(db_session, data)
        assert inst.id is not None
        assert inst.name == "Steel mill TR"
        assert inst.country_code == "TR"

        fetched = get_installation(db_session, inst.id)
        assert fetched is not None
        assert fetched.id == inst.id

    def test_list_installations(self, db_session, sample_installation):
        items = list_installations(db_session)
        assert len(items) >= 1
        assert any(i.name == "Test steel mill TR" for i in items)


class TestProductServices:
    """Products."""

    def test_create_product_with_precursors(self, db_session, sample_installation):
        data = ProductCreate(
            name="Steel plate",
            cn_code="7208",
            sector="iron_steel",
            installation_id=sample_installation.id,
            activity_level=Decimal(1000),
            attributed_emissions=Decimal(50),
            precursors=[
                PrecursorInput(mass_kg=Decimal(1050), see_per_kg=Decimal("1.6"), is_real_data=True),
            ],
        )
        prod = create_product(db_session, data)
        assert prod.id is not None
        assert len(prod.precursors) == 1
        assert prod.precursors[0].mass_kg == Decimal(1050)

    def test_calculate_product_see(self, sample_product):
        result = calculate_product_see(sample_product)
        assert "see_per_kg" in result
        assert result["see_per_kg"] > 0
        assert "rule_80_20_compliant" in result


class TestCbamReportService:
    """calculate_cbam_report."""

    def test_calculate_cbam_report(self, db_session, sample_product):
        request = CBAMReportRequest(
            declarant_id="EU-TEST",
            reporting_period="2026-Q1",
            products=[ProductReportItem(product_id=sample_product.id, quantity_tonnes=Decimal(10))],
        )
        response = calculate_cbam_report(db_session, request)
        assert response.compliant is not None
        assert len(response.results) == 1
        assert response.results[0].product_id == sample_product.id
        assert response.results[0].see_kg_co2_per_tonne > 0
        assert "CBAMReport" in response.xml_content

    def test_calculate_cbam_report_product_not_found(self, db_session):
        request = CBAMReportRequest(
            declarant_id="EU",
            reporting_period="2026-Q1",
            products=[ProductReportItem(product_id=99999, quantity_tonnes=Decimal(1))],
        )
        with pytest.raises(ValueError, match="not found"):
            calculate_cbam_report(db_session, request)


class TestListCnCodes:
    """list_cn_codes."""

    def test_list_empty(self, db_session):
        codes = list_cn_codes(db_session)
        assert isinstance(codes, list)

    def test_list_with_data(self, db_session, sample_cn_codes):
        codes = list_cn_codes(db_session)
        assert len(codes) >= 3
        assert any(c["code"] == "7208" for c in codes)


class TestClassifyProduct:
    """classify_product."""

    def test_classify_returns_suggestions(self, db_session, sample_cn_codes):
        result = classify_product(db_session, "Hot-rolled steel plate", top_k=3)
        assert "suggestions" in result
        assert len(result["suggestions"]) >= 1
        for s in result["suggestions"]:
            assert "code" in s
            assert "confidence" in s
