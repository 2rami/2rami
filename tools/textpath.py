"""도트 폰트(Pixelify Sans) 글자를 SVG path 로 굽는다.

GitHub 은 SVG 안에서 외부 폰트를 못 불러온다. 글자를 도형으로 바꿔 두면
보는 사람 컴퓨터에 폰트가 없어도 의도한 모양 그대로 나온다.
"""
import functools, pathlib
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen

_DIR = pathlib.Path(__file__).parent

@functools.lru_cache(maxsize=4)
def _font(weight):
    f = TTFont(_DIR / f"pixelify-{weight}.ttf")
    return f, f.getGlyphSet(), f.getBestCmap(), f["head"].unitsPerEm

@functools.lru_cache(maxsize=4096)
def _glyph(ch, weight):
    _, gs, cmap, _ = _font(weight)
    name = cmap.get(ord(ch))
    if name is None:
        return "", cmap.get(ord(" ")) and gs[cmap[ord(" ")]].width or 500
    pen = SVGPathPen(gs)
    g = gs[name]
    g.draw(pen)
    return pen.getCommands(), g.width

def measure(s, size, weight="bold", tracking=0):
    _, _, _, upm = _font(weight)
    w = sum(_glyph(c, weight)[1] for c in s)
    return w * size / upm + tracking * max(0, len(s) - 1)

def text(s, x, y, size, fill="currentColor", weight="bold", tracking=0,
         anchor="start", cls=None, opacity=None):
    """한 줄 글자를 <g> 로 돌려준다. y 는 baseline."""
    _, _, _, upm = _font(weight)
    k = size / upm
    total = measure(s, size, weight, tracking)
    if anchor == "middle": x -= total / 2
    elif anchor == "end":  x -= total
    # scale(k,-k) 안에서 그리므로 좌표를 폰트 단위로 누적한다
    parts, cx = [], 0.0
    for c in s:
        d, adv = _glyph(c, weight)
        if d:
            parts.append(f'<path transform="translate({cx:.1f},0)" d="{d}"/>')
        cx += adv + tracking / k
    a = [f'transform="translate({x:.2f},{y:.2f}) scale({k:.5f},{-k:.5f})"']
    if cls: a.append(f'class="{cls}"')
    else:   a.append(f'fill="{fill}"')
    if opacity is not None: a.append(f'opacity="{opacity}"')
    return f'<g {" ".join(a)}>{"".join(parts)}</g>'
