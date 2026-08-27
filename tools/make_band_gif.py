#!/usr/bin/env python3
"""리드미 띠를 장르가 바뀌는 GIF 로 굽는다.

같은 자리에 정지 그림 한 장(자전거)만 있었다. 장르를 여럿 보여 달라는 요청이라
띠 한 칸에서 장면을 갈아 끼운다 — 새 줄을 만들지 않으니 레이아웃이 안 늘어난다.

**전환을 페이드가 아니라 쓸어내기로 한 건 용량 때문이다.** GIF 는 앞 프레임과
달라진 사각형만 저장한다. 페이드는 화면 전체가 매 프레임 바뀌어 프레임 수만큼
용량이 붙지만, 세로로 쓸면 바뀌는 건 좁은 세로 띠뿐이라 전환 한 번이 한 장
값도 안 된다. 실측: 페이드로 굽던 것과 같은 장면 수에서 1/4 이하다.

머무는 프레임은 길게(1.8초), 쓸어내는 프레임은 짧게(40ms) 준다 — GIF 는
프레임마다 시간을 따로 줄 수 있어서, 느리게 보여 주면서도 프레임 수는 안 는다.

팔레트는 전 장면을 합쳐 한 벌만 만든다. 장면마다 따로 뽑으면 전환할 때 색이
튄다.
"""
import pathlib
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
from make_band import subject_row

ROOT = HERE.parent
GEN = ROOT / "assets" / "gen"
OUT = ROOT / "assets" / "band.gif"

W, H = 846, 190             # 리드미 한 줄 폭. 프레임이 여럿이라 2배는 안 쓴다
COLORS = 128
HOLD = 1800                 # 한 장면이 머무는 시간(ms)
WIPE_MS = 40
WIPE_N = 14                 # 쓸어내는 단계 수 — 많을수록 부드럽고 조금 무겁다
EDGE = 3                    # 쓸어내는 경계에 긋는 밝은 선 두께
EDGE_RGB = (88, 182, 248)   # 다크모드 이름색과 같은 하늘색

FONT = HERE / "pixelify-bold.ttf"
LFS = 15

# 장르가 서로 안 겹치게 고른다. 띠가 4.5:1 이라 세로로 긴 구도는 안 담긴다.
#
# 셋째 값은 원본 세로에서 띠 가운데가 앉을 자리(0~1)다. 안 주면 make_band 의
# 자동 규칙을 쓰는데, 그건 어두운 화소가 몰린 줄을 찾는 방식이라 하늘이 밝고
# 넓은 그림에서 엉뚱한 데를 짚는다 — 기차 창은 창밖 들판 대신 좌석만, 여름
# 언덕은 언덕 대신 빈 하늘만 잡혔다. 그런 장면만 손으로 박는다.
SCENES = [
    ("b1-riverside-hq", "youth", None),
    ("02-city-night", "cyberpunk", None),
    ("05-platformer", "retro game", None),
    ("06-rainy-window", "rainy night", None),
    ("04-starfield", "space", 0.55),
    ("01-cozy-desk", "cozy", None),
    ("s5-train-window", "travel", 0.36),
    ("s3-summer-hill", "summer", 0.62),
]


def band(path, anchor=None):
    """그림 한 장을 띠 크기로. 자르는 세로 위치는 make_band 와 같은 규칙."""
    im = Image.open(path).convert("RGB")
    im = im.resize((W, round(im.height * W / im.width)), Image.LANCZOS)
    center = subject_row(im) if anchor is None else anchor
    top = round(im.height * center - H / 2)
    top = max(0, min(top, im.height - H))
    return im.crop((0, top, W, top + H))


def label(im, text):
    """왼쪽 아래에 장르 이름. 배경 위에 그냥 얹으면 밝은 하늘에서 안 읽혀서
    어두운 알약을 깔고 그 위에 쓴다."""
    d = ImageDraw.Draw(im, "RGBA")
    f = ImageFont.truetype(str(FONT), LFS)
    x0, y0 = 14, H - 14 - LFS - 8
    w = d.textlength(text, font=f)
    d.rounded_rectangle([x0, y0, x0 + w + 20, y0 + LFS + 12], 6, fill=(9, 20, 30, 190))
    d.text((x0 + 10, y0 + 5), text, font=f, fill=(210, 235, 252, 255))
    return im


def main():
    bands = []
    for name, gen, anchor in SCENES:
        p = GEN / f"{name}.png"
        if not p.exists():
            print(f"  없음: {p.name}")
            continue
        bands.append(label(band(p, anchor), gen))
    n = len(bands)

    # 전 장면을 세로로 이어 붙여 팔레트 한 벌을 뽑는다
    tall = Image.new("RGB", (W, H * n))
    for i, b in enumerate(bands):
        tall.paste(b, (0, H * i))
    pal = tall.quantize(colors=COLORS, method=Image.MEDIANCUT)

    frames, delays = [], []
    for i, b in enumerate(bands):
        frames.append(b)
        delays.append(HOLD)
        nxt = bands[(i + 1) % n]
        for s in range(1, WIPE_N + 1):
            x = round(W * s / WIPE_N)
            f = b.copy()
            f.paste(nxt.crop((0, 0, x, H)), (0, 0))
            if s < WIPE_N:
                ImageDraw.Draw(f).rectangle([x - EDGE, 0, x - 1, H], fill=EDGE_RGB)
            frames.append(f)
            delays.append(WIPE_MS)

    q = [f.quantize(palette=pal, dither=Image.FLOYDSTEINBERG) for f in frames]
    q[0].save(OUT, save_all=True, append_images=q[1:], duration=delays,
              loop=0, optimize=True, disposal=1)
    size = OUT.stat().st_size
    total = sum(delays) / 1000
    print(f"  band.gif  {W}x{H}  장면 {n}개 · 프레임 {len(q)}장 · "
          f"{COLORS}색 · 한 바퀴 {total:.1f}초 · {size//1024}KB")


if __name__ == "__main__":
    main()
