#!/usr/bin/env python3
"""카운터 자릿수 0~9 에 세울 캐릭터를 스프라이트 시트에서 잘라 JSON 한 덩이로 굽는다.

캐릭터는 일곱인데 자릿수는 열이라 셋이 두 번 선다. 같은 그림을 두 번 쓰면 눈에
띄므로 두 번째는 동작을 바꾼다.

크기 104 는 실측으로 정했다. 프레임 256px 안에서 캐릭터 알파 bbox 가 정확히
208px 이고 도트 피치가 2px 이라 도트 격자는 104 칸이다. 즉 0.5 배로 줄일 때만
1도트=1픽셀이 되고, 그 밖의 배율은 도트를 반씩 걸쳐 뭉갠다. 전에 쓰던 96 은
0.4615 배라 어긋나 있었다.

축소는 NEAREST 다. 정확히 절반이라 평균을 낼 것도 없고, BOX/LANCZOS 로 섞으면
선명함만 잃는다.

프레임은 동작 전체를 다 쓴다. 한 동작의 프레임들은 **합집합 bbox** 로 잘라야
한다 — 프레임마다 제 bbox 로 자르면 팔을 든 프레임이 혼자 커져 캐릭터가
들썩인다.

가로 띠 한 장에 프레임을 이어 붙여 굽는다. 낱장으로 나누면 팔레트가 프레임마다
달라져 색이 깜빡이고, base64 머리도 장수만큼 붙는다.

동작마다 '부유' 세기를 재서 함께 굽는다. 어떤 동작은 프레임이 다 다른데도
멈춰 보인다 — 긴 머리카락만 흔들리고 팔다리는 그대로일 때가 그렇다. 픽셀
변화율로 재면 그런 것도 높게 나와 눈과 어긋나므로, **알파 실루엣**이 켜졌다
꺼진 양과 프레임별 가로폭 변동으로 잰다. 팔을 뻗어야 둘 다 커진다.
모자란 칸은 렌더러가 위아래로 1~2px 띄워 살린다.

원본 시트 없이 sprites.json 만 있을 때는 `--rebob` 으로 부유만 다시 잰다.
구운 띠에서 프레임을 도로 떼어내 같은 잣대로 재므로 결과가 같다.
"""
import base64
import io
import json
import pathlib
import sys

from PIL import Image

SRC = pathlib.Path(
    "/private/tmp/claude-501/-Users-kasa-Desktop-momewomo/"
    "3cbfe71f-e562-4a61-a3f7-e65b0aaf1a3d/scratchpad/theme-counter"
)
OUT = pathlib.Path(__file__).parent.parent / "counter" / "sprites.json"

SCALE = 0.5        # 도트 격자에 맞는 유일한 배율 (256프레임의 피치가 2px)
COLORS = 32

# 자릿수 -> (캐릭터, 동작). 이웃한 칸이 같은 동작을 쓰지 않게 섞었다.
SLOTS = [
    ("nacho", "yawn"),          # 고양이 기지개
    ("norma", "salute"),        # 헬멧에 제복 — 경례
    ("sparkle", "taunt"),      # 광대 차림 트릭스터 — 약 올리기
    ("kei", "think"),           # 게임개발부 연구원 — 골똘히
    ("aria", "dance"),          # AoD 보컬 — 아이돌 춤
    ("nangongyu", "point"),     # AoD 리더 — 센터가 객석을 가리킨다
    ("sunna", "clap"),          # AoD 작곡 — 박수로 박자
    ("nacho", "dance"),         # 버튜버 방송 춤
    ("kei", "read"),            # 문서 읽기
    ("aria", "victory"),        # 무대 피날레
]

NAMES = {
    "nacho": "나쵸", "norma": "노르마", "sparkle": "스파키", "kei": "케이",
    "aria": "아리아", "nangongyu": "난궁위", "sunna": "순나",
}


def sheet_with(slug, pose):
    """그 동작이 들어 있는 시트를 찾는다.

    동작을 추가로 구울 때마다 폴더가 하나씩 는다(out, sig, sig2...). 한 폴더에
    몰아 다시 구우면 이미 잘 나온 동작까지 새로 뽑혀 그림이 바뀌므로, 폴더를
    늘리고 여기서 찾아 쓴다.
    """
    for d in sorted((SRC / slug).glob("*")):
        j = d / "sprite-sheet.json"
        if not j.exists():
            continue
        meta = json.load(open(j))
        fr = [f for f in meta["frames"] if f["filename"].rsplit(" ", 1)[0] == pose]
        if fr:
            return d, fr
    raise SystemExit(f"{slug}: {pose} 동작이 없다")


