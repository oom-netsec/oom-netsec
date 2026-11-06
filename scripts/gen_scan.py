#!/usr/bin/env python3
"""Generate the scan panel: dot-art logos cycling under a scan beam, next to a terminal running show run.

Writes assets/generated/scan.svg (desktop, side by side) and scan-mobile.svg (stacked, larger text).
No glow filters on text: phones downscale the image and blurred text turns to mush.
Static content, so it runs locally (needs chromium and Pillow), not in the daily workflow.
Usage: python3 scripts/gen_scan.py
"""
import re, subprocess, tempfile
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image

from profile_art import DIM, GREEN, MACUAHUITL, MID, MONO, OUT, ROOT, SANS, TEXT, doc

ICONS = ROOT / "icons"
SLOT = 4.0  # seconds each logo stays on screen
PROMPT = "oom-netsec#"
COMMAND = "show running-config | section engineer"
OUTPUT = [  # (text, color); keep lines <= 64 chars so the mobile version fits
    ("Building configuration...", DIM),
    ("", DIM),
    ("engineer osvaldo-ordonez", GREEN),
    (" description    engineer who codes so networks heal faster", MID),
    (" role           network-operations-lead vice-president", MID),
    (" experience     11+ years ! TAC > High Touch > VP NetOps", MID),
    (" certification  ccie enterprise-wireless 68143", MID),
    (" certification  ccnp enterprise", MID),
    (" expertise      wireless sd-wan sd-access zero-trust ise", MID),
    (" automation     go python ansible rest-api iac", MID),
    (" ai             llm-agents aiops root-cause-analysis", MID),
    (" building       macuahuitl zylant-os", MID),
    (" status         up, line protocol up", TEXT),
    ("!", DIM),
    ("end", DIM),
]


def simple_icon(name):
    return re.search(r'<path d="([^"]+)"', (ICONS / f"{name}.svg").read_text()).group(1)


def raster(svg_body, viewbox):
    """Render a white-on-black SVG with chromium and return it as a grayscale image."""
    with tempfile.TemporaryDirectory(dir=ROOT) as tmp:  # chromium (snap) cannot read /tmp
        src, png = Path(tmp) / "i.svg", Path(tmp) / "i.png"
        src.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="240" height="240" viewBox="{viewbox}">'
                       f'<rect width="100%" height="100%"/>{svg_body}</svg>')
        subprocess.run(["chromium", "--headless", "--disable-gpu", "--hide-scrollbars", "--window-size=240,240",
                        f"--screenshot={png}", src.as_uri()], check=True, capture_output=True)
        return Image.open(png).convert("L")


def logos():
    """(label, grayscale image) for each logo; white = ink."""
    xolotl = Image.open(ROOT / "assets" / "zylant-os.png").convert("RGBA").getchannel("A")
    return [
        ("CISCO", raster(f'<path d="{simple_icon("cisco")}" fill="#fff"/>', "0 0 24 24")),
        ("XOLOTL · ZYLANT-OS", xolotl),
        ("MACUAHUITL", raster(MACUAHUITL.format(c="#fff"), "0 0 64 64")),
        ("UBUNTU", raster(f'<path d="{simple_icon("ubuntu")}" fill="#fff"/>', "0 0 24 24")),
    ]


