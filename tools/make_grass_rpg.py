#!/usr/bin/env python3
"""잔디 위를 도트 캐릭터가 뛰어다니는 RPG 애니메이션.

make_grass.py 의 격자·팔레트·데이터 수집을 그대로 쓰고, 그 위에 작은 도트
캐릭터 한 마리를 얹는다. 캐릭터는 53개 열(주)을 왼쪽에서 오른쪽으로
순회하며, 각 열의 최고 기여 단계만큼 솟은 곳에 착지한다. 높은 칸은
사다리를 타고 올라간 듯 높이 솟고, 낮은 칸은 폴짝 뛰어 넘는다.

★ GitHub 제약 — 순수 SVG + CSS 만:
  - <script> 는 마크다운에서 통째로 걷혀 나가고, <img> 로 불린 SVG 의
    스크립트도 실행 안 된다. CSS 애니메이션으로만 움직인다.
  - 이동은 1px 정수 단위. 0.5px 씩 보간하면 도트가 픽셀 격자를 벗어나
    번져서 픽셀아트로 안 보인다 → keyframe 마다 steps(1) 로 딱 착지.
  - 다크/라이트는 SVG 안 @media (prefers-color-scheme) 로.
  - @media (prefers-reduced-motion: reduce) 면 캐릭터가 멈춘다.

★ 용량 — 프레임을 통째로 복제하지 않는다. 캐릭터는 도트 path 하나이고,
  위치만 transform(translateX/translateY) 시퀀스로 구운다. keyframe 은
  53열×2(착지/점프정점) = 106개지만 전부 짧은 숫자 쌍이라 수 KB 다.

★ 설계 핵심 — X 와 Y 를 두 개 <g> 로 분리:
  바깥 g(.hero-x): translateX, 열마다 착지.
  안쪽 g(.hero-y): translateY, 열 높이마다 착지.
  둘이 독립 타이밍을 가져야 같은 keyframe 블록에서 X·Y 가 묶이지 않는다.
  점프 궤적은 열 사이에 '공중' keyframe 을 끼워 만든다 — 안 찍으면
  순간이동이라 '뛴다'는 느낌이 안 난다.
"""
import json
import os
import pathlib
import subprocess
import sys
import urllib.request

ROOT = pathlib.Path(__file__).parent.parent
OUT = ROOT / "assets" / "grass-rpg.svg"

CELL, GAP = 12, 3                      # 칸·간격 (정수 — 도트가 안 번진다)
STRIDE = CELL + GAP                    # 15 — 열·행 간격
PAD_X, PAD_TOP, PAD_BOT = 10, 26, 20
DAYS = 7
TOUR = 26.0                            # 캐릭터가 53열을 한 바퀴 도는 시간(초)
HOP = 0.9                              # 제자리 폴짝 점프 주기(초)

QUERY = """{ viewer { contributionsCollection { contributionCalendar {
  totalContributions
  weeks { contributionDays { date contributionCount weekday } }
} } } }"""

LIGHT = ["#e8f4fb", "#b8dcf0", "#7cc0e8", "#3d9fdb", "#1479c9"]
DARK = ["#14202c", "#1d4460", "#2a6b94", "#3a95c7", "#58b6f8"]
# 캐릭터 색 — 잔디 팔레트의 가장 진한 하늘(라이트) / 가장 밝은 하늘(다크)
HERO_LIGHT = "#0d4f8a"
HERO_DARK = "#9fd4ff"
HERO_EYE = "#ffffff"
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
    if count <= 0:
        return 0
    for i, s in enumerate(steps):
        if count <= s:
            return i + 1
    return 4


# ── 도트 캐릭터 ────────────────────────────────────────────────
# 12×12 픽셀. 칸(CELL=12)을 꽉 채워 형태가 읽히게. 7px 때는 점 하나로
# 보여 캐릭터인 줄 몰랐다 — 눈이 보일 만큼은 커야 한다.
# 좌표계: (col,row) 왼위 원점. 1=본체, 2=눈. 발(맨 아래 행)이 y=0 원점에
# 오도록 그리드를 뒤집어 path 를 굽는다 — translateY=0 이면 격자 위에 딱 붙음.
# 두 프레임: A=착지(넓적, 발 벌림), B=도약(타이트, 다리 모음).
W12, H12 = 12, 12