def frames_of(slug, pose):
    """한 동작의 프레임을 순서대로. 합집합 bbox 로 잘라 크기를 맞춘다."""
    d, fr = sheet_with(slug, pose)
    sheet = Image.open(d / "sprite-sheet.png").convert("RGBA")
    rects = [f["frame"] for f in fr]
    dur = fr[0]["duration"]
    ims = [sheet.crop((r["x"], r["y"], r["x"] + r["w"], r["y"] + r["h"]))
           for r in rects]

    box = None
    for im in ims:
        b = im.getbbox()
        box = b if box is None else (min(box[0], b[0]), min(box[1], b[1]),
                                     max(box[2], b[2]), max(box[3], b[3]))
    # 자른 폭을 짝수로 — 0.5 배에서 반 픽셀이 생기면 도트가 어긋난다
    x0, y0, x1, y1 = box
    if (x1 - x0) % 2:
        x1 += 1
    if (y1 - y0) % 2:
        y1 += 1
    w, h = int((x1 - x0) * SCALE), int((y1 - y0) * SCALE)
    return [im.crop((x0, y0, x1, y1)).resize((w, h), Image.NEAREST)
            for im in ims], w, h, dur


def bob_of(ims):
    """부유 세기 0~2. 실루엣이 안 변하는 동작일수록 크게 띄운다.

    변화율을 색으로 재면 안 된다 — 머리카락만 나부껴도 30%가 넘게 나와서
    실제로는 미동도 없는 동작이 '충분'으로 잡힌다(케이 read 가 그랬다).
    알파만 보면 팔다리가 움직인 만큼만 잡힌다.
    """
    import numpy as np

    a = [np.array(im.getchannel("A")) > 32 for im in ims]
    n = len(a)
    tot = a[0].size
    sil = sum(np.logical_xor(a[i], a[(i + 1) % n]).sum() for i in range(n)) / n / tot * 100
    ws = []
    for f in a:
        cols = np.where(f.any(axis=0))[0]
        ws.append(int(cols[-1] - cols[0] + 1) if len(cols) else 0)
    span = max(ws) - min(ws)

    if sil < 4 and span < 4:
        return 2
    if sil < 7:
        return 1
    return 0


def strip(ims, w, h):
    """프레임을 가로로 이어 붙여 한 장으로. 팔레트를 한 번만 잡게 하려는 것."""
    s = Image.new("RGBA", (w * len(ims), h), (0, 0, 0, 0))
    for i, im in enumerate(ims):
        s.paste(im, (i * w, 0))
    q = s.quantize(colors=COLORS, method=Image.FASTOCTREE, dither=Image.NONE)
    buf = io.BytesIO()
    q.save(buf, "PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


def main():
    slots, total = [], 0
    for d, (slug, pose) in enumerate(SLOTS):
        ims, w, h, dur = frames_of(slug, pose)
        b64 = strip(ims, w, h)
        bob = bob_of(ims)
        total += len(b64)
        slots.append({"name": NAMES[slug], "slug": slug, "pose": pose,
                      "w": w, "h": h, "n": len(ims), "dur": dur,
                      "bob": bob, "png": b64})
        print(f"  {d} {NAMES[slug]:<5} {pose:<10} {w}x{h} x{len(ims)}프레임 "
              f"{dur}ms  {len(b64)*3//4//1024}KB  부유{bob}")

    H = max(s["h"] for s in slots)
    OUT.write_text(json.dumps({"h": H, "slots": slots}, separators=(",", ":")))
    print(f"\n  {OUT.name}  10칸 · 칸높이 {H} · {OUT.stat().st_size//1024}KB")


def rebob():
    """구워 둔 sprites.json 의 부유만 다시 잰다 (원본 시트가 없을 때)."""
    d = json.loads(OUT.read_text())
    for i, s in enumerate(d["slots"]):
        strip_im = Image.open(io.BytesIO(base64.b64decode(s["png"]))).convert("RGBA")
        w, h, n = s["w"], s["h"], s["n"]
        ims = [strip_im.crop((k * w, 0, (k + 1) * w, h)) for k in range(n)]
        s["bob"] = bob_of(ims)
        print(f"  {i} {s['name']:<5} {s['pose']:<10} 부유{s['bob']}")
    OUT.write_text(json.dumps(d, separators=(",", ":")))
    print(f"\n  {OUT.name} 갱신 — 부유 준 칸 "
          f"{sum(1 for s in d['slots'] if s['bob'])}개")


if __name__ == "__main__":
    if "--rebob" in sys.argv:
        rebob()
    else:
        main()
