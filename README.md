# 🛰️ Jamabandi Land Monitor

A Streamlit web app to **upload any Indian jamabandi / LPC / land-record PDF**,
parse it into structured data, and **monitor the land on free satellite
imagery** — with driving directions and site weather. Built entirely with
**free, open-source Python libraries and open data services — no API keys**.

## Features

| Tab | What it does |
|-----|--------------|
| 📄 **Record** | Parses the PDF (Hindi + English) into location fields, plots (khesra + rakba/area), applicant details, owners and dues. Export to CSV / JSON. Raw text always available. |
| 🛰️ **Satellite** | Places the land on **Esri World Imagery** with OSM streets & labels. Per-plot markers with area-scaled footprints. Toggle **NASA MODIS true-color & NDVI vegetation** layers by date for change-over-time monitoring. |
| 🧭 **Directions** | Driving route from any start point via the **OSRM** public server (turn-by-turn), with Google Maps / OpenStreetMap deep links and a straight-line fallback. |
| 🌦️ **Site Conditions** | Current weather + 7-day temperature & rainfall outlook (**Open-Meteo**) — useful for agricultural land. |

## Quick start

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open the local URL Streamlit prints, upload a jamabandi PDF in the sidebar,
click **Locate on map**, and explore the tabs.

## How parsing works

Indian land records have **no single format** (Bihar Bhumi, Bhulekh UP,
MahaBhulekh, …) and their PDFs mix Devanagari and Latin scripts with custom
font encodings. The pipeline is deliberately robust:

1. **`jamabandi/pdf_extract.py`** — extracts text with `pdfplumber`
   (well-ordered, primary path). If `pdfplumber` is unavailable or yields
   nothing, it falls back to…
2. **`jamabandi/stdlib_pdf.py`** — a **zero-dependency** extractor that
   decompresses PDF content streams and decodes glyphs through font
   `/Differences` (`uniXXXX`) and `ToUnicode` CMaps, then groups text by
   position. Handles the bilingual government PDFs that trip up naive readers.
3. **`jamabandi/parser.py`** — bilingual, keyword/regex-driven extraction into a
   `JamabandiRecord` dataclass. Every field is optional; Devanagari digits are
   normalised and column-header words are filtered so fields are either correct
   or honestly blank. Area (rakba) in एकड़/डिसमिल/हेक्टेयर is converted to hectares.

## Important limitations

- **No GPS in jamabandi PDFs.** The map location comes from geocoding the
  village/circle name (Nominatim), so it marks the **village centroid**, not the
  exact parcel. Use the sidebar coordinate override, or your state's
  **Bhu-Naksha** cadastral portal, for precise plot boundaries.
- Plot circles indicate **approximate area**, not real plot shape.
- Parsing is best-effort across formats; always cross-check against the source.

## Data sources (all free, keyless)

Esri World Imagery · OpenStreetMap / Nominatim · NASA EOSDIS GIBS ·
OSRM (router.project-osrm.org) · Open-Meteo.

## Development

```bash
python -m unittest discover -s tests -v   # run parser tests
python -m py_compile app.py jamabandi/*.py services/*.py ui/*.py
```

Project layout:

```
app.py                 Streamlit UI (Record / Satellite / Directions / Weather / Help)
jamabandi/             PDF extraction + record parsing
services/              geocode.py · routing.py · weather.py
ui/maps.py             folium map builders (satellite, GIBS, routes)
tests/                 parser tests against real decoded sample text
```