def dot_layers(cx, cy, radius, n=45):
    """One <g> of dots per logo, cycling forever; plus the unlit board and the beam."""
    pitch = 2 * radius / n
    board, layers, labels = [], [], []
    total = SLOT * len(logos_cache)
    for i, (label, img) in enumerate(logos_cache):
        w, h = img.size
        scale = max(w, h) / (n * 0.74)  # logo spans ~74% of the circle
        ox, oy = (n * scale - w) / 2, (n * scale - h) / 2
        dots = []
        for gy in range(n):
            for gx in range(n):
                x, y = cx - radius + (gx + 0.5) * pitch, cy - radius + (gy + 0.5) * pitch
                if (x - cx) ** 2 + (y - cy) ** 2 > (radius - pitch / 2) ** 2:
                    continue
                if i == 0:
                    board.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{pitch * 0.16:.2f}" fill="#123A1D"/>')
                box = (int(gx * scale - ox), int(gy * scale - oy), int((gx + 1) * scale - ox), int((gy + 1) * scale - oy))
                if box[2] <= 0 or box[3] <= 0 or box[0] >= w or box[1] >= h:
                    continue
                crop = img.crop((max(box[0], 0), max(box[1], 0), min(box[2], w), min(box[3], h)))
                v = sum(crop.get_flattened_data()) / max(1, crop.width * crop.height) / 255
                if v > 0.42:  # firm threshold keeps thin gaps (the Xolotl's inner lines) visible
                    dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{pitch * (0.26 + 0.14 * v):.2f}"/>')
        a, b = i / len(logos_cache), (i + 1) / len(logos_cache)
        f = 0.35 / total  # fade length as a fraction of the cycle
        if i == 0:  # visible from t=0, so a still frame is never empty
            keys, vals = [0, b - f, b, 1], [1, 1, 0, 0]
        else:  # fade in at its slot start, fade out at its slot end
            keys, vals = [0, a, a + f, b - f, b, 1], [0, 0, 1, 1, 0, 0]
        anim = (f'<animate attributeName="opacity" values="{";".join(map(str, vals))}" keyTimes="{";".join(f"{k:.4f}" for k in keys)}" '
                f'dur="{total}s" repeatCount="indefinite"/>')
        layers.append(f'<g fill="{GREEN}" opacity="{1 if i == 0 else 0}">{anim}{"".join(dots)}</g>')
        labels.append(f'<text x="{cx}" y="{cy + radius + 26}" text-anchor="middle" fill="{DIM}" font-family="{SANS}" '
                      f'font-size="11" letter-spacing="2" opacity="{1 if i == 0 else 0}">{anim}{escape(label)}</text>')
    beam = (f'<rect x="{cx - radius}" y="{cy - radius}" width="{2 * radius}" height="22" fill="url(#beam)" clip-path="url(#disc)">'
            f'<animate attributeName="y" values="{cy - radius - 22};{cy + radius}" dur="{SLOT}s" repeatCount="indefinite"/></rect>')
    ring = f'<circle cx="{cx}" cy="{cy}" r="{radius + 6}" fill="none" stroke="#1C3B24"/>'
    disc = f'<clipPath id="disc"><circle cx="{cx}" cy="{cy}" r="{radius}"/></clipPath>'
    return ring + "".join(board) + "".join(layers) + beam + "".join(labels), disc