# frame A — 착지. 사람 형태: 머리(눈)/몸통(팔)/다리(벌림).
# 12×12, 위 row0 → 아래 row11. 발(맨 아래)이 y=0 원점.
_A = [
    [0,0,0,0,1,1,1,1,0,0,0,0],   # 머리 꼭대기
    [0,0,0,1,1,1,1,1,1,0,0,0],
    [0,0,0,1,2,1,1,2,1,0,0,0],   # 눈
    [0,0,0,1,1,1,1,1,1,0,0,0],
    [0,0,0,0,1,1,1,1,0,0,0,0],   # 목
    [0,1,1,1,1,1,1,1,1,1,1,0],   # 팔 벌림
    [0,1,1,1,1,1,1,1,1,1,1,0],
    [0,0,0,1,1,1,1,1,1,0,0,0],   # 허리
    [0,0,0,1,1,1,1,1,1,0,0,0],
    [0,0,0,1,1,0,0,1,1,0,0,0],   # 다리 벌림
    [0,0,0,1,1,0,0,1,1,0,0,0],
    [0,0,0,1,1,0,0,1,1,0,0,0],   # 발
]
# frame B — 도약. 다리 모으고 몸을 1도트 위로. 머리/몸은 그대로 → 같은 캐릭터.
_B = [
    [0,0,0,1,1,1,1,0,0,0,0,0],   # 머리 1도트 위
    [0,0,0,1,1,1,1,1,1,0,0,0],
    [0,0,0,1,2,1,1,2,1,0,0,0],   # 눈
    [0,0,0,1,1,1,1,1,1,0,0,0],
    [0,0,0,0,1,1,1,1,0,0,0,0],
    [0,1,1,1,1,1,1,1,1,1,1,0],
    [0,1,1,1,1,1,1,1,1,1,1,0],
    [0,0,0,1,1,1,1,1,1,0,0,0],
    [0,0,0,0,1,1,1,1,0,0,0,0],   # 다리 모음
    [0,0,0,0,1,1,1,1,0,0,0,0],
    [0,0,0,0,1,1,1,1,0,0,0,0],
    [0,0,0,1,1,1,1,1,1,0,0,0],   # 발 모음
]


def _grid_paths(grid):
    """grid(1=본체,2=눈) → (본체path, 눈path). 발(마지막 행)이 y=0 원점.
    위로 올라갈수록 y 는 음수. x 는 col-6 으로 가운데(칸 중앙) 맞춤."""
    body, eye = [], []
    for r, row in enumerate(grid):
        y = r - (H12 - 1)          # 맨 아래 행 → y=0, 위로 음수
        for c, v in enumerate(row):
            if v:
                x = c - 6         # 칸 중앙(6) 맞춤
                seg = f"M{x} {y}h1v1h-1z"
                (eye if v == 2 else body).append(seg)
    return " ".join(body), " ".join(eye)


def hero_paths():
    """캐릭터 두 프레임 (body, eye) path 쌍 반환."""
    return _grid_paths(_A), _grid_paths(_B)


