# -*- coding: utf-8 -*-
"""खतियान — मुख्य ऐप शेल (nav + होम पन्ना)"""

import streamlit as st

st.set_page_config(page_title="खतियान", page_icon="📜", layout="centered")

from data.curriculum import CURRICULUM, FINAL_BADGE, total_lessons
from modules import calculator, decoder, glossary_page, lessons, ui
from modules.progress import (
    completion_pct,
    current_streak,
    earned_badges,
    get_state,
)

ui.inject_css()

NAV_HOME = "🏠 होम"
NAV_LESSONS = "📚 पाठशाला"
NAV_DECODER = "🔍 दस्तावेज़ डिकोडर"
NAV_GLOSSARY = "📖 शब्दकोश"
NAV_CALC = "🧮 ज़मीन कैलकुलेटर"

with st.sidebar:
    st.markdown(
        f"""<div style="font-family:'Tiro Devanagari Hindi',serif;
        font-size:1.9rem;color:{ui.BASTA};line-height:1.1;">खतियान</div>
        <div style="font-size:0.9rem;opacity:0.85;margin-bottom:0.8rem;">
        दादा जी पढ़ लेते थे। अब आप पढ़िए।</div>""",
        unsafe_allow_html=True,
    )
    nav = st.radio(
        "पन्ना चुनिए",
        [NAV_HOME, NAV_LESSONS, NAV_DECODER, NAV_GLOSSARY, NAV_CALC],
        label_visibility="collapsed",
    )
    st.caption("संस्करण 0.1 · निजी उपयोग")


def _home():
    data = get_state()
    completed = set(data.get("completed", []))

    ui.basta_header("खतियान", "दादा जी पढ़ लेते थे। अब आप पढ़िए।")

    m1, m2, m3 = st.columns(3)
    m1.metric("🔥 स्ट्रीक", f"{current_streak(data)} दिन")
    m2.metric("📚 पाठ पूर्ण", f"{len(completed)}/{total_lessons()}")
    m3.metric("🔍 डिकोड किए", data.get("decodes_used", 0))

    st.progress(completion_pct(data))
    st.caption("पाठशाला प्रगति")

    # बैज दीवार — L6 का बैज ही FINAL_BADGE है, दोहराव न हो
    wall = [lv["badge"] for lv in CURRICULUM]
    if FINAL_BADGE not in wall:
        wall.append(FINAL_BADGE)
    ui.muhar_badges(wall, earned_badges(data))

    ui.register_card(
        "<b>📚 पाठशाला</b><br>छह स्तर, पंद्रह पाठ — काग़ज़ पहचानने से 'दादा स्तर' तक। "
        "हर पाठ के बाद छोटा अभ्यास, हर स्तर पर मुहर।",
        kona="१",
    )
    ui.register_card(
        "<b>🔍 दस्तावेज़ डिकोडर</b><br>खतियान/जमाबंदी/केवाला की फोटो भेजिए — AI पढ़कर "
        "समझाएगा, और अगली बार ख़ुद पढ़ने के सुराग़ भी देगा।",
        kona="२",
    )
    ui.register_card(
        "<b>🧮 ज़मीन कैलकुलेटर</b><br>बीघा–कट्ठा–धुर ⇄ डिसमिल ⇄ एकड़ — अपने ज़िले का "
        "कट्ठा चुनकर सही हिसाब कीजिए।",
        kona="३",
    )

    ui.disclaimer()


if nav == NAV_LESSONS:
    lessons.render()
elif nav == NAV_DECODER:
    decoder.render()
elif nav == NAV_GLOSSARY:
    glossary_page.render()
elif nav == NAV_CALC:
    calculator.render()
else:
    _home()
