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

TW, TH = 20, 4                  # 타일 마름모 폭·높이. 2:1 이 정석이지만 그러면 세로가
                                # 너무 길어진다 — 리드미 한 줄에서 방문자 카운터와 나란히
                                # 서야 해서 납작하게 눕혔다(2026-08-27 지시)
LEVEL_H = 8                     # 한 단계 블록 높이
FLOOR = 4                       # 0 단계에서도 보이는 바닥 두께
BAND = 2                        # 옆면 위쪽 잔디 띠
DAYS = 7
# 캔버스를 640x192 로 떨어뜨리는 여백. 리드미 한 줄 폭 846 에서 오른쪽 방문자
# 카운터 202 와 그림 사이 간격 4 를 빼면 640 이고, 높이는 카운터와 같은 192 라야
# 두 덩이 아랫변이 한 줄에 선다(2026-08-27 확정)
PAD_L, PAD_R, PAD_T, PAD_B = 24, 16, 22, 14

DOT = 1                         # 도트 한 칸의 화면 픽셀. 도트가 세로 24 라
                                # 캐릭터가 블록 세 단 높이다
RUNNERS = ["norma", "sparkle", "kei", "aria", "nangongyu", "sunna"]
ROWS = [1, 2, 3, 4, 5, 6]       # 각자 다른 요일 줄을 달린다
                                # 0(맨 뒷줄)은 뒤가 허공이라 떠 보인다 — 비운다
POSES = 4                       # 러닝 프레임 수
CELL_SEC = 0.75                 # 한 칸 주기 — 뛰는 동안과 서 있는 동안을 합친 것
PREP = 0.08                     # 웅크리는 몫. 이게 없으면 예비동작 없이 몸이 튄다
JUMP = 0.30                     # 도약이 끝나는 지점(= 착지)
LAND = 0.38                     # 착지해서 눌려 있는 동안. 그 뒤로는 서 있는다
STEP = 2                        # 뛰는 동안 몇 번에 나눠 옮기나. 가로 10px 과 사다리
                                # 32px 을 둘 다 정수로 쪼개는 값이라 2 다 — 소수가
                                # 되면 도트가 반 픽셀에 걸려 번진다
ARC = [0, -8, -12, -7]          # 도약 중 몸이 뜨는 높이 — 마리오처럼 포물선
LADDER = 4                      # 이 단수 이상 솟은 칸은 점프로 못 오른다. 벽 앞까지
                                # 간 뒤 기어오른다(2026-08-27 지시 「4칸이상은 사다리
                                # 모션으로하자」). 한 해 데이터에서 11 곳이 걸린다
LADDER_MID = 0.45               # 벽 앞에 닿는 박자
LADDER_TOP = 0.92               # 다 올라간 박자
# 눌리고 늘어나는 몫. 러닝 프레임이 따로 도니 예전만큼 셀 필요가 없다.
# 발밑이 원점이라 세로 배율만 건드려도 발은 붙어 있고 몸만 내려앉는다.
# (박자, 가로배율, 세로배율)
FLY = JUMP - PREP
SQUASH = [(0, 1, 1),
          (PREP, 1.05, 0.94),               # 웅크림
          (PREP + FLY * .25, 0.97, 1.04),   # 차고 나가며 늘어남
          (PREP + FLY * .75, 1, 1),         # 공중에서는 그대로
          (JUMP, 1.06, 0.93),               # 착지 충격
          (LAND, 1, 1)]

CAL = """contributionsCollection { contributionCalendar {
  totalContributions
  weeks { contributionDays { date contributionCount weekday } }
} }"""

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

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


def sprite(d, k, dy=0):
    """도트 데이터를 색깔별 path 로. 발밑 가운데가 (0,0) 에 오게 놓는다."""
    ox, oy = -(d["w"] * DOT) // 2, -d["h"] * DOT - dy
    by = {}
    for y, row in enumerate(d["poses"][k]):
        for x, n, c in row:
            by.setdefault(c, []).append(
                f'M{ox + x * DOT} {oy + y * DOT}h{n * DOT}v{DOT}h-{n * DOT}z')
    return "".join(f'<path fill="{d["pal"][c]}" d="{"".join(v)}"/>'
                   for c, v in sorted(by.items()))


