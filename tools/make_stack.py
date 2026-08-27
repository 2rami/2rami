#!/usr/bin/env python3
"""기술 스택 줄과 연락처 배지를 도트로 직접 그린다.

전에는 skillicons.dev 와 shields.io 에서 받아 걸었다. 문제가 둘이었다.
하나는 말투다 — 페이지의 나머지가 전부 직접 찍은 도트인데 저 둘만 매끈한
벡터 로고에 검은 각진 사각형이라 하늘색 바탕에 박힌 것처럼 보였다.
다른 하나는 의존이다. 남의 서비스가 죽으면 리드미에 깨진 그림이 남는다.

로고는 원·사각·도트글자로 16x16 격자에 다시 찍는다(tools/dotlogo.py).
벡터 원을 얹지 않는 이유는 가장자리가 매끈해지면 옆에 놓인 도트 글자와
같은 그림으로 안 읽히기 때문이다 — 계단이 보여야 한다.

폭 기준 846 은 카드와 같다. 프로필 리드미가 실제로 차지하는 폭이고, 축소되면
도트가 픽셀 격자에서 어긋나 뭉개진다. 칸 간격은 여덟 개를 그 폭에 정확히
채우도록 역산한다.
"""
import pathlib
import sys

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
import textpath as T
import dotlogo as L

ROOT = HERE.parent
OUT = ROOT / "assets"

# 로고 옆에 이름을 붙이면 여덟 칸이 921px 이 되어 846 을 넘는다. 원본(skillicons)
# 처럼 로고만 세우고, 대신 도트가 보이도록 격자 한 칸을 3px 로 키운다.
DOT = 3
ICON = L.N * DOT            # 48
PAD = 8
SIDE = ICON + PAD * 2       # 정사각 칸 64
GAP = 8
W = 846                    # 리드미 한 줄 폭

STYLE = """
  .chip{fill:#f4fafe;stroke:#bcdcef}
  @media (prefers-color-scheme: dark){.chip{fill:#0f1b26;stroke:#2b4257}}
"""


def dots(layers, ox, oy, dot=None):
    """도트 집합을 rect 로. 가로로 이어진 칸은 한 사각형으로 묶는다.

    dot 을 안 주면 이 모듈의 칸 크기를 쓴다. 배지처럼 더 작은 칸으로 그리는
    쪽에서 값을 넘긴다 — 예전에는 부르는 쪽이 제 DOT 으로 자리를 재고 여기서는
    스택의 DOT 으로 그려서, 로고가 칩 높이를 4px 넘어 삐져나갔다.
    """
    dot = DOT if dot is None else dot
    out = []
    for color, cells in layers:
        if not cells:
            continue
        run = []
        for y in sorted({c[1] for c in cells}):
            xs = sorted(x for x, yy in cells if yy == y)
            i = 0
            while i < len(xs):
                j = i
                while j + 1 < len(xs) and xs[j + 1] == xs[j] + 1:
                    j += 1
                run.append(f'<rect x="{ox + xs[i] * dot}" y="{oy + y * dot}" '
                           f'width="{(j - i + 1) * dot}" height="{dot}"/>')
                i = j + 1
        out.append(f'<g fill="{color}">{"".join(run)}</g>')
    return "".join(out)


def stack():
    """칸을 리드미 한 줄 폭에 정확히 걸쳐 세운다.

    간격을 상수로 두면 칸 개수가 바뀔 때마다 오른쪽 끝이 잔디·띠와 어긋난다
    (2026-08-27 지적: "끝단이나 그리드좀 맞춰봐"). 그래서 남는 폭을 칸 사이로
    나눠 반올림한다 — 간격이 한 칸씩 들쭉날쭉해지지만 1px 라 안 보이고,
    마지막 칸의 오른쪽 변은 늘 W 에 정확히 선다.
    """
    names = [n for n, _ in L.LOGOS]
    n = len(L.LOGOS)
    w = W
    step = (w - SIDE) / (n - 1)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {SIDE}" '
             f'width="{w}" height="{SIDE}" role="img" '
             f'aria-label="{", ".join(names)}">', f"<style>{STYLE}</style>"]
    for i, (name, fn) in enumerate(L.LOGOS):
        x = round(i * step)
        parts.append(f'<rect class="chip" x="{x + .5}" y=".5" width="{SIDE - 1}" '
                     f'height="{SIDE - 1}" rx="10" stroke-width="1"/>')
        parts.append(dots(fn(), x + PAD, PAD))
    parts.append("</svg>")
    return "".join(parts), w


if __name__ == "__main__":
    svg, w = stack()
    (OUT / "stack.svg").write_text(svg)
    print(f"  stack.svg  {w}x{SIDE} · 칸 {len(L.LOGOS)}개 · {len(svg)//1024}KB")
