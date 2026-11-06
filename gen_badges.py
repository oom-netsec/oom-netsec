#!/usr/bin/env python3
"""Generate the profile badges as local SVGs in assets/badges/ (no shields.io at view time).

Icons come from icons/*.svg (Simple Icons, CC0). Usage: python3 gen_badges.py
"""
import re
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
OUT = HERE / "assets" / "badges"
BG, EDGE, ICON, TEXT, VALUE_BG, VALUE_TEXT = "#0B0F0C", "#1C3B24", "#00FF41", "#D6FFE0", "#163F23", "#9CFFB5"
H, FS, CHAR = 28, 11, 7.4  # height, font size, width per uppercase letter incl. letter spacing

STACK = ["cisco", "go", "python", "ansible", "sqlite", "wireshark", "linux", "ubuntu"]
NAMES = {"go": "Go", "sqlite": "SQLite"}
CERTS = [("CCIE", "Enterprise Wireless #68143"), ("CCNP", "Enterprise"), ("Cisco", "SCOR"),
         ("Cisco", "ENCOR"), ("CCNA", "Cisco")]
EMAIL = "osvaldo.ordonez@yahoo.com.mx"
# Envelope outline, 24x24 (drawn here; Simple Icons has no generic mail icon).
MAIL = "M2 5h20v14H2zM3.5 6.5v.4l8.5 6 8.5-6v-.4zM3.5 8.7v8.8h17V8.7L12 14.7z"


def label(x, w, s, color, weight="600"):
    s = s.upper()
    return (f'<text x="{x + w / 2:.1f}" y="{H / 2 + FS * 0.36:.1f}" fill="{color}" font-size="{FS}" font-weight="{weight}" '
            f'text-anchor="middle" textLength="{len(s) * CHAR - 1.6:.1f}" lengthAdjust="spacingAndGlyphs">{escape(s)}</text>')


def svg(w, body, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" height="{H}" viewBox="0 0 {w:.0f} {H}" role="img" aria-label="{escape(title)}">'
            f'<title>{escape(title)}</title><g font-family="Verdana, \'DejaVu Sans\', Geneva, sans-serif">{body}</g></svg>\n')


def frame(w):
    return f'<rect x="0.5" y="0.5" width="{w - 1:.0f}" height="{H - 1}" rx="5" fill="{BG}" stroke="{EDGE}"/>'


def icon_badge(name, path, text):
    tw = len(text) * CHAR
    w = 12 + 14 + 8 + tw + 12
    ico = f'<svg x="12" y="7" width="14" height="14" viewBox="0 0 24 24"><path d="{path}" fill="{ICON}" fill-rule="evenodd"/></svg>'
    return svg(w, frame(w) + ico + label(34, tw, text, TEXT), text)


def pair_badge(left, right):
    lw, rw = len(left) * CHAR + 20, len(right) * CHAR + 20
    w = lw + rw
    body = (frame(w) + f'<path d="M{lw} 1H{w - 5.5}a4.5 4.5 0 0 1 4.5 4.5v17a4.5 4.5 0 0 1-4.5 4.5H{lw}z" fill="{VALUE_BG}"/>'
            + label(0, lw, left, TEXT, "500") + label(lw, rw, right, VALUE_TEXT))
    return svg(w, body, f"{left} {right}")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for s in STACK:
        path = re.search(r'<path d="([^"]+)"', (HERE / "icons" / f"{s}.svg").read_text()).group(1)
        (OUT / f"{s}.svg").write_text(icon_badge(s, path, NAMES.get(s, s.title())))
    for i, (l, r) in enumerate(CERTS):
        (OUT / f"cert-{i + 1}.svg").write_text(pair_badge(l, r))
    (OUT / "email.svg").write_text(icon_badge("email", MAIL, EMAIL))
    print(f"{len(list(OUT.glob('*.svg')))} badges written to {OUT.relative_to(HERE)}")


if __name__ == "__main__":
    main()
