"""
make_qr.py — the QR code for the closing slide.

Run it once the app is deployed:

    python scripts/make_qr.py https://your-app.streamlit.app

Optionally fill the other two slots on the same slide at the same time:

    python scripts/make_qr.py https://your-app.streamlit.app \
        --repo https://github.com/you/real-estate-machine \
        --kaggle https://www.kaggle.com/code/you/real-estate-machine

It writes reports/slides/qr_live_app.png and records the URL in
reports/slides/deck_facts.json, so the next `node scripts/build_deck.js`
replaces the placeholder frame on the last slide with the real code and the
real link. With no URL recorded, the deck draws the placeholder instead - the
slide is designed for both states, so nothing needs editing by hand.

The QR is drawn in the project's ink, on the project's paper, at the highest
error correction level, so it still scans from a projector at an angle.
"""
import json
import sys
from pathlib import Path

import qrcode

ROOT = Path(__file__).resolve().parent.parent
SLIDES = ROOT / "reports" / "slides"
FACTS = SLIDES / "deck_facts.json"

INK = "#191714"
PAPER = "#FBFAF7"


def build(url: str) -> Path:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,  # survives a bad angle
        box_size=14,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color=INK, back_color=PAPER)
    out = SLIDES / "qr_live_app.png"
    img.save(out)

    facts = json.loads(FACTS.read_text())
    facts["live_url"] = url
    FACTS.write_text(json.dumps(facts, indent=1))
    return out


def _flag(name: str) -> str | None:
    if name in sys.argv:
        i = sys.argv.index(name)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1].strip()
    return None


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1].startswith("-"):
        print(__doc__)
        raise SystemExit(1)
    url = sys.argv[1].strip()
    if not url.startswith("http"):
        raise SystemExit("That does not look like a URL - include https://")

    path = build(url)
    facts = json.loads(FACTS.read_text())
    for flag, key in (("--repo", "repo_url"), ("--kaggle", "kaggle_url")):
        value = _flag(flag)
        if value:
            facts[key] = value
            print(f"recorded {key} = {value}")
    FACTS.write_text(json.dumps(facts, indent=1))

    print(f"wrote {path}")
    print(f"recorded live_url = {url} in {FACTS.name}")
    print("now run:  node scripts/build_deck.js")
