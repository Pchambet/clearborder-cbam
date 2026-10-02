"""ClearBorder dashboard: a thin Streamlit client over the API."""

import os

import requests
import streamlit as st

# API_BASE from the environment (docker compose) or localhost
API_BASE = os.getenv("API_BASE", "http://localhost:8000/api/v1")
HEALTH_URL = os.getenv("API_BASE", "http://localhost:8000").replace("/api/v1", "") + "/health"

st.set_page_config(
    page_title="ClearBorder — CBAM embedded emissions",
    layout="wide",
)

st.title("ClearBorder — CBAM embedded emissions")
st.caption("Specific embedded emissions (SEE) of imported goods — Regulation (EU) 2023/956, Annex IV")


# Sent as X-API-Key when the API has keys configured (API_KEYS on the server side).
HEADERS = {"X-API-Key": key} if (key := os.getenv("API_KEY")) else {}


def api_get(path: str):
    """JSON body on success; otherwise shows the error and returns None.

    An error is shown, not masked as an empty list: a 401 (missing API_KEY) or a 500
    must not read as "no data yet".
    """
    try:
        r = requests.get(f"{API_BASE}{path}", headers=HEADERS, timeout=5)
    except requests.exceptions.RequestException as e:
        st.error(f"API unavailable: {e}")
        return None
    if not r.ok:
        st.error(f"API error {r.status_code}: {r.text}")
        return None
    return r.json()


def api_post(path: str, json: dict):
    """The response (even 4xx/5xx), or None when the request failed (unreachable, timeout).

    Callers must test ``r is None``: a requests.Response is falsy on 4xx/5xx.
    """
    try:
        return requests.post(f"{API_BASE}{path}", json=json, headers=HEADERS, timeout=10)
    except requests.exceptions.RequestException:
        return None


# Sidebar
SECTORS = ["iron_steel", "aluminium", "cement", "fertilisers", "hydrogen", "electricity"]

st.sidebar.header("Navigation")
page = st.sidebar.radio(
    "Menu",
    ["Home", "CN classification", "Installations", "Products", "CBAM report", "About"],
)

# API health
try:
    h = requests.get(HEALTH_URL, timeout=2)
    if not h.ok:
        st.sidebar.warning("API unavailable")
except requests.exceptions.RequestException:
    st.sidebar.warning("Start the API, or set API_BASE to point at a running one")

if page == "Home":
    st.header("How it works")
    st.markdown("""
    ClearBorder computes the specific embedded emissions (SEE) of goods covered by the
    EU Carbon Border Adjustment Mechanism and checks the 20 % cap on estimated data that
    applied during the 2023–2025 transitional period.

    1. **Installations**: register the non-EU producer.
    2. **Products**: declare a good, its direct emissions and its precursors.
    3. **CBAM report**: compute SEE and export a simplified quarterly-report XML
       (not the official CBAM Registry schema).
    """)

elif page == "CN classification":
    st.header("CN code suggestions")
    st.caption("Keyword heuristic, or a TF-IDF model once trained. Suggestions need expert review.")

    desc = st.text_area("Product description", placeholder="e.g. hot-rolled steel plate, 2 mm")
    if st.button("Suggest"):
        if desc.strip():
            r = api_post("/classify", {"description": desc, "top_k": 5})
            if r is not None and r.status_code == 200:
                suggestions = r.json().get("suggestions", [])
                if not suggestions:
                    st.info("No suggestion for this description.")
                for i, s in enumerate(suggestions, 1):
                    st.markdown(
                        f"**{i}.** `{s.get('code', '')}` — score {s.get('confidence', 0):.2f} — *{s.get('description', '')}*"
                    )
            elif r is not None:
                st.error(r.text)
            else:
                st.error("API unavailable")
        else:
            st.warning("Enter a description")

    cn_codes = api_get("/cn-codes")
    if cn_codes:
        with st.expander("Loaded CN codes"):
            st.dataframe(cn_codes)

