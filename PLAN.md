# KHATIYAN (खतियान) — Build Plan for Claude Code

> **Paste this to Claude Code as the first message:**
> "Read PLAN.md fully. Verify existing files against §1 (do NOT regenerate them). Then execute Phase 1 → Phase 4 in order, running the QA gate in Phase 3 before finishing. Ask me only if a decision is not covered by this plan."

---

## 0. Project context

- **What:** Hindi-first Streamlit app that (a) teaches users to read Indian land records (Bihar focus) through a structured course, and (b) decodes uploaded document photos using AI in a "teach-mode" (explains AND shows how to self-read next time).
- **Brand:** खतियान · Tagline: **"दादा जी पढ़ लेते थे। अब आप पढ़िए।"**
- **Scope of this build:** Personal-use MVP. Single user. **No auth, no payments, no usage limits.** Runs locally: `streamlit run app.py`. Python 3.11+.
- **All user-facing text is Hindi.** Code identifiers/comments may be English.

---

## 1. Current state — files ALREADY WRITTEN (source of truth, do not regenerate)

```
khatiyan/
├── .streamlit/config.toml      ✅ theme (aged-paper palette)
├── requirements.txt            ✅ streamlit, requests, Pillow, PyMuPDF, sarvamai
├── data/
│   ├── curriculum.py           ✅ 6 levels · 15 lessons · full Hindi content + ~50 MCQs
│   │                              exports: CURRICULUM, all_lesson_ids(), total_lessons(), FINAL_BADGE
│   └── glossary.py             ✅ 32 terms · exports: GLOSSARY
└── modules/
    ├── ui.py                   ✅ design system: inject_css(), basta_header(), register_card(),
    │                              muhar_badges(badges, earned), disclaimer()
    ├── progress.py             ✅ JSON persistence (user_data/*.json): get_state(), save_profile(),
    │                              touch_today(), current_streak(), mark_lesson_done(),
    │                              earned_badges(), completion_pct()
    ├── lessons.py              ✅ render() — level/lesson picker, content, quiz engine
    ├── calculator.py           ✅ render() — bigha/kattha/dhur ⇄ decimal/acre, district presets
    ├── glossary_page.py        ✅ render() — searchable glossary cards
    ├── providers.py            ✅ TEACH_PROMPT + decode_anthropic() + decode_sarvam()
    └── decoder.py              ✅ render() — provider radio, upload, demo mode, download button
```

**Missing (your job):** `app.py`, `README.md`, `.streamlit/secrets.toml.example`, `.gitignore`, `tests/test_data.py`, `eval_providers.py`.

Rule: if any existing file has a bug, fix minimally; never rewrite lesson content in `data/curriculum.py` (it is domain-reviewed).

---

## 2. Design system (use for ALL new UI)

**Palette** (already in `modules/ui.py` + `config.toml`):

| Token | Hex | Use |
|---|---|---|
| INK स्याही | `#2B1D12` | text |
| PAPER पुराना कागज़ | `#F7F0DF` | app background |
| PAGE रजिस्टर पन्ना | `#EFE4CB` | cards/secondary bg |
| BASTA बस्ता लाल | `#A4243B` | primary accent, header band |
| STAMP हरा | `#2F5233` | success, earned badges |
| HALDI | `#C99700` | highlights, "याद रखिए" box |
| RULE रेखा | `#C9B893` | borders, ruled lines |

**Type:** display = *Tiro Devanagari Hindi*, body = *Mukta* (Google Fonts, injected in `inject_css()`).

