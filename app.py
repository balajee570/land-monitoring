"""Jamabandi Land Monitoring — Streamlit app.

Upload any Indian jamabandi / LPC / land-record PDF and the app will:
  * parse it into structured fields (bilingual Hindi + English),
  * show the land on free satellite imagery with per-plot markers,
  * overlay NASA vegetation imagery by date for monitoring over time,
  * give driving directions from any starting location,
  * show current weather + a 7-day outlook for the parcel.

Everything uses free, keyless Python libraries and open data services.
"""
from __future__ import annotations

import datetime as dt

import pandas as pd
import streamlit as st

from jamabandi import parse_jamabandi
from jamabandi.pdf_extract import extract_text_verbose
from services import geocode as geo
from services import routing, weather

st.set_page_config(page_title="Jamabandi Land Monitor", page_icon="🛰️",
                   layout="wide")

# --- session state ----------------------------------------------------------
_defaults = {
    "record": None, "raw_text": "", "method": "", "coords": None,
    "geo_display": "", "file_name": "",
}
for k, v in _defaults.items():
    st.session_state.setdefault(k, v)


# --- helpers ----------------------------------------------------------------
def _render_map(m, height=520):
    """Render a folium map, using streamlit-folium if present, else raw HTML."""
    try:
        from streamlit_folium import st_folium
        st_folium(m, height=height, use_container_width=True,
                  returned_objects=[])
    except Exception:
        st.components.v1.html(m._repr_html_(), height=height, scrolling=False)


def _fmt(v):
    return v if v not in (None, "", []) else "—"


# --- sidebar: upload + location --------------------------------------------
with st.sidebar:
    st.title("🛰️ Land Monitor")
    st.caption("Upload a jamabandi / LPC PDF. Free & open-source only.")

    up = st.file_uploader("Jamabandi PDF", type=["pdf"])
    if up is not None and up.name != st.session_state["file_name"]:
        with st.spinner("Extracting & parsing…"):
            data = up.read()
            text, method = extract_text_verbose(data)
            st.session_state["raw_text"] = text
            st.session_state["method"] = method
            st.session_state["record"] = parse_jamabandi(text)
            st.session_state["file_name"] = up.name
            st.session_state["coords"] = None  # reset location for new file

    rec = st.session_state["record"]
    if rec is not None:
        st.success(f"Parsed via **{st.session_state['method']}**")
        found = sum(1 for f in ("district", "circle_anchal", "mauja_village",
                                "jamabandi_no", "khata_no") if getattr(rec, f))
        st.progress(min(found / 5, 1.0), text=f"{found}/5 key location fields found")

    st.divider()
    st.subheader("📍 Land location")
    st.caption("Jamabandi PDFs have no GPS. We geocode the village name; "
               "refine below if needed.")

    if rec is not None:
        default_q = rec.location_query() or ""
        loc_q = st.text_input("Location to geocode", value=default_q)
        if st.button("🔎 Locate on map", use_container_width=True):
            with st.spinner("Geocoding via OpenStreetMap…"):
                g = geo.geocode(loc_q)
            if g:
                st.session_state["coords"] = (g.lat, g.lon)
                st.session_state["geo_display"] = g.display_name
                st.toast(f"Found: {g.query_used}")
            else:
                st.warning("Couldn't geocode. Enter coordinates manually below.")

    with st.expander("✏️ Enter exact coordinates"):
        c1, c2 = st.columns(2)
        lat = c1.number_input("Latitude", value=25.9, format="%.6f")
        lon = c2.number_input("Longitude", value=85.9, format="%.6f")
        if st.button("Use these coordinates", use_container_width=True):
            st.session_state["coords"] = (float(lat), float(lon))
            st.session_state["geo_display"] = "Manually entered coordinates"


# --- main -------------------------------------------------------------------
st.title("Jamabandi Land Monitoring")

if st.session_state["record"] is None:
    st.info("👈 Upload a jamabandi / LPC PDF in the sidebar to begin.")
    st.markdown(
        """
        **What this does**
        - 📄 Parses land records (Hindi + English) into structured fields
        - 🛰️ Plots the land on free satellite imagery (Esri World Imagery)
        - 🌱 Overlays NASA MODIS true-color & NDVI vegetation by date
        - 🧭 Gives driving directions from any starting point (OSRM, Google/OSM links)
        - 🌦️ Shows current weather + 7-day outlook (Open-Meteo)

        All powered by free Python libraries and open data — no API keys.
        """
    )
    st.stop()

