"""
Fixtures pytest partagées — base de données de test, client API, données.
"""
import sys
from pathlib import Path

# Ajouter le répertoire parent au path pour importer app
sys.path.insert(0, str(Path(__file__).parent.parent))

from decimal import Decimal
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app
from app.models import (
    Installation, Product, ProductPrecursor,
    DefaultEmissionFactor, CNCode,
)


@pytest.fixture(autouse=True)
def isolated_model_path(tmp_path, monkeypatch):
    """Keep tests from reading or writing a classifier model inside the repository."""
    from app import classifier

    monkeypatch.setattr(classifier, "MODEL_PATH", tmp_path / "cn_classifier.pkl")


@pytest.fixture(scope="function")
def db_engine(tmp_path):
    """Moteur SQLite fichier temporaire, recréé pour chaque test."""
    db_file = tmp_path / "test.db"
    url = f"sqlite:///{db_file}"
    engine = create_engine(url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Session DB isolée par test."""
    Session = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_engine):
    """Client HTTP TestClient avec DB de test."""
    from app import database
    # Patcher l'engine pour que init_db crée les tables sur la DB de test
    original_engine = database.engine
    original_session_local = database.SessionLocal
    database.engine = db_engine
    database.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    Session = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    def override_get_db():
        session = Session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=db_engine)

    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()
        database.engine = original_engine
        database.SessionLocal = original_session_local
        Base.metadata.drop_all(bind=db_engine)


@pytest.fixture
def sample_installation(db_session):
    """Installation de test — aciérie Turquie."""
    inst = Installation(
        name="Test Aciérie TR",
        country_code="TR",
        sector="iron_steel",
        emissions_per_tonne=Decimal("1.65"),
    )
    db_session.add(inst)
    db_session.commit()
    db_session.refresh(inst)
    return inst


@pytest.fixture
def sample_product(db_session, sample_installation):
    """Produit de test avec précurseur."""
    prod = Product(
        name="Tôle acier laminée",
        cn_code="7208",
        sector="iron_steel",
        installation_id=sample_installation.id,
        activity_level=Decimal("1000"),
        attributed_emissions=Decimal("50"),
    )
    db_session.add(prod)
    db_session.commit()
    db_session.refresh(prod)
    
    db_session.add(ProductPrecursor(
        product_id=prod.id,
        mass_kg=Decimal("1050"),
        see_per_kg=Decimal("1.6"),
        is_real_data=True,
    ))
    db_session.commit()
    db_session.refresh(prod)
    return prod


@pytest.fixture
def sample_product_simple(db_session, sample_installation):
    """Produit simple sans précurseur."""
    prod = Product(
        name="Billettes acier",
        cn_code="7207",
        sector="iron_steel",
        installation_id=sample_installation.id,
        activity_level=Decimal("500"),
        attributed_emissions=Decimal("100"),
    )
    db_session.add(prod)
    db_session.commit()
    db_session.refresh(prod)
    return prod


@pytest.fixture
def sample_default_factors(db_session):
    """Facteurs d'émission par défaut."""
    factors = [
        ("iron_steel", "TR", 1.8),
        ("iron_steel", "CN", 2.2),
        ("aluminium", "TR", 8.0),
    ]
    for sector, country, factor in factors:
        db_session.add(DefaultEmissionFactor(
            sector=sector,
            country_code=country,
            emission_factor_kg_co2_per_tonne=Decimal(str(factor)),
            source="Test",
        ))
    db_session.commit()


@pytest.fixture
def sample_cn_codes(db_session):
    """Codes CN de référence."""
    codes = [
        ("7208", "Plaques acier laminées à chaud"),
        ("7306", "Tubes acier soudés"),
        ("7606", "Plaques aluminium"),
    ]
    for code, desc in codes:
        db_session.add(CNCode(code=code, description=desc, level=2))
    db_session.commit()


@pytest.fixture
def seeded_client(client, db_engine):
    """Client API avec données pré-chargées (installation, produit, codes CN)."""
    Session = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = Session()
    try:
        inst = Installation(
            name="Aciérie Test TR",
            country_code="TR",
            sector="iron_steel",
            emissions_per_tonne=Decimal("1.65"),
        )
        session.add(inst)
        session.commit()
        session.refresh(inst)

        prod = Product(
            name="Tôle acier laminée",
            cn_code="7208",
            sector="iron_steel",
            installation_id=inst.id,
            activity_level=Decimal("1000"),
            attributed_emissions=Decimal("50"),
        )
        session.add(prod)
        session.commit()
        session.refresh(prod)

        session.add(ProductPrecursor(
            product_id=prod.id,
            mass_kg=Decimal("1050"),
            see_per_kg=Decimal("1.6"),
            is_real_data=True,
        ))
        for code, desc in [("7208", "Plaques acier"), ("7306", "Tubes"), ("7606", "Alu")]:
            session.add(CNCode(code=code, description=desc, level=2))
        session.commit()
    finally:
        session.close()
    return client
