"""Zero-dependency PDF text extractor.

A pure-stdlib fallback used when ``pdfplumber`` is not installed. It handles the
kind of bilingual (Devanagari + Latin) government PDFs that Indian jamabandi /
LPC documents use, where glyphs are mapped through font ``/Differences`` arrays
(``uniXXXX`` names) or ``ToUnicode`` CMaps.

This is intentionally small and forgiving: it decodes FlateDecode content
streams, walks the text-showing operators (``Tj`` / ``TJ``) while tracking the
current font and text position, then groups runs into lines by their Y
coordinate. It is not a full PDF renderer, but it recovers readable text from
the common single-column government layouts.
"""
from __future__ import annotations

import re
import zlib
from typing import Dict, List, Optional, Tuple

# Devanagari combining vowel signs (matras). Some PDFs emit the matra glyph
# *before* the consonant it attaches to; we re-order those so the text reads
# correctly (e.g. the raw "िज" -> "जि").
_PRE_MATRA = "ि"  # only the "i" matra renders before its consonant


def _decompress(raw: bytes) -> Optional[bytes]:
    try:
        return zlib.decompress(raw)
    except Exception:
        # Some streams are not Flate encoded (or are already plain); return as-is
        return raw


def _parse_objects(data: bytes) -> Dict[int, bytes]:
    objs: Dict[int, bytes] = {}
    for m in re.finditer(rb"(\d+)\s+(\d+)\s+obj(.*?)endobj", data, re.S):
        objs[int(m.group(1))] = m.group(3)
    return objs


def _get_stream(body: bytes) -> Optional[bytes]:
    m = re.search(rb"stream\r?\n(.*?)endstream", body, re.S)
    if not m:
        return None
    return _decompress(m.group(1))


def _build_differences_map(body: bytes) -> Optional[Dict[int, str]]:
    """Decode a font /Encoding /Differences array into {code: unicode char}."""
    m = re.search(rb"/Differences\s*\[(.*?)\]", body, re.S)
    if not m:
        return None
    enc: Dict[int, str] = {}
    code = 0
    for tok in re.finditer(rb"(\d+)|/([^\s/\]]+)", m.group(1)):
        if tok.group(1):
            code = int(tok.group(1))
        else:
            name = tok.group(2).decode("latin-1")
            uni = re.match(r"uni([0-9A-Fa-f]{4})", name)
            if uni:
                enc[code] = chr(int(uni.group(1), 16))
            elif name == "space":
                enc[code] = " "
            elif name in ("period", "comma", "hyphen", "colon", "slash"):
                enc[code] = {"period": ".", "comma": ",", "hyphen": "-",
                             "colon": ":", "slash": "/"}[name]
            else:
                enc[code] = ""
            code += 1
    return enc


def _build_tounicode_map(cmap: bytes) -> Dict[int, str]:
    mapping: Dict[int, str] = {}
    for block in re.finditer(rb"beginbfchar(.*?)endbfchar", cmap, re.S):
        for line in block.group(1).split(b"\n"):
            hexes = re.findall(rb"<([0-9A-Fa-f]+)>", line)
            if len(hexes) >= 2:
                src = int(hexes[0], 16)
                try:
                    dst = bytes.fromhex(hexes[1].decode()).decode("utf-16-be", "replace")
                except ValueError:
                    continue
                mapping[src] = dst
    for block in re.finditer(rb"beginbfrange(.*?)endbfrange", cmap, re.S):
        for line in block.group(1).split(b"\n"):
            hexes = re.findall(rb"<([0-9A-Fa-f]+)>", line)
            if len(hexes) >= 3:
                a, b, d = int(hexes[0], 16), int(hexes[1], 16), int(hexes[2], 16)
                for c in range(a, b + 1):
                    mapping[c] = chr(d + (c - a))
    return mapping


def _build_fonts(objs: Dict[int, bytes]) -> Dict[int, Optional[Dict[int, str]]]:
    """Return {font_obj_num: code->char map or None (means MacRoman/latin)}."""
    fonts: Dict[int, Optional[Dict[int, str]]] = {}
    for num, body in objs.items():
        if b"/Font" not in body or b"/BaseFont" not in body:
            continue
        diff = _build_differences_map(body)
        if diff is not None:
            fonts[num] = diff
            continue
        tu = re.search(rb"/ToUnicode\s+(\d+)\s+\d+\s+R", body)
        if tu and int(tu.group(1)) in objs:
            cmap = _get_stream(objs[int(tu.group(1))])
            if cmap:
                fonts[num] = _build_tounicode_map(cmap)
                continue
        fonts[num] = None  # fall back to MacRoman decode
    return fonts


