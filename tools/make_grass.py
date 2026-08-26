#!/usr/bin/env python3
"""기여 잔디를 직접 그린다.

남의 서비스를 쓰지 않는 이유는 톤이다. snake 도 3d-contrib 도 색을 우리 팔레트로
못 맞춘다. 데이터는 GitHub GraphQL 로 받아 오고 그림은 우리가 그린다.

칸 크기와 간격은 정수로 잡는다. 소수로 두면 브라우저가 반 픽셀에 걸쳐 그려
도트 경계가 흐려진다.

토큰은 GITHUB_TOKEN 환경변수를 먼저 보고, 없으면 gh CLI 를 부른다.
(CI 에서는 환경변수, 로컬에서는 gh)
"""
import json
import os
import pathlib
import subprocess
import sys
import urllib.request

ROOT = pathlib.Path(__file__).parent.parent
OUT = ROOT / "assets" / "grass.svg"

CELL, GAP = 12, 3                      # 칸·간격 (정수여야 도트가 안 번진다)
PAD_X, PAD_TOP, PAD_BOT = 10, 26, 20
DAYS = 7
SWEEP = 7.0                            # 빛이 한 번 훑는 데 걸리는 시간(초)

QUERY = """{ viewer { contributionsCollection { contributionCalendar {
  totalContributions
  weeks { contributionDays { date contributionCount weekday } }
} } } }"""

# 하늘색 5단계 — 히어로 그림에서 뽑은 팔레트와 같은 계열
LIGHT = ["#e8f4fb", "#b8dcf0", "#7cc0e8", "#3d9fdb", "#1479c9"]
DARK = ["#14202c", "#1d4460", "#2a6b94", "#3a95c7", "#58b6f8"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import textpath as T  # noqa: E402


def fetch():
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req = urllib.request.Request(
            "https://api.github.com/graphql",
            data=json.dumps({"query": QUERY}).encode(),
            headers={"Authorization": f"bearer {token}",
                     "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            payload = json.load(r)
    else:
        out = subprocess.run(["gh", "api", "graphql", "-f", f"query={QUERY}"],
                             capture_output=True, text=True, check=True)
        payload = json.loads(out.stdout)
    return payload["data"]["viewer"]["contributionsCollection"]["contributionCalendar"]


def level(count, steps):
    """기여 수를 0~4 단계로. 절대값으로 자르면 활동이 많은 사람은 전부 최고 단계가 된다."""
    if count <= 0:
        return 0
    for i, s in enumerate(steps):
        if count <= s:
            return i + 1
    return 4


def build(cal):
    weeks = cal["weeks"]
    counts = sorted(c for w in weeks for d in w["contributionDays"]
                    if (c := d["contributionCount"]) > 0)
    # 활동한 날만 4분위로 나눈다 — 0 을 섞으면 대부분이 1단계로 몰린다
    q = [counts[len(counts) * k // 4] for k in (1, 2, 3)] if counts else [1, 2, 3]
    steps = [q[0], q[1], q[2]]

    W = PAD_X * 2 + len(weeks) * (CELL + GAP) - GAP
    H = PAD_TOP + DAYS * (CELL + GAP) - GAP + PAD_BOT

    css = ["  .lbl{fill:#5d7f95}"]
    for i, c in enumerate(LIGHT):
        css.append(f"  .l{i}{{fill:{c}}}")
    css.append("  @media (prefers-color-scheme: dark){")
    css.append("    .lbl{fill:#8badc4}")
    for i, c in enumerate(DARK):
        css.append(f"    .l{i}{{fill:{c}}}")
    css.append("  }")
    # 빛이 왼쪽에서 오른쪽으로 훑는다 — 구름 그림자가 지나가는 느낌
    css.append(f"  .sweep{{animation:sw {SWEEP}s linear infinite}}")
    css.append(f"  @keyframes sw{{from{{transform:translateX({-W*0.35:.0f}px)}}"
               f"to{{transform:translateX({W}px)}}}}")
    css.append("  @media (prefers-reduced-motion:reduce){.sweep{animation:none;opacity:0}}")

    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" '
         f'height="{H}" role="img" aria-label="contributions">',
         "<style>\n" + "\n".join(css) + "\n</style>"]

    # 월 이름 — 그 달이 처음 나오는 주 위에만
    seen = set()
    for wi, w in enumerate(weeks):
        m = int(w["contributionDays"][0]["date"][5:7])
        if m not in seen and wi < len(weeks) - 1:
            seen.add(m)
            s.append(T.text(MONTHS[m - 1], PAD_X + wi * (CELL + GAP), PAD_TOP - 9,
                            9, cls="lbl", weight="regular"))

    for wi, w in enumerate(weeks):
        x = PAD_X + wi * (CELL + GAP)
        for d in w["contributionDays"]:
            y = PAD_TOP + d["weekday"] * (CELL + GAP)
            lv = level(d["contributionCount"], steps)
            s.append(f'<rect class="l{lv}" x="{x}" y="{y}" width="{CELL}" '
                     f'height="{CELL}" rx="2"/>')

    total = cal["totalContributions"]
    s.append(T.text(f"{total} contributions this year", PAD_X, H - 6, 10,
                    cls="lbl", weight="regular"))

    s.append(f'<rect class="sweep" x="0" y="0" width="{int(W*0.35)}" height="{H}" '
             f'fill="url(#sw)" opacity=".5"/>')
    s.append('<defs><linearGradient id="sw" x1="0" y1="0" x2="1" y2="0">'
             '<stop offset="0" stop-color="#fff" stop-opacity="0"/>'
             '<stop offset=".5" stop-color="#fff" stop-opacity=".55"/>'
             '<stop offset="1" stop-color="#fff" stop-opacity="0"/>'
             "</linearGradient></defs>")
    s.append("</svg>")
    return "\n".join(s), W, H, steps


if __name__ == "__main__":
    cal = fetch()
    svg, W, H, steps = build(cal)
    OUT.write_text(svg)
    print(f"  {OUT.relative_to(ROOT)}  {W}x{H}  {OUT.stat().st_size//1024}KB")
    print(f"  단계 경계: 1~{steps[0]} / ~{steps[1]} / ~{steps[2]} / 그 이상")