def runner_css(rows_lv, ox, oy, nw):
    """웅크렸다 한 칸 뛰고, 착지해서 눌렸다가, 다음 박자까지 서 있게 한다.

    쉬지 않고 움직이면 여섯이 한 화면에서 산만하다. 한 칸을 한 박자로 잡고
    앞쪽 일부만 도약에 쓴다. 남는 동안은 다음 키프레임이 같은 자리라 저절로
    멈춰 선다 — 서 있는 동안을 따로 그릴 필요가 없다.

    러닝 프레임 넷을 박자 안에서 갈아 끼운다. 웅크림·도약·착지·서 있기에 하나씩
    배정해 다리가 실제로 움직인다(2026-08-27 지적 「모션이 없는데」). 프레임을
    공통 캔버스에 정렬해 구웠으므로 갈아 끼워도 몸이 좌우로 안 튄다.

    가로는 steps 로 끊어 옮긴다. 부드럽게 이으면 반 픽셀 자리가 생겨 도트가
    번진다. 눌림은 칸마다 같으므로 짧은 반복으로 걸지만, 세로 포물선은 칸마다
    달라야 한다 — 사다리로 오르는 칸에서는 포물선이 없어야 하기 때문이다.
    그래서 도약만 전체 주기짜리 키프레임으로 캐릭터마다 따로 만든다.
    """
    hw, hh = TW // 2, TH // 2
    w0 = -3
    span = -(-(nw + 6) // STEP) * STEP      # 칸 수를 STEP 배수로 올린다
    w1 = w0 + span
    dur = CELL_SEC * span
    n = len(ROWS)

    sq = "".join(f"{t * 100:.4g}%{{transform:scale({sx:g},{sy:g})}}"
                 for t, sx, sy in SQUASH) + "100%{transform:scale(1,1)}"

    # 프레임 넷이 도는 구간. 서 있는 동안은 한 장으로 고정한다
    mid = PREP + FLY / 2
    win = [(LAND, 1.0), (PREP, mid), (mid, JUMP), (JUMP, LAND)]
    css = [f".ch{{animation:fade {dur:.2f}s linear infinite}}",
           f".sq{{transform-origin:0 0;"
           f"animation:sq {CELL_SEC}s steps(1,start) infinite}}",
           "@keyframes fade{0%,2%{opacity:0}5%,95%{opacity:1}98%,100%{opacity:0}}",
           "@keyframes sq{" + sq + "}"]
    for j, (t0, t1) in enumerate(win):
        kf = [(0.0, 1 if j == 0 else 0)]
        if t0 > 0:
            kf.append((t0, 1))
        if t1 < 1:
            kf.append((t1, 0))
        last = 1 if t1 >= 1 else 0
        css.append(f"@keyframes f{j}{{" + "".join(
            f"{t * 100:.4g}%{{opacity:{v}}}" for t, v in kf)
            + f"100%{{opacity:{last}}}}}")
        css.append(f".f{j}{{animation:f{j} {CELL_SEC}s steps(1,start) infinite}}")

    def spot(wd, wi):
        lv = rows_lv[wd][wi] if 0 <= wi < nw else 0
        return (ox + (wi + wd) * hw, oy + (wd - wi) * hh - lv * LEVEL_H)

    def lvl(wd, wi):
        return rows_lv[wd][wi] if 0 <= wi < nw else 0

    home = []
    for i, wd in enumerate(ROWS):
        kf, arc = [], []
        for k in range(span + 1):
            wi = w0 + k
            x, y = spot(wd, wi)
            nx, ny = spot(wd, wi + 1)
            pct = k * 100 / span
            kf.append(f"{pct:.4g}%{{transform:translate({x}px,{y}px)}}")
            if k >= span:
                break
            # 웅크리는 동안은 제자리 — 웅크린 채 미끄러지면 안 된다
            kf.append(f"{(k + PREP) * 100 / span:.4g}%"
                      f"{{transform:translate({x}px,{y}px)}}")
            if lvl(wd, wi + 1) - lvl(wd, wi) >= LADDER:
                # 벽 앞까지 간 뒤 수직으로 오른다. 벽 앞은 다음 칸 자리에 지금 높이
                kf.append(f"{(k + LADDER_MID) * 100 / span:.4g}%"
                          f"{{transform:translate({nx}px,{y - hh}px)}}")
                kf.append(f"{(k + LADDER_TOP) * 100 / span:.4g}%"
                          f"{{transform:translate({nx}px,{ny}px)}}")
                continue
            kf.append(f"{(k + JUMP) * 100 / span:.4g}%"
                      f"{{transform:translate({nx}px,{ny}px)}}")
            for m, v in enumerate(ARC):
                arc.append(f"{(k + PREP + m * FLY / (len(ARC) - 1)) * 100 / span:.4g}%"
                           f"{{transform:translateY({v}px)}}")
            arc.append(f"{(k + JUMP) * 100 / span:.4g}%{{transform:translateY(0)}}")
        home.append(spot(wd, (w0 + w1) // 2))
        css.append(f"@keyframes r{i}{{" + "".join(kf) + "}")
        css.append(f".p{i}{{animation:r{i} {dur:.2f}s steps({STEP},end) infinite}}")
        css.append("@keyframes h%d{0%%{transform:translateY(0)}%s100%%"
                   "{transform:translateY(0)}}" % (i, "".join(arc)))
        css.append(f".h{i}{{animation:h{i} {dur:.2f}s linear infinite}}")
    for i in range(n):
        # 칸 단위로만 어긋나게 한다 — 반 칸이 섞이면 도약과 착지가 엇박이 된다
        css.append(f".d{i}{{animation-delay:{-CELL_SEC * round(span * i / n):.2f}s}}")
    stop = ",".join(f".p{i},.h{i}" for i in range(n))
    css.append("@media (prefers-reduced-motion:reduce){"
               f".ch,.sq,.f0,.f1,.f2,.f3,{stop}{{animation:none}}"
               ".f0{opacity:1}.f1,.f2,.f3{opacity:0}}")
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
        poses = "".join(f'<g class="f{j} d{i}">{sprite(run[name], j)}</g>'
                        for j in range(POSES))
        s.append(f'<g class="ch d{i}"><g class="p{i} d{i}" '
                 f'transform="translate({hx},{hy})">'
                 f'<g class="h{i} d{i}"><g class="sq d{i}">'
                 f'{poses}</g></g></g></g>')

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
    # 합계는 왼쪽 위에. 아래쪽에 두면 낮은 지형과 겹쳐 글씨가 안 읽히고,
    # 아이소메트릭 대각선이 만드는 좌상단 빈 자리가 마침 여기다
    s.append(T.text(f'{cal["totalContributions"]} contributions', PAD_L, PAD_T + 12, 10,
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
