# -*- coding: utf-8 -*-
"""पाठशाला — पाठ-प्लेयर और क्विज़ इंजन"""

import streamlit as st

from data.curriculum import CURRICULUM
from modules import ui
from modules.progress import get_state, mark_lesson_done, earned_badges


def _quiz(lesson: dict, data: dict):
    """क्विज़: सारे उत्तर चुनिए → 'जाँचें' → पास (सभी सही) पर पाठ पूर्ण।"""
    st.markdown("#### ✍️ अभ्यास — जाँचिए कि पाठ बैठा या नहीं")
    qs = lesson["quiz"]
    key_base = f"quiz_{lesson['id']}"

    answers = []
    for i, q in enumerate(qs):
        st.markdown(f"**प्रश्न {i+1}.** {q['q']}")
        choice = st.radio(
            "उत्तर चुनिए",
            options=list(range(len(q["options"]))),
            format_func=lambda x, opts=q["options"]: opts[x],
            key=f"{key_base}_{i}",
            index=None,
            label_visibility="collapsed",
        )
        answers.append(choice)
        st.write("")

    if st.button("उत्तर जाँचें", type="primary", key=f"{key_base}_check"):
        if any(a is None for a in answers):
            st.warning("पहले सभी प्रश्नों के उत्तर चुनिए।")
            return
        correct = 0
        for i, q in enumerate(qs):
            if answers[i] == q["answer"]:
                correct += 1
                st.success(f"प्रश्न {i+1}: सही ✅ — {q['explain']}")
            else:
                st.error(
                    f"प्रश्न {i+1}: सही उत्तर — **{q['options'][q['answer']]}**। {q['explain']}"
                )
        if correct == len(qs):
            mark_lesson_done(data, lesson["id"])
            st.balloons()
            st.success(f"🎉 पाठ **{lesson['title']}** पूर्ण! प्रगति सहेज ली गई।")
        else:
            st.info(f"{correct}/{len(qs)} सही। व्याख्याएँ पढ़कर दुबारा प्रयास कीजिए — यही सीखना है।")


def render():
    data = get_state()
    done = set(data.get("completed", []))
    earned = earned_badges(data)

    ui.basta_header("पाठशाला", "स्तर-दर-स्तर — कागज़ पहचानने से 'दादा स्तर' तक")

    # स्तर चुनें
    level_titles = [lv["title"] for lv in CURRICULUM]
    default_idx = 0
    for i, lv in enumerate(CURRICULUM):
        if not all(l["id"] in done for l in lv["lessons"]):
            default_idx = i
            break
    sel = st.selectbox("स्तर चुनिए", level_titles, index=default_idx)
    level = CURRICULUM[level_titles.index(sel)]

    badge_state = "✅ मुहर प्राप्त" if level["badge"] in earned else f"🔓 पूरा करने पर मुहर: **{level['badge']}**"
    ui.register_card(f"<p style='margin:0'>{level['intro']}<br><small>{badge_state}</small></p>", kona=level["id"])

    # पाठ चुनें
    lesson_titles = [
        ("✅ " if l["id"] in done else "▫️ ") + f"{l['id']} · {l['title']}" for l in level["lessons"]
    ]
    lsel = st.radio("पाठ", lesson_titles, label_visibility="collapsed")
    lesson = level["lessons"][lesson_titles.index(lsel)]

    st.markdown("---")
    st.markdown(f"### {lesson['title']}")
    st.markdown(lesson["content"])

    yaad = "".join(f"<li>{y}</li>" for y in lesson["yaad_rakhiye"])
    st.markdown(
        f'<div class="yaad-box"><b>📌 याद रखिए</b><ul style="margin:0.3rem 0 0 1rem">{yaad}</ul></div>',
        unsafe_allow_html=True,
    )

    st.markdown("---")
    if lesson["id"] in done:
        st.success("यह पाठ आप पूरा कर चुके हैं — चाहें तो अभ्यास दोहराइए।")
    _quiz(lesson, data)

    ui.disclaimer()