elif page == "Installations":
    st.header("Installations (non-EU producers)")

    with st.expander("New installation"), st.form("new_installation"):
        name = st.text_input("Name")
        country = st.text_input("Country (ISO alpha-2)", "TR", max_chars=2)
        sector = st.selectbox("Sector", SECTORS)
        emissions = st.number_input("Emissions (t CO2e per t)", min_value=0.0, value=1.5, step=0.1)
        if st.form_submit_button("Create"):
            r = api_post(
                "/installations",
                {
                    "name": name,
                    "country_code": country.upper(),
                    "sector": sector,
                    "emissions_per_tonne": float(emissions),
                },
            )
            if r is not None and r.status_code == 200:
                st.success("Installation created")
            elif r is not None:
                st.error(r.text)
            else:
                st.error("API unavailable")

    data = api_get("/installations")
    if data:
        st.dataframe(data)
    elif data is not None:  # None: the error is already shown
        st.info("No installation yet. Create one above.")

elif page == "Products":
    st.header("Products")

    installations = api_get("/installations") or []
    inst_map = {str(i["id"]): i["name"] for i in installations}

    with st.expander("New product"), st.form("new_product"):
        name = st.text_input("Product name")
        cn_code = st.text_input("CN code", "7208 10 00")
        sector = st.selectbox("Sector", SECTORS)
        inst_id = st.selectbox(
            "Installation", options=list(inst_map.keys()), format_func=lambda x: inst_map.get(x, x)
        )
        activity = st.number_input("Activity level: mass produced (kg)", min_value=0.1, value=1000.0)
        attr_em = st.number_input("Direct (attributed) emissions (kg CO2e)", min_value=0.0, value=0.0)

        st.subheader("Precursor (optional)")
        p1_mass = st.number_input("Precursor mass (kg)", min_value=0.0, value=0.0)
        p1_see = st.number_input("Precursor SEE (kg CO2e/kg)", min_value=0.0, value=0.0)
        p1_real = st.checkbox("Precursor SEE is actual installation data", False)

        submitted = st.form_submit_button("Create")

    if submitted and inst_id is None:
        st.error("Create an installation first.")
    elif submitted:
        precursors = []
        if p1_mass > 0:
            precursors.append(
                {"mass_kg": float(p1_mass), "see_per_kg": float(p1_see), "is_real_data": p1_real}
            )
        r = api_post(
            "/products",
            {
                "name": name,
                "cn_code": cn_code.replace(" ", ""),
                "sector": sector,
                "installation_id": int(inst_id),
                "activity_level": float(activity),
                "attributed_emissions": float(attr_em),
                "precursors": precursors,
            },
        )
        if r is not None and r.status_code == 200:
            st.success("Product created")
        elif r is not None:
            st.error(r.text)
        else:
            st.error("API unavailable")

    data = api_get("/products")
    if data:
        st.dataframe(data)
    elif data is not None:  # None: the error is already shown
        st.info("No product yet. Create one above.")

elif page == "CBAM report":
    st.header("Quarterly CBAM report")

    products = api_get("/products")

    if products == []:
        st.info("Add products before generating a report.")
    elif products:
        with st.form("cbam_report"):
            declarant_id = st.text_input("Declarant ID", "EU-CBAM-2026-001")
            period = st.text_input("Period", "2026-Q1")

            st.subheader("Products to include")
            selected = []
            for p in products:
                qty = st.number_input(
                    f"{p.get('name', '')} ({p.get('cn_code', '')}) — quantity (t)",
                    min_value=0.01,
                    value=1.0,
                    key=f"qty_{p['id']}",
                )
                selected.append({"product_id": p["id"], "quantity_tonnes": float(qty)})

            submitted = st.form_submit_button("Generate report")

        # Results are rendered outside the form: Streamlit forbids download buttons inside one.
        if submitted:
            r = api_post(
                "/generate-cbam-report",
                {"declarant_id": declarant_id, "reporting_period": period, "products": selected},
            )
            if r is not None and r.status_code == 200:
                data = r.json()
                st.success("Report generated")
                st.dataframe(data.get("results", []))
                st.download_button(
                    "Download XML",
                    data.get("xml_content", ""),
                    file_name=f"cbam_report_{period}.xml",
                    mime="application/xml",
                )
            elif r is not None:
                st.error(r.text)
            else:
                st.error("API unavailable")

else:
    st.header("About")
    st.markdown("""
    **ClearBorder** v0.1.0 — prototype, spring 2026.

    - SEE per Annex IV of Regulation (EU) 2023/956, including nested bills of materials
    - 20 % cap on estimated data for complex goods (2023–2025 transitional period),
      measured on embedded emissions
    - Simplified quarterly-report XML (not the official CBAM Registry schema)
    """)
