#!/usr/bin/env python3
"""히어로 자리에 걸 도트 터미널 애니메이션을 그린다.

프레임 전환은 steps(1) 로 끊는다. ease 를 쓰면 도트가 흐릿하게 섞여
픽셀 아트 느낌이 죽는다.

애니메이션 전체 길이는 CYCLE 초. 줄이 하나씩 나타나고, 마지막에 커서가
깜빡이다가 처음으로 돌아간다.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import textpath as T

ROOT = pathlib.Path(__file__).parent.parent
OUT = ROOT / "assets" / "hero.svg"

W, H = 240, 190
BAR = 22           # 제목줄 높이
CYCLE = 9.0        # 한 바퀴(초)

LINES = [
    ("$ ", "whoami", "cmd"),
    ("> ", "designer who codes", "out"),
    ("$ ", "ls ~/projects", "cmd"),
    ("> ", "terminal  bots", "out"),
    ("> ", "games  agents", "out"),
]

# 팔레트는 히어로 그림에서 뽑은 값 — 카드(make_cards)와 같은 값을 쓴다.
STYLE = f"""
  .win{{fill:#f4fafe;stroke:#bcdcef}}
  .bar{{fill:#e3f1fb}}
  .cmd{{fill:#2b4257}} .out{{fill:#5d7f95}} .tit{{fill:#8badc4}}
  .cur{{fill:#1479c9}} .pr{{fill:#1479c9}}
  @media (prefers-color-scheme: dark){{
    .win{{fill:#0f1b26;stroke:#2b4257}}
    .bar{{fill:#16283a}}
    .cmd{{fill:#cfe6f5}} .out{{fill:#8badc4}} .tit{{fill:#5d7f95}}
    .cur{{fill:#58b6f8}} .pr{{fill:#58b6f8}}
  }}
  .blink{{animation:bl 1s steps(1) infinite}}
  @keyframes bl{{0%,50%{{opacity:1}}50.01%,100%{{opacity:0}}}}
  .scan{{animation:sc {CYCLE}s linear infinite}}
  @keyframes sc{{from{{transform:translateY(0)}}to{{transform:translateY({H}px)}}}}
"""


def line_keyframes():
    """줄 i 는 자기 차례(%)에 나타나 사이클 끝까지 남는다.

    steps() 로는 이 동작이 안 나온다 — 구간 내내 시작값이라 줄이 뜨지 않는다.
    퍼센트를 직접 끊어 0 에서 1 로 점프시킨다.
    """
    out = []
    n = len(LINES)
    for i in range(n):
        at = i * (100.0 / n)
        if at == 0:
            out.append(f".l{i}{{opacity:1}}")
            continue
        out.append(
            f".l{i}{{opacity:0;animation:k{i} {CYCLE}s infinite}}"
            f"@keyframes k{i}{{0%,{at-0.01:.2f}%{{opacity:0}}"
            f"{at:.2f}%,100%{{opacity:1}}}}"
        )
    return "\n  ".join(out)


def build():
    s = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" '
        f'height="{H}" role="img" aria-label="terminal">',
        f"<style>{STYLE}\n  {line_keyframes()}</style>",
        f'<rect class="win" x=".5" y=".5" width="{W-1}" height="{H-1}" rx="7" stroke-width="1"/>',
        f'<path class="bar" d="M.5 7.5a7 7 0 017-7h{W-15}a7 7 0 017 7v{BAR-7}H.5z"/>',
        f'<line x1="0" y1="{BAR}" x2="{W}" y2="{BAR}" stroke="currentColor" '
        f'stroke-opacity=".12" stroke-width="1"/>',
    ]
    # 신호등
    for i, c in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
        s.append(f'<rect x="{11+i*13}" y="{BAR//2-3}" width="6" height="6" rx="1" fill="{c}"/>')
    s.append(T.text("2rami", 62, BAR // 2 + 4, 9, cls="tit", weight="regular"))

    y = BAR + 22
    for i, (prompt, body, cls) in enumerate(LINES):
        g = [f'<g class="l{i}">']
        g.append(T.text(prompt, 12, y, 11, cls="pr", weight="bold"))
        g.append(T.text(body, 12 + T.measure(prompt, 11, "bold"), y, 11, cls=cls,
                        weight="bold" if cls == "cmd" else "regular"))
        g.append("</g>")
        s.append("".join(g))
        y += 21

    # 커서 — 마지막 줄 아래에서 계속 깜빡인다
    s.append(f'<rect class="cur blink" x="12" y="{y-9}" width="7" height="11"/>')
    # 스캔선 — CRT 흉내
    s.append(f'<rect class="scan" x="0" y="{-H}" width="{W}" height="{H}" fill="url(#g)" opacity=".05"/>')
    s.append('<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">'
             '<stop offset="0" stop-color="transparent"/>'
             '<stop offset=".9" stop-color="#58b6f8"/>'
             '<stop offset="1" stop-color="transparent"/></linearGradient></defs>')
    s.append("</svg>")
    return "\n".join(s)


if __name__ == "__main__":
    OUT.write_text(build())
    print(f"  {OUT.relative_to(ROOT)}  {OUT.stat().st_size}B  {W}x{H}  {CYCLE}초 순환")
