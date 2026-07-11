# -*- coding: utf-8 -*-
"""ज़मीन कैलकुलेटर — बीघा · कट्ठा · धुर · डिसमिल · एकड़ (क्षेत्र-अनुसार)"""

import streamlit as st

from modules import ui

# 1 बीघा = 20 कट्ठा, 1 कट्ठा = 20 धुर  (संरचना पूरे बिहार में समान; *आकार* बदलता है)
SQFT_PER_ACRE = 43560.0
SQFT_PER_DECIMAL = 435.6

# कट्ठे का आकार (वर्ग फुट) — प्रचलित मान; ज़िले/मौजे में भिन्नता संभव
KATTHA_PRESETS = {
    "मानक बिहार (पटना क्षेत्र) — 1361 वर्ग फुट": 1361.25,
    "कई उत्तर-बिहार क्षेत्र — 720 वर्ग फुट": 720.0,
    "कुछ क्षेत्र — 900 वर्ग फुट": 900.0,
    "कुछ क्षेत्र — 1280 वर्ग फुट": 1280.0,
    "अपना मान डालें (कस्टम)": None,
}


def render():
    ui.basta_header("ज़मीन कैलकुलेटर", "बीघा–कट्ठा–धुर ⇄ डिसमिल ⇄ एकड़ — क्षेत्र चुनकर सही हिसाब")

    ui.register_card(
        "<b>ज़रूरी बात:</b> बीघा-कट्ठा की <b>संरचना</b> तय है (1 बीघा = 20 कट्ठा, 1 कट्ठा = 20 धुर), "
        "पर कट्ठे का <b>आकार</b> ज़िले-दर-ज़िले बदलता है। इसीलिए 'कितना बीघा' पूछने से पहले "
        "'किस इलाक़े का कट्ठा' पूछना पड़ता है — सौदों में ठगी अक्सर यहीं होती है। "
        "सरकारी रिकॉर्ड प्रायः <b>एकड़–डिसमिल</b> में होते हैं (1 एकड़ = 100 डिसमिल)।",
        kona="⚠️",
    )

    preset = st.selectbox("कट्ठे का आकार (अपना क्षेत्र चुनिए)", list(KATTHA_PRESETS.keys()))
    kattha_sqft = KATTHA_PRESETS[preset]
    if kattha_sqft is None:
        kattha_sqft = st.number_input(
            "1 कट्ठा = कितने वर्ग फुट?", min_value=100.0, max_value=5000.0, value=1361.25, step=1.0
        )

    dhur_sqft = kattha_sqft / 20.0
    bigha_sqft = kattha_sqft * 20.0

    st.markdown("---")
    mode = st.radio(
        "क्या बदलना है?",
        ["बीघा–कट्ठा–धुर → डिसमिल/एकड़", "डिसमिल → बीघा–कट्ठा–धुर", "एकड़ → सब कुछ"],
        horizontal=False,
    )

    if mode == "बीघा–कट्ठा–धुर → डिसमिल/एकड़":
        c1, c2, c3 = st.columns(3)
        bigha = c1.number_input("बीघा", min_value=0, value=0, step=1)
        kattha = c2.number_input("कट्ठा", min_value=0, value=1, step=1)
        dhur = c3.number_input("धुर", min_value=0.0, value=0.0, step=0.5)
        sqft = bigha * bigha_sqft + kattha * kattha_sqft + dhur * dhur_sqft
    elif mode == "डिसमिल → बीघा–कट्ठा–धुर":
        dec = st.number_input("डिसमिल", min_value=0.0, value=62.0, step=1.0)
        sqft = dec * SQFT_PER_DECIMAL
    else:
        acre = st.number_input("एकड़", min_value=0.0, value=1.0, step=0.05)
        sqft = acre * SQFT_PER_ACRE

    if sqft > 0:
        dec = sqft / SQFT_PER_DECIMAL
        acre = sqft / SQFT_PER_ACRE
        hect = acre * 0.404686
        total_dhur = sqft / dhur_sqft
        b = int(total_dhur // 400)
        k = int((total_dhur % 400) // 20)
        d = total_dhur % 20

        st.markdown("### 📐 परिणाम")
        m1, m2, m3 = st.columns(3)
        m1.metric("वर्ग फुट", f"{sqft:,.0f}")
        m2.metric("डिसमिल", f"{dec:,.2f}")
        m3.metric("एकड़", f"{acre:,.4f}")
        m4, m5, m6 = st.columns(3)
        m4.metric("बीघा–कट्ठा–धुर", f"{b} बी. {k} क. {d:.1f} धु.")
        m5.metric("हेक्टेयर", f"{hect:,.4f}")
        m6.metric("चुना कट्ठा", f"{kattha_sqft:,.0f} वर्ग फुट")

        st.caption(
            f"आधार: 1 कट्ठा = {kattha_sqft:,.2f} वर्ग फुट · 1 धुर = {dhur_sqft:,.2f} वर्ग फुट · "
            f"1 डिसमिल = {SQFT_PER_DECIMAL} वर्ग फुट · 1 एकड़ = 100 डिसमिल"
        )

    ui.disclaimer()