**Signature elements (reuse, don't invent new ones):** `basta_header()` red cloth band with stitched dashed border on every page; `register_card()` ruled-paper cards; `muhar_badges()` circular ink-stamp badges (green earned / faded locked / red for दादा स्तर).

**Copy rules:** simple respectful Hindi ("आप"), sentence-length lines, active verbs on buttons ("पढ़कर समझाइए", not "Submit"). Every page ends with `ui.disclaimer()`.

---

## 3. Phase plan

### Phase 1 — App shell: `app.py`

```python
st.set_page_config(page_title="खतियान", page_icon="📜", layout="centered")
```
- Call `ui.inject_css()` once at top.
- Sidebar: app name (styled), tagline, then `st.radio` nav with EXACTLY these labels:
  `🏠 होम` · `📚 पाठशाला` · `🔍 दस्तावेज़ डिकोडर` · `📖 शब्दकोश` · `🧮 ज़मीन कैलकुलेटर`
- Route: पाठशाला→`lessons.render()`, डिकोडर→`decoder.render()`, शब्दकोश→`glossary_page.render()`, कैलकुलेटर→`calculator.render()`.
- **होम page (build inline in app.py):**
  1. `basta_header("खतियान", "दादा जी पढ़ लेते थे। अब आप पढ़िए।")`
  2. Metrics row (3 × `st.metric`): 🔥 स्ट्रीक (`current_streak`), 📚 पाठ पूर्ण (`len(completed)/total_lessons()` as "n/15"), 🔍 डिकोड किए (`decodes_used`)
  3. `st.progress(completion_pct(data))` with caption "पाठशाला प्रगति"
  4. Badge wall: `muhar_badges([lv["badge"] for lv in CURRICULUM] + [FINAL_BADGE], earned_badges(data))`
  5. Three `register_card`s introducing पाठशाला / डिकोडर / कैलकुलेटर (2 lines each, Hindi)
  6. `ui.disclaimer()`
- Sidebar footer caption: `संस्करण 0.1 · निजी उपयोग` 

### Phase 2 — Packaging & DX

1. `.streamlit/secrets.toml.example`:
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-..."   # console.anthropic.com
   SARVAM_API_KEY = "..."             # dashboard.sarvam.ai
   ```
2. `.gitignore`: `user_data/`, `.streamlit/secrets.toml`, `__pycache__/`, `*.pyc`, `.venv/`
3. `README.md` (Hinglish, concise): what it is; setup (`python -m venv .venv` → activate → `pip install -r requirements.txt`); copy secrets example → `secrets.toml`, add keys (app also accepts keys via in-app सेटिंग expander for the session); run `streamlit run app.py`; provider notes (Claude = instant single-call vision; Sarvam = Vision **batch** job 1–3 min, 10 pages/PDF cap, 10 req/min rate limit, then 105B explains); troubleshooting (PyMuPDF install, `sarvamai` missing → pip install, port busy → `--server.port 8502`); privacy line (documents leave the machine ONLY to the chosen AI provider; progress stays local in `user_data/`).

### Phase 3 — QA gate (must pass before done)

1. `python -m py_compile` on every `.py` file.
2. Create `tests/test_data.py` (runnable via `python -m pytest tests/ -q` — add `pytest` to a new `requirements-dev.txt`, NOT to runtime requirements):
   - all lesson ids unique; `total_lessons() == 15`
   - every lesson has non-empty `content`, ≥1 `yaad_rakhiye`, ≥3 quiz questions
   - every quiz `answer` index is valid for its `options`; every question has `explain`
   - every level has non-empty `badge`, `intro`; GLOSSARY entries all have term/en/meaning
   - calculator math: `SQFT_PER_ACRE/SQFT_PER_DECIMAL == 100`; for preset 1361.25: bigha=20×kattha, dhur=kattha/20
   - `providers.TEACH_PROMPT` contains all six section headings (listed in §4)
3. Manual checklist (print at end for the human): app boots; complete L1.1 quiz → balloons → होम shows 1/15 + streak 1; restart app → progress persisted; decoder demo button renders; each provider path errors gracefully without key (Hindi error, no traceback); PDF upload previews page 1; download button yields .md.

### Phase 4 — Eval harness: `eval_providers.py`

CLI: `python eval_providers.py --dir ./eval_docs --providers anthropic,sarvam`
- For each file (jpg/png/pdf) × provider: call the same functions in `modules/providers.py`; record `file, provider, ok, latency_s, chars_out, error`.
- Keys from env `ANTHROPIC_API_KEY` / `SARVAM_API_KEY`; skip a provider (with warning) if key absent.
- Respect Sarvam's 10 req/min: `time.sleep(7)` between Sarvam calls.
- Write `eval_results.csv` + print a summary table (per provider: success rate, median latency). No pass/fail judgment — the human compares outputs manually.

### Phase 5 — Backlog (do NOT build unless explicitly asked)

Kaithi practice module (Noto Sans Kaithi renders Unicode block U+11080–110CF); वंशावली builder → PDF export; voice Q&A (Sarvam Saaras STT + Bulbul TTS); multi-profile switcher; deploy (Streamlit Cloud / HF Space, private).

---

## 4. Provider contracts (already implemented — reference only)

- **Anthropic:** POST `https://api.anthropic.com/v1/messages`, model `claude-sonnet-4-6`, headers `x-api-key`, `anthropic-version: 2023-06-01`; image = base64 PNG (long edge ≤1600px); `system=TEACH_PROMPT`; `max_tokens=2000`. ~₹3–4/decode.
- **Sarvam:** `sarvamai` SDK → `document_intelligence.create_job(language="hi-IN", output_format="md")` → `upload_file` → `start` → `wait_until_complete` → `download_output` (ZIP; prefer `.md`, fallback `.html`) → `chat.completions(model="sarvam-105b", temperature=0.3, max_tokens=2000)` with extracted text (≤12,000 chars) — batch latency; surface "1–3 मिनट" in UI copy.
- **TEACH_PROMPT invariant:** output must keep EXACTLY these headings (UI/markdown depends on them):
  `## 📄 यह कौन-सा दस्तावेज़ है` · `## 🔑 मुख्य जानकारी` · `## 🗣️ सरल भाषा में मतलब` · `## 🎓 अगली बार ख़ुद ऐसे पढ़िए` · `## ⚠️ ध्यान देने योग्य बातें` · `## ➡️ सुझाए गए अगले क़दम`
  Plus rules: no fabrication — unclear fields are written as "स्पष्ट नहीं"; always includes not-legal-advice framing.

---

## 5. Conventions & guardrails

- UTF-8 everywhere; Devanagari strings must never be escaped/mangled.
- Wrap all network calls in try/except → friendly Hindi `st.error`, never a raw traceback to the user.
- Never print/log/echo API keys; never commit `secrets.toml`.
- No new runtime dependencies beyond §1 without stating why.
- `st.session_state` keys in use: `profile`, `ANTHROPIC_API_KEY`, `SARVAM_API_KEY`, quiz widget keys `quiz_<lesson_id>_<i>`.
- Keep functions small; prefer editing existing modules over adding parallel ones.

## 6. Acceptance criteria (definition of done)

1. Fresh venv: `pip install -r requirements.txt` → `streamlit run app.py` boots clean.
2. All five pages render; होम metrics/badges reflect real state; lesson→quiz→badge→streak flow persists across app restarts (`user_data/default.json`).
3. Decoder: demo works offline; with a real key each provider returns the six-section Hindi markdown or a graceful Hindi error.
4. `pytest tests/ -q` green; py_compile clean.
5. README instructions verified by actually following them.
