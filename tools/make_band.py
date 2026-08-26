#!/usr/bin/env python3
"""생성한 그림을 리드미 띠 크기로 자르고 용량을 줄인다.

리드미에서 실제로 보이는 폭은 846px 이다. 1536px 짜리를 그대로 걸면 보이지도
않는 화소를 매번 받게 된다. 2배(1692px)까지만 두면 고해상도 화면에서도 선명하다.

자르는 세로 위치는 눈대중으로 정하지 않는다 — 어두운 화소(인물·자전거)가 몰린
줄을 찾아 그 줄이 띠 한가운데 오게 맞춘다. 하늘만 남는 사고를 막는다.

원본은 건드리지 않는다. 영상 모델에 넣을 재료로 그대로 남겨야 한다.
"""
import pathlib
import sys

from PIL import Image

ROOT = pathlib.Path(__file__).parent.parent
BAND_W, BAND_H = 1692, 380          # 846x190 의 2배


def subject_row(im, sample=200):
    """어두운 화소가 가장 몰린 세로 위치(0~1)를 돌려준다."""
    g = im.convert("L").resize((sample, sample))
    px = g.load()
    rows = []
    for y in range(sample):
        dark = sum(1 for x in range(sample) if px[x, y] < 110)
        rows.append(dark)
    # 위아래 가장자리는 배경(하늘/땅)이라 가중치를 낮춘다
    best = max(range(sample), key=lambda y: rows[y] * (1 - abs(y / sample - 0.55)))
    return best / sample


def build(src, out, quiet=False):
    im = Image.open(src).convert("RGB")
    scale = BAND_W / im.width
    im = im.resize((BAND_W, round(im.height * scale)), Image.LANCZOS)

    center = subject_row(im)
    top = round(im.height * center - BAND_H / 2)
    top = max(0, min(top, im.height - BAND_H))
    band = im.crop((0, top, BAND_W, top + BAND_H))

    # 도트 그림은 색이 적어 팔레트로 크게 줄어든다. 손실이 보이면 색 수를 올린다.
    best, bestn = None, None
    for n in (64, 128, 256):
        q = band.quantize(colors=n, method=Image.MEDIANCUT, dither=Image.FLOYDSTEINBERG)
        tmp = out.with_suffix(f".{n}.png")
        q.save(tmp, optimize=True)
        size = tmp.stat().st_size
        if not quiet:
            print(f"    {n:>3}색  {size//1024:>4}KB")
        if best is None or size < best:
            best, bestn = size, n
        tmp.unlink()

    q = band.quantize(colors=bestn, method=Image.MEDIANCUT, dither=Image.FLOYDSTEINBERG)
    q.save(out, optimize=True)
    return center, top, bestn, out.stat().st_size


if __name__ == "__main__":
    src = pathlib.Path(sys.argv[1])
    out = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "assets" / "band.png"
    orig = src.stat().st_size
    print(f"  원본 {src.name}  {orig//1024}KB")
    center, top, n, size = build(src, out)
    print(f"\n  피사체 세로 위치 {center:.0%} · 자른 지점 y={top}")
    print(f"  결과 {out.relative_to(ROOT)}  {BAND_W}x{BAND_H}  {n}색  "
          f"{size//1024}KB  (원본의 {size*100//orig}%)")
