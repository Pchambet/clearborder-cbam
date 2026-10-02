"""Service layer: glue between the API, the database and the pure CBAM engine."""

from sqlalchemy.orm import Session

from .cbam_engine import PrecursorData, ProductEmissionData, calculate_see
from .classifier import classify as ml_classify
from .models import CNCode, Installation, Product, ProductPrecursor
from .schemas import (
    CBAMProductResult,
    CBAMReportRequest,
    CBAMReportResponse,
    InstallationCreate,
    ProductCreate,
)
from .xml_generator import create_cbam_report_xml


def create_installation(db: Session, data: InstallationCreate) -> Installation:
    inst = Installation(
        name=data.name,
        country_code=data.country_code.upper(),
        sector=data.sector,
        emissions_per_tonne=data.emissions_per_tonne,
        o3ci_id=data.o3ci_id,
    )
    db.add(inst)
    db.commit()
    db.refresh(inst)
    return inst


def get_installation(db: Session, inst_id: int) -> Installation | None:
    return db.get(Installation, inst_id)


def list_installations(db: Session, skip: int = 0, limit: int = 100) -> list[Installation]:
    return db.query(Installation).offset(skip).limit(limit).all()


def create_product(db: Session, data: ProductCreate) -> Product:
    """Create a product and its precursors in one transaction."""
    product = Product(
        name=data.name,
        cn_code=data.cn_code,
        sector=data.sector,
        installation_id=data.installation_id,
        activity_level=data.activity_level,
        attributed_emissions=data.attributed_emissions,
        precursors=[
            ProductPrecursor(mass_kg=p.mass_kg, see_per_kg=p.see_per_kg, is_real_data=p.is_real_data)
            for p in data.precursors or []
        ],
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def get_product(db: Session, product_id: int) -> Product | None:
    return db.get(Product, product_id)


def list_products(db: Session, skip: int = 0, limit: int = 100) -> list[Product]:
    return db.query(Product).offset(skip).limit(limit).all()


def _product_to_emission_data(product: Product) -> ProductEmissionData:
    """Convert the ORM row (Decimal columns) into engine inputs (floats)."""
    return ProductEmissionData(
        attr_em=float(product.attributed_emissions or 0),
        activity_level=float(product.activity_level),
        precursors=[
            PrecursorData(
                mass_kg=float(p.mass_kg),
                see_per_kg=float(p.see_per_kg),
                is_real_data=p.is_real_data,
            )
            for p in product.precursors
        ],
    )


def calculate_product_see(product: Product) -> dict:
    return calculate_see(_product_to_emission_data(product))


def calculate_cbam_report(db: Session, request: CBAMReportRequest) -> CBAMReportResponse:
    """Compute SEE for each requested product and build the quarterly report XML.

    Raises ValueError when a product id does not exist (mapped to HTTP 400).
    """
    results = []
    xml_products = []
    for item in request.products:
        product = get_product(db, item.product_id)
        if product is None:
            raise ValueError(f"Product {item.product_id} not found")

        see = calculate_product_see(product)
        installation = get_installation(db, product.installation_id)
        results.append(
            CBAMProductResult(
                product_id=product.id,
                cn_code=product.cn_code,
                description=product.name,
                see_kg_co2_per_tonne=see["see_per_kg"] * 1000,
                real_data_ratio=see["real_data_ratio"],
                compliant_80_20=see["rule_80_20_compliant"],
                quantity_tonnes=item.quantity_tonnes,
            )
        )
        xml_products.append(
            {
                "cn_code": product.cn_code,
                "product_name": product.name,
                "quantity_kg": float(item.quantity_tonnes * 1000),
                "see_per_kg": see["see_per_kg"],
                "country_of_origin": installation.country_code if installation else "",
            }
        )

    return CBAMReportResponse(
        results=results,
        xml_content=create_cbam_report_xml(
            declarant_id=request.declarant_id,
            reporting_period=request.reporting_period,
            products=xml_products,
        ),
        compliant=all(r.compliant_80_20 for r in results),
    )


def list_cn_codes(db: Session, skip: int = 0, limit: int = 100) -> list[dict]:
    rows = db.query(CNCode).offset(skip).limit(limit).all()
    return [{"id": r.id, "code": r.code, "description": r.description, "level": r.level} for r in rows]


def classify_product(db: Session, description: str, top_k: int = 3) -> dict:
    """Suggest CN codes and attach the nomenclature description when it is known."""
    suggestions = ml_classify(description, top_k=top_k)
    for s in suggestions:
        cn = db.query(CNCode).filter(CNCode.code == s["code"]).first()
        s["description"] = cn.description if cn else ""
    return {"suggestions": suggestions}
