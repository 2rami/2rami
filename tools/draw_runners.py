"""여섯을 8x12 도트로 직접 그린다.

원본을 줄이는 길은 버렸다. 12칸에 얼굴을 우겨넣으면 눈·머리·옷이 한 덩어리로
뭉개져 색깔 얼룩만 남는다(2026-08-27 확인). 형태는 손으로 잡고 색만 원본에서
가져온다. 두 프레임 크기가 같으니 프레임이 바뀔 때 몸이 좌우로 튀지도 않는다.
"""
import json, pathlib, sys

W, H = 8, 12

# 원본에서 뽑은 색을 또렷하게 올린 것. 작을수록 색이 세야 구분된다
SKIN = {
    "norma":  ("#e9c49b", "#c79a72"), "sparxie": ("#f0d9d2", "#c9a89f"),
    "kei":    ("#f4e2dd", "#cdb0ab"), "aria":    ("#f0d2cd", "#c99f9c"),
    "nangong":("#dcc3b8", "#b0917f"), "sunna":   ("#ecd2b9", "#c2a184"),
}
HAIR = {"norma": ("#ddd6cc", "#a89f95"), "sparxie": ("#ece0dc", "#b9a6a2"),
        "kei": ("#e88fb0", "#b45f80"), "aria": ("#f2a3ad", "#bd6e7c"),
        "nangong": ("#7b5c50", "#4c382f"), "sunna": ("#ded08c", "#a89a5f")}
BODY = {"norma": ("#37528f", "#22345c"), "sparxie": ("#7d3039", "#4e1d24"),
        "kei": ("#3d3950", "#252234"), "aria": ("#2f6f77", "#1c454b"),
        "nangong": ("#4a3f3c", "#2b2422"), "sunna": ("#6d4b6a", "#432c42")}
LEG = {"norma": "#22343c", "sparxie": "#332e31", "kei": "#1d2f36",
       "aria": "#5c5f66", "nangong": "#26252a", "sunna": "#4a3846"}
EYE = "#33262c"

# 머리 모양 — 실루엣이 달라야 여섯이 구분된다. (x, y) 에 머리색을 더 찍는다.
# 긴 머리는 0·7 열(몸 바깥)에 둔다. 1·6 열은 팔이 차지해 가려진다
LOCKS = {
    "norma":   [(0, 2), (7, 2), (0, 3), (7, 3)],                  # 짧은 옆머리
    "sparxie": [(0, 3), (7, 3), (0, 4), (7, 4), (0, 5), (7, 5),
                (0, 6), (7, 6)],                                  # 긴 생머리
    "kei":     [(0, 2), (7, 2), (0, 3), (7, 3), (0, 4), (7, 4)],  # 트윈테일
    "aria":    [(0, 3), (7, 3), (0, 4), (7, 4), (0, 5), (7, 5)],  # 반묶음
    "nangong": [(7, 3), (7, 4), (7, 5), (7, 6)],                  # 포니테일
    "sunna":   [(0, 1), (7, 1), (0, 2)],                          # 삐침머리
}

# . 비움  h 머리  H 머리그늘  s 피부  S 피부그늘  e 눈  b 옷  B 옷그늘  l 다리
HEAD = [
    "..hhhh..",
    ".hhhhhh.",
    ".hssssh.",
    ".hesseh.",
    "..ssSs..",
]
# 팔다리는 프레임마다 다르다. 아랫줄 둘만 바꾸면 붙어서 볼 때 멈춘 것처럼 보인다
POSE = {
    "a": ["..bbbb..",       # 팔 내리고 다리 벌린 자세
          ".sbbbbs.",
          ".SbBBbS.",
          "..bBBb..",
          ".ll..ll.",
          ".l....l.",
          ".l....l."],
    "b": [".sbbbbs.",       # 팔 올리고 다리 모은 자세
          ".SbbbbS.",
          "..bBBb..",
          "..bBBb..",
          "..llll..",
          "..llll..",
          ".ll..ll."],
}


def build(name, frame):
    px = [[None] * W for _ in range(H)]
    pal = {"h": HAIR[name][0], "H": HAIR[name][1], "s": SKIN[name][0],
           "S": SKIN[name][1], "e": EYE, "b": BODY[name][0],
           "B": BODY[name][1], "l": LEG[name]}
    for y, row in enumerate(HEAD + POSE[frame]):
        for x, c in enumerate(row):
            if c != ".":
                px[y][x] = pal[c]
    for x, y in LOCKS[name]:
        if px[y][x] is None:
            px[y][x] = HAIR[name][1]
    return px


def encode(px):
    used, cols = [], {}
    for row in px:
        for c in row:
            if c and c not in cols:
                cols[c] = len(used); used.append(c)
    rows = []
    for row in px:
        out, x = [], 0
        while x < W:
            c = row[x]
            if c is None:
                x += 1; continue
            n = 1
            while x + n < W and row[x + n] == c: n += 1
            out.append([x, n, cols[c]]); x += n
        rows.append(out)
    return {"w": W, "h": H, "pal": used, "rows": rows}


if __name__ == "__main__":
    data = {}
    for n in SKIN:
        for f in ("a", "b"):
            data[f"{f}-{n}"] = encode(build(n, f))
    p = pathlib.Path(sys.argv[1] if len(sys.argv) > 1
                     else str(pathlib.Path(__file__).parent / "runners.json"))
    p.write_text(json.dumps(data, separators=(",", ":")))
    print(p, p.stat().st_size, "bytes",
          f"({len(data)}개, 모두 {W}x{H})")
