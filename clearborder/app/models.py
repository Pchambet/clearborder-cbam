"""SQLAlchemy models."""

from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from .database import Base


def _now() -> datetime:
    """Naive UTC timestamp (the columns are timezone-naive)."""
    return datetime.now(UTC).replace(tzinfo=None)


class CNCode(Base):
    """EU Combined Nomenclature (CN) customs codes."""

    __tablename__ = "cn_codes"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(10), unique=True, index=True, nullable=False)
    description = Column(Text)
    level = Column(Integer)
    parent_code = Column(String(10), nullable=True)
    created_at = Column(DateTime, default=_now)


class Installation(Base):
    """Production installation of a non-EU producer."""

    __tablename__ = "installations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    country_code = Column(String(2), nullable=False)
    sector = Column(String(50), nullable=False)
    emissions_per_tonne = Column(Numeric(12, 4), nullable=True)  # tCO2e/tonne
    o3ci_id = Column(String(50), nullable=True)  # operator ID in the CBAM registry (O3CI)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    products = relationship("Product", back_populates="installation")


class Product(Base):
    """Imported good covered by CBAM."""

    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    cn_code = Column(String(10), nullable=False)
    sector = Column(String(50), nullable=False)
    installation_id = Column(Integer, ForeignKey("installations.id"), nullable=False)
    activity_level = Column(Numeric(12, 4), nullable=False)  # kg
    attributed_emissions = Column(Numeric(12, 4), default=0)  # kg CO2e
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    installation = relationship("Installation", back_populates="products")
    precursors = relationship("ProductPrecursor", back_populates="product", cascade="all, delete-orphan")


class ProductPrecursor(Base):
    """Precursor line of a complex good's bill of materials."""

    __tablename__ = "product_precursors"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    mass_kg = Column(Numeric(12, 4), nullable=False)
    see_per_kg = Column(Numeric(12, 6), nullable=False)  # kg CO2e/kg
    is_real_data = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_now)

    product = relationship("Product", back_populates="precursors")


class DefaultEmissionFactor(Base):
    """Default emission factor by sector and country (reference data, not used by the engine yet)."""

    __tablename__ = "default_emission_factors"

    id = Column(Integer, primary_key=True, index=True)
    sector = Column(String(50), nullable=False)
    country_code = Column(String(2), nullable=False)
    emission_factor_kg_co2_per_tonne = Column(Numeric(12, 4), nullable=False)
    source = Column(String(100))
    created_at = Column(DateTime, default=_now)


class CBAMReport(Base):
    """Generated report (history table, not written to yet)."""

    __tablename__ = "cbam_reports"

    id = Column(Integer, primary_key=True, index=True)
    report_period = Column(String(10), nullable=False)
    declarant_id = Column(String(100), nullable=False)
    xml_content = Column(Text)
    created_at = Column(DateTime, default=_now)
