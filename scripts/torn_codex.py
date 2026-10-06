"""Render the GitHub contribution calendar as a scene from The Torn Codex.

Each day is a torn page (a Folio) scattered across the void. A golden quill-light
travels the pages; every page with contributions is written back from teal ink
to gold, and the light finally falls into the Tear, whose gold heart flares.

Usage: python torn_codex.py <login> <output.svg>   (needs GITHUB_TOKEN)
"""

import json
import math
import os
import random
import sys
import urllib.request

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { contributionCount contributionLevel weekday } }
      }
    }
  }
}
"""

LEVELS = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
EMPTY = "#16131f"
TEAL = ["", "#0e3b3d", "#13605f", "#1b8f88", "#2cc5b8"]
GOLD = ["", "#6b5220", "#9c7425", "#d19d32", "#f6cd5e"]

W, H = 1000, 232
X0, Y0, STEP = 26, 80, 14.5
TEAR_X, TEAR_Y, TEAR_R = 905, 122, 80
CYCLE = 26  # seconds per loop
T_START, T_END = 0.04, 0.72  # fraction of the loop the quill spends travelling

PAGE_SHAPES = [
    "M-5.5 -5.5H4L5.5 -3.5V5.5H-5.5Z",  # dog-eared corner
    "M-5.5 -5.5H5.5V3L3.5 5.5L1 4.2L-1.5 5.5L-3.5 4.4L-5.5 5.5Z",  # torn bottom
    "M-5.5 -4L-3 -5.5L0 -4.5L2.5 -5.5L5.5 -5V5.5H-5.5Z",  # torn top
]


def fetch_calendar(login, token):
    body = json.dumps({"query": QUERY, "variables": {"login": login}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        data = json.load(resp)
    if "errors" in data:
        raise SystemExit(f"GitHub API error: {data['errors']}")
    return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def f(n):
    return f"{n:.2f}".rstrip("0").rstrip(".")


def spiral(radius, phase, turns=1.6, squash=1.0, cx=0.0, cy=0.0, steps=48):
    pts = []
    total = turns * 2 * math.pi
    for i in range(steps + 1):
        t = i / steps
        r = radius * (1 - t) ** 0.9
        a = phase + t * total
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a) * squash))
    return "M" + " L".join(f"{f(x)} {f(y)}" for x, y in pts)


def keytimes(*ts):
    return ";".join(f"{t:.4f}" for t in ts)


def build_cells(weeks, rng):
    cells = []
    for wi, week in enumerate(weeks):
        for day in week["contributionDays"]:
            cells.append({
                "week": wi,
                "day": day["weekday"],
                "level": LEVELS.get(day["contributionLevel"], 0),
                "x": X0 + wi * STEP + 5.5 + rng.uniform(-1.8, 1.8),
                "y": Y0 + day["weekday"] * STEP + 5.5 + rng.uniform(-1.8, 1.8),
                "rot": rng.uniform(-14, 14),
                "shape": rng.randrange(len(PAGE_SHAPES)),
            })
    return cells


def quill_route(cells):
    """Zig-zag through the written pages, week by week, ending in the Tear."""
    lit = [c for c in cells if c["level"] > 0]
    lit.sort(key=lambda c: (c["week"], c["day"] if c["week"] % 2 == 0 else -c["day"]))
    start = (X0 - 18, Y0 + 3 * STEP + 5.5)
    points = [start] + [(c["x"], c["y"]) for c in lit] + [(TEAR_X, TEAR_Y)]
    dist = [0.0]
    for (ax, ay), (bx, by) in zip(points, points[1:]):
        dist.append(dist[-1] + math.hypot(bx - ax, by - ay))
    total = dist[-1] or 1.0
    for c, d in zip(lit, dist[1:-1]):
        c["arrive"] = T_START + (T_END - T_START) * d / total
    path = "M" + " L".join(f"{f(x)} {f(y)}" for x, y in points)
    return path


def render(cal):
    rng = random.Random(7)
    cells = build_cells(cal["weeks"], rng)
    route = quill_route(cells)
    total = cal["totalContributions"]
    out = []
    add = out.append

    add(f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t">')
    add(f"<title id=\"t\">The Torn Codex: {total} contributions written back into a scattered world</title>")
    add("<defs>")
    for i, d in enumerate(PAGE_SHAPES):
        add(f'<path id="p{i}" d="{d}"/>')
    add('<radialGradient id="storm"><stop offset="0" stop-color="#3b1830" stop-opacity=".95"/>'
        '<stop offset=".55" stop-color="#1c1024" stop-opacity=".8"/>'
        '<stop offset="1" stop-color="#08070d" stop-opacity="0"/></radialGradient>')
    add('<radialGradient id="heart"><stop offset="0" stop-color="#fff6d8"/>'
        '<stop offset=".35" stop-color="#f6cd5e"/>'
        '<stop offset="1" stop-color="#f6cd5e" stop-opacity="0"/></radialGradient>')
    add('<radialGradient id="glow"><stop offset="0" stop-color="#ffe9a8" stop-opacity=".9"/>'
        '<stop offset="1" stop-color="#f6cd5e" stop-opacity="0"/></radialGradient>')
    add("</defs>")

    add(f'<rect width="{W}" height="{H}" rx="10" fill="#08070d"/>')

    # Ink motes drifting in the Blank
    for _ in range(36):
        x, y = rng.uniform(10, W - 10), rng.uniform(10, H - 10)
        dur = rng.uniform(3, 7)
        add(f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(rng.uniform(.5, 1.3))}" fill="#f6cd5e" opacity="0">'
            f'<animate attributeName="opacity" values="0;{f(rng.uniform(.2, .55))};0" dur="{f(dur)}s" '
            f'begin="-{f(rng.uniform(0, dur))}s" repeatCount="indefinite"/></circle>')

    # Title
    add(f'<text x="{X0}" y="40" font-family="Georgia,\'Times New Roman\',serif" font-size="20" '
        f'letter-spacing="6" fill="#f6cd5e">THE TORN CODEX</text>')
    add(f'<text x="{X0}" y="60" font-family="Georgia,serif" font-style="italic" font-size="11.5" '
        f'fill="#8a8499">Each contribution is a word written back into a scattered world.</text>')

    # The Folios: one torn page per day
    for c in cells:
        tf = f'translate({f(c["x"])} {f(c["y"])}) rotate({f(c["rot"])})'
        lvl = c["level"]
        if lvl == 0:
            add(f'<use href="#p{c["shape"]}" transform="{tf}" fill="{EMPTY}"/>')
            continue
        a = c["arrive"]
        kt = keytimes(0, a, a + .004, .93, .98, 1)
        teal, gold = TEAL[lvl], GOLD[lvl]
        add(f'<use href="#p{c["shape"]}" transform="{tf}" fill="{teal}">'
            f'<animate attributeName="fill" values="{teal};{teal};{gold};{gold};{teal};{teal}" '
            f'keyTimes="{kt}" dur="{CYCLE}s" repeatCount="indefinite"/></use>')

    # The Tear: storm halo, rotating spiral walls, ink-lightning, gold heart
    add(f'<circle cx="{TEAR_X}" cy="{TEAR_Y}" r="{TEAR_R + 22}" fill="url(#storm)"/>')
    for layer, (dur, alpha, width) in enumerate([(19, .14, 1.1), (12, .24, 1.4), (7, .35, 1)]):
        add(f'<g transform="translate({TEAR_X} {TEAR_Y}) scale(1 .62)"><g>')
        arms = 6 - layer
        for k in range(arms):
            d = spiral(TEAR_R * (1 - layer * .18), k * 2 * math.pi / arms + layer, turns=1.2)
            add(f'<path d="{d}" fill="none" stroke="#e9e4f5" stroke-opacity="{alpha}" '
                f'stroke-width="{width}" stroke-linecap="round"/>')
        add(f'<animateTransform attributeName="transform" type="rotate" from="0" to="360" '
            f'dur="{dur}s" repeatCount="indefinite"/></g></g>')

    for i in range(5):
        ang = rng.uniform(0, 2 * math.pi)
        r0 = TEAR_R * rng.uniform(.75, .95)
        pts = []
        for s in range(7):
            r = r0 * (1 - s / 7.5)
            a = ang + s * .22 + rng.uniform(-.25, .25)
            pts.append(f"{f(TEAR_X + r * math.cos(a))},{f(TEAR_Y + r * math.sin(a) * .62)}")
        poly = " ".join(pts)
        dur = rng.uniform(3.5, 6.5)
        at = rng.uniform(.1, .8)
        kt = keytimes(0, at, at + .015, at + .03, at + .045, at + .06, 1)
        add(f'<g opacity="0"><polyline points="{poly}" fill="none" stroke="#000" stroke-width="3.2"/>'
            f'<polyline points="{poly}" fill="none" stroke="#d23a4a" stroke-width="1.1"/>'
            f'<animate attributeName="opacity" values="0;0;1;.2;.9;0;0" keyTimes="{kt}" '
            f'dur="{f(dur)}s" repeatCount="indefinite"/></g>')

    # Torn pages spiralling into the Tear
    for i in range(10):
        d = spiral(TEAR_R * 1.05, i * .63, turns=1.4, squash=.62, cx=TEAR_X, cy=TEAR_Y)
        dur = rng.uniform(5, 8)
        add(f'<g opacity="0"><animateMotion path="{d}" dur="{f(dur)}s" begin="-{f(i * dur / 10)}s" '
            f'rotate="auto" repeatCount="indefinite"/>'
            f'<animate attributeName="opacity" values="0;.85;.85;0" keyTimes="0;.15;.75;1" '
            f'dur="{f(dur)}s" begin="-{f(i * dur / 10)}s" repeatCount="indefinite"/>'
            f'<use href="#p{i % 3}" fill="#d8cfb8" transform="scale(.7)">'
            f'<animateTransform attributeName="transform" type="scale" values=".8;.2" '
            f'dur="{f(dur)}s" begin="-{f(i * dur / 10)}s" repeatCount="indefinite"/></use></g>')

    add(f'<circle cx="{TEAR_X}" cy="{TEAR_Y}" r="12" fill="url(#heart)">'
        f'<animate attributeName="r" values="11;15;11" dur="3s" repeatCount="indefinite"/></circle>')
    kt = keytimes(0, T_END, T_END + .02, T_END + .12, 1)
    add(f'<circle cx="{TEAR_X}" cy="{TEAR_Y}" r="0" fill="url(#heart)">'
        f'<animate attributeName="r" values="0;0;46;0;0" keyTimes="{kt}" dur="{CYCLE}s" '
        f'repeatCount="indefinite"/></circle>')

    # The quill-light and its trail
    for lag, (r, op) in enumerate([(4, .9), (3.2, .5), (2.5, .3), (1.8, .18)]):
        shift = lag * .0035
        mk = keytimes(0, T_START + shift, T_END + shift, 1)
        vis = keytimes(0, T_START + shift, T_START + shift + .005, T_END + shift, T_END + shift + .005, 1)
        add(f'<g opacity="0">')
        if lag == 0:
            add('<circle r="11" fill="url(#glow)"/>')
        add(f'<circle r="{r}" fill="#fff3c4" opacity="{op}"/>')
        add(f'<animateMotion path="{route}" keyPoints="0;0;1;1" keyTimes="{mk}" calcMode="linear" '
            f'dur="{CYCLE}s" repeatCount="indefinite"/>')
        add(f'<animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="{vis}" '
            f'dur="{CYCLE}s" repeatCount="indefinite"/></g>')

    add(f'<text x="{X0}" y="{f(Y0 + 7 * STEP + 26)}" font-family="Georgia,serif" font-size="11.5" '
        f'fill="#8a8499"><tspan fill="#f6cd5e">{total}</tspan> words restored this year  ·  '
        f'the Tear still hungers</text>')
    add("</svg>")
    return "\n".join(out)


def main():
    login = sys.argv[1] if len(sys.argv) > 1 else os.environ["GITHUB_REPOSITORY_OWNER"]
    out = sys.argv[2] if len(sys.argv) > 2 else "dist/torn-codex.svg"
    cal = fetch_calendar(login, os.environ["GITHUB_TOKEN"])
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(render(cal))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
