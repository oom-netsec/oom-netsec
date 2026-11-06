#!/usr/bin/env python3
"""Generate the animated profile panels in assets/generated/:

  banner.svg   name in dot-matrix lights over code rain, with the MACUAHUITL and Xolotl logos
  contrib.svg  contribution graph; the Xolotl runs across once and eats it, then it grows back
  stats.svg    "GitHub signal": live contribution stats as tiles

Data comes from the GitHub GraphQL API (env GITHUB_TOKEN; locally: GITHUB_TOKEN=$(gh auth token)).
Runs daily from .github/workflows/profile-art.yml. Usage: python3 scripts/profile_art.py
"""
import base64, datetime as dt, json, os, random, urllib.request
from pathlib import Path
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "generated"
USER = "oom-netsec"
W = 900
GREEN, MID, DIM, INK, TEXT = "#00FF41", "#19C24F", "#1F8F3A", "#D6FFE0", "#9CFFB5"
LEVELS = {"NONE": "#0F1A12", "FIRST_QUARTILE": "#0B4D22", "SECOND_QUARTILE": "#118C3A",
          "THIRD_QUARTILE": "#19C24F", "FOURTH_QUARTILE": "#00FF41"}
MONO = "'JetBrains Mono', 'Fira Code', SFMono-Regular, Menlo, Consolas, 'DejaVu Sans Mono', monospace"
SANS = "Verdana, 'DejaVu Sans', Geneva, sans-serif"

# Macuahuitl mark from MACUAHUITL's app icon (ui/frontend/public/favicon.svg), 64x64, without its background.
MACUAHUITL = ('<path d="M14 6H50V14H58V50H50V58H14V50H6V14H14Z" fill="none" stroke="{c}" stroke-width="3.5"/>'
              '<g transform="rotate(-45 32 32)" fill="{c}"><rect x="28" y="14" width="8" height="26" rx="1.5"/>'
              '<rect x="30" y="40" width="4" height="10" rx="1"/>'
              '<path d="M29 16 23 19 29 22ZM29 24 23 27 29 30ZM29 32 23 35 29 38ZM35 16 41 19 35 22ZM35 24 41 27 35 30ZM35 32 41 35 35 38Z"/></g>')

# 5x7 dot-matrix glyphs for the banner name.
GLYPHS = {
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "Z": ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
    " ": ["00000"] * 7,
}


# ---------- data ----------

QUERY = """query($login: String!) { user(login: $login) { createdAt
  contributionsCollection {
    contributionCalendar { totalContributions weeks { contributionDays { date contributionCount contributionLevel } } } } } }"""


def fetch():
    req = urllib.request.Request("https://api.github.com/graphql",
                                 data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
                                 headers={"Authorization": f"bearer {os.environ['GITHUB_TOKEN']}"})
    data = json.load(urllib.request.urlopen(req, timeout=30))
    if "errors" in data:
        raise SystemExit(f"GitHub API error: {data['errors']}")
    return data["data"]["user"]


def streaks(days):
    """(current, longest) streaks in days; today not counting yet does not break the current one."""
    longest = run = 0
    for d in days:
        run = run + 1 if d["contributionCount"] else 0
        longest = max(longest, run)
    current = 0
    for i, d in enumerate(reversed(days)):
        if d["contributionCount"]:
            current += 1
        elif i:  # a zero today is fine, a zero before that ends the streak
            break
    return current, longest


# ---------- shared pieces ----------

def doc(h, body, title, defs=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" role="img" aria-label="{escape(title)}">'
            f'<title>{escape(title)}</title><defs>'
            '<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#07110A"/><stop offset="1" stop-color="#030704"/></linearGradient>'
            '<filter id="glow" x="-10%" y="-30%" width="120%" height="160%"><feGaussianBlur stdDeviation="2" result="b"/>'
            '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
            '<filter id="green"><feColorMatrix values="0 0 0 0 0  0 0 0 0 1  0 0 0 0 0.255  0 0 0 1 0"/></filter>'
            f'{defs}</defs>'
            f'<rect width="{W}" height="{h}" rx="14" fill="url(#bg)"/>'
            f'<rect x="0.5" y="0.5" width="{W - 1}" height="{h - 1}" rx="14" fill="none" stroke="#1C3B24"/>'
            f'{body}</svg>\n')


