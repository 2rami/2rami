#!/usr/bin/env python3
"""달리는 여섯을 15x21 도트로 그린다.

원본을 줄이는 길은 두 번 버렸다. counter/sprites.json 의 고해상도 픽셀아트를
8칸으로도 10칸으로도 줄여 봤지만 눈·머리·옷이 한 덩어리로 뭉개진다 —
줄이는 방식으로는 안 되고 형태는 손으로 잡아야 한다(2026-08-27 확인).
색만 그 원본에서 뽑아 오므로 인상은 어긋나지 않는다.

격자를 15x21 로 잡은 이유:
- 얼굴이 성립하는 최소치다. 눈 한 짝에 두 칸, 눈 사이 세 칸, 양옆 머리 두 칸씩
  = 가로 열다섯. 이보다 좁으면 눈이 한 칸이 되어 표정이 사라진다.
- 세로는 머리 10 + 몸통 6 + 다리 5. 치비 비율(머리가 절반 가까이)이라야
  작게 줄여도 사람으로 읽힌다.
- 화면에는 DOT=1 로 그려 15x21px 이다. 전(8x12 를 DOT=2 로 그린 16x24px)보다
  작으면서 칸은 4배다 — "도트를 자세히해서 작게" (2026-08-27 지시).

자세가 넷인 것은 도약 때문이다. 서기만 있으면 예비동작 없이 몸이 튄다.
웅크렸다가 뛰고, 공중에서 다리를 접고, 착지에서 한 번 눌린다.
"""
import json
import pathlib

W, H = 15, 21

# 부위 색 — counter/sprites.json 의 고해상도 픽셀아트에서 뽑았다(tools/pal.py 없음,
# 값만 남긴다). h 머리 H 머리그늘 k 머리장식 s 피부 S 피부그늘 e 눈
# b 옷 B 옷그늘 w 옷장식 l 다리 f 신발
PAL = {
    "norma":    dict(h="#e0d8c8", H="#a8a09c", k="#8a8f9c", s="#f0c898", S="#d09868",
                     e="#4a3b32", b="#303048", B="#20203a", w="#f8f8f0",
                     l="#e8e2d8", f="#606068"),
    "sparkle":  dict(h="#f4f0ea", H="#bda9ad", k="#c8a0a8", s="#f6e6e0", S="#cf9fa6",
                     e="#7a3546", b="#d8a6b0", B="#9d6474", w="#f8f4f0",
                     l="#e8d4d4", f="#3a1c24"),
    "kei":      dict(h="#f6f4f8", H="#bab0c2", k="#e8a8c0", s="#faeef4", S="#c9b6c4",
                     e="#484050", b="#b6adbc", B="#7b7286", w="#f8f8f8",
                     l="#3f3a4a", f="#241f2a"),
    "aria":     dict(h="#f8c8c0", H="#d8a0a0", k="#f8f8f0", s="#f8f0ec", S="#e0b4ae",
                     e="#8a4a52", b="#609890", B="#385050", w="#f8f8f0",
                     l="#e8e4e0", f="#586060"),
    "nangongyu":dict(h="#3a3a3a", H="#141414", k="#b8322e", s="#f8e8d8", S="#d8a098",
                     e="#2a2024", b="#282020", B="#101010", w="#c8bcb4",
                     l="#4a4448", f="#101010"),
    "sunna":    dict(h="#e0d8c8", H="#a8a49c", k="#d8a0a0", s="#f8f0e8", S="#c8b8a8",
                     e="#5a4a48", b="#d8a0a0", B="#b07c80", w="#f8f8f0",
                     l="#f0ece4", f="#989890"),
}
ORDER = ["norma", "sparkle", "kei", "aria", "nangongyu", "sunna"]

HEAD = [
    ".....hhhhh.....",
    "...hhhhhhhhh...",
    "..hhhhhhhhhHH..",
    ".hhhhhhhhhhhHH.",
    ".hhsssssssssHH.",
    ".hhseessseesHH.",
    ".hhsssssssssHH.",
    ".hhsSsssssSsHH.",
    "..hsssssssssH..",
    "....sssssss....",
]

