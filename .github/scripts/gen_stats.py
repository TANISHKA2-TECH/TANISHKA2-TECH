"""Generates neon-themed stats SVGs for the profile README.
Runs inside GitHub Actions with the built-in GITHUB_TOKEN. No extra packages needed."""
import html
import json
import os
import urllib.request

USER = os.environ.get("GH_USER", "TANISHKA2-TECH")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "assets")

SANS = "'Segoe UI',Inter,'Helvetica Neue',Arial,sans-serif"
MONO = "'JetBrains Mono','SF Mono',Menlo,Consolas,'Courier New',monospace"

LANG_COLORS = {
    "Python": "#3b82f6", "Jupyter Notebook": "#f97316", "SQL": "#22d3ee", "JavaScript": "#facc15",
    "TypeScript": "#38bdf8", "HTML": "#f87171", "CSS": "#a78bfa", "C++": "#f472b6", "C": "#94a3b8",
    "Java": "#fb923c", "Shell": "#34d399", "R": "#60a5fa", "MATLAB": "#fbbf24", "Dockerfile": "#0ea5e9",
}
FALLBACK = ["#8b5cf6", "#22d3ee", "#f472b6", "#34d399", "#fbbf24", "#60a5fa", "#fb7185"]


def api(url, data=None):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "profile-stats"}
    if TOKEN:
        headers["Authorization"] = "Bearer " + TOKEN
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def collect():
    info = {"repos": 0, "stars": 0, "followers": 0, "contribs": None, "langs": {}}
    u = api(f"https://api.github.com/users/{USER}")
    info["repos"] = u.get("public_repos", 0)
    info["followers"] = u.get("followers", 0)
    repos = api(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner")
    for r in repos:
        if r.get("fork"):
            continue
        info["stars"] += r.get("stargazers_count", 0)
        try:
            for lang, b in api(r["languages_url"]).items():
                info["langs"][lang] = info["langs"].get(lang, 0) + b
        except Exception as e:
            print("lang fetch failed for", r.get("name"), e)
    nb = info["langs"].pop("Jupyter Notebook", 0)
    if nb:
        info["langs"]["Python"] = info["langs"].get("Python", 0) + nb
    try:
        q = ('{ user(login: "%s") { contributionsCollection { contributionCalendar { totalContributions } } } }' % USER)
        res = api("https://api.github.com/graphql", json.dumps({"query": q}).encode())
        info["contribs"] = res["data"]["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]
    except Exception as e:
        print("graphql failed", e)
    return info


def head(w, h, extra=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" font-family="{SANS}">'
            '<style>.tile{animation:tp 3.6s ease-in-out infinite}@keyframes tp{0%,100%{stroke-opacity:.35}50%{stroke-opacity:.95}}'
            '@media (prefers-reduced-motion:reduce){*{animation:none!important}}' + extra + '</style>'
            '<defs><filter id="glow" x="-30%" y="-50%" width="160%" height="200%"><feGaussianBlur stdDeviation="4" result="b"/>'
            '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>')


def render_stats(info):
    W, H = 1000, 140
    contribs = "-" if info["contribs"] is None else f'{info["contribs"]:,}'
    data = [(f'{info["repos"]:,}', "public repos", "#a78bfa"), (f'{info["stars"]:,}', "stars earned", "#fbbf24"),
            (f'{info["followers"]:,}', "followers", "#22d3ee"), (contribs, "contributions, last year", "#f472b6")]
    tw, gap = 238, 16
    s = head(W, H)
    for i, (v, l, c) in enumerate(data):
        x = i * (tw + gap)
        s += (f'<g transform="translate({x},0)"><rect width="{tw}" height="{H}" rx="16" fill="#0a0e24"/>'
              f'<rect class="tile" x="1" y="1" width="{tw - 2}" height="{H - 2}" rx="16" fill="none" stroke="{c}" stroke-width="1.6" style="animation-delay:-{i * 0.8:.1f}s"/>'
              f'<rect x="{tw / 2 - 22}" width="44" height="3" rx="1.5" fill="{c}"/>'
              f'<text x="{tw / 2}" y="72" text-anchor="middle" font-size="40" font-weight="800" fill="{c}" filter="url(#glow)">{html.escape(v)}</text>'
              f'<text x="{tw / 2}" y="104" text-anchor="middle" font-size="14" fill="#94a3b8">{l}</text></g>')
    return s + '</svg>'


def fmt_pct(p):
    return "&lt;0.1%" if p < 0.1 else f"{p:.1f}%"


def render_langs(info):
    W = 1000
    langs = sorted(info["langs"].items(), key=lambda kv: -kv[1])
    total = sum(b for _, b in langs) or 1
    top = langs[:6]
    rest = sum(b for _, b in langs[6:])
    if rest:
        top.append(("Other", rest))
    H = (140 + ((len(top) + 1) // 2 - 1) * 34 + 46) if top else 150
    s = head(W, H)
    s += (f'<rect width="{W}" height="{H}" rx="18" fill="#0a0e24"/>'
          f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="18" fill="none" stroke="#6d28d9" stroke-opacity=".55" stroke-width="1.5"/>'
          f'<text x="40" y="48" font-family="{MONO}" font-size="14" fill="#94a3b8">most used languages</text>')
    if not langs:
        s += '<text x="40" y="120" font-size="16" fill="#e2e8f0">No language data yet. Push some code and this fills itself.</text>'
        return s + '</svg>'
    bx, bw = 40, 920
    s += f'<clipPath id="bar"><rect x="{bx}" y="68" width="{bw}" height="22" rx="11"/></clipPath><g clip-path="url(#bar)"><rect x="{bx}" y="68" width="{bw}" height="22" fill="#151a3d"/>'
    x = bx
    items = []
    for i, (name, b) in enumerate(top):
        col = "#64748b" if name == "Other" else LANG_COLORS.get(name, FALLBACK[i % len(FALLBACK)])
        w = bw * b / total
        s += (f'<rect x="{x:.1f}" y="68" height="22" width="0" fill="{col}">'
              f'<animate attributeName="width" from="0" to="{w:.1f}" dur="1.2s" begin="{i * 0.15:.2f}s" fill="freeze"/></rect>')
        items.append((name, b / total * 100, col))
        x += w
    s += '</g>'
    for i, (name, pct, col) in enumerate(items):
        cx = 40 if i % 2 == 0 else 520
        cy = 140 + (i // 2) * 34
        s += (f'<circle cx="{cx + 7}" cy="{cy - 5}" r="7" fill="{col}"/>'
              f'<text x="{cx + 24}" y="{cy}" font-size="16" font-weight="600" fill="#e2e8f0">{html.escape(name)}</text>'
              f'<text x="{cx + 440}" y="{cy}" text-anchor="end" font-family="{MONO}" font-size="15" fill="#94a3b8">{fmt_pct(pct)}</text>')
    return s + '</svg>'


def main():
    info = collect()
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "gh-stats.svg"), "w", encoding="utf-8") as f:
        f.write(render_stats(info))
    with open(os.path.join(OUT, "gh-langs.svg"), "w", encoding="utf-8") as f:
        f.write(render_langs(info))
    print("done", info["repos"], info["stars"], info["followers"], info["contribs"], list(info["langs"])[:5])


if __name__ == "__main__":
    main()
