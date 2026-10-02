#!/usr/bin/env python3
"""Load demo data: illustrative default factors, one installation, one product, CN codes.

All values are illustrative and chosen for readability; they are not the
default values published by the European Commission.
"""

import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal, init_db
from app.models import DefaultEmissionFactor, Installation, Product, ProductPrecursor
from scripts.load_cn_codes import load_cn_codes

# (sector, country, kg CO2e per tonne of product) - illustrative
DEFAULT_FACTORS = [
    ("iron_steel", "TR", 1800),
    ("iron_steel", "CN", 2200),
    ("iron_steel", "IN", 2500),
    ("aluminium", "TR", 8000),
    ("aluminium", "CN", 12000),
    ("cement", "TR", 650),
    ("cement", "CN", 850),
]


def seed() -> None:
    init_db()
    db = SessionLocal()
    try:
        for sector, country, factor in DEFAULT_FACTORS:
            exists = (
                db.query(DefaultEmissionFactor)
                .filter(DefaultEmissionFactor.sector == sector, DefaultEmissionFactor.country_code == country)
                .first()
            )
            if exists is None:
                db.add(
                    DefaultEmissionFactor(
                        sector=sector,
                        country_code=country,
                        emission_factor_kg_co2_per_tonne=Decimal(factor),
                        source="illustrative",
                    )
                )
        db.commit()

        inst = db.query(Installation).filter(Installation.name == "Demo steel mill").first()
        if inst is None:
            inst = Installation(
                name="Demo steel mill",
                country_code="TR",
                sector="iron_steel",
                emissions_per_tonne=Decimal("1.65"),  # t CO2e per t
            )
            db.add(inst)
            db.commit()
            db.refresh(inst)
            print(f"Created installation: {inst.name} (id={inst.id})")

        if db.query(Product).filter(Product.cn_code == "7208").first() is None:
            # 1 t of hot-rolled plate from 1.05 t of slab: SEE = (50 + 1050 * 1.6) / 1000 = 1.73
            prod = Product(
                name="Hot-rolled steel plate",
                cn_code="7208",
                sector="iron_steel",
                installation_id=inst.id,
                activity_level=Decimal(1000),  # kg
                attributed_emissions=Decimal(50),  # kg CO2e
                precursors=[
                    ProductPrecursor(mass_kg=Decimal(1050), see_per_kg=Decimal("1.6"), is_real_data=True)
                ],
            )
            db.add(prod)
            db.commit()
            print(f"Created product: {prod.name} (id={prod.id})")
    finally:
        db.close()

    load_cn_codes()
    print("Seed completed.")


if __name__ == "__main__":
    seed()
