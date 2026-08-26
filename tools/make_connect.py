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

DOT = 2
ICON = L.N * DOT            # 32
H = 44
FS = 15
PADL, MID, PADR = 8, 12, 13

STYLE = """
  .chip{fill:#f4fafe;stroke:#bcdcef}
  .hole{fill:#f4fafe} .mono{fill:#2b4257} .nm{fill:#2b4257}
  @media (prefers-color-scheme: dark){
    .chip{fill:#0f1b26;stroke:#2b4257}
    .hole{fill:#0f1b26} .mono{fill:#cfe6f5} .nm{fill:#cfe6f5}
  }
"""


def badge(slug, label, fn):
    tw = round(T.measure(label, FS, "bold"))
    w = PADL + ICON + MID + tw + PADR
    layers = [(c, cells) for c, cells in fn()]
    body = []
    for color, cells in layers:
        cls = {"MONO": "mono", None: "hole"}.get(color)
        chunk = dots([(color if cls is None else "#000", cells)], PADL, (H - ICON) // 2)
        body.append(chunk.replace('fill="#000"', f'class="{cls}"') if cls else chunk)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {H}" '
            f'width="{w}" height="{H}" role="img" aria-label="{label}">'
            f'<style>{STYLE}</style>'
            f'<rect class="chip" x=".5" y=".5" width="{w - 1}" height="{H - 1}" '
            f'rx="8" stroke-width="1"/>'
            + "".join(body)
            + T.text(label, PADL + ICON + MID, H / 2 + FS * .36, FS,
                     weight="bold", cls="nm")
            + "</svg>"), w


if __name__ == "__main__":
    for slug, label, fn, url in L.CONTACT:
        svg, w = badge(slug, label, fn)
        (OUT / f"connect-{slug}.svg").write_text(svg)
        print(f"  connect-{slug}.svg  {w}x{H}  {label}")
