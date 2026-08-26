#!/usr/bin/env python3
"""카드를 든 캐릭터 그림을 카운터용 스프라이트로 굽는다.

전에는 카드를 렌더러가 벡터로 그리고 양옆에 살색 네모를 붙여 손인 척했다.
포즈가 고정된 그림에 카드를 얹으려니 그 수밖에 없었는데, 이제는 캐릭터가
**실제로 흰 카드를 쥔** 그림을 뽑아 두었으므로 그 그림의 카드 자리를 찾아
숫자만 찍으면 된다.

굽는 순서는 넷이다.

1. 매젠타 배경 지우기. 그냥 지우고 줄이면 가장자리가 보라로 물든다 — 투명
   자리의 매젠타가 칸 평균에 섞이기 때문이다. 지우기 전에 배경을 제일 가까운
   캐릭터 색으로 메워 둔다.
   여기에 더 성가신 것이 하나 있다. 머리카락 사이로 배경이 비친 자리는 매젠타가
   반쯤 섞인 보라가 되는데, 그 정도면 문턱을 통과해 **캐릭터 색으로 남는다.**
   문턱을 올려 잡으면 진짜 분홍 리본까지 배경으로 날아간다. 둘은 색상으로
   갈린다 — 물든 것은 매젠타를 탄 것이라 r 과 b 가 같이 올라가고, 진짜 분홍은
   r 이 b 보다 뚜렷이 높다.
2. 150 로 줄이기. AI 가 그린 '도트풍'은 격자가 10.4px 처럼 정수가 아니라
   NEAREST 로 줄이면 한 칸이 반씩 걸쳐 선이 끊긴다. 칸 평균(BOX)으로 줄인 뒤
   팔레트를 줄여 평평한 도트로 되돌린다. 1536/10.4 이 148 이라 150 이
   격자에 맞는 높이이고, 원본 moe-counter 도 마침 150 이다.
3. 카드 찾기. 카드는 제일 큰 '거의 흰' 덩어리인데 옷이 흰 캐릭터가 있어
   밝기만으로는 못 가른다. 카드는 속이 꽉 찬 직사각형이라 덩어리 넓이가
   외접사각형을 거의 다 채운다(채움률). 옷은 주름과 팔에 잘려 낮다.
4. 프레임 겹치기. 프레임마다 몸이 몇 px 어긋나는데 **카드가 흔들리면 그 위의
   숫자가 같이 흔들린다.** 몸이 아니라 카드를 기준으로 맞추고, 남는 한두 px 는
   첫 프레임의 카드를 그대로 얹어 지운다.

프레임은 가로 띠 한 장에 이어 붙인다. 낱장으로 나누면 팔레트가 프레임마다
달라져 색이 깜빡이고 base64 머리도 장수만큼 붙는다.
"""
import base64
import io
import json
import pathlib

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = pathlib.Path(__file__).parent.parent
GEN = ROOT / "assets" / "gen"
OUT = ROOT / "counter" / "sprites.json"

H = 150            # 도트 격자에 맞는 높이 (원본 테마와 같다)
COLORS = 44        # 24·28 은 눈동자와 옷 무늬가 뭉갠다
CHROMA = np.array([255, 0, 255])
K = np.ones((3, 3))
HOLE = 900        # 이보다 작은 구멍만 메운다 (도트 3칸쯤)

# 자릿수 -> 캐릭터. 일곱 명이 열 칸을 채우느라 셋이 두 번 서는데, 두 번째는
# 표정을 달리 뽑아 같은 그림이 나란히 서지 않게 했다.
SLOTS = [
    ("nacho", "나쵸"), ("norma", "노르마"), ("sparkle", "스파키"),
    ("kei", "케이"), ("aria", "아리아"), ("nangongyu", "난궁위"),
    ("sunna", "순나"), ("nacho", "나쵸"), ("kei", "케이"), ("aria", "아리아"),
]


def key(path, tol=110):
    im = Image.open(path).convert("RGB")
    a = np.array(im).astype(int)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    fg = np.abs(a - CHROMA).sum(axis=2) >= tol
    fg = ndimage.binary_opening(fg, K)                     # 배경에 튄 점 제거
    fg = ndimage.binary_closing(fg, K)                     # 캐릭터 안의 잔구멍 메우기

    # 배경색에 물든 픽셀. 진짜 분홍(r>b)과 가르려고 색상으로 잰다.
    tint = (((r + b) / 2 - g) >= 50) & (np.abs(r - b) <= 40) & (r >= 100)

    # 머리카락 사이로 배경이 비친 작은 구멍은 메운다 — 150px 로 줄이면 한 점이라
    # 뚫려 있어 봐야 하늘색이 비칠 뿐이다. 겨드랑이 같은 큰 틈은 그대로 둔다.
    hole = ndimage.binary_fill_holes(fg) & ~fg
    lab, n = ndimage.label(hole)
    if n:
        sz = np.array(ndimage.sum(hole, lab, range(1, n + 1)))
        fg = fg | np.isin(lab, 1 + np.where(sz <= HOLE)[0])

    # 색은 물들지 않은 속살에서만 가져온다 (가장자리 한 줄도 같이 깎인다)
    clean = ndimage.binary_erosion(fg & ~tint, K)
    if not clean.any():
        clean = fg
    _, (iy, ix) = ndimage.distance_transform_edt(~clean, return_indices=True)
    rgb = np.array(im)[iy, ix]
    return Image.fromarray(
        np.dstack([rgb, np.where(fg, 255, 0).astype(np.uint8)]), "RGBA")