def heading(x, y, title, sub=""):
    s = (f'<text x="{x}" y="{y}" fill="{GREEN}" font-family="{SANS}" font-size="13" font-weight="700" '
         f'letter-spacing="2">{escape(title.upper())}</text>')
    if sub:
        s += f'<text x="{x}" y="{y + 20}" fill="{DIM}" font-family="{MONO}" font-size="12">{escape(sub)}</text>'
    return s


def xolotl_png():
    """The Zylant-OS Xolotl, pre-shrunk to assets/xolotl-small.png (recolored green by the #green filter)."""
    data = (ROOT / "assets" / "xolotl-small.png").read_bytes()
    size = int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")  # PNG IHDR width, height
    return base64.b64encode(data).decode(), size


# ---------- banner ----------

def banner():
    h = 250
    rnd = random.Random(68143)
    rain = []
    for col in range(0, W, 18):
        chars = [rnd.choice("0123456789ABCDEF:#/<>") for _ in range(14)]
        dur, delay = rnd.uniform(7, 13), -rnd.uniform(0, 13)
        spans = "".join(f'<tspan x="{col + 9}" dy="16" fill-opacity="{(i + 1) / 14:.2f}">{escape(c)}</tspan>' for i, c in enumerate(chars))
        rain.append(f'<g><text y="0" fill="{DIM}" font-family="{MONO}" font-size="13" text-anchor="middle">{spans}</text>'
                    f'<animateTransform attributeName="transform" type="translate" from="0 -230" to="0 {h}" '
                    f'dur="{dur:.1f}s" begin="{delay:.1f}s" repeatCount="indefinite"/></g>')

    name, pitch, r = "OS ORDONEZ", 9.5, 3.4
    cols = len(name) * 6 - 1
    x0, y0 = (W - cols * pitch) / 2 + pitch / 2, 62
    dots = []
    for ci, ch in enumerate(name):
        for ry, row in enumerate(GLYPHS[ch]):
            for rx, bit in enumerate(row):
                gx = ci * 6 + rx
                cx, cy = x0 + gx * pitch, y0 + ry * pitch
                if bit == "1":
                    t = 0.4 + gx * 0.035 + rnd.uniform(0, 0.12)
                    dots.append(f'<circle cx="{cx:.1f}" cy="{cy}" r="{r}" fill="{GREEN}" opacity="0">'
                                f'<set attributeName="opacity" to="1" begin="{t:.2f}s" fill="freeze"/></circle>')
                else:
                    dots.append(f'<circle cx="{cx:.1f}" cy="{cy}" r="{r}" fill="#0E2414"/>')

    png, (pw, ph) = xolotl_png()
    xo_w = 92
    xo_h = xo_w * ph / pw
    logos = (f'<g transform="translate(38 {y0 + 3 * pitch - 30}) scale(0.94)" filter="url(#glow)">{MACUAHUITL.format(c=GREEN)}</g>'
             f'<image href="data:image/png;base64,{png}" x="{W - 38 - xo_w}" y="{y0 + 3 * pitch - xo_h / 2:.1f}" '
             f'width="{xo_w}" height="{xo_h:.1f}" filter="url(#green)"/>')
    sub = "NETWORK OPERATIONS LEAD  ·  CCIE ENTERPRISE WIRELESS #68143  ·  AUTOMATION &amp; AI"
    body = (f'<g opacity="0.45" clip-path="url(#clip)">{"".join(rain)}</g>'
            f'<rect x="40" y="{y0 - 22}" width="{W - 80}" height="{7 * pitch + 30}" rx="10" fill="#040A06" opacity="0.82"/>'
            f'<g filter="url(#glow)">{"".join(dots)}</g>{logos}'
            f'<text x="{W / 2}" y="{h - 42}" text-anchor="middle" fill="{TEXT}" font-family="{SANS}" font-size="12" '
            f'letter-spacing="2.4">{sub}</text>'
            f'<text x="{W / 2}" y="{h - 22}" text-anchor="middle" fill="{DIM}" font-family="{MONO}" font-size="11">'
            'Mexico · English / Español</text>')
    return doc(h, body, "Os Ordonez, Network Operations Lead, CCIE Enterprise Wireless #68143",
               f'<clipPath id="clip"><rect width="{W}" height="{h}" rx="14"/></clipPath>')


