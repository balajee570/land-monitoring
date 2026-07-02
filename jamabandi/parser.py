"""Parse extracted jamabandi text into a structured record.

Indian land records vary widely by state (Bihar Bhumi, Bhulekh UP, MahaBhulekh,
etc.) and even by document type (LPC, jamabandi nakal, khatauni). There is no
single fixed layout, and text extracted from these multi-column PDFs is often
jumbled. So parsing here is deliberately *keyword and pattern driven with
graceful fallback*: every field is optional, we extract what we confidently
can, and the full raw text is always retained so any upload "parses" — fully
structured where possible, raw otherwise.

All matching is bilingual (Devanagari + common English / transliterated
synonyms) and Devanagari digits are normalised to ASCII first.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

# --- normalisation ----------------------------------------------------------

_DEV_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")


def normalize(text: str) -> str:
    """Normalise Devanagari digits and collapse whitespace runs."""
    if not text:
        return ""
    text = text.translate(_DEV_DIGITS)
    # normalise NBSP and repeated spaces, keep newlines
    text = text.replace(" ", " ")
    text = re.sub(r"[ \t]+", " ", text)
    return text


# Column-header / label words and boilerplate that must never be mistaken for a
# field *value*. In jumbled multi-column extraction the header row of labels
# often collapses into one line, so a naive "label: value" match can capture the
# next label instead of real data. We reject any candidate made only of these.
_STOPWORDS = {
    "जिला", "अनुमंडल", "अंचल", "अचंल", "हलका", "मौजा", "थाना", "जमाबंदी", "खाता",
    "भाग", "पृष", "पृष्ठ", "रकबा", "खेसरा", "खसरा", "चौहदी", "पूरब", "पशिम",
    "पश्चिम", "दकिण", "दक्षिण", "उतर", "उत्तर", "रैयत", "जाति", "भूमि", "नाम",
    "विवरण", "संखा", "संख्या", "लगान", "बकाया", "सेस", "चालू", "साल", "कुल",
    "दखल", "एवं", "वगैरह", "का", "के", "की", "से", "तक", "पिता", "राज", "बाप",
    "सरकार", "पोट", "परिमान", "हिसेदार", "वारिशान", "कबा", "नमर", "शमार",
    "उफ", "मिश", "पत", "ए", "डि", "हे", "और", "N", "Code", "o", "ame", "PI",
    "लि", "पापि", "अंतिम", "तारीख", "रोड", "शिका", "सास", "कृषि", "लागत",
}


def _is_stopword_only(value: str) -> bool:
    tokens = [t for t in re.split(r"\s+", value.strip()) if t]
    if not tokens:
        return True
    return all(t.strip(" :-।.,") in _STOPWORDS for t in tokens)


def _clean_value(value: str) -> str:
    """Trim a captured value at the first column-header/label token.

    Handles the jumbled case where a value regex over-captures into the next
    label(s), e.g. "थाना जमाबंदी बालाजी" -> "" (all leading tokens are labels)
    while "Rosera हलका" -> "Rosera".
    """
    tokens = re.split(r"\s+", value.strip())
    kept = []
    for t in tokens:
        if t.strip(" :-।.,") in _STOPWORDS:
            break
        kept.append(t)
    return " ".join(kept).strip(" :-।.,")


def _first(patterns: List[str], text: str, flags=re.I,
           reject_stopwords: bool = False,
           reject: Optional[set] = None) -> Optional[str]:
    """Return the first clean capturing-group match across a list of patterns.

    ``reject_stopwords`` drops candidates that are only column-header labels.
    ``reject`` is an optional set of exact (case-insensitive) values to skip.
    """
    reject = {r.lower() for r in (reject or set())}
    for pat in patterns:
        for m in re.finditer(pat, text, flags):
            val = (m.group(1) if m.groups() else m.group(0)).strip(" :-।")
            if not val:
                continue
            if val.lower() in reject:
                continue
            if reject_stopwords:
                val = _clean_value(val)
                if not val or val.lower() in reject:
                    continue
            return val
    return None


# --- data model -------------------------------------------------------------


@dataclass
class Plot:
    khesra_no: Optional[str] = None          # खेसरा / survey / plot no.
    rakba_text: Optional[str] = None         # raw area string as printed
    rakba_hectare: Optional[float] = None     # best-effort area in hectares
    boundaries: Dict[str, str] = field(default_factory=dict)  # E/W/N/S neighbours
    owner: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Applicant:
    name: Optional[str] = None
    father: Optional[str] = None
    address: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[str] = None
    aadhaar: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DueRow:
    year: Optional[str] = None
    demand: Optional[str] = None   # लगान / rent
    arrears: Optional[str] = None  # बकाया

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class JamabandiRecord:
    state: Optional[str] = None
    district: Optional[str] = None
    circle_anchal: Optional[str] = None
    subdivision: Optional[str] = None       # अनुमंडल
    halka: Optional[str] = None
    mauja_village: Optional[str] = None
    thana_no: Optional[str] = None
    khata_no: Optional[str] = None
    jamabandi_no: Optional[str] = None
    part_no: Optional[str] = None           # भाग
    page_no: Optional[str] = None           # पृष्ठ
    document_type: Optional[str] = None
    plots: List[Plot] = field(default_factory=list)
    owners: List[str] = field(default_factory=list)
    applicant: Optional[Applicant] = None
    dues: List[DueRow] = field(default_factory=list)
    raw_text: str = ""

    # convenience -----------------------------------------------------------
    def location_query(self) -> Optional[str]:
        """Build a geocoder-friendly location string from what we parsed."""
        parts = [self.mauja_village, self.halka, self.circle_anchal,
                 self.subdivision, self.district, self.state]
        parts = [p for p in parts if p]
        if not parts:
            return None
        if self.state and self.state.lower() not in ("india",):
            parts.append("India")
        else:
            parts.append("India")
        # de-duplicate while preserving order
        seen = set()
        uniq = []
        for p in parts:
            key = p.lower()
            if key not in seen:
                seen.add(key)
                uniq.append(p)
        return ", ".join(uniq)

    def total_hectare(self) -> Optional[float]:
        vals = [p.rakba_hectare for p in self.plots if p.rakba_hectare]
        return round(sum(vals), 4) if vals else None

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


# --- area conversion --------------------------------------------------------

# Bihar records commonly express rakba as एकड़ (acre) / डिसमिल (decimal) /
# हेक्टेयर (hectare). 1 acre = 0.404686 ha; 1 decimal = 1/100 acre.
_ACRE_HA = 0.404686
_DECIMAL_HA = _ACRE_HA / 100.0


def _rakba_to_hectare(acre: float, decimal: float, hectare: float) -> Optional[float]:
    total = acre * _ACRE_HA + decimal * _DECIMAL_HA + hectare
    return round(total, 5) if total > 0 else None


# --- field extractors -------------------------------------------------------


def _extract_applicant(text: str) -> Optional[Applicant]:
    a = Applicant()
    a.name = _first([
        r"Applicant\s*(?:Name)?\s*:?\s*([A-Za-z][A-Za-z .]+?)(?:\s{2,}|Father|$)",
        r"आवेदक\s*:?\s*([^\n]+)",
    ], text)
    a.father = _first([
        r"Father\s*(?:Name|'s Name)?\s*:?\s*(?:Sri|Shri|श्री)?\s*([A-Za-z][A-Za-z .]+?)(?:\s{2,}|Relation|Case|$)",
        r"पिता\s*:?\s*([^\n]+)",
    ], text)
    a.mobile = _first([r"Mobile\s*:?\s*(\+?\d[\d\- ]{8,13}\d)",
                       r"मोबाइल\s*:?\s*(\d{10})"], text)
    a.email = _first([r"([A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,})"], text)
    a.aadhaar = _first([r"(X{3,4}[- ]?X{3,4}[- ]?\d{4})",
                        r"Aadha?ar\s*:?\s*([X\d\- ]{8,14})"], text)
    a.address = _first([
        r"Address\s*:?\s*([^\n]+?)(?:\s{2,}(?:District|State|PI|PIN)|$)",
        r"पता\s*:?\s*([^\n]+)",
    ], text)
    if any(getattr(a, f) for f in ("name", "father", "mobile", "email", "aadhaar")):
        return a
    return None


def _extract_plots(text: str) -> List[Plot]:
    """Extract plots from the rakba table.

    Bihar layout emits rows like ``<khesra> <acre> ए <decimal> डि <hectare> हे``.
    We anchor on that rakba triple and grab the nearest preceding number as the
    khesra/plot number. Falls back to detecting standalone survey/khesra tokens.
    """
    plots: List[Plot] = []

    # Bihar acre/decimal/hectare triple, with the plot no. just before it.
    triple = re.compile(
        r"(?P<khesra>\d{2,5})\s+"
        r"(?P<acre>\d+(?:\.\d+)?)\s*ए\s*"
        r"(?P<dec>\d+(?:\.\d+)?)\s*डि\s*"
        r"(?P<hec>\d+(?:\.\d+)?)\s*हे"
    )
    for m in triple.finditer(text):
        acre = float(m.group("acre"))
        dec = float(m.group("dec"))
        hec = float(m.group("hec"))
        plots.append(Plot(
            khesra_no=m.group("khesra"),
            rakba_text=f"{acre} एकड़ {dec} डिसमिल {hec} हेक्टेयर".strip(),
            rakba_hectare=_rakba_to_hectare(acre, dec, hec),
        ))

    if plots:
        return _dedupe_plots(plots)

    # Generic fallback: "Khesra/Khasra/Survey No <n>" ... "Area/Rakba <x> <unit>"
    for m in re.finditer(
        r"(?:Khesra|Khasra|Survey|Plot|खेसरा|खसरा|सर्वे)\s*(?:No\.?|नं\.?|संख्या)?\s*:?\s*(\d[\d/]*)",
        text, re.I,
    ):
        plots.append(Plot(khesra_no=m.group(1)))
    return _dedupe_plots(plots)


def _dedupe_plots(plots: List[Plot]) -> List[Plot]:
    seen = set()
    out = []
    for p in plots:
        key = (p.khesra_no, p.rakba_text)
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


def _extract_owners(text: str) -> List[str]:
    """Heuristically collect owner (रैयत) names.

    We look for Devanagari personal-name tokens ending in common surname words
    (ठाकुर, महतो, झा, कुमार, देवी, यादव …). This is best-effort; jumbled tables
    make perfect owner-to-plot mapping unreliable, so we surface a de-duplicated
    owner list rather than guess wrong associations.
    """
    surnames = ["ठाकुर", "महतो", "झा", "यादव", "कुमार", "देवी", "सिंह", "राय",
                "पासवान", "साह", "मिश्र", "मिश", "प्रसाद", "लाल", "मंडल"]
    owners: List[str] = []
    # name = 1-3 Devanagari words followed by a surname
    name_re = re.compile(
        r"([ऀ-ॿ]+(?:\s+[ऀ-ॿ]+){0,2}\s+(?:" + "|".join(surnames) + r"))"
    )
    for m in name_re.finditer(text):
        raw_name = m.group(1).strip()
        tokens = [t.strip(" :-।.,") for t in raw_name.split() if t.strip(" :-।.,")]
        # Reject if any token is a column label / boilerplate word — in jumbled
        # tables those leak in and produce nonsense "names".
        if any(t in _STOPWORDS for t in tokens):
            continue
        # Collapse repeated tokens ("ठाकुर ठाकुर ठाकुर" -> "ठाकुर") that come
        # from adjacent table cells bleeding together.
        deduped = []
        for t in tokens:
            if not deduped or deduped[-1] != t:
                deduped.append(t)
        name = " ".join(deduped)
        if len(name) >= 4 and name not in owners:
            owners.append(name)
    return owners[:50]


def _extract_dues(text: str) -> List[DueRow]:
    """Extract rent/arrears rows keyed by fiscal year (YYYY-YYYY / YYYY- YYYY)."""
    dues: List[DueRow] = []
    seen = set()
    for m in re.finditer(r"\b(20\d{2})\s*-\s*(20\d{2})\b", text):
        year = f"{m.group(1)}-{m.group(2)}"
        if year in seen:
            continue
        seen.add(year)
        dues.append(DueRow(year=year))
    return dues


# --- main entry point -------------------------------------------------------


def parse_jamabandi(text: str) -> JamabandiRecord:
    """Parse raw extracted text into a :class:`JamabandiRecord`."""
    raw = text or ""
    text = normalize(raw)

    rec = JamabandiRecord(raw_text=raw)

    rec.document_type = _first([
        r"(Ownership Document)", r"(Acknowledgement Receipt)",
        r"(LPC|Land Possession Certificate)", r"(जमाबंदी)", r"(खतियान)",
        r"(खतौनी)",
    ], text) or "Jamabandi / Land Record"

    rec.jamabandi_no = _first([
        r"(?:Jamabandi|जमाबंदी)\s*(?:No\.?|संख्या|सं\.?)\s*:?\s*(\d+\s*/\s*\d{4}\s*-\s*\d{4})",
        r"(?:Case|केस)\s*:?\s*(\d+\s*/\s*\d{4}\s*-\s*\d{4})",
        r"Application Number is\s*(\d+\s*/\s*\d{4}\s*-\s*\d{4})",
        r"(\d+\s*/\s*20\d{2}\s*-\s*20\d{2})",
    ], text)

    rec.part_no = _first([r"भाग\s*:?\s*(\d+)", r"Part\s*:?\s*(\d+)"], text)
    rec.page_no = _first([r"पृष्?[ठष्]\s*:?\s*(\d+)", r"Page No\.?\s*:?\s*(\d+)"], text)
    rec.khata_no = _first([r"खाता\s*(?:सं\.?|संख्या|No\.?)?\s*:?\s*(\d+)",
                           r"Khata\s*(?:No\.?)?\s*:?\s*(\d+)"], text)
    rec.thana_no = _first([r"थाना\s*(?:नं\.?|No\.?|संख्या)?\s*:?\s*(\d+)",
                           r"Thana\s*(?:No\.?)?\s*:?\s*(\d+)"], text)

    _states = {"bihar", "uttar pradesh", "maharashtra", "rajasthan",
               "madhya pradesh", "haryana", "punjab", "jharkhand", "odisha",
               "gujarat", "west bengal", "karnataka", "telangana"}
    rec.state = _first([
        r"State\s*:?\s*(Bihar|Uttar Pradesh|Maharashtra|Rajasthan|Madhya Pradesh|Haryana|Punjab|Jharkhand|Odisha|Gujarat|West Bengal|Karnataka|Telangana)",
        r"\b(Bihar|Uttar Pradesh|Maharashtra|Rajasthan|Madhya Pradesh|Haryana|Punjab|Jharkhand|Odisha|Gujarat|West Bengal|Karnataka|Telangana)\b",
    ], text)
    rec.district = _first([
        r"(?:जिला|िजला)\s*:?\s*([^\n]+?)(?:\s{2,}|अनुमंडल|अंचल|$)",
        r"District\s*:?\s*([A-Za-z]+)",
    ], text, reject_stopwords=True, reject=_states)
    rec.subdivision = _first([r"अनुमंडल\s*:?\s*([^\n]+?)(?:\s{2,}|अंचल|$)",
                              r"Sub[- ]?division\s*:?\s*([A-Za-z]+)"],
                             text, reject_stopwords=True)
    rec.circle_anchal = _first([
        # (?![ऀ-ॿ]) stops अंचल matching inside अंचलाधिकारी (circle officer)
        r"(?:अंचल|अचंल)(?![ऀ-ॿ])\s*:?\s*([^\n]+?)(?:\s{2,}|हलका|मौजा|$)",
        r"(?:Circle|Anchal|Tehsil|Tahsil)\s*:?\s*([A-Za-z]+)",
    ], text, reject_stopwords=True)
    rec.halka = _first([r"हलका\s*:?\s*([^\n]+?)(?:\s{2,}|मौजा|$)",
                        r"Halka\s*:?\s*([A-Za-z]+)"],
                       text, reject_stopwords=True)
    rec.mauja_village = _first([
        r"मौजा\s*:?\s*([^\n]+?)(?:\s{2,}|थाना|खाता|$)",
        r"(?:Mauja|Village|Mouza)\s*:?\s*([A-Za-z]+)",
    ], text, reject_stopwords=True)

    rec.plots = _extract_plots(text)
    rec.owners = _extract_owners(text)
    rec.applicant = _extract_applicant(text)
    rec.dues = _extract_dues(text)

    return rec
