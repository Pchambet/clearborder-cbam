"""
API integration tests (FastAPI TestClient on a temporary SQLite database).
"""

import pytest
from fastapi.testclient import TestClient


class TestHealth:
    """Root and health endpoints."""

    def test_root(self, client: TestClient):
        r = client.get("/")
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "ClearBorder"
        assert "version" in data

    def test_health(self, client: TestClient):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


class TestInstallations:
    """Installations."""

    def test_create_installation(self, client: TestClient):
        payload = {
            "name": "Test steel mill",
            "country_code": "TR",
            "sector": "iron_steel",
            "emissions_per_tonne": 1.65,
        }
        r = client.post("/api/v1/installations", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "Test steel mill"
        assert data["country_code"] == "TR"
        assert "id" in data

    def test_list_installations(self, client: TestClient):
        r = client.get("/api/v1/installations")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_get_installation_not_found(self, client: TestClient):
        r = client.get("/api/v1/installations/99999")
        assert r.status_code == 404

    def test_get_installation(self, client: TestClient):
        create = client.post(
            "/api/v1/installations",
            json={
                "name": "Inst",
                "country_code": "CN",
                "sector": "iron_steel",
            },
        )
        inst_id = create.json()["id"]
        r = client.get(f"/api/v1/installations/{inst_id}")
        assert r.status_code == 200
        assert r.json()["id"] == inst_id


class TestProducts:
    """Products."""

    def test_create_product_requires_installation(self, client: TestClient):
        # a product needs an installation
        inst = client.post(
            "/api/v1/installations",
            json={
                "name": "Inst",
                "country_code": "TR",
                "sector": "iron_steel",
            },
        )
        inst_id = inst.json()["id"]
        payload = {
            "name": "Steel plate",
            "cn_code": "7208",
            "sector": "iron_steel",
            "installation_id": inst_id,
            "activity_level": 1000,
            "attributed_emissions": 50,
            "precursors": [
                {"mass_kg": 1050, "see_per_kg": 1.6, "is_real_data": True},
            ],
        }
        r = client.post("/api/v1/products", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "Steel plate"
        assert data["cn_code"] == "7208"

    def test_list_products(self, client: TestClient):
        r = client.get("/api/v1/products")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_get_product_not_found(self, client: TestClient):
        r = client.get("/api/v1/products/99999")
        assert r.status_code == 404


class TestCbamReport:
    """Report generation."""

    def test_generate_report_requires_valid_products(self, client: TestClient):
        payload = {
            "declarant_id": "EU-001",
            "reporting_period": "2026-Q1",
            "products": [{"product_id": 99999, "quantity_tonnes": 10}],
        }
        r = client.post("/api/v1/generate-cbam-report", json=payload)
        assert r.status_code == 400

    def test_generate_report_success(self, seeded_client: TestClient):
        # seeded_client a une installation et un produit
        products = seeded_client.get("/api/v1/products").json()
        assert len(products) >= 1
        product_id = products[0]["id"]
        payload = {
            "declarant_id": "EU-CBAM-TEST",
            "reporting_period": "2026-Q1",
            "products": [{"product_id": product_id, "quantity_tonnes": 5}],
        }
        r = seeded_client.post("/api/v1/generate-cbam-report", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert "results" in data
        assert "xml_content" in data
        assert "compliant" in data
        assert len(data["results"]) == 1
        # seeded product: (50 + 1050 * 1.6) / 1000 kg = 1.73 kg/kg = 1730 kg CO2e per t
        assert data["results"][0]["see_kg_co2_per_tonne"] == pytest.approx(1730.0)
        assert data["compliant"] is True
        assert "<Quantity>5000.0</Quantity>" in data["xml_content"]
        assert "<CountryOfOrigin>TR</CountryOfOrigin>" in data["xml_content"]


class TestCnCodes:
    """CN codes."""

    def test_list_cn_codes_empty(self, client: TestClient):
        r = client.get("/api/v1/cn-codes")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_list_cn_codes_with_data(self, seeded_client: TestClient):
        r = seeded_client.get("/api/v1/cn-codes")
        assert r.status_code == 200
        codes = r.json()
        assert isinstance(codes, list)
        if len(codes) > 0:
            assert "code" in codes[0]
            assert "description" in codes[0]


class TestClassify:
    """CN classification."""

    def test_classify_product(self, client: TestClient):
        r = client.post(
            "/api/v1/classify",
            json={
                "description": "hot-rolled steel plate",
                "top_k": 3,
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert "suggestions" in data
        assert len(data["suggestions"]) >= 1
        assert "code" in data["suggestions"][0]
        assert "confidence" in data["suggestions"][0]


class TestApiKeys:
    """Authentication is off with no configured key, enforced otherwise."""

    def test_missing_and_invalid_keys_are_rejected(self, client: TestClient, monkeypatch):
        from app.config import settings

        monkeypatch.setattr(settings, "api_keys", "secret")
        assert client.get("/api/v1/products").status_code == 401
        assert client.get("/api/v1/products", headers={"X-API-Key": "wrong"}).status_code == 403
        assert client.get("/api/v1/products", headers={"X-API-Key": "secret"}).status_code == 200

    def test_keys_parsed_from_comma_separated_env(self, monkeypatch):
        from app.config import Settings

        monkeypatch.setenv("API_KEYS", "a, b,,c")
        assert Settings().allowed_api_keys == ["a", "b", "c"]