def trim(im):
    return im.crop(im.getbbox())


def shrink(im, h=H, colors=COLORS):
    r = h / im.height
    w = max(1, round(im.width * r))
    if w % 2:
        w += 1                                             # 짝수 폭 — 가운데 정렬이 반픽셀로 안 어긋나게
    s = np.array(im.resize((w, h), Image.BOX))
    alpha = np.where(s[..., 3] > 110, 255, 0).astype(np.uint8)
    rgb = Image.fromarray(s[..., :3], "RGB").quantize(
        colors=colors, method=Image.FASTOCTREE, dither=Image.NONE).convert("RGB")
    return trim(Image.fromarray(np.dstack([np.array(rgb), alpha]), "RGBA"))


def bake(path):
    return shrink(trim(key(path)))


def card_of(im, thr=232, fill=0.80):
    a = np.array(im)
    m = (a[..., 3] > 128) & (a[..., :3] > thr).all(axis=2)
    lab, n = ndimage.label(m)
    best = None
    for i in range(1, n + 1):
        ys, xs = np.where(lab == i)
        h, w = int(np.ptp(ys)) + 1, int(np.ptp(xs)) + 1
        if w < 12 or h < 8 or w < h:                       # 카드는 세로보다 가로가 길다
            continue
        if len(ys) / (w * h) < fill:
            continue
        if best is None or w * h > best[4]:
            best = (int(xs.min()), int(ys.min()), int(w), int(h), int(w * h))
    return best[:4] if best else None


def align(frames, pad=6):
    boxes = [card_of(f) for f in frames]
    bad = [i for i, b in enumerate(boxes) if b is None]
    if bad:
        raise SystemExit(f"카드를 못 찾은 프레임: {bad}")
    W = max(f.width for f in frames) + pad * 2
    Ht = max(f.height for f in frames) + pad * 2
    tx, ty = boxes[0][0] + pad, boxes[0][1] + pad           # 첫 프레임의 카드 자리로 모은다
    out = []
    for f, b in zip(frames, boxes):
        c = Image.new("RGBA", (W, Ht), (0, 0, 0, 0))
        c.paste(f, (tx - b[0], ty - b[1]), f)
        out.append(c)
    cw, ch = boxes[0][2], boxes[0][3]
    card = out[0].crop((tx, ty, tx + cw, ty + ch))
    for c in out[1:]:
        c.paste(card, (tx, ty))                            # 남는 한두 px 어긋남을 지운다

    box = None
    for c in out:
        b = c.getbbox()
        box = b if box is None else (min(box[0], b[0]), min(box[1], b[1]),
                                     max(box[2], b[2]), max(box[3], b[3]))
    x0, y0, x1, y1 = box
    if (x1 - x0) % 2:
        x1 += 1
    return [c.crop((x0, y0, x1, y1)) for c in out], (tx - x0, ty - y0, cw, ch)


def strip(ims):
    w, h = ims[0].size
    s = Image.new("RGBA", (w * len(ims), h), (0, 0, 0, 0))
    for i, im in enumerate(ims):
        s.paste(im, (i * w, 0))
    q = s.quantize(colors=COLORS, method=Image.FASTOCTREE, dither=Image.NONE)
    buf = io.BytesIO()
    q.save(buf, "PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


def main():
    slots = []
    for d, (slug, name) in enumerate(SLOTS):
        paths = [GEN / f"card-{d}-{slug}.png",
                 GEN / f"anim-{d}-{slug}-a.png",
                 GEN / f"anim-{d}-{slug}-b.png"]
        frames, card = align([bake(p) for p in paths])
        w, h = frames[0].size
        b64 = strip(frames)
        slots.append({"name": name, "slug": slug, "w": w, "h": h,
                      "n": len(frames), "card": list(card), "png": b64})
        print(f"  {d} {name:<5} {w}x{h} x{len(frames)}  카드 {card}  "
              f"{len(b64)*3//4//1024}KB")

    top = max(s["h"] for s in slots)
    OUT.write_text(json.dumps({"h": top, "slots": slots}, separators=(",", ":")))
    print(f"\n  {OUT.name}  10칸 · 칸높이 {top} · {OUT.stat().st_size//1024}KB")


if __name__ == "__main__":
    main()
