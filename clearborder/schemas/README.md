# XSD schemas

Place an XSD here as `cbam_report.xsd` to have `app.xml_generator.validate_xml_against_xsd`
check generated reports against it. Without it, only the structural check
(`validate_xml_structure`) runs.

The XML produced by this prototype uses its own namespace and is not the official CBAM
Registry format, so the official schema would reject it. Mapping to that schema is listed
under limitations in the main README.
