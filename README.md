# खतियान 📜

**दादा जी पढ़ लेते थे। अब आप पढ़िए।**

Hindi-first Streamlit app jo aapko Indian land records (Bihar focus) **padhna
sikhata hai** — 6-level ka structured course, searchable शब्दकोश, zameen
calculator, aur ek AI **दस्तावेज़ डिकोडर** jo aapke khatiyan/jamabandi/kewala ki
photo ko sirf explain hi nahi karta, **agli baar khud padhne ke surāg bhi
deta hai** (teach-mode).

Personal-use MVP · single user · no auth, no payments, no limits · sab kuch
local (`user_data/` mein progress).

## Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

API keys (sirf decoder ke liye zaroori — baaki app bina key ke poora chalta hai):

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# phir secrets.toml mein apni keys daaliye
```

App in-app **🔐 सेटिंग** expander se bhi keys leta hai (sirf us session ke liye).

## Run

```bash
streamlit run app.py
```

## AI providers

| Provider | Kaisa | Kitna time |
|---|---|---|
| **Claude (Anthropic)** | Single-call vision — photo seedha padhta hai | ~aadha minute |
| **Sarvam** | Vision **batch** job se pehle text nikalta hai, phir `sarvam-105b` samjhata hai | 1–3 minute; 10 pages/PDF cap; 10 req/min rate limit |

- Anthropic key: [console.anthropic.com](https://console.anthropic.com) (~₹3–4/decode)
- Sarvam key: [dashboard.sarvam.ai](https://dashboard.sarvam.ai)

## Troubleshooting

- **PyMuPDF install error** → `pip install --upgrade pip` phir dobara
  `pip install PyMuPDF`. (PDF preview/convert ke liye chahiye.)
- **`sarvamai` missing** → `pip install sarvamai`
- **Port busy** → `streamlit run app.py --server.port 8502`

## Privacy

Documents aapki machine se bahar **sirf aapke chune hue AI provider** ko jaate
hain — aur kahin nahi. Course progress/streak local `user_data/` folder mein
rehta hai; koi analytics/tracking nahi.

## Dev

```bash
pip install -r requirements-dev.txt
python -m pytest tests/ -q       # data integrity tests
python eval_providers.py --dir ./eval_docs --providers anthropic,sarvam
```

> 📜 Yeh app **shaikshanik jaankari** deta hai — vakil ki kanooni salah ka
> vikalp nahi. Bade faisle se pehle yogya adhivakta se mashwara kijiye.
