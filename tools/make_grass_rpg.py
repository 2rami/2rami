#!/usr/bin/env python3
"""기여 잔디를 아이소메트릭 블록 지형으로 그린다.

평면 격자 대신 칸마다 블록을 세운다. 기여가 많은 날일수록 기둥이 높아져
지형이 울퉁불퉁해지고, 그 위를 캐릭터가 뛰어다닌다.

좌표는 전부 정수로 떨어지게 잡았다(TW=24, TH=12 — 2:1 이라야 정육면체로 보인다).
소수가 섞이면 브라우저가 반 픽셀에 걸쳐 그려 도트 경계가 흐려진다.

GitHub 마크다운은 <script>/<style> 속성을 지우지만, SVG 파일 안에 들어 있는
<style> 은 <img> 로 불러도 그대로 산다. 색 전환과 애니메이션이 거기 얹힌다.
"""
import json
import os
import pathlib
import subprocess
import sys
import urllib.request

ROOT = pathlib.Path(__file__).parent.parent
OUT = ROOT / "assets" / "grass-rpg.svg"
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import textpath as T  # noqa: E402

TW, TH = 24, 12                 # 타일 마름모 폭·높이 — 2:1 이라야 정육면체로 보인다
LEVEL_H = 12                    # 한 단계 = 정육면체 한 개 (TW 의 절반)
FLOOR = 6                       # 0 단계에서도 보이는 바닥 두께
BAND = 3                        # 옆면 위쪽 잔디 띠
DAYS = 7
PAD_L, PAD_R, PAD_T, PAD_B = 56, 70, 76, 44

DOT = 2                         # 도트 한 칸의 화면 픽셀 — 8x12 도트가 16x24px 이
                                # 되어 블록 한 칸과 키가 같다
RUNNERS = ["norma", "sparxie", "kei", "aria", "nangong", "sunna"]
ROWS = [1, 2, 3, 4, 5, 6]       # 각자 다른 요일 줄을 달린다
                                # 0(맨 뒷줄)은 뒤가 허공이라 떠 보인다 — 비운다
CELL_SEC = 0.75                 # 한 칸 주기 — 뛰는 동안과 서 있는 동안을 합친 것
JUMP = 0.30                     # 그중 뛰는 몫. 나머지는 착지해서 가만히 있는다
STEP = 4                        # 뛰는 동안 몇 번에 나눠 옮기나 — 12px/4 = 3px 씩
ARC = [0, -7, -10, -6]          # 도약 중 몸이 뜨는 높이 — 마리오처럼 포물선

CAL = """contributionsCollection { contributionCalendar {
  totalContributions
  weeks { contributionDays { date contributionCount weekday } }
} }"""

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
WD = {1: "Mon", 3: "Wed", 5: "Fri"}   # GitHub 주는 일요일 시작 — 0 이 일요일이다

PALETTES = {
    # 초록 — 레퍼런스에 충실. 라이트/다크 같은 색이라 어디서 봐도 인상이 같다
    "green": {
        "top": ["#2f5134", "#3f7038", "#5f9243", "#8bb851", "#c8e176"],
        "dirtL": "#352915", "dirtR": "#634529",
        "lbl": "#6f8a5f", "lblDark": "#8fae7c",
    },
    # 하늘색 — README 위쪽 카운터·카드와 같은 계열. 라이트/다크가 다르다
    "sky": {
        "top": ["#e8f4fb", "#b8dcf0", "#7cc0e8", "#3d9fdb", "#1479c9"],
        "dirtL": "#3d5468", "dirtR": "#6a8296",
        "topDark": ["#14202c", "#1d4460", "#2a6b94", "#3a95c7", "#58b6f8"],
        "dirtLDark": "#101c26", "dirtRDark": "#22384a",
        "lbl": "#5d7f95", "lblDark": "#8badc4",
    },
}