def build(cal):
    weeks = cal["weeks"]
    counts = sorted(c for w in weeks for d in w["contributionDays"]
                    if (c := d["contributionCount"]) > 0)
    q = [counts[len(counts) * k // 4] for k in (1, 2, 3)] if counts else [1, 2, 3]
    steps = [q[0], q[1], q[2]]

    nweeks = len(weeks)
    W = PAD_X * 2 + nweeks * STRIDE - GAP
    H = PAD_TOP + DAYS * STRIDE - GAP + PAD_BOT

    # 각 열(주)의 최고 단계 → 캐릭터가 착지할 높이. 0이면 바닥.
    col_level = []
    for w in weeks:
        lv = max(level(d["contributionCount"], steps) for d in w["contributionDays"])
        col_level.append(lv)

    # ── CSS ──────────────────────────────────────────────────
    css = ["  .lbl{fill:#5d7f95}"]
    for i, c in enumerate(LIGHT):
        css.append(f"  .l{i}{{fill:{c}}}")
    css.append(f"  .hero{{fill:{HERO_LIGHT}}}")
    css.append(f"  .hero-eye{{fill:{HERO_EYE}}}")
    css.append(f"  .ladder{{fill:none;stroke:{HERO_LIGHT};stroke-width:1;opacity:.6}}")
    css.append("  @media (prefers-color-scheme: dark){")
    css.append("    .lbl{fill:#8badc4}")
    for i, c in enumerate(DARK):
        css.append(f"    .l{i}{{fill:{c}}}")
    css.append(f"    .hero{{fill:{HERO_DARK}}}")
    css.append(f"    .ladder{{fill:none;stroke:{HERO_DARK};stroke-width:1;opacity:.6}}")
    css.append("  }")

    # ── 캐릭터 이동 시간표 ───────────────────────────────────
    # ★ 핵심: 각 keyframe 안에 animation-timing-function:steps(1,start) 를
    #   넣는다. 그 구간 시작 즉시 그 keyframe 값으로 '도약' 후 다음 keyframe
    #   전까지 유지 → 보간이 섞지 않아 정수 좌표만 나온다(도트 안 번짐).
    #   전체 timing-function 은 linear(또는 생략) 로 두어 keyframe 내부 값이
    #   우선하게 한다. steps(N) 전체 타이밍은 keyframe 이 비균등(사다리 구간
    #   촘촘)이면 step 경계와 어긋나 보간이 섞이므로 쓰지 않는다.
    STEP1 = "animation-timing-function:steps(1,start);"
    seg = 100.0 / nweeks

    # X: 53열을 한 칸(15px)씩. 캐릭터가 칸 중앙(칸 왼쪽 모서리 + CELL/2)
    # 에 서야 두 칸에 반씩 걸치지 않는다. 사다리(cx=x+CELL/2)와 같은 x.
    kx = ["@keyframes hx{"]
    for i in range(nweeks):
        x = PAD_X + i * STRIDE + CELL // 2
        kx.append(f"{i * seg:.4f}%{{{STEP1}transform:translateX({x}px)}}")
    kx.append("}")

    # Y: 각 열의 고도(0/-15/-30/-45/-60). 올라갈 때(다음 열이 더 높음)는
    # 1px 씩 기어오르는 중간 keyframe 을 끼워 사다리 모션. 한 단계=STRIDE
    # 이므로 한 단계 올라가는 데 STRIDE 개의 중간 프레임. 내려갈 땐 뛰어
    # 내리므로 중간 프레임 없이 착지만(빠른 하강).
    ky = ["@keyframes hy{"]
    cur_y = 0
    for i in range(nweeks):
        lv = col_level[i]
        tgt_y = -(lv * STRIDE)
        if i == 0:
            ky.append(f"0%{{{STEP1}transform:translateY({tgt_y}px)}}")
            cur_y = tgt_y
        else:
            dy = tgt_y - cur_y
            if dy < 0:
                # 올라간다(더 높은 칸) → 사다리. 1px 씩 기어오르는 중간 프레임.
                steps_up = -dy
                for k in range(1, steps_up + 1):
                    yp = cur_y - k
                    pp = (i - 1 + k / (steps_up + 1)) * seg
                    ky.append(f"{pp:.4f}%{{{STEP1}transform:translateY({yp}px)}}")
                ky.append(f"{i * seg:.4f}%{{{STEP1}transform:translateY({tgt_y}px)}}")
            else:
                # 내려간다(같거나 더 낮은 칸) → 뛰어내림, 중간 없이 착지.
                ky.append(f"{i * seg:.4f}%{{{STEP1}transform:translateY({tgt_y}px)}}")
            cur_y = tgt_y
    ky.append("}")
    css += kx + ky

    # ── 다리(본체 프레임 교대) 동기화 ─────────────────────────
    # 스텝 시간 = TOUR / nweeks. 한 스텝 동안 다리 2프레임(A/B)이 한 번씩
    # 교대하려면 hop 주기 = 스텝 시간. 리드미꾸미기 지적: 0.9s 고정 hop 과
    # 0.248s/스텝이 어긋났다 → 스텝 시간의 정수배로 맞춘다.
    step_time = TOUR / nweeks
    hop_dur = step_time   # 한 스텝당 한 hop 주기(2프레임)
    css.append("@keyframes hop{0%,49%{opacity:1}50%,99%{opacity:0}}")
    css.append("@keyframes hop2{0%,49%{opacity:0}50%,99%{opacity:1}}")

    css.append(f"  .hero-x{{animation:hx {TOUR}s linear infinite}}")
    css.append(f"  .hero-y{{animation:hy {TOUR}s linear infinite}}")
    css.append(f"  .hero-a{{animation:hop {hop_dur:.4f}s steps(2) infinite}}")
    css.append(f"  .hero-b{{animation:hop2 {hop_dur:.4f}s steps(2) infinite}}")
    # 빛이 훑는 효과 (원본 유지)
    css.append(f"  .sweep{{animation:sw {7.0}s linear infinite}}")
    css.append(f"  @keyframes sw{{from{{transform:translateX({-W*0.35:.0f}px)}}"
               f"to{{transform:translateX({W}px)}}}}")
    css.append("  @media (prefers-reduced-motion:reduce){"
               ".hero-x,.hero-y,.hero-a,.hero-b,.sweep{animation:none}"
               ".sweep{opacity:0}}")

    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" '
         f'height="{H}" role="img" aria-label="contributions">',
         "<style>\n" + "\n".join(css) + "\n</style>"]

    # 월 이름
    seen = set()
    for wi, w in enumerate(weeks):
        m = int(w["contributionDays"][0]["date"][5:7])
        if m not in seen and wi < len(weeks) - 1:
            seen.add(m)
            s.append(T.text(MONTHS[m - 1], PAD_X + wi * STRIDE, PAD_TOP - 9,
                            9, cls="lbl", weight="regular"))

    # 잔디 격자
    for wi, w in enumerate(weeks):
        x = PAD_X + wi * STRIDE
        for d in w["contributionDays"]:
            y = PAD_TOP + d["weekday"] * STRIDE
            lv = level(d["contributionCount"], steps)
            s.append(f'<rect class="l{lv}" x="{x}" y="{y}" width="{CELL}" '
                     f'height="{CELL}" rx="2"/>')

    total = cal["totalContributions"]
    s.append(T.text(f"{total} contributions this year", PAD_X, H - 6, 10,
                    cls="lbl", weight="regular"))

    # 빛 훑기
    s.append(f'<rect class="sweep" x="0" y="0" width="{int(W*0.35)}" height="{H}" '
             f'fill="url(#sw)" opacity=".5"/>')
    s.append('<defs><linearGradient id="sw" x1="0" y1="0" x2="1" y2="0">'
             '<stop offset="0" stop-color="#fff" stop-opacity="0"/>'
             '<stop offset=".5" stop-color="#fff" stop-opacity=".55"/>'
             '<stop offset="1" stop-color="#fff" stop-opacity="0"/>'
             "</linearGradient></defs>")

    # ── 사다리 도트 ──────────────────────────────────────────
    # 단계≥2 칸(한 단계=15px 보다 높이 솟은 곳)에 사다리를 그린다.
    # 캐릭터가 그 위를 기어오를 때 사다리가 보임. 세로 레일 2줄 + 가로 발판.
    # 사다리는 칸의 세로 폭(단계×15)만큼 위로 뻗는다.
    # 바닥 기준선: 맨 아래 칸은 y=116~128. 발바닥(y=0)이 칸 아래변(128)
    # 에 닿아야 하는데 fill 이 정수 경계에서 반 픽셀 아래로 렌더링돼 129 까지
    # 삐져나가 보인다(리드미꾸미기 4배 확대). base_y 를 1 줄여 발이 칸 안에.
    base_y = PAD_TOP + (DAYS - 1) * STRIDE + CELL - 1  # 127
    for wi, w in enumerate(weeks):
        lv = col_level[wi]
        if lv >= 2:
            x = PAD_X + wi * STRIDE
            h = lv * STRIDE  # 사다리 높이
            # 캐릭터가 서는 자리 = 칸 중앙(x + CELL/2 = x+6). 사다리도 그 위에.
            # 레일 2줄을 중앙 기준 ±3. stroke 로 그려야 보인다(폭 0 경로는
            # fill 이 안 칠해진다 — 리드미꾸미기 진단).
            cx = x + CELL // 2
            top_y = base_y - h
            rails = [f"M{cx-3} {top_y}v{h}", f"M{cx+3} {top_y}v{h}"]
            # 가로 발판: 4px 간격
            rungs = []
            ry = base_y - 4
            while ry > top_y:
                rungs.append(f"M{cx-3} {ry}h6")
                ry -= 4
            s.append(f'<g class="ladder" shape-rendering="crispEdges">'
                     f'<path d="{" ".join(rails)}"/>'
                     f'<path d="{" ".join(rungs)}"/></g>')

    # ── 캐릭터 ────────────────────────────────────────────────
    # 발(맨 아래 행)이 기준선(base_y)에 오도록. hero-y 의 translateY 가
    # 단계만큼 위로 끌어올린다(translateY=0 → 바닥에 서 있음).
    # 캐릭터 path 는 x=0 이 가운데(칸 중앙). hero-x 가 열 x 를 더함.
    (ba, ea), (bb, eb) = hero_paths()
    s.append('<g class="hero-x">')
    s.append('<g class="hero-y">')
    s.append(f'<g transform="translate(0,{base_y})">')
    # frame A / B 겹쳐놓고 깜빡임 — 본체 + 눈 각각
    s.append(f'<path class="hero hero-a" d="{ba}"/>')
    s.append(f'<path class="hero-eye hero-a" d="{ea}"/>')
    s.append(f'<path class="hero hero-b" d="{bb}"/>')
    s.append(f'<path class="hero-eye hero-b" d="{eb}"/>')
    s.append('</g></g></g>')

    s.append("</svg>")
    return "\n".join(s), W, H, steps, col_level


if __name__ == "__main__":
    cal = fetch()
    svg, W, H, steps, col_level = build(cal)
    OUT.write_text(svg)
    print(f"  {OUT.relative_to(ROOT)}  {W}x{H}  {OUT.stat().st_size//1024}KB")
    print(f"  단계 경계: 1~{steps[0]} / ~{steps[1]} / ~{steps[2]} / 그 이상")
    print(f"  열 단계(앞 10): {col_level[:10]}")
