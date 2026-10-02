"""HTTP routes (all under /api/v1)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from . import services
from .auth import get_api_key
from .database import get_db
from .schemas import (
    CBAMReportRequest,
    CBAMReportResponse,
    ClassifyRequest,
    InstallationCreate,
    InstallationResponse,
    ProductCreate,
    ProductResponse,
)

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]
ApiKey = Annotated[str | None, Depends(get_api_key)]


# --- Installations ---
@router.post("/installations", response_model=InstallationResponse)
def create_installation(
    data: InstallationCreate,
    db: DbSession,
    _api_key: ApiKey,
):
    return services.create_installation(db, data)


@router.get("/installations", response_model=list[InstallationResponse])
def list_installations(
    db: DbSession,
    _api_key: ApiKey,
    skip: int = 0,
    limit: int = 100,
):
    return services.list_installations(db, skip=skip, limit=limit)


@router.get("/installations/{installation_id}", response_model=InstallationResponse)
def get_installation(
    installation_id: int,
    db: DbSession,
    _api_key: ApiKey,
):
    inst = services.get_installation(db, installation_id)
    if not inst:
        raise HTTPException(status_code=404, detail="Installation not found")
    return inst


# --- Products ---
@router.post("/products", response_model=ProductResponse)
def create_product(
    data: ProductCreate,
    db: DbSession,
    _api_key: ApiKey,
):
    return services.create_product(db, data)


@router.get("/products", response_model=list[ProductResponse])
def list_products(
    db: DbSession,
    _api_key: ApiKey,
    skip: int = 0,
    limit: int = 100,
):
    return services.list_products(db, skip=skip, limit=limit)


@router.get("/products/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: int,
    db: DbSession,
    _api_key: ApiKey,
):
    product = services.get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


# --- CBAM Report ---
@router.post("/generate-cbam-report", response_model=CBAMReportResponse)
def generate_cbam_report(
    request: CBAMReportRequest,
    db: DbSession,
    _api_key: ApiKey,
):
    try:
        return services.calculate_cbam_report(db, request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# --- CN classification ---
@router.get("/cn-codes")
def list_cn_codes(
    db: DbSession,
    _api_key: ApiKey,
    skip: int = 0,
    limit: int = 100,
):
    """List CN codes loaded from the sample nomenclature."""
    return services.list_cn_codes(db, skip=skip, limit=limit)


@router.post("/classify")
def classify_product(
    data: ClassifyRequest,
    db: DbSession,
    _api_key: ApiKey,
):
    """Suggest CN codes from a product description (keywords, or a trained model)."""
    return services.classify_product(db, data.description, top_k=data.top_k)