rec = st.session_state["record"]
coords = st.session_state["coords"]

tab_rec, tab_sat, tab_dir, tab_wx, tab_help = st.tabs(
    ["📄 Record", "🛰️ Satellite", "🧭 Directions", "🌦️ Site Conditions", "ℹ️ Help"])

# ---- Record tab ----
with tab_rec:
    st.subheader(rec.document_type or "Land Record")
    c = st.columns(4)
    c[0].metric("Jamabandi No.", _fmt(rec.jamabandi_no))
    c[1].metric("Khata No.", _fmt(rec.khata_no))
    c[2].metric("Plots", len(rec.plots))
    c[3].metric("Total area (ha)", _fmt(rec.total_hectare()))

    st.markdown("#### Location")
    loc = {
        "State": rec.state, "District": rec.district,
        "Subdivision (Anumandal)": rec.subdivision,
        "Circle (Anchal)": rec.circle_anchal, "Halka": rec.halka,
        "Village (Mauja)": rec.mauja_village, "Thana No.": rec.thana_no,
        "Part (Bhag)": rec.part_no, "Page (Prishth)": rec.page_no,
    }
    st.table(pd.DataFrame(
        [(k, _fmt(v)) for k, v in loc.items()], columns=["Field", "Value"]))

    if rec.applicant:
        st.markdown("#### Applicant")
        a = rec.applicant
        st.table(pd.DataFrame([
            ("Name", _fmt(a.name)), ("Father", _fmt(a.father)),
            ("Mobile", _fmt(a.mobile)), ("Email", _fmt(a.email)),
            ("Aadhaar", _fmt(a.aadhaar)), ("Address", _fmt(a.address)),
        ], columns=["Field", "Value"]))

    if rec.plots:
        st.markdown("#### Plots (Khesra)")
        plots_df = pd.DataFrame([{
            "#": i + 1, "Khesra/Plot": p.khesra_no, "Rakba": p.rakba_text,
            "Area (ha)": p.rakba_hectare, "Owner": p.owner,
        } for i, p in enumerate(rec.plots)])
        st.dataframe(plots_df, use_container_width=True, hide_index=True)

    if rec.owners:
        st.markdown("#### Owners / Raiyat (detected)")
        st.write(", ".join(rec.owners))
        st.caption("Owner ↔ plot mapping is approximate on jumbled scans; "
                   "verify against the source document.")

    if rec.dues:
        st.markdown("#### Rent / Dues years detected")
        st.write(", ".join(d.year for d in rec.dues if d.year))

    st.markdown("#### Export")
    ce1, ce2 = st.columns(2)
    if rec.plots:
        ce1.download_button(
            "⬇️ Plots CSV",
            pd.DataFrame([p.to_dict() for p in rec.plots]).to_csv(index=False),
            file_name="plots.csv", mime="text/csv", use_container_width=True)
    import json
    ce2.download_button(
        "⬇️ Full record JSON",
        json.dumps(rec.to_dict(), ensure_ascii=False, indent=2),
        file_name="jamabandi.json", mime="application/json",
        use_container_width=True)

    with st.expander("📜 Raw extracted text"):
        st.text(st.session_state["raw_text"])

# ---- Satellite tab ----
with tab_sat:
    if coords is None:
        st.warning("Set the land location in the sidebar (Locate on map or "
                   "enter coordinates) to view satellite imagery.")
    else:
        st.caption(f"📍 {st.session_state['geo_display']}  ·  "
                   f"{coords[0]:.5f}, {coords[1]:.5f}")
        cset = st.columns([2, 1])
        gibs_date = cset[0].date_input(
            "NASA imagery date (toggle layers in map control)",
            value=dt.date.today() - dt.timedelta(days=3),
            max_value=dt.date.today())
        zoom = cset[1].slider("Zoom", 10, 19, 16)
        from ui import maps
        m = maps.build_land_map(coords, record=rec,
                                gibs_date=gibs_date.isoformat(), zoom=zoom)
        _render_map(m)
        st.caption("Layers: Esri satellite, OSM streets, NASA MODIS true-color "
                   "& NDVI. Numbered circles = plots (size ≈ area; not exact "
                   "shape). For exact plot boundaries use your state's "
                   "Bhu-Naksha cadastral map.")
        st.link_button("🗺️ Open Bihar Bhu-Naksha (cadastral map)",
                       "https://bhunaksha.bihar.gov.in/")