def fetch():
    """달력을 받아 온다.

    GRASS_USER 가 있으면 그 사람 것을, 없으면 토큰 주인 것을 본다. CI 는
    저장소 토큰으로 도는데 그 주인이 봇이라 viewer 로는 빈 달력이 온다.
    다만 남의 자격으로 보면 비공개 기여는 안 세므로, 그것까지 넣으려면
    본인 PAT 를 GITHUB_TOKEN 으로 넣어야 한다.
    """
    cache = os.environ.get("GRASS_CAL")
    if cache and pathlib.Path(cache).exists():
        return json.loads(pathlib.Path(cache).read_text())
    login = os.environ.get("GRASS_USER")
    who = f'user(login:"{login}")' if login else "viewer"
    key = "user" if login else "viewer"
    query = "{ %s { %s } }" % (who, CAL)
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req = urllib.request.Request(
            "https://api.github.com/graphql",
            data=json.dumps({"query": query}).encode(),
            headers={"Authorization": f"bearer {token}",
                     "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            payload = json.load(r)
    else:
        out = subprocess.run(["gh", "api", "graphql", "-f", f"query={query}"],
                             capture_output=True, text=True, check=True)
        payload = json.loads(out.stdout)
    cal = payload["data"][key]["contributionsCollection"]["contributionCalendar"]
    if cache:
        pathlib.Path(cache).write_text(json.dumps(cal))
    return cal


def shade(hexc, k):
    """면마다 밝기를 달리해 입체를 만든다."""
    r, g, b = (int(hexc[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02x%02x%02x" % tuple(min(255, int(v * k)) for v in (r, g, b))


def level(count, steps):
    if count <= 0:
        return 0
    for i, s in enumerate(steps):
        if count <= s:
            return i + 1
    return 4


def css_block(pal, dark=False):
    """면 색 클래스. 다크 전용 팔레트가 있으면 그쪽을 쓴다."""
    tops = pal.get("topDark", pal["top"]) if dark else pal["top"]
    dl = pal.get("dirtLDark", pal["dirtL"]) if dark else pal["dirtL"]
    dr = pal.get("dirtRDark", pal["dirtR"]) if dark else pal["dirtR"]
    out = []
    for i, c in enumerate(tops):
        out.append(f".t{i}{{fill:{c}}}")
        out.append(f".a{i}{{fill:{shade(c, .42)}}}")   # 왼쪽 잔디 띠
        out.append(f".b{i}{{fill:{shade(c, .66)}}}")   # 오른쪽 잔디 띠
    out.append(f".dl{{fill:{dl}}}")
    out.append(f".dr{{fill:{dr}}}")
    out.append(f".lbl{{fill:{pal['lblDark'] if dark else pal['lbl']}}}")
    return out


def block(cx, base_y, lv):
    """블록 기둥 하나. 윗면 마름모 + 좌우 옆면(잔디 띠 + 흙)."""
    hw, hh = TW // 2, TH // 2
    h = lv * LEVEL_H + FLOOR          # 옆면 세로 길이
    ty = base_y - lv * LEVEL_H        # 윗면 중심 y
    s = []
    # 윗면
    s.append(f'<path class="t{lv}" d="M{cx - hw} {ty}L{cx} {ty - hh}'
             f'L{cx + hw} {ty}L{cx} {ty + hh}Z"/>')
    # 왼쪽 면 — 잔디 띠와 흙을 따로 그린다
    s.append(f'<path class="a{lv}" d="M{cx - hw} {ty}L{cx} {ty + hh}'
             f'L{cx} {ty + hh + BAND}L{cx - hw} {ty + BAND}Z"/>')
    s.append(f'<path class="dl" d="M{cx - hw} {ty + BAND}L{cx} {ty + hh + BAND}'
             f'L{cx} {ty + hh + h}L{cx - hw} {ty + h}Z"/>')
    # 오른쪽 면
    s.append(f'<path class="b{lv}" d="M{cx + hw} {ty}L{cx} {ty + hh}'
             f'L{cx} {ty + hh + BAND}L{cx + hw} {ty + BAND}Z"/>')
    s.append(f'<path class="dr" d="M{cx + hw} {ty + BAND}L{cx} {ty + hh + BAND}'
             f'L{cx} {ty + hh + h}L{cx + hw} {ty + h}Z"/>')
    return s


def load_runners():
    return json.loads((pathlib.Path(__file__).parent / "runners.json").read_text())


def sprite(d, dy=0):
    """도트 데이터를 색깔별 path 로. 발밑 가운데가 (0,0) 에 오게 놓는다."""
    ox, oy = -(d["w"] * DOT) // 2, -d["h"] * DOT - dy
    by = {}
    for y, row in enumerate(d["rows"]):
        for x, n, c in row:
            by.setdefault(c, []).append(
                f'M{ox + x * DOT} {oy + y * DOT}h{n * DOT}v{DOT}h-{n * DOT}z')
    return "".join(f'<path fill="{d["pal"][c]}" d="{"".join(v)}"/>'
                   for c, v in sorted(by.items()))


def runner_css(rows_lv, ox, oy, nw):
    """칸에서 칸으로 폴짝 뛰고, 착지하면 다음 박자까지 가만히 서 있게 한다.

    쉬지 않고 움직이면 여섯이 한 화면에서 산만하다. 한 칸을 한 박자로 잡고
    그중 앞의 30% 만 도약에 쓴다. 나머지 70% 는 다음 키프레임이 같은 자리라
    저절로 멈춰 선다 — 서 있는 동안을 따로 그릴 필요가 없다.

    가로는 steps(4) 로 3px 씩 끊어 옮긴다. 부드럽게 이으면 반 픽셀 자리가
    생겨 도트가 번진다. 세로는 착지 높이까지 계단으로 오르고 그 위에
    포물선을 얹는데, 포물선은 칸마다 같으므로 안쪽 그룹에 짧은 반복 하나로
    건다. 대신 경로의 지연이 칸 길이의 정수배여야 도약과 착지가 안 엇갈린다.
    """
    hw, hh = TW // 2, TH // 2
    w0 = -3
    span = -(-(nw + 6) // STEP) * STEP      # 칸 수를 STEP 배수로 올린다
    w1 = w0 + span
    dur = CELL_SEC * span
    n = len(ROWS)

    arc = "".join(f"{k * JUMP * 100 / len(ARC):.4g}%{{transform:translateY({v}px)}}"
                  for k, v in enumerate(ARC))
    arc += f"{JUMP * 100:.4g}%,100%{{transform:translateY(0)}}"
    css = [f".ch{{animation:fade {dur:.2f}s linear infinite}}",
           f".hp{{animation:hop {CELL_SEC}s steps(1,start) infinite}}",
           f".fa{{animation:legA {CELL_SEC}s linear infinite}}",
           f".fb{{animation:legB {CELL_SEC}s linear infinite}}",
           "@keyframes fade{0%,2%{opacity:0}5%,95%{opacity:1}98%,100%{opacity:0}}",
           "@keyframes hop{" + arc + "}",
           # 뜬 동안만 두 번째 포즈, 서 있는 동안은 첫 번째 포즈
           f"@keyframes legA{{0%,{JUMP*100-1:.4g}%{{opacity:0}}"
           f"{JUMP*100:.4g}%,100%{{opacity:1}}}}",
           f"@keyframes legB{{0%,{JUMP*100-1:.4g}%{{opacity:1}}"
           f"{JUMP*100:.4g}%,100%{{opacity:0}}}}"]

    def spot(wd, wi):
        lv = rows_lv[wd][wi] if 0 <= wi < nw else 0
        return (ox + (wi + wd) * hw, oy + (wd - wi) * hh - lv * LEVEL_H)

    home = []
    for i, wd in enumerate(ROWS):
        kf = []
        for k in range(span + 1):
            x, y = spot(wd, w0 + k)
            kf.append(f"{k * 100 / span:.4g}%{{transform:translate({x}px,{y}px)}}")
            if k < span:                       # 도약이 끝나는 순간 = 다음 칸 자리
                nx, ny = spot(wd, w0 + k + 1)
                kf.append(f"{(k + JUMP) * 100 / span:.4g}%"
                          f"{{transform:translate({nx}px,{ny}px)}}")
        home.append(spot(wd, (w0 + w1) // 2))
        css.append(f"@keyframes r{i}{{" + "".join(kf) + "}")
        css.append(f".p{i}{{animation:r{i} {dur:.2f}s steps({STEP},end) infinite}}")
    for i in range(n):
        # 칸 단위로만 어긋나게 한다 — 반 칸이 섞이면 도약과 착지가 엇박이 된다
        css.append(f".d{i}{{animation-delay:{-CELL_SEC * round(span * i / n):.2f}s}}")
    stop = ",".join(f".p{i}" for i in range(n))
    css.append("@media (prefers-reduced-motion:reduce){"
               f".ch,.hp,.fa,.fb,{stop}{{animation:none}}}}")
    return css, home


def build(cal, pal):
    weeks = cal["weeks"]
    counts = sorted(c for w in weeks for d in w["contributionDays"]
                    if (c := d["contributionCount"]) > 0)
    steps = [counts[len(counts) * k // 4] for k in (1, 2, 3)] if counts else [1, 2, 3]

    nw = len(weeks)
    hw, hh = TW // 2, TH // 2
    maxh = 4 * LEVEL_H
    # 화면 좌표로 옮기는 오프셋 — 왼쪽 위 끝이 (PAD_L, PAD_T) 에 오게
    ox = PAD_L + hw
    oy = PAD_T + (nw - 1) * hh + maxh + hh
    W = PAD_L + hw + (nw - 1 + DAYS - 1) * hw + hw + PAD_R
    H = oy + (DAYS - 1) * hh + hh + FLOOR + PAD_B

    css = css_block(pal)
    css.append("@media (prefers-color-scheme:dark){")
    css += css_block(pal, dark=True)
    css.append("}")

    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
         f'width="{W}" height="{H}" role="img" aria-label="contribution terrain">',
         "<style>__CSS__</style>"]

    # 뒤에서 앞으로 — 아이소메트릭은 (d-w) 가 클수록 앞이다
    cells = []
    rows_lv = [[0] * nw for _ in range(DAYS)]
    for wi, w in enumerate(weeks):
        for d in w["contributionDays"]:
            wd = d["weekday"]
            lv = level(d["contributionCount"], steps)
            rows_lv[wd][wi] = lv
            cells.append((wd - wi, wi, wd, lv))
    cells.sort(key=lambda c: c[0])
    for _, wi, wd, lv in cells:
        s += block(ox + (wi + wd) * hw, oy + (wd - wi) * hh, lv)

    run = load_runners()
    rcss, home = runner_css(rows_lv, ox, oy, nw)
    css += rcss
    for i, name in enumerate(RUNNERS):
        hx, hy = home[i]
        s.append(f'<g class="ch d{i}"><g class="p{i} d{i}" '
                 f'transform="translate({hx},{hy})">'
                 f'<g class="hp d{i}">'
                 f'<g class="fa d{i}">{sprite(run[f"a-{name}"])}</g>'
                 f'<g class="fb d{i}" opacity="0">{sprite(run[f"b-{name}"])}</g>'
                 f'</g></g></g>')

    # 요일 — 왼쪽 모서리 바깥
    for wd, name in WD.items():
        s.append(T.text(name, ox - hw - 8, oy + wd * hh + 4, 9,
                        cls="lbl", weight="regular", anchor="end"))
    # 월 — 아래쪽 대각 모서리를 따라
    seen = set()
    for wi, w in enumerate(weeks):
        m = int(w["contributionDays"][0]["date"][5:7])
        if m in seen or wi >= nw - 1:
            continue
        seen.add(m)
        x = ox + (wi + DAYS - 1) * hw
        y = oy + (DAYS - 1 - wi) * hh + FLOOR + 16
        s.append(T.text(MONTHS[m - 1], x, y, 9, cls="lbl", weight="regular",
                        anchor="middle"))

    # 범례
    lx, ly = W - PAD_R - 5 * 14 - 46, H - 14
    s.append(T.text("Less", lx - 6, ly, 9, cls="lbl", weight="regular", anchor="end"))
    for i in range(5):
        s.append(f'<path class="t{i}" d="M{lx + i*14} {ly-3}L{lx + i*14 + 6} {ly-8}'
                 f'L{lx + i*14 + 12} {ly-3}L{lx + i*14 + 6} {ly+2}Z"/>')
    s.append(T.text("More", lx + 5 * 14, ly, 9, cls="lbl", weight="regular"))
    s.append(T.text(f'{cal["totalContributions"]} contributions', PAD_L, H - 14, 10,
                    cls="lbl", weight="regular"))
    s.append("</svg>")
    return "\n".join(s).replace("__CSS__", "\n" + "\n".join(css) + "\n"), W, H, steps


if __name__ == "__main__":
    cal = fetch()
    name = os.environ.get("GRASS_PALETTE", "green")
    out = pathlib.Path(os.environ.get("GRASS_OUT") or OUT)
    svg, W, H, steps = build(cal, PALETTES[name])
    out.write_text(svg)
    print(f"  {out}  {name}  {W}x{H}  {out.stat().st_size//1024}KB")
    print(f"  단계 경계: 1~{steps[0]} / ~{steps[1]} / ~{steps[2]} / 그 이상")
