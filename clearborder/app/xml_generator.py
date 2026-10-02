"""Quarterly CBAM report as XML.

The structure mirrors the content of a transitional-period quarterly report
(declarant, period, goods, CN code, quantity, specific embedded emissions,
country of origin) but it is a simplified, project-specific format under its own
namespace. It is *not* the official CBAM Registry XSD; when that schema is
placed in ``schemas/cbam_report.xsd``, ``validate_xml_against_xsd`` checks
documents against it.
"""

import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path
from xml.dom import minidom

NAMESPACE = "urn:clearborder:cbam-report:0.1"
REQUIRED_PRODUCT_FIELDS = (
    "CNCode",
    "ProductName",
    "Quantity",
    "SpecificEmbeddedEmissions",
    "CountryOfOrigin",
)


def create_cbam_report_xml(
    declarant_id: str,
    reporting_period: str,
    products: list[dict],
    installation_emissions: dict | None = None,
) -> str:
    """Build the report.

    ``reporting_period`` looks like "2026-Q1". Each product dict holds cn_code,
    product_name, quantity_kg, see_per_kg (kg CO2e/kg), country_of_origin (ISO
    alpha-2) and optionally installation_id.
    """
    root = ET.Element(
        "CBAMReport",
        attrib={"xmlns": NAMESPACE, "version": "0.1", "reportingPeriod": reporting_period},
    )

    meta = ET.SubElement(root, "ReportMetadata")
    ET.SubElement(meta, "DeclarantId").text = declarant_id
    ET.SubElement(meta, "ReportDate").text = datetime.now(UTC).strftime("%Y-%m-%d")
    ET.SubElement(meta, "ReportType").text = "Quarterly"

    products_elem = ET.SubElement(root, "ReportedProducts")
    for i, p in enumerate(products, start=1):
        product = ET.SubElement(products_elem, "Product", attrib={"id": str(i)})
        ET.SubElement(product, "CNCode").text = str(p.get("cn_code", ""))
        ET.SubElement(product, "ProductName").text = str(p.get("product_name", ""))
        ET.SubElement(product, "Quantity").text = str(p.get("quantity_kg", 0))
        ET.SubElement(product, "Unit").text = "kg"
        ET.SubElement(product, "SpecificEmbeddedEmissions").text = str(
            round(float(p.get("see_per_kg", 0)), 6)
        )
        ET.SubElement(product, "UnitEmissions").text = "kgCO2e/kg"
        ET.SubElement(product, "CountryOfOrigin").text = str(p.get("country_of_origin", ""))
        if p.get("installation_id"):
            ET.SubElement(product, "InstallationId").text = str(p["installation_id"])

    if installation_emissions:
        installations = ET.SubElement(root, "Installations")
        for inst_id, data in installation_emissions.items():
            inst = ET.SubElement(installations, "Installation", attrib={"id": inst_id})
            ET.SubElement(inst, "Country").text = data.get("country", "")
            ET.SubElement(inst, "Sector").text = data.get("sector", "")
            ET.SubElement(inst, "TotalEmissions").text = str(data.get("total_emissions", 0))

    xml_str = ET.tostring(root, encoding="unicode", method="xml")
    return minidom.parseString(xml_str).toprettyxml(indent="  ")


def _local_name(tag: str) -> str:
    """Tag name without its namespace."""
    return tag.split("}")[-1]


def _find_by_localname(parent: ET.Element, localname: str) -> ET.Element | None:
    """First descendant (or self) with this local name."""
    return next((e for e in parent.iter() if _local_name(e.tag) == localname), None)


def _findall_by_localname(parent: ET.Element, localname: str) -> list[ET.Element]:
    """All descendants (or self) with this local name."""
    return [e for e in parent.iter() if _local_name(e.tag) == localname]


def validate_xml_against_xsd(xml_content: str, xsd_path: str | None = None) -> tuple[bool, list[str]]:
    """Validate against an XSD; skipped (returns valid) when no schema file is present."""
    path = Path(xsd_path) if xsd_path else Path(__file__).parent.parent / "schemas" / "cbam_report.xsd"
    if not path.exists():
        return True, []

    from lxml import etree

    try:
        schema = etree.XMLSchema(etree.parse(str(path)))
    except etree.XMLSchemaParseError as e:
        return False, [f"Invalid XSD: {e}"]
    try:
        schema.assertValid(etree.fromstring(xml_content.encode("utf-8")))
    except etree.DocumentInvalid as e:
        return False, [str(err) for err in e.error_log]
    except etree.XMLSyntaxError as e:
        return False, [f"Malformed XML: {e}"]
    return True, []


def validate_xml_structure(xml_content: str) -> tuple[bool, list[str]]:
    """Check that the elements this format requires are present and non-empty."""
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        return False, [f"Malformed XML: {e}"]

    errors = []
    if _local_name(root.tag) != "CBAMReport":
        errors.append("Root element must be CBAMReport")

    meta = _find_by_localname(root, "ReportMetadata")
    if meta is None:
        errors.append("ReportMetadata is missing")
    else:
        for name in ("DeclarantId", "ReportDate", "ReportType"):
            if _find_by_localname(meta, name) is None:
                errors.append(f"ReportMetadata.{name} is missing")

    products = _find_by_localname(root, "ReportedProducts")
    if products is None:
        errors.append("ReportedProducts is missing")
    else:
        for i, product in enumerate(_findall_by_localname(products, "Product"), start=1):
            for name in REQUIRED_PRODUCT_FIELDS:
                elem = _find_by_localname(product, name)
                if elem is None or not (elem.text or "").strip():
                    errors.append(f"Product[{i}].{name} is missing or empty")

    return not errors, errors
