"""Tests for the quarterly report XML: structure and validation."""

import xml.etree.ElementTree as ET

from app.xml_generator import (
    NAMESPACE,
    _find_by_localname,
    _findall_by_localname,
    create_cbam_report_xml,
    validate_xml_against_xsd,
    validate_xml_structure,
)

STEEL = {
    "cn_code": "7208",
    "product_name": "Hot-rolled steel plate",
    "quantity_kg": 5000,
    "see_per_kg": 1.65,
    "country_of_origin": "TR",
}


class TestCreateCbamReportXml:
    def test_root_namespace_and_period(self):
        root = ET.fromstring(create_cbam_report_xml("EU-12345", "2026-Q1", [STEEL]))
        assert root.tag == f"{{{NAMESPACE}}}CBAMReport"
        assert root.get("reportingPeriod") == "2026-Q1"

    def test_report_metadata(self):
        root = ET.fromstring(create_cbam_report_xml("EU-999", "2026-Q2", []))
        meta = _find_by_localname(root, "ReportMetadata")
        assert _find_by_localname(meta, "DeclarantId").text == "EU-999"
        assert _find_by_localname(meta, "ReportType").text == "Quarterly"

    def test_product_values_are_written(self):
        root = ET.fromstring(create_cbam_report_xml("EU-1", "2026-Q1", [STEEL]))
        product = _findall_by_localname(root, "Product")[0]
        assert _find_by_localname(product, "Quantity").text == "5000"
        assert _find_by_localname(product, "SpecificEmbeddedEmissions").text == "1.65"
        assert _find_by_localname(product, "CountryOfOrigin").text == "TR"

    def test_multiple_products(self):
        aluminium = {**STEEL, "cn_code": "7606", "see_per_kg": 8.0, "country_of_origin": "CN"}
        root = ET.fromstring(create_cbam_report_xml("EU-1", "2026-Q1", [STEEL, aluminium]))
        products = _findall_by_localname(_find_by_localname(root, "ReportedProducts"), "Product")
        assert [p.get("id") for p in products] == ["1", "2"]

    def test_installation_emissions_section(self):
        xml = create_cbam_report_xml(
            "EU-1",
            "2026-Q1",
            [],
            installation_emissions={
                "INST-001": {"country": "TR", "sector": "iron_steel", "total_emissions": 15000},
            },
        )
        assert _find_by_localname(ET.fromstring(xml), "Installations") is not None


class TestValidateXmlStructure:
    def test_generated_report_is_valid(self):
        assert validate_xml_structure(create_cbam_report_xml("EU-1", "2026-Q1", [STEEL])) == (
            True,
            [],
        )

    def test_missing_required_field_is_reported(self):
        incomplete = {**STEEL, "country_of_origin": ""}
        valid, errors = validate_xml_structure(create_cbam_report_xml("EU-1", "2026-Q1", [incomplete]))
        assert valid is False
        assert errors == ["Product[1].CountryOfOrigin is missing or empty"]

    def test_invalid_root_fails(self):
        valid, errors = validate_xml_structure('<?xml version="1.0"?><WrongRoot></WrongRoot>')
        assert valid is False
        assert any("CBAMReport" in e for e in errors)

    def test_malformed_xml_fails(self):
        valid, errors = validate_xml_structure("<not valid xml")
        assert valid is False
        assert errors[0].startswith("Malformed XML")


class TestValidateXmlAgainstXsd:
    def test_skipped_without_schema(self, tmp_path):
        assert validate_xml_against_xsd("<a/>", str(tmp_path / "missing.xsd")) == (True, [])

    def test_document_checked_against_schema(self, tmp_path):
        xsd = tmp_path / "schema.xsd"
        xsd.write_text(
            '<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">'
            '<xs:element name="a" type="xs:integer"/></xs:schema>'
        )
        assert validate_xml_against_xsd("<a>3</a>", str(xsd)) == (True, [])
        valid, errors = validate_xml_against_xsd("<a>x</a>", str(xsd))
        assert valid is False
        assert errors

    def test_broken_schema_is_reported(self, tmp_path):
        xsd = tmp_path / "broken.xsd"
        xsd.write_text("<xs:schema")
        valid, errors = validate_xml_against_xsd("<a/>", str(xsd))
        assert valid is False
        assert errors[0].startswith("Invalid XSD")
