# -*- coding: utf-8 -*-
"""शब्दकोश पन्ना — खोजिए, समझिए"""

import streamlit as st

from data.glossary import GLOSSARY
from modules import ui


def render():
    ui.basta_header("शब्दकोश", "कचहरी-दफ़्तर की भाषा, सीधी हिंदी में")

    q = st.text_input("🔎 शब्द खोजिए (जैसे: खेसरा, दाखिल, कैथी…)", "")
    items = GLOSSARY
    if q.strip():
        ql = q.strip().lower()
        items = [
            g for g in GLOSSARY
            if ql in g["term"].lower() or ql in g["en"].lower() or ql in g["meaning"].lower()
        ]

    st.caption(f"{len(items)} शब्द")
    if not items:
        st.info("यह शब्द अभी सूची में नहीं है — 'पाठशाला' के पाठों में खोजिए, या हमें सुझाइए।")

    for g in items:
        ui.register_card(
            f"<b style='font-size:1.05rem'>{g['term']}</b> "
            f"<span style='opacity:0.65'>· {g['en']}</span><br>{g['meaning']}"
        )

    ui.disclaimer()