def _resolve_font_dict(body: bytes, objs: Dict[int, bytes]) -> Dict[str, int]:
    """Map resource font names (e.g. 'TT1') -> font object number."""
    m = re.search(rb"/Font\s*<<(.*?)>>", body, re.S)
    if not m:
        r = re.search(rb"/Resources\s+(\d+)\s+\d+\s+R", body)
        if r and int(r.group(1)) in objs:
            return _resolve_font_dict(objs[int(r.group(1))], objs)
        return {}
    fd: Dict[str, int] = {}
    for x in re.finditer(rb"/(\w+)\s+(\d+)\s+\d+\s+R", m.group(1)):
        fd[x.group(1).decode()] = int(x.group(2))
    return fd


def _fix_matras(text: str) -> str:
    """Swap a pre-consonant 'i' matra with the following consonant."""
    out = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == _PRE_MATRA and i + 1 < len(text):
            nxt = text[i + 1]
            # Devanagari consonants sit in U+0915..U+0939 / U+0958..U+095F
            if "क" <= nxt <= "ह" or "क़" <= nxt <= "य़":
                out.append(nxt)
                out.append(ch)
                i += 2
                continue
        out.append(ch)
        i += 1
    return "".join(out)


def _decode_page(page_body: bytes, objs: Dict[int, bytes],
                 fonts: Dict[int, Optional[Dict[int, str]]]) -> str:
    fd = _resolve_font_dict(
        page_body if b"/Font" in page_body else b"", objs)
    if not fd:
        r = re.search(rb"/Resources\s+(\d+)\s+\d+\s+R", page_body)
        if r and int(r.group(1)) in objs:
            fd = _resolve_font_dict(objs[int(r.group(1))], objs)

    cm = re.search(rb"/Contents\s+(\d+)\s+\d+\s+R", page_body)
    if not cm or int(cm.group(1)) not in objs:
        return ""
    content = _get_stream(objs[int(cm.group(1))])
    if content is None:
        return ""

    cur_font: Optional[int] = None
    cur_x = cur_y = 0.0
    lines: Dict[int, List[Tuple[float, str]]] = {}

    token_re = re.compile(
        rb"/(\w+)\s+[\d.]+\s+Tf"                                  # font select
        rb"|([\d.\-]+)\s+([\d.\-]+)\s+Td"                          # relative move
        rb"|[\d.\-]+\s+[\d.\-]+\s+[\d.\-]+\s+[\d.\-]+\s+([\d.\-]+)\s+([\d.\-]+)\s+Tm"  # text matrix
        rb"|\(((?:\\.|[^\\()])*)\)\s*Tj"                          # simple string
        rb"|\[((?:\\.|[^\]])*)\]\s*TJ"                            # array string
        rb"|BT",
        re.S,
    )
    for t in token_re.finditer(content):
        s = t.group(0)
        if s == b"BT":
            cur_x = cur_y = 0.0
        elif s.endswith(b"Tf"):
            cur_font = fd.get(t.group(1).decode())
        elif s.endswith(b"Tm"):
            cur_x, cur_y = float(t.group(4)), float(t.group(5))
        elif s.endswith(b"Td"):
            cur_x += float(t.group(2))
            cur_y += float(t.group(3))
        else:  # Tj or TJ
            lits = re.findall(rb"\(((?:\\.|[^\\()])*)\)", s)
            txt = ""
            enc = fonts.get(cur_font)
            for lit in lits:
                lit = re.sub(rb"\\([()\\])", rb"\1", lit)
                lit = lit.replace(b"\\n", b"").replace(b"\n", b"")
                if enc is None:
                    txt += lit.decode("mac-roman", "replace")
                else:
                    txt += "".join(enc.get(ch, "") for ch in lit)
            if txt.strip():
                lines.setdefault(round(cur_y), []).append((cur_x, txt))

    out_lines: List[str] = []
    for y in sorted(lines, reverse=True):
        parts = sorted(lines[y], key=lambda p: p[0])
        line = " ".join(p[1] for p in parts).strip()
        if line:
            out_lines.append(_fix_matras(line))
    return "\n".join(out_lines)


def extract_text(pdf_bytes: bytes) -> str:
    """Extract readable text from raw PDF bytes using only the stdlib."""
    objs = _parse_objects(pdf_bytes)
    if not objs:
        return ""
    fonts = _build_fonts(objs)
    pages = [
        body for body in objs.values()
        if b"/Type" in body and b"/Page" in body and b"/Contents" in body
    ]
    chunks = [_decode_page(p, objs, fonts) for p in pages]
    return "\n".join(c for c in chunks if c)


if __name__ == "__main__":  # pragma: no cover - manual smoke test
    import sys

    with open(sys.argv[1], "rb") as fh:
        print(extract_text(fh.read()))