# 머리 모양 — 여섯을 가르는 것은 결국 실루엣이다. (x, y, 색) 을 덧찍는다.
# y 는 머리 윗줄 기준이라 자세가 내려가도 같이 따라간다
LOCKS = {
    # 곰귀 후드
    "norma":    [(2, 0, "H"), (3, 0, "h"), (11, 0, "H"), (12, 0, "H"),
                 (2, 1, "h"), (12, 1, "H"), (0, 4, "h"), (14, 4, "H"),
                 (0, 5, "h"), (14, 5, "H"), (0, 6, "h"), (14, 6, "H")],
    # 긴 트윈테일
    "sparkle":  [(0, 3, "h"), (14, 3, "H"), (0, 4, "h"), (14, 4, "H"),
                 (0, 5, "h"), (14, 5, "H"), (0, 6, "h"), (14, 6, "H"),
                 (0, 7, "H"), (14, 7, "H"), (0, 8, "H"), (14, 8, "H"),
                 (1, 9, "H"), (13, 9, "H"), (1, 10, "H"), (13, 10, "H"),
                 (6, 0, "k"), (8, 0, "k")],
    # 긴 생머리 + 분홍 리본
    "kei":      [(0, 4, "h"), (14, 4, "H"), (0, 5, "h"), (14, 5, "H"),
                 (0, 6, "h"), (14, 6, "H"), (0, 7, "H"), (14, 7, "H"),
                 (0, 8, "H"), (14, 8, "H"), (0, 9, "H"), (14, 9, "H"),
                 (1, 10, "H"), (13, 10, "H"), (1, 11, "H"), (13, 11, "H"),
                 (10, 0, "k"), (11, 0, "k"), (11, 1, "k")],
    # 옆으로 뻗친 단발 + 흰 장식
    "aria":     [(0, 3, "h"), (14, 3, "H"), (0, 4, "h"), (14, 4, "H"),
                 (0, 5, "h"), (14, 5, "H"), (1, 6, "H"), (13, 6, "H"),
                 (3, 0, "k"), (11, 0, "k")],
    # 짧은 단발 + 붉은 꽃
    "nangongyu":[(1, 4, "h"), (13, 4, "H"), (1, 5, "h"), (13, 5, "H"),
                 (1, 6, "H"), (13, 6, "H"), (2, 1, "k"), (3, 1, "k"),
                 (2, 2, "k")],
    # 오른쪽 사이드테일
    "sunna":    [(13, 2, "h"), (14, 3, "h"), (14, 4, "H"), (14, 5, "H"),
                 (13, 6, "H"), (14, 6, "H"), (13, 7, "H"), (5, 0, "k")],
}

# 자세마다 몸통·다리가 다르고, 머리가 내려앉는 깊이(dy)도 다르다.
# 네 자세 모두 마지막 줄이 21 이라야 발이 같은 땅에 선다
POSES = {
    # 서 있기 — 쉬는 동안 대부분 이 자세다
    "s": (0, ["....wbbbbbw....",
              "..ssbbbbbbbss..",
              "..ssbbbbbbbss..",
              "...bbbbbbbbb...",
              "...BBBBBBBBB...",
              "..BBBBBBBBBBB.."],
             [".....ll.ll.....",
              ".....ll.ll.....",
              ".....ll.ll.....",
              "....fff.fff....",
              "....fff.fff...."]),
    # 웅크리기 — 뛰기 직전. 머리가 셋 내려앉고 다리가 접힌다
    "c": (3, ["..sswbbbbbwss..",
              "..ssbbbbbbbss..",
              "...bbbbbbbbb...",
              "...BBBBBBBBB...",
              "..BBBBBBBBBBB.."],
             ["....ll...ll....",
              "...fff...fff...",
              "...fff...fff..."]),
    # 공중 — 다리를 접어 올린다. 아랫줄이 비어 몸이 떠 보인다
    "j": (0, ["..sswbbbbbwss..",
              "..ssbbbbbbbss..",
              "....bbbbbbb....",
              "...bbbbbbbbb...",
              "...BBBBBBBBB...",
              "...BBBBBBBBB..."],
             ["....ll...ll....",
              "...ff.....ff...",
              "...ff.....ff...",
              "...............",
              "..............."]),
    # 착지 — 한 번 눌린다. 머리가 둘 내려앉고 다리가 넓게 벌어진다
    "l": (2, ["...wbbbbbbbw...",
              ".ssbbbbbbbbbss.",
              "...bbbbbbbbb...",
              "..BBBBBBBBBBB..",
              ".BBBBBBBBBBBBB."],
             ["...ll.....ll...",
              "..fff.....fff..",
              "..fff.....fff.."]),
}


def build(name, pose):
    dy, torso, legs = POSES[pose]
    pal = PAL[name]
    px = [[None] * W for _ in range(H)]

    def put(y, x, c):
        if 0 <= y < H and 0 <= x < W and c != ".":
            px[y][x] = pal[c]

    for y, row in enumerate(HEAD):
        for x, c in enumerate(row):
            put(dy + y, x, c)
    for x, y, c in LOCKS[name]:
        if 0 <= dy + y < H and px[dy + y][x] is None:
            put(dy + y, x, c)
    for y, row in enumerate(torso + legs):
        for x, c in enumerate(row):
            put(dy + len(HEAD) + y, x, c)
    return px


def encode(px):
    used, idx = [], {}
    rows = []
    for row in px:
        out, x = [], 0
        while x < W:
            c = row[x]
            if c is None:
                x += 1
                continue
            if c not in idx:
                idx[c] = len(used)
                used.append(c)
            n = 1
            while x + n < W and row[x + n] == c:
                n += 1
            out.append([x, n, idx[c]])
            x += n
        rows.append(out)
    return {"w": W, "h": H, "pal": used, "rows": rows}


if __name__ == "__main__":
    import sys
    data = {f"{p}-{n}": encode(build(n, p)) for n in ORDER for p in POSES}
    out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1
                       else pathlib.Path(__file__).parent / "runners.json")
    out.write_text(json.dumps(data, separators=(",", ":")))
    dots = sum(sum(n for _, n, _ in r) for v in data.values() for r in v["rows"])
    print(f"{out}  {out.stat().st_size} bytes  "
          f"{len(data)}장({len(ORDER)}명 x {len(POSES)}자세) {W}x{H}  총 {dots}칸")
