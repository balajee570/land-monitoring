# -*- coding: utf-8 -*-
"""Data-integrity tests (PLAN.md Phase 3). Run: python -m pytest tests/ -q

Also runnable without pytest: python tests/test_data.py
Streamlit-dependent checks (calculator) skip cleanly when streamlit is absent.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.curriculum import CURRICULUM, FINAL_BADGE, all_lesson_ids, total_lessons
from data.glossary import GLOSSARY
from modules.providers import TEACH_PROMPT

TEACH_HEADINGS = [
    "## 📄 यह कौन-सा दस्तावेज़ है",
    "## 🔑 मुख्य जानकारी",
    "## 🗣️ सरल भाषा में मतलब",
    "## 🎓 अगली बार ख़ुद ऐसे पढ़िए",
    "## ⚠️ ध्यान देने योग्य बातें",
    "## ➡️ सुझाए गए अगले क़दम",
]


def test_lesson_ids_unique_and_count():
    ids = all_lesson_ids()
    assert len(ids) == len(set(ids)), "duplicate lesson ids"
    assert total_lessons() == 15


def test_every_lesson_has_content_yaad_quiz():
    for level in CURRICULUM:
        for lesson in level["lessons"]:
            assert lesson.get("content", "").strip(), f"{lesson['id']}: empty content"
            assert len(lesson.get("yaad_rakhiye", [])) >= 1, f"{lesson['id']}: no yaad_rakhiye"
            assert len(lesson.get("quiz", [])) >= 3, f"{lesson['id']}: fewer than 3 quiz questions"


def test_quiz_answers_valid_and_explained():
    for level in CURRICULUM:
        for lesson in level["lessons"]:
            for i, q in enumerate(lesson["quiz"]):
                assert 0 <= q["answer"] < len(q["options"]), (
                    f"{lesson['id']} q{i}: answer index out of range")
                assert q.get("explain", "").strip(), f"{lesson['id']} q{i}: missing explain"


def test_levels_have_badge_and_intro():
    for level in CURRICULUM:
        assert level.get("badge", "").strip(), f"{level['id']}: empty badge"
        assert level.get("intro", "").strip(), f"{level['id']}: empty intro"
    assert FINAL_BADGE.strip()


def test_glossary_entries_complete():
    assert GLOSSARY, "glossary empty"
    for g in GLOSSARY:
        assert g.get("term", "").strip(), f"glossary entry missing term: {g}"
        assert g.get("en", "").strip(), f"{g.get('term')}: missing en"
        assert g.get("meaning", "").strip(), f"{g.get('term')}: missing meaning"


def test_calculator_math():
    try:
        from modules import calculator
    except ImportError:
        # streamlit not installed in this environment — covered on dev machine
        import pytest
        pytest.skip("streamlit not installed")
    assert calculator.SQFT_PER_ACRE / calculator.SQFT_PER_DECIMAL == 100
    kattha = calculator.KATTHA_PRESETS[
        "मानक बिहार (पटना क्षेत्र) — 1361 वर्ग फुट"]
    assert kattha == 1361.25
    assert kattha * 20.0 == 27225.0     # bigha = 20 × kattha
    assert kattha / 20.0 == 68.0625     # dhur = kattha / 20


def test_teach_prompt_headings():
    for h in TEACH_HEADINGS:
        assert h in TEACH_PROMPT, f"TEACH_PROMPT missing heading: {h}"


if __name__ == "__main__":
    # plain-python runner (no pytest needed)
    failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS  {name}")
            except Exception as e:  # noqa: BLE001
                if type(e).__name__ in ("Skipped", "ImportError", "ModuleNotFoundError"):
                    print(f"SKIP  {name} ({e})")
                else:
                    failed += 1
                    print(f"FAIL  {name}: {e}")
    sys.exit(1 if failed else 0)
