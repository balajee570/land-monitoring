# -*- coding: utf-8 -*-
"""AI प्रोवाइडर — Anthropic (Claude Vision) और Sarvam (Vision → 105B)
दोनों एक ही teach-mode हिंदी output देते हैं। config: decoder page पर चुनें।
"""

import io
import os
import tempfile
import zipfile

import requests

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL = "claude-sonnet-4-6"
SARVAM_CHAT_MODEL = "sarvam-105b"

TEACH_PROMPT = """आप 'खतियान' ऐप के भूमि-दस्तावेज़ शिक्षक हैं — बिहार/हिंदी पट्टी के ज़मीन के काग़ज़ों (खतियान, जमाबंदी, केवाला, लगान रसीद, एल.पी.सी., नक्शा) के विशेषज्ञ। आपका काम सिर्फ़ बताना नहीं, **पढ़ना सिखाना** है।

सरल हिंदी में, ठीक इन्हीं शीर्षकों के साथ markdown में उत्तर दीजिए:

## 📄 यह कौन-सा दस्तावेज़ है
(प्रकार + कैसे पहचाना। लिपि कैथी/उर्दू लगे तो साफ़ बताइए।)

## 🔑 मुख्य जानकारी
(तालिका: रैयत/नाम, मौजा, थाना नं., खाता, खेसरा, रकबा, किस्म, चौहद्दी, तिथि — जो मिले बस वही। **अनुमान मत लगाइए**; अस्पष्ट को 'स्पष्ट नहीं' लिखिए।)

## 🗣️ सरल भाषा में मतलब
(3–5 वाक्य: यह काग़ज़ क्या कहता/साबित करता है, और क्या नहीं।)

## 🎓 अगली बार ख़ुद ऐसे पढ़िए
(3–4 ठोस सुराग़ — ताकि उपयोगकर्ता अगला काग़ज़ बिना मदद पढ़ सके।)

## ⚠️ ध्यान देने योग्य बातें
(विसंगति/जोखिम/कमी; कुछ न हो तो 'कोई स्पष्ट चिंता नहीं दिखी'।)

## ➡️ सुझाए गए अगले क़दम
(2–3 व्यावहारिक क़दम — कौन-सा पोर्टल/कार्यालय, क्या मिलान करें।)

नियम: अटकल नहीं; पढ़ न पाने को ईमानदारी से स्वीकारिए। यह क़ानूनी सलाह नहीं — जटिल मामले में अधिवक्ता से मिलने को कहिए।"""


# ---------------- Anthropic: एक ही कॉल में देखना + सिखाना ----------------

def decode_anthropic(b64_png: str, api_key: str, user_note: str) -> str:
    note = f"\n\nउपयोगकर्ता की टिप्पणी: {user_note}" if user_note.strip() else ""
    payload = {
        "model": ANTHROPIC_MODEL,
        "max_tokens": 2000,
        "system": TEACH_PROMPT,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": "image/png", "data": b64_png},
                    },
                    {"type": "text", "text": "कृपया इस दस्तावेज़ को पढ़कर सिखाइए।" + note},
                ],
            }
        ],
    }
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    r = requests.post(ANTHROPIC_URL, headers=headers, json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()
    return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")


# ---------------- Sarvam: Vision (batch job) → 105B व्याख्या ----------------

def _sarvam_extract_text(client, file_bytes: bytes, filename: str) -> str:
    """Sarvam Vision Document Intelligence job: upload → start → wait → ZIP → md/html text.
    (docs.sarvam.ai के job-flow के अनुसार; batch API होने से समय लग सकता है)"""
    job = client.document_intelligence.create_job(language="hi-IN", output_format="md")
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, filename or "document.png")
        with open(path, "wb") as f:
            f.write(file_bytes)
        job.upload_file(path)
        job.start()
        job.wait_until_complete()
        out_zip = os.path.join(td, "output.zip")
        job.download_output(out_zip)

        text_parts = []
        with zipfile.ZipFile(out_zip) as z:
            names = z.namelist()
            md_names = [n for n in names if n.lower().endswith(".md")]
            html_names = [n for n in names if n.lower().endswith(".html")]
            # pehle .md; agar sab .md khaali nikle to .html se koshish
            for group in (md_names, html_names):
                for n in group:
                    part = z.read(n).decode("utf-8", errors="replace").strip()
                    if part:
                        text_parts.append(part)
                if text_parts:
                    break
    return "\n\n".join(text_parts).strip()


def _chat_content(resp) -> str:
    """SDK response se text nikaalo — object/dict/parts-list sab shapes handle."""
    try:
        choice = resp.choices[0]
    except (AttributeError, TypeError):
        choice = resp["choices"][0]
    msg = getattr(choice, "message", None)
    if msg is None and isinstance(choice, dict):
        msg = choice.get("message", {})
    content = getattr(msg, "content", None)
    if content is None and isinstance(msg, dict):
        content = msg.get("content")
    if isinstance(content, list):
        content = "".join(
            p.get("text", "") if isinstance(p, dict) else str(p) for p in content
        )
    return (content or "").strip()


def decode_sarvam(file_bytes: bytes, filename: str, api_key: str, user_note: str) -> str:
    try:
        from sarvamai import SarvamAI
    except ImportError as e:
        raise RuntimeError(
            "sarvamai package नहीं मिला — `pip install sarvamai` चलाइए।"
        ) from e

    client = SarvamAI(api_subscription_key=api_key)

    extracted = _sarvam_extract_text(client, file_bytes, filename)
    if not extracted:
        raise RuntimeError("Sarvam Vision से पाठ नहीं निकला — साफ़ फोटो/PDF आज़माइए।")

    note = f"\n\nउपयोगकर्ता की टिप्पणी: {user_note}" if user_note.strip() else ""
    user_msg = (
        "नीचे Sarvam Vision (OCR) से निकाला गया दस्तावेज़-पाठ है। इसी के आधार पर "
        "ऊपर बताए ढाँचे में सिखाइए। ('अगली बार ख़ुद ऐसे पढ़िए' खंड में दस्तावेज़ के "
        "ढाँचे/शब्द-सुराग़ों पर आधारित संकेत दीजिए।)\n\n"
        f"--- निकाला गया पाठ ---\n{extracted[:12000]}\n--- समाप्त ---" + note
    )
    result = ""
    for _attempt in range(2):  # khaali jawab par ek baar dubara koshish
        resp = client.chat.completions(
            model=SARVAM_CHAT_MODEL,
            messages=[
                {"role": "system", "content": TEACH_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.3,
            max_tokens=2000,
        )
        result = _chat_content(resp)
        if result:
            return result

    # 105B khaali lauta — OCR paath to mila hai, use hi dikha dein
    return (
        "## ⚠️ ध्यान देने योग्य बातें\n"
        "AI व्याख्या इस बार खाली लौटी (दो प्रयासों के बाद) — थोड़ी देर बाद फिर "
        "आज़माइए। नीचे दस्तावेज़ से निकाला गया कच्चा पाठ है, ताकि आपकी मेहनत "
        "बेकार न जाए:\n\n---\n\n" + extracted[:8000]
    )