def terminal(x, y, font):
    char, line = font * 0.602, round(font * 1.6)
    t0, tc, tl = 0.9, 0.045, 0.11
    px = x + (len(PROMPT) + 1) * char
    n = len(COMMAND)
    times = ";".join(f"{i / n:.4f}" for i in range(n + 1))
    typing = f'begin="{t0}s" dur="{n * tc:.2f}s" calcMode="discrete" keyTimes="{times}" fill="freeze"'
    widths = ";".join(f"{i * char:.1f}" for i in range(n + 1))
    xs = ";".join(f"{px + i * char:.1f}" for i in range(n + 1))
    txt = lambda tx, ty, s, c: (f'<text x="{tx:.1f}" y="{ty}" fill="{c}" font-family="{MONO}" font-size="{font}" '
                                f'xml:space="preserve">{escape(s)}</text>')
    cur = lambda cx, cy: f'x="{cx:.1f}" y="{cy - font + 2}" width="{char:.1f}" height="{font + 3}" fill="{GREEN}"'
    blink = lambda b: f'<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.5;1" dur="1.06s" repeatCount="indefinite" begin="{b}"/>'
    parts = [txt(x, y, PROMPT, GREEN),
             f'<g clip-path="url(#typed)">{txt(px, y, COMMAND, TEXT)}</g>',
             f'<rect {cur(px, y)}><animate attributeName="x" values="{xs}" {typing}/>{blink("0s")}'
             f'<set attributeName="visibility" to="hidden" begin="{t0 + n * tc + 0.3:.2f}s" fill="freeze"/></rect>']
    t, yy = t0 + n * tc + 0.35, y + line
    for i, (s, c) in enumerate(OUTPUT):
        parts.append(f'<g opacity="0"><animate attributeName="opacity" from="0" to="1" begin="{t:.2f}s" dur="0.01s" fill="freeze"/>'
                     f'{txt(x, yy, s, c)}</g>')
        t += 0.55 if i == 0 else tl
        yy += line
    yy += line
    parts.append(f'<g opacity="0"><animate attributeName="opacity" from="0" to="1" begin="{t + 0.15:.2f}s" dur="0.01s" fill="freeze"/>'
                 f'{txt(x, yy, PROMPT, GREEN)}<rect {cur(x + (len(PROMPT) + 1) * char, yy)}>{blink(f"{t + 0.15:.2f}s")}</rect></g>')
    clip = (f'<clipPath id="typed"><rect x="{px:.1f}" y="{y - font - 2}" height="{line + 4}" width="0">'
            f'<animate attributeName="width" values="{widths}" {typing}/></rect></clipPath>')
    return "".join(parts), clip, yy


def window(x, y, w, h, title):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="#050C07" stroke="#1C3B24"/>'
            f'<path d="M{x} {y + 30}H{x + w}" stroke="#12261A"/>'
            + "".join(f'<circle cx="{x + 18 + i * 18}" cy="{y + 15}" r="5" fill="#1E3A26"/>' for i in range(3))
            + f'<text x="{x + w / 2}" y="{y + 19}" text-anchor="middle" fill="#4D7A57" font-family="{MONO}" font-size="11">{title}</text>')


BEAM = (f'<linearGradient id="beam" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{GREEN}" stop-opacity="0"/>'
        f'<stop offset="0.85" stop-color="{GREEN}" stop-opacity="0.3"/><stop offset="1" stop-color="{GREEN}" stop-opacity="0.85"/></linearGradient>')
TITLE = "Profile scan: Cisco, Xolotl, macuahuitl and Ubuntu logos next to a terminal running show running-config"


def desktop():
    term, clip, bottom = terminal(332, 94, 12.5)
    h = int(bottom + 30)
    art, disc = dot_layers(170, (h + 40) / 2, 118)
    body = (f'<text x="40" y="36" fill="{GREEN}" font-family="{SANS}" font-size="13" font-weight="700" letter-spacing="2">PROFILE SCAN</text>'
            + art + window(312, 50, 548, h - 70, "osvaldo@oom-netsec: ssh core-01") + term)
    return doc(h, body, TITLE, BEAM + clip + disc)


def mobile():
    import profile_art
    profile_art.W = 480  # doc() reads the module width
    radius = 130
    art, disc = dot_layers(240, 70 + radius, radius)
    top = 70 + 2 * radius + 50
    term, clip, bottom = terminal(30, top + 52, 11)
    h = int(bottom + 34)
    body = (f'<text x="24" y="36" fill="{GREEN}" font-family="{SANS}" font-size="13" font-weight="700" letter-spacing="2">PROFILE SCAN</text>'
            + art + window(16, top, 448, h - top - 16, "ssh core-01") + term)
    svg = doc(h, body, TITLE, BEAM + clip + disc)
    profile_art.W = 900
    return svg


if __name__ == "__main__":
    logos_cache = logos()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "scan.svg").write_text(desktop())
    (OUT / "scan-mobile.svg").write_text(mobile())
    print("scan.svg and scan-mobile.svg written")
