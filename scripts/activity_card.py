"""Render a compact activity card: four stat tiles over a weekly contribution sparkline.

Usage: python activity_card.py <login> <output.svg>   (needs GITHUB_TOKEN)
"""

import datetime as dt
import os
import sys

from torn_codex import fetch_calendar, f

W, H = 1000, 236
PAD = 40
FONT = "'Segoe UI', -apple-system, BlinkMacSystemFont, Inter, Helvetica, Arial, sans-serif"
INK, INK_2, MUTED = "#f5f3fa", "#b5afc4", "#8a8499"
GOLD = "#f6cd5e"
WEEKDAYS = ["Sundays", "Mondays", "Tuesdays", "Wednesdays", "Thursdays", "Fridays", "Saturdays"]


def stats(cal):
    days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    longest = run = 0
    for d in days:
        run = run + 1 if d["contributionCount"] > 0 else 0
        longest = max(longest, run)
    # Today may not have commits yet; the current streak counts from yesterday then.
    tail = days[:-1] if days and days[-1]["contributionCount"] == 0 else days
    current = 0
    for d in reversed(tail):
        if d["contributionCount"] == 0:
            break
        current += 1
    by_day = [0] * 7
    for d in days:
        by_day[d["weekday"]] += d["contributionCount"]
    weekly = [(w["contributionDays"][0]["date"], sum(d["contributionCount"] for d in w["contributionDays"]))
              for w in cal["weeks"]]
    return {
        "total": cal["totalContributions"],
        "longest": longest,
        "current": current,
        "busiest": WEEKDAYS[by_day.index(max(by_day))],
        "weekly": weekly,
    }


def smooth(points, top, bottom):
    """Catmull-Rom through the points, with control points clamped to the plot band."""
    clamp = lambda y: min(max(y, top), bottom)
    d = f"M{f(points[0][0])} {f(points[0][1])}"
    for i in range(len(points) - 1):
        p0 = points[max(i - 1, 0)]
        p1, p2 = points[i], points[i + 1]
        p3 = points[min(i + 2, len(points) - 1)]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, clamp(p1[1] + (p2[1] - p0[1]) / 6))
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, clamp(p2[1] - (p3[1] - p1[1]) / 6))
        d += f" C{f(c1[0])} {f(c1[1])} {f(c2[0])} {f(c2[1])} {f(p2[0])} {f(p2[1])}"
    return d


def render(cal):
    s = stats(cal)
    out = []
    add = out.append
    add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
        f'role="img" aria-labelledby="t">')
    add(f'<title id="t">{s["total"]} contributions in the last year, longest streak {s["longest"]} days, '
        f'current streak {s["current"]} days, most active on {s["busiest"]}</title>')
    add('<defs><linearGradient id="area" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{GOLD}" stop-opacity=".28"/>'
        f'<stop offset="1" stop-color="{GOLD}" stop-opacity="0"/></linearGradient></defs>')
    add(f'<rect width="{W}" height="{H}" rx="16" fill="#0b0a12"/>')
    add(f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="15.5" fill="none" stroke="#fff" stroke-opacity=".06"/>')
    add(f'<g font-family="{FONT}">')
    add(f'<text x="{PAD}" y="42" font-size="12" font-weight="600" letter-spacing="2.5" fill="{MUTED}">ACTIVITY · LAST 12 MONTHS</text>')

    tiles = [
        (f'{s["total"]:,}', "contributions"),
        (f'{s["longest"]}', "day longest streak"),
        (f'{s["current"]}', "day current streak"),
        (s["busiest"], "most active day"),
    ]
    col = (W - 2 * PAD) / len(tiles)
    for i, (value, label) in enumerate(tiles):
        x = PAD + i * col
        if i:
            add(f'<line x1="{f(x - 18)}" y1="62" x2="{f(x - 18)}" y2="104" stroke="#fff" stroke-opacity=".07"/>')
        add(f'<text x="{f(x)}" y="88" font-size="28" font-weight="700" letter-spacing="-.5" fill="{INK}">{value}</text>')
        add(f'<text x="{f(x)}" y="106" font-size="12.5" fill="{MUTED}">{label}</text>')

    # Weekly sparkline
    top, bottom = 128, 206
    weekly = s["weekly"]
    peak = max(v for _, v in weekly) or 1
    step = (W - 2 * PAD) / (len(weekly) - 1)
    pts = [(PAD + i * step, bottom - (bottom - top) * v / peak) for i, (_, v) in enumerate(weekly)]
    line = smooth(pts, top, bottom)
    add(f'<line x1="{PAD}" y1="{bottom}" x2="{W - PAD}" y2="{bottom}" stroke="#fff" stroke-opacity=".08"/>')
    add(f'<path d="{line} L{f(pts[-1][0])} {bottom} L{f(pts[0][0])} {bottom}Z" fill="url(#area)" opacity="0">'
        f'<animate attributeName="opacity" from="0" to="1" begin=".9s" dur="1.2s" fill="freeze"/></path>')
    add(f'<path d="{line}" fill="none" stroke="{GOLD}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        f'pathLength="1" stroke-dasharray="1" stroke-dashoffset="1">'
        f'<animate attributeName="stroke-dashoffset" from="1" to="0" dur="2s" fill="freeze" calcMode="spline" '
        f'keyTimes="0;1" keySplines=".4 0 .2 1"/></path>')

    pi = max(range(len(weekly)), key=lambda i: weekly[i][1])
    px, py = pts[pi]
    week_of = dt.date.fromisoformat(weekly[pi][0]).strftime("%b %d").replace(" 0", " ")
    anchor = "end" if px > W - 200 else "start"
    lx = px - 10 if anchor == "end" else px + 10
    add(f'<g opacity="0"><circle cx="{f(px)}" cy="{f(py)}" r="4.5" fill="{GOLD}" stroke="#0b0a12" stroke-width="2"/>'
        f'<text x="{f(lx)}" y="{f(py + 4)}" text-anchor="{anchor}" font-size="12" fill="{INK_2}">'
        f'peak · {weekly[pi][1]} in week of {week_of}</text>'
        f'<animate attributeName="opacity" from="0" to="1" begin="1.8s" dur=".6s" fill="freeze"/></g>')

    # Month ticks
    seen = set()
    for i, (date, _) in enumerate(weekly):
        d = dt.date.fromisoformat(date)
        if d.month in seen or i == 0:
            seen.add(d.month)
            continue
        if d.day <= 7:
            seen.add(d.month)
            add(f'<text x="{f(pts[i][0])}" y="{bottom + 18}" text-anchor="middle" font-size="11" fill="{MUTED}">{d.strftime("%b")}</text>')
    add("</g></svg>")
    return "\n".join(out)


def main():
    login = sys.argv[1] if len(sys.argv) > 1 else os.environ["GITHUB_REPOSITORY_OWNER"]
    out = sys.argv[2] if len(sys.argv) > 2 else "dist/activity.svg"
    cal = fetch_calendar(login, os.environ["GITHUB_TOKEN"])
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(render(cal))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