# ---- Directions tab ----
with tab_dir:
    if coords is None:
        st.warning("Set the land location in the sidebar first.")
    else:
        st.markdown("Enter your starting point to get driving directions.")
        start_text = st.text_input("Start location (address / place)",
                                   placeholder="e.g. Samastipur Railway Station")
        use_here = st.checkbox("Or enter start coordinates")
        start_coords = None
        if use_here:
            d1, d2 = st.columns(2)
            slat = d1.number_input("Start latitude", value=25.86, format="%.6f")
            slon = d2.number_input("Start longitude", value=85.78, format="%.6f")
            start_coords = (float(slat), float(slon))
        if st.button("🧭 Get directions", type="primary"):
            if not start_coords and start_text:
                g = geo.geocode(start_text + ", India")
                if g:
                    start_coords = (g.lat, g.lon)
                else:
                    st.error("Couldn't geocode the start location.")
            if start_coords:
                with st.spinner("Routing via OSRM…"):
                    route = routing.get_route(start_coords, coords)
                st.session_state["_route"] = (route, start_coords)

        rt = st.session_state.get("_route")
        if rt:
            route, start_coords = rt
            if route.straight_line:
                st.info("Live routing unavailable — showing straight-line "
                        "estimate and map links below.")
            m1 = st.columns(3)
            m1[0].metric("Distance", f"{route.distance_km} km")
            m1[1].metric("Est. time", f"{route.duration_min} min")
            m1[2].metric("Steps", len(route.steps))
            from ui import maps
            _render_map(maps.build_route_map(start_coords, coords, route), height=460)
            lc = st.columns(2)
            lc[0].link_button("🟢 Google Maps directions",
                              routing.google_maps_link(start_coords, coords),
                              use_container_width=True)
            lc[1].link_button("🧭 OpenStreetMap directions",
                              routing.osm_link(start_coords, coords),
                              use_container_width=True)
            if route.steps and not route.straight_line:
                st.markdown("#### Turn-by-turn")
                st.dataframe(pd.DataFrame([{
                    "Step": i + 1, "Instruction": s.instruction,
                    "Distance (m)": round(s.distance_m),
                } for i, s in enumerate(route.steps)]),
                    use_container_width=True, hide_index=True)

# ---- Site Conditions tab ----
with tab_wx:
    if coords is None:
        st.warning("Set the land location in the sidebar first.")
    else:
        with st.spinner("Fetching weather (Open-Meteo)…"):
            w = weather.get_weather(coords[0], coords[1])
        if not w:
            st.error("Weather service unavailable right now.")
        else:
            wc = st.columns(3)
            wc[0].metric("Temperature", f"{_fmt(w.temperature_c)} °C")
            wc[1].metric("Wind", f"{_fmt(w.windspeed_kmh)} km/h")
            wc[2].metric("Condition", weather.describe(w.weather_code))
            if w.daily.get("date"):
                df = pd.DataFrame({
                    "Date": w.daily["date"],
                    "Max °C": w.daily["tmax"],
                    "Min °C": w.daily["tmin"],
                    "Rain mm": w.daily["rain"],
                }).set_index("Date")
                st.markdown("#### 7-day outlook")
                st.line_chart(df[["Max °C", "Min °C"]])
                st.bar_chart(df[["Rain mm"]])
            st.caption("Agricultural relevance: rain & temperature trends for "
                       "the parcel's coordinates.")

# ---- Help tab ----
with tab_help:
    st.markdown(
        """
        ### How to use
        1. **Upload** a jamabandi / LPC PDF (Bihar Bhumi, Bhulekh, etc.).
        2. Review parsed fields in **Record**; export CSV/JSON.
        3. In the sidebar, click **Locate on map** (or enter exact coordinates)
           to place the land.
        4. **Satellite** tab: view imagery, toggle NASA vegetation layers by date.
        5. **Directions** tab: enter a start point for driving directions.
        6. **Site Conditions** tab: current weather + 7-day outlook.

        ### Important notes
        - Jamabandi PDFs contain **no GPS coordinates**. Location is derived by
          geocoding the village/circle name, so it points to the **village
          centroid**, not the exact parcel. Use the coordinate override or the
          state Bhu-Naksha cadastral map for precise plot boundaries.
        - Plot circles show **approximate area**, not the real plot shape.
        - Parsing is best-effort across many state formats; the **raw text** is
          always available under the Record tab.

        ### Data sources (all free, no keys)
        Esri World Imagery · OpenStreetMap · NASA EOSDIS GIBS · OSRM · Open-Meteo
        · Nominatim geocoding.
        """
    )
