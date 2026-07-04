#!/usr/bin/env python3
"""Generate the profile stats SVGs (light + dark) from live GitHub data.

Runs in CI (see .github/workflows/stats.yml) with GH_TOKEN set.
Design system matches assets/header-*.svg: Segoe UI stack, #1f6feb -> #00c9a7 accent.
"""
import json
import os
import urllib.request

USER = "alishazahid01"
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")

QUERY = """
query {
  user(login: "%s") {
    followers { totalCount }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 5) { edges { size node { name color } } }
      }
    }
    contributionsCollection {
      contributionCalendar { totalContributions }
    }
  }
}
""" % USER

FALLBACK_COLORS = ["#1f6feb", "#00c9a7", "#8957e5", "#d29922", "#f778ba"]


def fetch():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY}).encode(),
        headers={
            "Authorization": f"bearer {os.environ['GH_TOKEN']}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req) as r:
        payload = json.load(r)
    return payload["data"]["user"]


def fmt(n):
    return f"{n / 1000:.1f}k" if n >= 1000 else str(n)


def build(user):
    repos = user["repositories"]
    stars = sum(r["stargazerCount"] for r in repos["nodes"])
    contribs = user["contributionsCollection"]["contributionCalendar"]["totalContributions"]

    # Aggregate language bytes across public repos
    langs = {}
    for repo in repos["nodes"]:
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            color = edge["node"]["color"]
            size, _ = langs.get(name, (0, color))
            langs[name] = (size + edge["size"], color)
    total = sum(s for s, _ in langs.values()) or 1
    top = sorted(langs.items(), key=lambda kv: kv[1][0], reverse=True)[:5]
    top = [
        (name, size / total * 100, color or FALLBACK_COLORS[i % 5])
        for i, (name, (size, color)) in enumerate(top)
    ]

    stats = [
        (fmt(contribs), "CONTRIBUTIONS · PAST YEAR"),
        (fmt(stars), "STARS EARNED"),
        (fmt(repos["totalCount"]), "PUBLIC REPOS"),
        (fmt(user["followers"]["totalCount"]), "FOLLOWERS"),
    ]
    return stats, top


def render(stats, top, primary, muted, path):
    W, BAR_X, BAR_W = 900, 40, 820
    parts = [
        f'<svg width="{W}" height="150" viewBox="0 0 {W} 150" fill="none" xmlns="http://www.w3.org/2000/svg">',
        "<g font-family=\"'Segoe UI', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', Arial, sans-serif\">",
    ]
    # Stat columns
    for i, (num, label) in enumerate(stats):
        cx = W / (len(stats) + 1) * (i + 1)
        parts.append(
            f'<text x="{cx:.0f}" y="46" text-anchor="middle" font-size="30" font-weight="650" fill="{primary}">{num}</text>'
        )
        parts.append(
            f'<text x="{cx:.0f}" y="70" text-anchor="middle" font-size="10.5" font-weight="600" letter-spacing="1.6" fill="{muted}">{label}</text>'
        )
    # Language bar (stacked, rounded via clip)
    parts.append(
        f'<clipPath id="bar"><rect x="{BAR_X}" y="92" width="{BAR_W}" height="8" rx="4"/></clipPath>'
    )
    x = BAR_X
    for name, pct, color in top:
        w = BAR_W * pct / 100
        parts.append(
            f'<rect x="{x:.1f}" y="92" width="{w:.1f}" height="8" fill="{color}" clip-path="url(#bar)"/>'
        )
        x += w
    if x < BAR_X + BAR_W:  # remainder (other languages)
        parts.append(
            f'<rect x="{x:.1f}" y="92" width="{BAR_X + BAR_W - x:.1f}" height="8" fill="{muted}" opacity="0.25" clip-path="url(#bar)"/>'
        )
    # Legend, evenly spaced
    for i, (name, pct, color) in enumerate(top):
        cx = W / (len(top) + 1) * (i + 1)
        label = f"{name} {pct:.0f}%"
        text_w = len(label) * 6.4
        parts.append(
            f'<circle cx="{cx - text_w / 2 - 10:.1f}" cy="126" r="4.5" fill="{color}"/>'
        )
        parts.append(
            f'<text x="{cx:.0f}" y="130" text-anchor="middle" font-size="12" fill="{muted}">{label}</text>'
        )
    parts.append("</g></svg>")
    with open(path, "w") as f:
        f.write("\n".join(parts) + "\n")
    print(f"wrote {path}")


def main():
    user = fetch()
    stats, top = build(user)
    os.makedirs(OUT_DIR, exist_ok=True)
    render(stats, top, "#1f2328", "#6e7781", os.path.join(OUT_DIR, "stats-light.svg"))
    render(stats, top, "#e6edf3", "#9198a1", os.path.join(OUT_DIR, "stats-dark.svg"))


if __name__ == "__main__":
    main()
