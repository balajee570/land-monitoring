# -*- coding: utf-8 -*-
"""दस्तावेज़ डिकोडर — काग़ज़ की फोटो → सिखाने वाली हिंदी व्याख्या
Provider चुनिए: Claude (Anthropic, तुरंत) या Sarvam (Vision → 105B, batch)।
निजी संस्करण — कोई सीमा/सदस्यता नहीं।
"""

import base64
import io

import requests
import streamlit as st
from PIL import Image

from modules import ui
from modules.progress import get_state, save_profile
from modules.providers import decode_anthropic, decode_sarvam

DEMO_RESULT = """## 📄 यह कौन-सा दस्तावेज़ है
यह **खतियान** (Record of Rights) का पन्ना है — पहचान: ऊपर मौजा/थाना नं. की पंक्ति, सारणीबद्ध कॉलम (खाता, खेसरा, रकबा, चौहद्दी), और पुरानी हस्तलिखित प्रविष्टियाँ। लिपि मुख्यतः देवनागरी है; कुछ प्रविष्टियों में शिरोरेखा टूटी है — **कैथी प्रभाव** की संभावना।

## 🔑 मुख्य जानकारी
| क्षेत्र | पढ़ा गया |
|---|---|
| मौजा | रोसड़ा (थाना नं. — स्पष्ट नहीं) |
| रैयत | रामेसर महतो, पिता बुधन महतो |
| खाता | 87 |
| खेसरा | 1204 |
| रकबा | 0 एकड़ 62 डिसमिल |
| किस्म | धनहर-II |
| चौहद्दी | उ.—पइन, द.—खे.1205, पू.—रास्ता, प.—खे.1203 |

## 🗣️ सरल भाषा में मतलब
यह पन्ना कहता है कि सर्वे के समय रोसड़ा मौजे के खाता 87 में रामेसर महतो के नाम खेसरा 1204 (62 डिसमिल, धान योग्य) दर्ज था। यह **जड़-दस्तावेज़** है — आज के मालिकाना हक़ के लिए इससे आपके नाम तक की कड़ी (वंशावली → बँटवारा → दाखिल-खारिज) जोड़नी होगी। यह अकेला आज का क़ब्ज़ा या चालू जमाबंदी साबित **नहीं** करता।

## 🎓 अगली बार ख़ुद ऐसे पढ़िए
- सबसे ऊपर बायें/मध्य में **मौजा-थाना नं.** खोजिए — पहले यही मिलाइए।
- नाम वाले कॉलम के ठीक बाद का छोटा अंक प्रायः **खाता**, और पंक्ति-दर-पंक्ति बदलता अंक **खेसरा** होता है।
- **रकबा** कॉलम में दो अंक-समूह = एकड़–डिसमिल।
- **चौहद्दी** में 'पइन/रास्ता' जैसे शब्द ज़मीन पर आँख से मिलाए जा सकते हैं।

## ⚠️ ध्यान देने योग्य बातें
- थाना नं. धुँधला है — सर्टिफ़ाइड कॉपी से पुष्टि कीजिए।
- 'रामेसर' आधुनिक काग़ज़ों में 'रामेश्वर' हो सकता है — वर्तनी-एकरूपता (परिमार्जन) आगे ज़रूरी होगी।

## ➡️ सुझाए गए अगले क़दम
1. biharbhumi.bihar.gov.in पर इसी खाता/खेसरा की **वर्तमान जमाबंदी** निकालिए — नाम किसका चल रहा है?
2. bhunaksha पर खेसरा 1204 देखकर **चौहद्दी मिलाइए**।
3. खतियानी रैयत से अपने तक की **वंशावली** काग़ज़ पर उतारिए (पाठ L4.2)।

*(यह डेमो-परिणाम है — असली दस्तावेज़ के लिए ऊपर अपनी फोटो अपलोड कीजिए।)*"""


def _secret(name: str) -> str:
    try:
        if name in st.secrets:
            # cloud Secrets box mein paste ki gayi key mein stray space/newline aam hai
            return str(st.secrets[name]).strip()
    except Exception:
        pass
    return str(st.session_state.get(name, "")).strip()


def _to_png_b64(raw: bytes, filename: str) -> tuple[str, Image.Image]:
    """छवि/PDF → PNG base64 + प्रीव्यू (PDF का पहला पृष्ठ)।"""
    if filename.lower().endswith(".pdf"):
        import fitz  # PyMuPDF

        doc = fitz.open(stream=raw, filetype="pdf")
        pix = doc[0].get_pixmap(dpi=200)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
    else:
        img = Image.open(io.BytesIO(raw))
    img = img.convert("RGB")
    img.thumbnail((1600, 1600))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.standard_b64encode(buf.getvalue()).decode(), img


