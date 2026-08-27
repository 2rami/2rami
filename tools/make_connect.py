#!/usr/bin/env python3
"""연락처 배지를 도트로 그린다. 링크를 걸어야 해서 한 장에 하나씩 낸다.

전에는 shields.io 였다. 검은·보라 사각형이 하늘색 페이지 끝에 박혀 있어서
말투가 안 맞았고, 남의 서비스가 죽으면 깨진 그림이 남았다.

배경을 브랜드 색으로 칠하지 않고 카드와 같은 옅은 하늘색으로 둔다 — 여덟
칸짜리 스택 줄과 여섯 장 카드가 이미 그 색이라, 배지만 브랜드 색으로 칠하면
페이지 끝에서 다시 튄다. 브랜드 색은 로고에만 남긴다.

로고 안의 '구멍'(디스코드 눈, 봉투 M, 고양이 눈)은 색을 안 준다. 명암 모드에
따라 칩 배경색이 바뀌므로 그 색을 그대로 따라가야 뚫린 것처럼 보인다.
"""
import pathlib
import sys

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
import textpath as T
import dotlogo as L
from make_stack import dots

OUT = HERE.parent / "assets"

# 로고를 칩 높이의 3/4 까지 키우면 글자보다 두 배가 되어, 배지가 아니라 아이콘
# 옆에 캡션이 붙은 꼴로 읽힌다(2026-08-27 지적: "디코 지메일 아이콘도 크기 커서
# 안맞고"). 로고:글자를 1.7 배쯤으로 낮춘다.
DOT = 1.5
ICON = L.N * DOT            # 24
H = 38
FS = 14
MID = 11

# 셋을 한 줄에 세울 때 폭이 제각각이면 오른쪽 끝이 들쭉날쭉해진다. 리드미 한 줄
# 폭 846 을 셋으로 나눠 고정한다 — 마크다운이 그림 사이에 4px 를 넣으므로
# 279*3 + 4*2 = 845 로 한 줄에 앉는다. 내용은 칩 안에서 가운데로 모은다.
BW = 279

STYLE = """
  .chip{fill:#f4fafe;stroke:#bcdcef}
  .hole{fill:#f4fafe} .mono{fill:#2b4257} .nm{fill:#2b4257}
  @media (prefers-color-scheme: dark){
    .chip{fill:#0f1b26;stroke:#2b4257}
    .hole{fill:#0f1b26} .mono{fill:#cfe6f5} .nm{fill:#cfe6f5}
  }
"""


def badge(slug, label, fn):
    layers = [(c, cells) for c, cells in fn()]
    # 로고마다 격자를 채운 범위가 다르다(고양이는 귀까지 y1, 봉투는 y3). 격자
    # 왼쪽 위에 맞춰 얹으면 배지마다 여백과 로고-글자 간격이 제각각이 된다.
    # 그래서 실제로 찍힌 칸의 경계를 재서 그만큼 당겨 붙인다.
    xs = [x for _, cells in layers for x, _ in cells]
    ys = [y for _, cells in layers for _, y in cells]
    x0, x1, y0, y1 = min(xs), max(xs) + 1, min(ys), max(ys) + 1
    lw = (x1 - x0) * DOT
    tw = T.measure(label, FS, "bold")
    inner = lw + MID + tw
    ox = (BW - inner) / 2 - x0 * DOT
    oy = (H - (y1 - y0) * DOT) / 2 - y0 * DOT
    tx = (BW - inner) / 2 + lw + MID
    body = []
    for color, cells in layers:
        cls = {"MONO": "mono", None: "hole"}.get(color)
        chunk = dots([(color if cls is None else "#000", cells)], ox, oy, DOT)
        body.append(chunk.replace('fill="#000"', f'class="{cls}"') if cls else chunk)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {BW} {H}" '
            f'width="{BW}" height="{H}" role="img" aria-label="{label}">'
            f'<style>{STYLE}</style>'
            f'<rect class="chip" x=".5" y=".5" width="{BW - 1}" height="{H - 1}" '
            f'rx="8" stroke-width="1"/>'
            + "".join(body)
            + T.text(label, tx, H / 2 + FS * .36, FS, weight="bold", cls="nm")
            + "</svg>"), BW


if __name__ == "__main__":
    for slug, label, fn, url in L.CONTACT:
        svg, w = badge(slug, label, fn)
        (OUT / f"connect-{slug}.svg").write_text(svg)
        print(f"  connect-{slug}.svg  {w}x{H}  {label}")