# ---------- contribution graph ----------

def contrib(user):
    cal = user["contributionsCollection"]["contributionCalendar"]
    weeks = cal["weeks"]
    cell, gap, top, left = 12, 3, 78, 56
    step = cell + gap
    start, speed = 0.8, 105.0  # seconds, px/s for the Xolotl
    png, (pw, ph) = xolotl_png()
    xo_w = 58
    xo_h = xo_w * ph / pw
    grid_y = top + 3 * step + cell / 2  # Xolotl rides along the middle row

    cells, months, last_month = [], [], None
    for wi, wk in enumerate(weeks):
        x = left + wi * step
        t_eat = start + (x + xo_w * 0.8) / speed  # when the Xolotl's mouth reaches this column
        for d in wk["contributionDays"]:
            y = top + dt.date.fromisoformat(d["date"]).isoweekday() % 7 * step
            cells.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2.5" fill="{LEVELS["NONE"]}"/>')
            if d["contributionLevel"] != "NONE":
                cells.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2.5" fill="{LEVELS[d["contributionLevel"]]}">'
                             f'<title>{d["contributionCount"]} on {d["date"]}</title>'
                             f'<set attributeName="opacity" to="0" begin="{t_eat:.2f}s"/>'
                             f'<animate attributeName="opacity" from="0" to="1" begin="{t_eat + 1.6:.2f}s" dur="0.5s" fill="freeze"/></rect>')
        month = wk["contributionDays"][0]["date"][:7]
        if month != last_month and wi < len(weeks) - 2:
            months.append(f'<text x="{x}" y="{top - 9}" fill="{DIM}" font-family="{MONO}" font-size="10">'
                          f'{dt.date.fromisoformat(month + "-01"):%b}</text>')
            last_month = month
    days = "".join(f'<text x="{left - 10}" y="{top + i * step + 10}" text-anchor="end" fill="{DIM}" '
                   f'font-family="{MONO}" font-size="10">{n}</text>' for i, n in ((1, "Mon"), (3, "Wed"), (5, "Fri")))
    travel = (W + xo_w) / speed
    xolotl = (f'<g transform="translate({-xo_w} 0)"><animateTransform attributeName="transform" type="translate" '
              f'from="{-xo_w} 0" to="{W} 0" begin="{start}s" dur="{travel:.2f}s" fill="freeze"/>'
              f'<image href="data:image/png;base64,{png}" x="0" y="{grid_y - xo_h / 2:.1f}" width="{xo_w}" height="{xo_h:.1f}" '
              f'transform="translate({xo_w} 0) scale(-1 1)" filter="url(#green)">'  # mirrored: the logo faces left, it runs right
              f'<animate attributeName="y" values="{grid_y - xo_h / 2:.1f};{grid_y - xo_h / 2 - 5:.1f};{grid_y - xo_h / 2:.1f}" '
              f'dur="0.35s" repeatCount="{travel / 0.35:.0f}" begin="{start}s"/></image></g>')
    legend_x = W - 40 - 5 * 15 - 70
    legend = (f'<text x="{legend_x}" y="{top + 7 * step + 22}" fill="{DIM}" font-family="{MONO}" font-size="10">Less</text>'
              + "".join(f'<rect x="{legend_x + 32 + i * 15}" y="{top + 7 * step + 12}" width="11" height="11" rx="2.5" fill="{c}"/>'
                        for i, c in enumerate(LEVELS.values()))
              + f'<text x="{legend_x + 32 + 5 * 15 + 4}" y="{top + 7 * step + 22}" fill="{DIM}" font-family="{MONO}" font-size="10">More</text>')
    h = top + 7 * step + 44
    body = (heading(40, 36, "Contribution activity", f"{cal['totalContributions']:,} contributions in the last year")
            + "".join(months) + days + "".join(cells) + legend + xolotl
            + f'<text x="40" y="{top + 7 * step + 22}" fill="{DIM}" font-family="{MONO}" font-size="10">'
              'The Xolotl eats a year of commits. It always grows back.</text>')
    return doc(h, body, f"Contribution activity: {cal['totalContributions']} contributions in the last year")