def render():
    data = get_state()
    ui.basta_header("दस्तावेज़ डिकोडर", "काग़ज़ की फोटो भेजिए — पढ़कर समझाएँगे, और पढ़ना सिखाएँगे")

    ui.register_card(
        "<b>टिप:</b> खतियान/जमाबंदी/केवाला/रसीद की <b>साफ़, सीधी रोशनी वाली</b> फोटो सबसे अच्छा "
        "परिणाम देती है — दिन की रोशनी में, ऊपर से सीधी। धुँधली फोटो = अधूरी पढ़ाई।",
        kona="📷",
    )

    provider = st.radio(
        "AI इंजन चुनिए",
        ["Claude (Anthropic) — तुरंत, एक-कॉल vision", "Sarvam — Vision (batch) → 105B"],
        help="Claude: फोटो सीधे पढ़ता है, ~आधा मिनट। Sarvam: पहले Vision job से पाठ निकलता है (batch — समय लग सकता है), फिर 105B समझाता है।",
    )
    use_sarvam = provider.startswith("Sarvam")

    with st.expander("🔐 API key सेटिंग", expanded=False):
        st.caption(
            "Key `.streamlit/secrets.toml` में रखिए (README देखिए) — या यहाँ इसी सत्र के लिए डालिए। "
            "Key आपके कंप्यूटर से सीधे provider को जाती है।"
        )
        a = st.text_input("ANTHROPIC_API_KEY", type="password", value=st.session_state.get("ANTHROPIC_API_KEY", ""))
        if a:
            st.session_state.ANTHROPIC_API_KEY = a
        s = st.text_input("SARVAM_API_KEY", type="password", value=st.session_state.get("SARVAM_API_KEY", ""))
        if s:
            st.session_state.SARVAM_API_KEY = s

    uploaded = st.file_uploader(
        "दस्तावेज़ चुनिए (JPG / PNG / PDF)", type=["jpg", "jpeg", "png", "pdf"]
    )
    user_note = st.text_input("कुछ बताना चाहें? (वैकल्पिक — जैसे: 'दादा जी के नाम वाली पंक्ति ढूँढिए')")

    col1, col2 = st.columns(2)
    run = col1.button("🔍 पढ़कर समझाइए", type="primary", use_container_width=True)
    demo = col2.button("👀 डेमो देखिए (बिना अपलोड)", use_container_width=True)

    if demo:
        st.markdown("---")
        st.markdown(DEMO_RESULT)
        ui.disclaimer()
        return

    if run:
        if uploaded is None:
            st.warning("पहले दस्तावेज़ की फोटो/PDF अपलोड कीजिए — या 'डेमो देखिए' दबाइए।")
            return

        raw = uploaded.read()
        try:
            if use_sarvam:
                key = _secret("SARVAM_API_KEY")
                if not key:
                    st.error("SARVAM_API_KEY डालिए (ऊपर सेटिंग में) — dashboard.sarvam.ai से मिलेगी।")
                    return
                _, img = _to_png_b64(raw, uploaded.name)
                st.image(img, caption="अपलोड किया गया दस्तावेज़", use_container_width=True)
                with st.spinner("Sarvam Vision job चल रहा है… (batch API — 1–3 मिनट; अधिकतम 5 मिनट प्रतीक्षा)"):
                    result = decode_sarvam(raw, uploaded.name, key, user_note)
            else:
                key = _secret("ANTHROPIC_API_KEY")
                if not key:
                    st.error("ANTHROPIC_API_KEY डालिए (ऊपर सेटिंग में) — console.anthropic.com से मिलेगी।")
                    return
                with st.spinner("काग़ज़ खोला जा रहा है…"):
                    b64, img = _to_png_b64(raw, uploaded.name)
                st.image(img, caption="अपलोड किया गया दस्तावेज़", use_container_width=True)
                with st.spinner("मुंशी जी पढ़ रहे हैं… (~आधा मिनट)"):
                    result = decode_anthropic(b64, key, user_note)

            if not result or not result.strip():
                st.error("पढ़ाई खाली लौटी — दुबारा प्रयास कीजिए या साफ़ फोटो लीजिए।")
                return

            data["decodes_used"] = data.get("decodes_used", 0) + 1
            save_profile(data)
            # session_state mein rakho — lambi batch call ke baad hone wala
            # rerun warna taiyaar result ko chupchaap uda deta tha
            st.session_state["last_decode_md"] = result
        except requests.HTTPError as e:
            st.error(f"AI सेवा से त्रुटि (HTTP {e.response.status_code})। Key/इंटरनेट जाँचिए।")
        except Exception as e:
            st.error(f"कुछ गड़बड़ हुई: {e}")

    saved = st.session_state.get("last_decode_md", "")
    if saved:
        st.markdown("---")
        st.markdown(saved)
        st.download_button(
            "⬇️ व्याख्या सहेजिए (.md)", saved,
            file_name="khatiyan_decode.md", mime="text/markdown",
        )

    ui.disclaimer()
