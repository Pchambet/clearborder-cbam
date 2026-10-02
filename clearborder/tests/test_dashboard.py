"""Dashboard smoke tests: every page renders, and the report page works end to end.

The dashboard talks to the API over HTTP with ``requests``; here those calls are
routed to the in-process FastAPI test client, so no server is needed.
"""

import pytest
import requests
from streamlit.testing.v1 import AppTest

API_ROOT = "http://localhost:8000"
PAGES = ["Home", "CN classification", "Installations", "Products", "CBAM report", "About"]


@pytest.fixture
def dashboard(seeded_client, monkeypatch):
    class Response:
        """Mimics requests.Response, including being falsy on 4xx/5xx."""

        def __init__(self, response):
            self.ok = response.is_success
            self.status_code = response.status_code
            self.text = response.text
            self.json = response.json

        def __bool__(self):
            return self.ok

    def fake_get(url, headers=None, timeout=None):
        return Response(seeded_client.get(url.removeprefix(API_ROOT), headers=headers))

    def fake_post(url, json=None, headers=None, timeout=None):
        return Response(seeded_client.post(url.removeprefix(API_ROOT), json=json, headers=headers))

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


def test_api_errors_are_shown_not_masked(dashboard):
    """A 4xx answer must surface the API's message, not "API unavailable"."""
    at = dashboard("Installations")
    at.text_input[0].input("Mill").run()
    at.text_input[1].input("").run()  # country code too short: 422 from the API
    at.button[0].click().run()
    assert not at.exception, at.exception
    errors = [e.value for e in at.error]
    assert errors and "API unavailable" not in errors[0]
    assert "country_code" in errors[0]


def test_list_errors_are_shown_not_read_as_empty(dashboard, monkeypatch):
    """With API keys required and none configured, the list page reports the 401."""
    from app.config import settings

    monkeypatch.setattr(settings, "api_keys", "secret")
    at = dashboard("Installations")
    assert any("401" in e.value for e in at.error)
    assert not at.info  # no "No installation yet" on top of the error


def test_timeout_is_reported_not_raised(dashboard, monkeypatch):
    def timeout(*args, **kwargs):
        raise requests.exceptions.ReadTimeout("read timed out")

    monkeypatch.setattr(requests, "get", timeout)
    at = dashboard("Products")
    assert any("API unavailable" in e.value for e in at.error)


def test_product_form_without_installation(dashboard, monkeypatch):
    """Submitting a product before any installation exists asks for one instead of crashing."""

    class Empty:
        ok, status_code, text = True, 200, "[]"

        def json(self):
            return []

    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: Empty())
    at = dashboard("Products")
    at.button[0].click().run()
    assert not at.exception, at.exception
    assert "Create an installation first." in [e.value for e in at.error]