# ---------- GitHub signal ----------

def stats(user):
    cal = user["contributionsCollection"]["contributionCalendar"]
    days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    cur, longest = streaks(days)
    best = max(days, key=lambda d: d["contributionCount"])
    since = dt.date.fromisoformat(user["createdAt"][:10])
    plural = lambda n: f"day{'s' * (n != 1)}"
    tiles = [("Contributions", f"{cal['totalContributions']:,}", "last year"),
             ("Active days", f"{sum(1 for d in days if d['contributionCount'])}", "last year"),
             ("Current streak", f"{cur}", plural(cur)),
             ("Longest streak", f"{longest}", plural(longest)),
             ("Busiest day", f"{best['contributionCount']}", f"{dt.date.fromisoformat(best['date']):%d %b %Y}"),
             ("On GitHub since", f"{since:%b}", f"{since:%Y}")]
    cols, gap, tw, th, top = 3, 16, (W - 80 - 2 * 16) / 3, 92, 58
    out = []
    for i, (label, value, sub) in enumerate(tiles):
        x, y = 40 + i % cols * (tw + gap), top + i // cols * (th + gap)
        # A fade with fill="freeze" keeps its end state; a <set> on a <g> was dropped once the timeline went idle.
        out.append(f'<g opacity="0"><animate attributeName="opacity" from="0" to="1" begin="{0.3 + i * 0.15:.2f}s" dur="0.3s" fill="freeze"/>'
                   f'<rect x="{x:.1f}" y="{y}" width="{tw:.1f}" height="{th}" rx="10" fill="#050C07" stroke="#1C3B24"/>'
                   f'<text x="{x + 18:.1f}" y="{y + 26}" fill="{DIM}" font-family="{SANS}" font-size="11" letter-spacing="1.6">{escape(label.upper())}</text>'
                   f'<text x="{x + 18:.1f}" y="{y + 68}" fill="{GREEN}" font-family="{SANS}" font-size="32" font-weight="700">{escape(value)}'
                   f'<tspan fill="{TEXT}" font-size="13" font-weight="400" dx="8">{escape(sub)}</tspan></text></g>')
    live = (f'<circle cx="{W - 92}" cy="31" r="4" fill="{GREEN}"><animate attributeName="opacity" values="1;0.25;1" dur="1.8s" repeatCount="indefinite"/></circle>'
            f'<text x="{W - 82}" y="35" fill="{DIM}" font-family="{MONO}" font-size="11">LIVE</text>')
    h = top + 2 * th + gap + 34
    return doc(h, heading(40, 36, "GitHub signal") + live + "".join(out), "GitHub signal: live contribution stats for oom-netsec")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "banner.svg").write_text(banner())
    user = fetch()
    (OUT / "contrib.svg").write_text(contrib(user))
    (OUT / "stats.svg").write_text(stats(user))
    print("banner.svg, contrib.svg, stats.svg written to", OUT.relative_to(ROOT))


if __name__ == "__main__":
    assert streaks([{"contributionCount": c} for c in (1, 1, 0, 1, 1, 1, 0)]) == (3, 3)
    assert streaks([{"contributionCount": c} for c in (2, 0, 5)]) == (1, 1)
    main()
