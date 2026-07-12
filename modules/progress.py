# -*- coding: utf-8 -*-
"""प्रगति — प्रोफ़ाइल, स्ट्रीक, बैज (लोकल JSON में सहेजा जाता है)"""

import json
import os
from datetime import date, timedelta

import streamlit as st

from data.curriculum import CURRICULUM, total_lessons, FINAL_BADGE

DATA_DIR = "user_data"


def _path(profile: str) -> str:
    safe = "".join(c for c in profile if c.isalnum() or c in ("_", "-")) or "default"
    return os.path.join(DATA_DIR, f"{safe}.json")


def load_profile(profile: str) -> dict:
    os.makedirs(DATA_DIR, exist_ok=True)
    p = _path(profile)
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"name": profile, "completed": [], "active_days": [], "decodes_used": 0, "premium": False}


def save_profile(data: dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(_path(data.get("name", "default")), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def touch_today(data: dict):
    today = date.today().isoformat()
    if today not in data["active_days"]:
        data["active_days"].append(today)
        save_profile(data)


def current_streak(data: dict) -> int:
    days = set(data.get("active_days", []))
    if not days:
        return 0
    streak, d = 0, date.today()
    # आज सक्रिय नहीं तो कल से गिनें (streak टूटा नहीं माना जाए)
    if d.isoformat() not in days:
        d = d - timedelta(days=1)
    while d.isoformat() in days:
        streak += 1
        d = d - timedelta(days=1)
    return streak


def mark_lesson_done(data: dict, lesson_id: str):
    if lesson_id not in data["completed"]:
        data["completed"].append(lesson_id)
        save_profile(data)


def earned_badges(data: dict) -> set:
    done = set(data.get("completed", []))
    earned = set()
    for level in CURRICULUM:
        if all(l["id"] in done for l in level["lessons"]):
            earned.add(level["badge"])
    if len(done) >= total_lessons():
        earned.add(FINAL_BADGE)
    return earned


def completion_pct(data: dict) -> float:
    return len(set(data.get("completed", []))) / max(total_lessons(), 1)


def get_state() -> dict:
    """session_state में प्रोफ़ाइल तैयार रखें।"""
    if "profile" not in st.session_state:
        st.session_state.profile = load_profile("default")
    return st.session_state.profile
