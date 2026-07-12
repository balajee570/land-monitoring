# -*- coding: utf-8 -*-
"""खतियान — UI: पुराने रजिस्टर की सौंदर्य-दृष्टि, मुहर-बैज, हेडर"""

import streamlit as st

INK = "#2B1D12"        # स्याही
PAPER = "#F7F0DF"      # पुराना कागज़
PAGE = "#EFE4CB"       # रजिस्टर पन्ना
BASTA = "#A4243B"      # बस्ता लाल
STAMP_GREEN = "#2F5233"  # रसीदी हरा
HALDI = "#C99700"      # हल्दी सोना
RULE = "#C9B893"       # फीकी रेखा


def inject_css():
    # Fonts alag call mein: <link> se shuru hone wala markdown HTML-block pehli
    # khaali line par toot jaata hai, jisse aage ka CSS page par text ban jaata
    # tha. <style> se shuru block </style> tak chalta hai — khaali lines safe.
    st.markdown(
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link href="https://fonts.googleapis.com/css2?family=Tiro+Devanagari+Hindi:ital@0;1'
        '&family=Mukta:wght@300;400;500;600;700&display=swap" rel="stylesheet">',
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""<style>
html, body, [class*="css"] {{
    font-family: 'Mukta', 'Noto Sans Devanagari', sans-serif;
    color: {INK};
}}
h1, h2, h3 {{
    font-family: 'Tiro Devanagari Hindi', 'Mukta', serif !important;
    color: {INK};
    letter-spacing: 0.2px;
}}

/* ---------- बस्ता हेडर: लाल कपड़े की पट्टी, सिलाई-बॉर्डर ---------- */
.basta-header {{
    background: {BASTA};
    color: {PAPER};
    padding: 1.1rem 1.4rem 1.2rem 1.4rem;
    border-radius: 6px;
    border: 2px dashed rgba(247,240,223,0.55);
    outline: 6px solid {BASTA};
    margin-bottom: 1.2rem;
    box-shadow: 0 3px 0 rgba(43,29,18,0.25);
}}
.basta-header .shirsh {{
    font-family: 'Tiro Devanagari Hindi', serif;
    font-size: 2rem;
    line-height: 1.15;
    margin: 0;
}}
.basta-header .upshirsh {{
    font-size: 1.02rem;
    opacity: 0.92;
    margin-top: 0.25rem;
}}

/* ---------- रजिस्टर पन्ना कार्ड: रूल्ड लाइनें ---------- */
.register-card {{
    background: repeating-linear-gradient(
        {PAGE},
        {PAGE} 30px,
        {RULE} 31px
    );
    border: 1px solid {RULE};
    border-left: 5px solid {BASTA};
    border-radius: 4px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.9rem;
    box-shadow: 1px 2px 6px rgba(43,29,18,0.10);
}}
.register-card .kona {{
    float: right;
    font-size: 0.8rem;
    color: {BASTA};
    border: 1px solid {BASTA};
    padding: 0 6px;
    border-radius: 3px;
    transform: rotate(2deg);
    background: {PAPER};
}}

/* ---------- मुहर-बैज: गोल स्याही-मुहर ---------- */
.muhar-row {{ display: flex; flex-wrap: wrap; gap: 14px; margin: 0.4rem 0 0.8rem 0; }}
.muhar {{
    width: 118px; height: 118px;
    border: 3px double {STAMP_GREEN};
    border-radius: 50%;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    text-align: center;
    color: {STAMP_GREEN};
    background: radial-gradient(circle at 35% 30%, rgba(47,82,51,0.06), transparent 60%), {PAPER};
    transform: rotate(-6deg);
    font-family: 'Tiro Devanagari Hindi', serif;
    box-shadow: inset 0 0 0 4px {PAPER}, inset 0 0 0 5px rgba(47,82,51,0.5);
}}
.muhar .naam {{ font-size: 0.95rem; font-weight: 700; padding: 0 8px; line-height: 1.15; }}
.muhar .tag {{ font-size: 0.62rem; letter-spacing: 1.5px; margin-top: 3px; opacity: 0.8; }}
.muhar.locked {{
    border-color: {RULE};
    color: {RULE};
    box-shadow: inset 0 0 0 4px {PAPER}, inset 0 0 0 5px {RULE};
    transform: rotate(-2deg);
}}
.muhar.dada {{ border-color: {BASTA}; color: {BASTA};
    box-shadow: inset 0 0 0 4px {PAPER}, inset 0 0 0 5px rgba(164,36,59,0.55); }}

/* ---------- छोटे तत्व ---------- */
.chhota-note {{
    font-size: 0.85rem; color: #6B5A44;
    border-top: 1px solid {RULE};
    padding-top: 0.5rem; margin-top: 1rem;
}}
.yaad-box {{
    background: {PAPER};
    border: 1px solid {HALDI};
    border-left: 6px solid {HALDI};
    border-radius: 4px;
    padding: 0.8rem 1rem;
    margin: 0.6rem 0;
}}
.stMarkdown table {{ background: {PAPER}; }}

/* बटन */
.stButton > button[kind="primary"] {{
    background: {BASTA}; color: {PAPER}; border: none;
    font-family: 'Mukta', sans-serif; font-weight: 600;
}}
.stButton > button[kind="primary"]:hover {{ background: #8A1E32; color: {PAPER}; }}

/* मोबाइल */
@media (max-width: 640px) {{
    .basta-header .shirsh {{ font-size: 1.5rem; }}
    .muhar {{ width: 98px; height: 98px; }}
}}
@media (prefers-reduced-motion: reduce) {{
    * {{ transition: none !important; animation: none !important; }}
}}
</style>
""",
        unsafe_allow_html=True,
    )


def basta_header(title: str, subtitle: str = ""):
    """हर पन्ने के ऊपर लाल बस्ते जैसी पट्टी — जैसे पोटली खोली जा रही हो।"""
    sub = f'<div class="upshirsh">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f'<div class="basta-header"><div class="shirsh">{title}</div>{sub}</div>',
        unsafe_allow_html=True,
    )


def register_card(md_html: str, kona: str = ""):
    kona_html = f'<span class="kona">{kona}</span>' if kona else ""
    st.markdown(
        f'<div class="register-card">{kona_html}{md_html}</div>',
        unsafe_allow_html=True,
    )


def muhar_badges(badges: list, earned: set):
    """गोल स्याही-मुहर बैज। earned में शामिल = हरी मुहर; 'दादा स्तर' = लाल।"""
    cells = []
    for b in badges:
        cls = "muhar"
        if b == "दादा स्तर":
            cls += " dada" if b in earned else " locked"
        elif b not in earned:
            cls += " locked"
        tag = "प्राप्त" if b in earned else "बाक़ी"
        cells.append(f'<div class="{cls}"><div class="naam">{b}</div><div class="tag">— {tag} —</div></div>')
    st.markdown(f'<div class="muhar-row">{"".join(cells)}</div>', unsafe_allow_html=True)


def disclaimer():
    st.markdown(
        '<div class="chhota-note">📜 यह ऐप <b>शैक्षणिक जानकारी</b> देता है — यह वकील की क़ानूनी सलाह '
        'का विकल्प नहीं है। बड़े फ़ैसलों (ख़रीद-बिक्री, मुक़दमा) से पहले योग्य अधिवक्ता से परामर्श कीजिए। '
        'सरकारी तिथियाँ/प्रक्रियाएँ बदलती रहती हैं — ताज़ा जानकारी आधिकारिक पोर्टल से मिलाएँ।</div>',
        unsafe_allow_html=True,
    )
