#!/usr/bin/env python3
"""도트 스프라이트를 runners.json 으로 굽는다.

원본 러닝 그림을 그냥 줄이던 방식은 버렸다 — 세로 38px 로는 팔다리와 소품이
덩어리로 뭉쳤다(2026-08-27 지적). 지금 재료는 tools/runners-dot/ 의 스프라이트
시트다. 이미 도트로 그려진 그림이라 형태가 남고, 무엇보다 한 캐릭터에 러닝
4프레임이 들어 있어 다리가 실제로 움직인다.

줄일 때는 넓이 평균(BOX)을 쓴다. 칸마다 최빈색 하나를 고르는 쪽도 해 봤는데,
이 그림들은 외곽선이 굵어서 최빈색이 자꾸 검정으로 쏠려 캐릭터가 통째로
어두워졌다. 대신 줄인 뒤 채도와 대비를 올려 중간색을 양끝으로 밀어낸다 —
경계가 또렷해지는 건 그쪽이다.

프레임은 공통 캔버스에 정렬해서 굽는다. 프레임마다 잘린 폭이 다른 채로 바꿔
끼우면 몸이 좌우로 튄다 — 예전에 그 증상을 겪었다. 배율도 프레임 전체에 하나만
쓴다. 프레임마다 세로를 꽉 채우면 웅크린 자세가 선 자세만큼 커져 키가 출렁인다.
세로는 발밑, 가로는 머리 중심에 맞춘다. 달릴 때 다리는 흔들려도 머리는 제자리다.
"""
import json
import pathlib
import sys

import numpy as np
from PIL import Image, ImageEnhance
from scipy import ndimage

SRC = pathlib.Path(__file__).parent / "runners-dot"
OUT = pathlib.Path(__file__).parent / "runners.json"
NAMES = ["norma", "sparkle", "kei", "aria", "nangongyu", "sunna"]
FRAMES = 4
TALL = int(sys.argv[1]) if len(sys.argv) > 1 else 26
COLORS = 16
ALPHA = 128
SAT, CON = 1.35, 1.2               # 축소로 흐려진 중간색을 양끝으로 밀어낸다


def sheet_alpha(a):
    """흰 배경만 지운다. 부츠·치마의 흰색은 테두리에 안 닿으므로 남는다."""
    white = (a > 244).all(axis=2)
    lab, _ = ndimage.label(white)
    edge = set(lab[0]) | set(lab[-1]) | set(lab[:, 0]) | set(lab[:, -1])
    edge.discard(0)
    return (~np.isin(lab, list(edge))).astype(np.uint8) * 255


def cut(name):
    """시트를 프레임 4장으로. 빈 열로 끊고, 머리카락이 옆까지 뻗으면 4등분한다."""
    a = np.array(Image.open(SRC / f"{name}.png").convert("RGB"))
    alpha = sheet_alpha(a)
    cols = alpha.sum(axis=0) > 0
    runs, s = [], None
    for x, v in enumerate(cols):
        if v and s is None:
            s = x
        elif not v and s is not None:
            runs.append((s, x)); s = None
    if s is not None:
        runs.append((s, len(cols)))
    runs = [r for r in runs if r[1] - r[0] > 30]
    if len(runs) != FRAMES:
        xs = np.where(cols)[0]
        x0, x1 = int(xs.min()), int(xs.max()) + 1
        w = (x1 - x0) / FRAMES
        runs = [(int(x0 + i * w), int(x0 + (i + 1) * w)) for i in range(FRAMES)]
    out = []
    for x0, x1 in runs:
        sub = alpha[:, x0:x1].copy()
        lab, n = ndimage.label(sub > 0)
        if n > 1:                      # 등분 자리에 남은 옆 캐릭터 조각을 버린다
            sizes = ndimage.sum(sub > 0, lab, range(1, n + 1))
            sub[lab != int(np.argmax(sizes)) + 1] = 0
        ys = np.where(sub.sum(axis=1) > 0)[0]
        xs2 = np.where(sub.sum(axis=0) > 0)[0]
        y0, y1 = int(ys.min()), int(ys.max()) + 1
        cx0, cx1 = int(xs2.min()), int(xs2.max()) + 1
        out.append(np.dstack([a[y0:y1, x0 + cx0:x0 + cx1], sub[y0:y1, cx0:cx1]]))
    return out


def anchor(mask):
    """머리 x 중심. 상단 30% 만 본다 — 다리는 흔들려도 머리는 제자리다."""
    head = mask[:max(1, int(mask.shape[0] * 0.3))]
    xs = np.where(head.any(axis=0))[0]
    return (int(xs.min()) + int(xs.max())) / 2 if len(xs) else mask.shape[1] / 2


def runs_of(row):
    """행을 [시작, 길이, 색] 묶음으로. 칸마다 rect 를 쓰면 파일이 세 배가 된다."""
    out, x = [], 0
    while x < len(row):
        c = row[x]
        if c < 0:
            x += 1; continue
        n = 1
        while x + n < len(row) and row[x + n] == c:
            n += 1
        out.append([x, n, c]); x += n
    return out


def bake(name):
    frames = cut(name)
    scale = TALL / max(f.shape[0] for f in frames)   # 배율은 하나 — 키가 안 출렁인다
    small = []
    for f in frames:
        th = max(1, round(f.shape[0] * scale))
        tw = max(1, round(f.shape[1] * scale))
        im = np.array(Image.fromarray(f, "RGBA").resize((tw, th), Image.BOX))
        small.append((im, anchor(f[:, :, 3] > ALPHA) * tw / f.shape[1]))
    left = max(round(a) for _, a in small)
    right = max(im.shape[1] - round(a) for im, a in small)
    W = left + right
    canvas = []
    for im, a in small:
        c = np.zeros((TALL, W, 4), np.uint8)
        ox, oy = left - round(a), TALL - im.shape[0]      # 발밑을 바닥에
        c[oy:oy + im.shape[0], ox:ox + im.shape[1]] = im
        canvas.append(c)
    # 색은 프레임 전체에서 한 번에 뽑는다. 프레임마다 따로 뽑으면 색이 깜빡인다
    stack = np.concatenate(canvas, axis=0)
    keep = stack[:, :, 3] > ALPHA
    rgb = Image.fromarray(stack[:, :, :3])
    rgb = ImageEnhance.Contrast(ImageEnhance.Color(rgb).enhance(SAT)).enhance(CON)
    q = rgb.quantize(colors=COLORS, method=Image.MEDIANCUT, dither=Image.NONE)
    pal = np.array(q.getpalette()[:COLORS * 3]).reshape(-1, 3)
    idx = np.array(q)
    used = sorted({int(c) for c in idx[keep]})
    remap = {c: i for i, c in enumerate(used)}
    poses = []
    for f in range(FRAMES):
        y0 = f * TALL
        poses.append([runs_of([remap[int(idx[y0 + y, x])] if keep[y0 + y, x] else -1
                               for x in range(W)]) for y in range(TALL)])
    return {"w": W, "h": TALL,
            "pal": ["#%02x%02x%02x" % tuple(int(v) for v in pal[c]) for c in used],
            "poses": poses}


if __name__ == "__main__":
    data = {}
    for n in NAMES:
        d = data[n] = bake(n)
        print(f"  {n:10s} {d['w']:2d}x{d['h']:2d}  {len(d['pal']):2d}색  "
              f"{sum(len(r) for p in d['poses'] for r in p):4d}런")
    OUT.write_text(json.dumps(data, separators=(",", ":")))
    print(f"  {OUT.name}  {OUT.stat().st_size // 1024}KB")
