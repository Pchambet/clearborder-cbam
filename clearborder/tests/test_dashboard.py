"""Dashboard smoke tests: every page renders, and the report page works end to end.

The dashboard talks to the API over HTTP with ``requests``; here those calls are
routed to the in-process FastAPI test client, so no server is needed.
"""

from types import SimpleNamespace

import pytest
import requests
from streamlit.testing.v1 import AppTest

API_ROOT = "http://localhost:8000"
PAGES = ["Home", "CN classification", "Installations", "Products", "CBAM report", "About"]


@pytest.fixture
def dashboard(seeded_client, monkeypatch):
    def adapt(response):
        return SimpleNamespace(
            ok=response.is_success,
            status_code=response.status_code,
            text=response.text,
            json=response.json,
        )

    def fake_get(url, timeout=None):
        return adapt(seeded_client.get(url.removeprefix(API_ROOT)))

    def fake_post(url, json=None, timeout=None):
        return adapt(seeded_client.post(url.removeprefix(API_ROOT), json=json))

    monkeypatch.delenv("API_BASE", raising=False)
    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.setattr(requests, "post", fake_post)

    def open_page(page: str) -> AppTest:
        at = AppTest.from_file("../dashboard/app.py", default_timeout=30).run()
        at.sidebar.radio[0].set_value(page).run()
        assert not at.exception, at.exception
        return at

    return open_page


@pytest.mark.parametrize("page", PAGES)
def test_every_page_renders(dashboard, page):
    at = dashboard(page)
    assert not at.sidebar.warning  # the API is reachable


def test_report_page_generates_report(dashboard):
    at = dashboard("CBAM report")
    at.button[0].click().run()
    assert not at.exception, at.exception
    assert [s.value for s in at.success] == ["Report generated"]
    row = at.dataframe[-1].value.iloc[0]
    assert row["see_kg_co2_per_tonne"] == pytest.approx(1730.0)
