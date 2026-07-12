# -*- coding: utf-8 -*-
"""AI प्रोवाइडर — Anthropic (Claude Vision) और Sarvam (Vision → 105B)
दोनों एक ही teach-mode हिंदी output देते हैं। config: decoder page पर चुनें।
"""

import io
import os
import re
import tempfile
import zipfile
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout

import requests

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL = "claude-sonnet-4-6"
# API ke anusaar uplabdh model: sarvam-30b, sarvam-105b (sarvam-m deprecated)
SARVAM_CHAT_MODELS = ("sarvam-105b", "sarvam-30b")
SARVAM_CHAT_MODEL = SARVAM_CHAT_MODELS[0]  # purani import-compat ke liye
# batch job kabhi-kabhi atak jaata hai — bina cap ke UI hamesha ke liye latak jaati hai
SARVAM_JOB_TIMEOUT_S = 300

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


def _strip_think(text: str) -> str:
    """Thinking-model output se <think>…</think> hatao — asli jawab bacha rahe."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()


def _html_to_text(md: str) -> str:
    """OCR ke HTML-table markup ko halka plain text banao.

    Sarvam Vision <table><tr><td>… wala markdown lautata hai — tags chat model
    ka aadha token-budget kha jaate hain aur samajh bhi bigaadte hain. Cells ko
    ' | ' se, rows ko nayi line se jodkar saara markup hata do.
    """
    import html as _html

    # OCR har tag alag line par deta hai — cell-band ko ' | ', row-band ko nayi
    # line banao; table/tbody jaise dhaanche-tags nayi line chhodkar hatao.
    text = re.sub(r"(?is)\s*</t[dh]>\s*", " | ", md)
    text = re.sub(r"(?is)\s*</tr>\s*", "\n", text)
    text = re.sub(r"(?is)\s*</?(?:table|thead|tbody|tfoot)[^>]*>\s*", "\n", text)
    text = re.sub(r"(?is)<(?:tr|t[dh])[^>]*>\s*", "", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = _html.unescape(text)
    text = re.sub(r"[ \t]*\|[ \t]*", " | ", text)         # pipe ke aaspaas ek-ek space
    text = re.sub(r"[ \t]*\|[ \t]*(?=\n|$)", "", text)    # row-ant ka faltu pipe
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _resp_summary(resp) -> str:
    """Khaali jawab par debugging ke liye response ka chhota, key-mukt saraansh."""
    try:
        return repr(resp)[:200]
    except Exception:
        return "<unrepr-able response>"


SARVAM_CHAT_URL = "https://api.sarvam.ai/v1/chat/completions"


def _sarvam_chat_http(api_key: str, model: str, messages: list) -> tuple:
    """Seedha REST call. Return (jawab, info) — key kabhi log nahi hoti.

    Do sabak seedhe production ke jawabon se:
    (1) sarvam-105b REASONING model hai — chhota max_tokens poori soch mein
        kharch ho kar content=None + finish_reason='length' deta hai;
    (2) har subscription-tier ki max_tokens seema alag hai (starter: 4096) —
        usse upar API 400 deta hai.
    Isliye 4096 + reasoning_effort=low se shuru; tier-seema 400 ke sandesh se
    padh kar apne-aap clamp ho jaati hai (kisi bhi tier par sahi).
    """
    last_info = "koi call nahi hui"

    def _post(payload):
        nonlocal last_info
        for headers in (
            {"api-subscription-key": api_key},
            {"Authorization": f"Bearer {api_key}"},
        ):
            try:
                r = requests.post(
                    SARVAM_CHAT_URL,
                    headers={**headers, "Content-Type": "application/json"},
                    json=payload,
                    timeout=120,
                )
            except requests.RequestException as e:
                last_info = f"network: {type(e).__name__}: {str(e)[:100]}"
                continue
            if r.status_code in (401, 403):
                last_info = f"HTTP {r.status_code} ({list(headers)[0]}): {r.text[:100]}"
                continue  # doosre auth-header se koshish
            return r
        return None

    base = {"model": model, "messages": messages, "temperature": 0.3}
    variants = [
        {**base, "max_tokens": 4096, "reasoning_effort": "low"},
        {**base, "max_tokens": 4096},   # agar reasoning_effort param reject ho
    ]
    for payload in variants:
        clamped = False
        while True:
            r = _post(payload)
            if r is None:
                break
            if r.status_code != 200:
                last_info = f"HTTP {r.status_code}: {r.text[:150]}"
                if r.status_code == 400:
                    if "deprecated" in r.text.lower():
                        return "", last_info  # model hi uplabdh nahi
                    m = re.search(r"maximum allowed[^:]*:\s*(\d+)", r.text)
                    if m and not clamped:
                        payload = {**payload, "max_tokens": int(m.group(1))}
                        clamped = True
                        continue  # tier-seema ke andar dobara
                break  # agli variant
            try:
                data = r.json()
            except ValueError:
                return "", f"HTTP 200 par JSON nahi: {r.text[:120]}"
            result = _strip_think(_chat_content(data))
            if result:
                return result, "ok"
            try:
                finish = str(data["choices"][0].get("finish_reason"))
            except Exception:
                finish = "?"
            last_info = (f"HTTP 200 khaali content (finish_reason={finish}, "
                         f"max_tokens={payload['max_tokens']})")
            break  # isi payload ko dohrana bekar — agli variant
    return "", last_info


def decode_sarvam(file_bytes: bytes, filename: str, api_key: str, user_note: str) -> str:
    try:
        from sarvamai import SarvamAI
    except ImportError as e:
        raise RuntimeError(
            "sarvamai package नहीं मिला — `pip install sarvamai` चलाइए।"
        ) from e

    client = SarvamAI(api_subscription_key=api_key)

    # Vision job ko hard timeout ke saath chalao — warna atka job UI ko
    # hamesha ke liye latka deta hai (koi result, koi error nahi).
    executor = ThreadPoolExecutor(max_workers=1)
    try:
        future = executor.submit(_sarvam_extract_text, client, file_bytes, filename)
        extracted = future.result(timeout=SARVAM_JOB_TIMEOUT_S)
    except FutureTimeout:
        raise RuntimeError(
            f"Sarvam Vision job {SARVAM_JOB_TIMEOUT_S // 60} मिनट में पूरा नहीं हुआ — "
            "थोड़ी देर बाद दुबारा आज़माइए, या छोटी/साफ़ फोटो (एक पन्ना) भेजिए।"
        )
    finally:
        executor.shutdown(wait=False, cancel_futures=True)

    if not extracted:
        raise RuntimeError("Sarvam Vision से पाठ नहीं निकला — साफ़ फोटो/PDF आज़माइए।")

    # HTML-table markup hatao — tags token-budget khaate hain aur model ko
    # bhatkate hain; saaf text chhota bhi hai aur samajhne mein aasan bhi.
    extracted = _html_to_text(extracted)

    note = f"\n\nउपयोगकर्ता की टिप्पणी: {user_note}" if user_note.strip() else ""
    attempts = []
    # Pehle poora (6000) excerpt; agar reasoning tier-seema par bhi budget kha
    # gaya (finish_reason=length) to chhote excerpt se dobara — kam padhna,
    # kam sochna, jawab ke liye zyada jagah.
    for excerpt_len in (6000, 2500):
        user_msg = (
            "नीचे Sarvam Vision (OCR) से निकाला गया दस्तावेज़-पाठ है। इसी के आधार पर "
            "ऊपर बताए ढाँचे में सिखाइए। ('अगली बार ख़ुद ऐसे पढ़िए' खंड में दस्तावेज़ के "
            "ढाँचे/शब्द-सुराग़ों पर आधारित संकेत दीजिए।)\n\n"
            f"--- निकाला गया पाठ ---\n{extracted[:excerpt_len]}\n--- समाप्त ---" + note
        )
        messages = [
            {"role": "system", "content": TEACH_PROMPT},
            {"role": "user", "content": user_msg},
        ]
        got_length = False
        for model in SARVAM_CHAT_MODELS:
            result, info = _sarvam_chat_http(api_key, model, messages)
            if result:
                return result
            attempts.append(f"{model}@{excerpt_len}: {info}")
            got_length = got_length or "finish_reason=length" in info
        if not got_length:
            break  # chhota excerpt sirf length-samasya mein madad karta hai

    # Explanation nahi mili — OCR paath to mila hai, use hi dikha dein
    detail = " · ".join(attempts) if attempts else "कोई प्रयास दर्ज नहीं"
    return (
        "## ⚠️ ध्यान देने योग्य बातें\n"
        "AI व्याख्या नहीं मिल पाई — नीचे दस्तावेज़ से निकाला गया कच्चा पाठ है, "
        "ताकि आपकी मेहनत बेकार न जाए।\n\n"
        f"<small>तकनीकी विवरण (support के लिए): {detail}</small>\n\n"
        "---\n\n" + extracted[:8000]
    )
