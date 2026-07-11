# -*- coding: utf-8 -*-
"""Eval harness — compare AI providers on a folder of land-record documents.

Usage:
    python eval_providers.py --dir ./eval_docs --providers anthropic,sarvam

For each (file × provider) it calls the SAME functions the app uses
(modules/providers.py) and records: file, provider, ok, latency_s, chars_out,
error. Results go to eval_results.csv plus a printed summary (success rate,
median latency per provider). No pass/fail judgment — compare outputs manually.

Keys come from env: ANTHROPIC_API_KEY / SARVAM_API_KEY. A provider with no key
is skipped with a warning. Sarvam's 10 req/min limit is respected (sleep 7s
between Sarvam calls).
"""
import argparse
import base64
import csv
import io
import os
import statistics
import sys
import time

from modules.providers import decode_anthropic, decode_sarvam

SUPPORTED = (".jpg", ".jpeg", ".png", ".pdf")


def _to_png_b64(raw: bytes, filename: str) -> str:
    """Image/PDF bytes → base64 PNG (long edge ≤1600px), same as the app."""
    from PIL import Image

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
    return base64.standard_b64encode(buf.getvalue()).decode()


def run_one(provider: str, path: str, keys: dict) -> dict:
    fname = os.path.basename(path)
    row = {"file": fname, "provider": provider, "ok": False,
           "latency_s": None, "chars_out": 0, "error": ""}
    with open(path, "rb") as f:
        raw = f.read()
    t0 = time.time()
    try:
        if provider == "anthropic":
            b64 = _to_png_b64(raw, fname)
            out = decode_anthropic(b64, keys["anthropic"], "")
        else:
            out = decode_sarvam(raw, fname, keys["sarvam"], "")
        row["ok"] = bool(out and out.strip())
        row["chars_out"] = len(out or "")
        if not row["ok"]:
            row["error"] = "empty output"
    except Exception as e:  # noqa: BLE001 — record, don't crash the sweep
        row["error"] = f"{type(e).__name__}: {e}"
    row["latency_s"] = round(time.time() - t0, 2)
    return row


def main() -> int:
    ap = argparse.ArgumentParser(description="खतियान provider eval harness")
    ap.add_argument("--dir", default="./eval_docs", help="folder of jpg/png/pdf docs")
    ap.add_argument("--providers", default="anthropic,sarvam",
                    help="comma list: anthropic,sarvam")
    ap.add_argument("--out", default="eval_results.csv")
    args = ap.parse_args()

    wanted = [p.strip().lower() for p in args.providers.split(",") if p.strip()]
    keys = {
        "anthropic": os.environ.get("ANTHROPIC_API_KEY", ""),
        "sarvam": os.environ.get("SARVAM_API_KEY", ""),
    }
    providers = []
    for p in wanted:
        if p not in ("anthropic", "sarvam"):
            print(f"WARNING: unknown provider '{p}' — skipped")
        elif not keys[p]:
            print(f"WARNING: no {p.upper()}_API_KEY in env — skipping {p}")
        else:
            providers.append(p)
    if not providers:
        print("No usable providers. Set ANTHROPIC_API_KEY / SARVAM_API_KEY.")
        return 1

    if not os.path.isdir(args.dir):
        print(f"No such folder: {args.dir}")
        return 1
    files = sorted(
        os.path.join(args.dir, f) for f in os.listdir(args.dir)
        if f.lower().endswith(SUPPORTED)
    )
    if not files:
        print(f"No jpg/png/pdf files in {args.dir}")
        return 1

    print(f"{len(files)} file(s) × {providers} …")
    rows = []
    for path in files:
        for p in providers:
            print(f"→ {p:9s} {os.path.basename(path)}", flush=True)
            rows.append(run_one(p, path, keys))
            if p == "sarvam":
                time.sleep(7)  # 10 req/min limit

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["file", "provider", "ok",
                                          "latency_s", "chars_out", "error"])
        w.writeheader()
        w.writerows(rows)
    print(f"\nWrote {args.out} ({len(rows)} rows)")

    print("\n=== Summary ===")
    print(f"{'provider':10s} {'n':>3s} {'ok':>3s} {'success':>8s} {'median_s':>9s}")
    for p in providers:
        pr = [r for r in rows if r["provider"] == p]
        oks = [r for r in pr if r["ok"]]
        lat = [r["latency_s"] for r in oks]
        med = f"{statistics.median(lat):.1f}" if lat else "—"
        print(f"{p:10s} {len(pr):3d} {len(oks):3d} {len(oks)/len(pr):8.0%} {med:>9s}")
    print("\n(No pass/fail judgment — compare the outputs yourself.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
