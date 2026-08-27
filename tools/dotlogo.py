# -*- coding: utf-8 -*-
"""기술 로고를 16x16 도트 격자에 찍는다.

skillicons.dev 의 아이콘을 그대로 걸면 검은 각진 사각형이 하늘색 페이지에
박힌다. 페이지의 나머지가 전부 직접 찍은 도트라 저기만 말투가 다르다.
그래서 로고를 프리미티브(원·사각·글자)로 도트 격자에 다시 찍는다.

원은 방정식으로 채운다. 벡터 원을 얹으면 가장자리가 매끈해져 옆에 놓인
도트 글자와 안 어울린다 — 계단이 보여야 같은 그림으로 읽힌다.
"""

import math

N = 16   # 격자 한 변

# 5x7 도트 글자. 로고 안에 들어가는 것만 (Ps · Ae · TS · R).
GLYPH = {
    'T': "11111 00100 00100 00100 00100 00100 00100",
    'S': "01111 10000 10000 01110 00001 00001 11110",
    'P': "11110 10001 10001 11110 10000 10000 10000",
    'A': "01110 10001 10001 11111 10001 10001 10001",
    'R': "11110 10001 10001 11110 10100 10010 10001",
    # 소문자는 5x5 — 위 두 줄을 비워 베이스라인을 맞춘다
    's': "00000 00000 01111 10000 01110 00001 11110",
    'e': "00000 00000 01110 10001 11111 10000 01110",
}


def glyph(ch, ox, oy):
    rows = GLYPH[ch].split()
    return {(ox + c, oy + r) for r, row in enumerate(rows)
            for c, v in enumerate(row) if v == '1'}


def word(s, ox, oy, gap=1):
    out, x = set(), ox
    for ch in s:
        out |= glyph(ch, x, oy)
        x += 5 + gap
    return out


def box(x0, y0, x1, y1):
    return {(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)}


def disc(cx, cy, r):
    """반지름 r 인 원판. 도트 중심으로 재서 계단이 좌우대칭이 되게 한다."""
    return {(x, y) for x in range(N) for y in range(N)
            if (x + .5 - cx) ** 2 + (y + .5 - cy) ** 2 <= r * r}


def ring(cx, cy, ro, ri):
    return disc(cx, cy, ro) - disc(cx, cy, ri)


def cap(x0, x1, y0, y1, side):
    """한쪽 끝이 반원인 조각. 반지름은 높이의 절반이고, 결과를 사각형으로
    잘라 낸다 — 안 자르면 반원이 위아래로 한 칸씩 삐져나온다."""
    r = (y1 - y0 + 1) / 2
    cy = (y0 + y1 + 1) / 2
    clip = box(x0, y0, x1, y1)
    if side == 'l':
        return (box(int(x0 + r), y0, x1, y1) | disc(x0 + r, cy, r)) & clip
    if side == 'r':
        return (box(x0, y0, int(x1 - r), y1) | disc(x1 + 1 - r, cy, r)) & clip
    return disc((x0 + x1 + 1) / 2, cy, r) & clip      # 완전한 원


def half(cells, side):
    """원판을 반으로 자른다 (figma 의 반원 조각)."""
    if side == 'r':
        return {c for c in cells if c[0] >= 8}
    return {c for c in cells if c[0] < 8}


# ── 로고 여덟 ──────────────────────────────────────────────────────────────
# 값은 [(색, 도트집합), ...] — 뒤에 오는 것이 위에 덮인다.

def rust():
    """톱니 링 + R. 링을 캔버스 끝까지 키우면 톱니가 링에 묻혀 그냥 원이 된다."""
    o = "#ce6a3a"
    body = ring(8, 8, 6.9, 4.9)
    teeth = (box(6, 0, 9, 2) | box(6, 13, 9, 15)
             | box(0, 6, 2, 9) | box(13, 6, 15, 9))
    return [(o, body | teeth), (o, word('R', 6, 5))]


def python_():
    """맞물린 두 조각. 위는 「, 아래는 그것을 180도 돌린 것."""
    up = box(4, 1, 11, 6) | box(1, 6, 6, 11)
    dn = box(9, 4, 14, 9) | box(4, 9, 11, 14)
    up -= dn                                   # 겹치는 허리는 아래 조각에 준다
    return [("#3776ab", up - {(9, 3), (10, 3)}),
            ("#ffd43b", dn - {(5, 12), (6, 12)})]


def typescript():
    return [("#3178c6", box(0, 0, 15, 15)), ("#ffffff", word('TS', 2, 5, gap=2))]


def flutter():
    """접힌 종이. 우상에서 좌하로 내려왔다가 우하로 되꺾인다."""
    a = {(x, y) for y in range(0, 12) for x in range(9 - y, 16 - y) if 0 <= x < N}
    b = {(x, y) for y in range(8, 16) for x in range(y - 8, y - 1) if 0 <= x < N}
    # 겹치는 칸은 아래 조각이 가진다 — 세 색으로 나누면 두 띠가 X 로 교차해 보인다
    return [("#54c5f8", a - b), ("#01579b", b)]


def figma():
    """세 줄 다섯 조각. 오른쪽 끝과 아래 끝만 둥글다."""
    return [("#f24e1e", cap(3, 7, 0, 4, 'l')),
            ("#a259ff", cap(8, 12, 0, 4, 'r')),
            ("#ff7262", cap(3, 7, 5, 9, 'l')),
            ("#1abcfe", cap(8, 12, 5, 9, 'o')),
            ("#0acf83", cap(3, 7, 10, 14, 'o'))]


def photoshop():
    return [("#001e36", box(0, 0, 15, 15)), ("#31a8ff", word('Ps', 2, 5))]


def aftereffects():
    return [("#00005b", box(0, 0, 15, 15)), ("#9999ff", word('Ae', 2, 5))]


def git():
    """마름모 + 가지. |dx|+|dy| 로 찍어야 계단이 네 변에서 고르다."""
    dia = {(x, y) for x in range(N) for y in range(N)
           if abs(x - 7.5) + abs(y - 7.5) <= 8.2}
    # 노드를 십자로 줄인다. 3x3 이면 1칸 선보다 세 배 굵어 가지가 선과 뭉쳐
    # 세로 막대로 읽힌다. 가지는 대각으로 눕혀야 갈라진 것으로 보인다.
    line = box(4, 7, 9, 7) | {(9, 6), (10, 6), (11, 5)}
    node = disc(4.5, 7.5, 1.4) | disc(9.5, 7.5, 1.4) | disc(11.5, 4.5, 1.4)
    return [("#f05033", dia), ("#ffffff", line | node)]


def dart():
    """같은 각도로 겹쳐 내려가는 두 톤 파랑. 채워진 쐐기 하나와 그 위를 지나는
    얇은 띠 하나다.

    바로 옆이 Flutter 라 그쪽의 '<' 꺾임과 안 겹치게 각도를 한 방향으로만
    남겼다 — 전에는 접힌 종이로 그려서 둘 다 「파란 접힌 조각」으로 보였다.
    """
    dk = {(x, y) for y in range(4, 15) for x in range(3, 15) if x - 3 <= y - 4}
    lt = {(x, y) for y in range(0, 12) for x in range(3, 15) if 0 <= x - 3 - y <= 3}
    return [("#40c4ff", lt), ("#0175c2", dk)]


def godot():
    """로봇 머리. 눈이 얼굴 폭의 절반을 먹어야 16칸에서 로봇으로 읽힌다."""
    head = box(2, 2, 13, 2) | box(1, 3, 14, 12) | box(3, 13, 12, 14)
    eyes = box(3, 6, 6, 9) | box(9, 6, 12, 9)
    pupil = box(4, 7, 5, 8) | box(10, 7, 11, 8)
    mouth = box(5, 11, 10, 12)
    return [("#478cbf", head), ("#ffffff", eyes | mouth), ("#414042", pupil)]


def claude():
    """앤트로픽 마크 — 가운데서 뻗는 여덟 갈래. 팔을 한 칸으로 그으면 별표가
    되므로 안쪽에 심을 두고 거기서 뻗게 한다."""
    cells = set(box(6, 6, 9, 9))
    for k in range(8):
        a = math.pi * k / 4
        for t in range(2, 8):
            x, y = int(round(7.5 + math.cos(a) * t)), int(round(7.5 + math.sin(a) * t))
            if 0 <= x < N and 0 <= y < N:
                cells.add((x, y))
                if t < 5:                      # 안쪽 절반만 굵게 — 끝으로 갈수록 가늘어진다
                    for dx, dy in ((1, 0), (0, 1)):
                        if 0 <= x + dx < N and 0 <= y + dy < N:
                            cells.add((x + dx, y + dy))
    return [("#d97757", cells)]


def slack():
    """네 갈래 바람개비. 진짜 로고는 막대 끝이 둥글지만 16칸에서는 그 곡률이
    한 칸도 안 되니 각진 막대로 찍고, 대신 **가운데를 십자로 비운다** — 이
    로고를 읽게 하는 건 색 넷이 아니라 서로 어긋나게 도는 배치다.
    전에는 막대 넷을 흩어 놓기만 해서 색 조각 넷으로만 보였다."""
    return [("#2eb67d", box(0, 4, 6, 6) | box(4, 1, 6, 3)),      # 좌상 — 왼쪽으로 뻗고 위로 꺾인다
            ("#ecb22e", box(9, 0, 11, 6) | box(12, 4, 14, 6)),   # 우상
            ("#e01e5a", box(9, 9, 15, 11) | box(9, 12, 11, 14)),  # 우하
            ("#36c5f0", box(4, 9, 6, 15) | box(1, 9, 3, 11))]     # 좌하


# 언어 → 엔진·프레임워크 → 디자인 → 도구 순. 리드미 한 줄 폭 846 을 열둘로 나눠
# 세우므로 개수를 바꾸면 make_stack 이 간격을 다시 계산한다.
LOGOS = [
    ("Rust", rust), ("Python", python_), ("TypeScript", typescript), ("Dart", dart),
    ("Flutter", flutter), ("Godot", godot),
    ("Figma", figma), ("Photoshop", photoshop), ("AfterFX", aftereffects),
    ("Claude", claude), ("Slack", slack), ("Git", git),
]


# ── 연락처 셋 ─────────────────────────────────────────────────────────────
# 이쪽은 칩 색 위에 얹히므로 배경을 뚫는 자리(눈·M)는 '구멍'으로 준다.
# 색이 None 이면 렌더러가 칩 배경색으로 채운다.

def discord():
    body = box(2, 3, 13, 10) | box(1, 4, 14, 9) | box(3, 2, 12, 2)
    horn = {(2, 11), (3, 11), (3, 12), (4, 12), (13, 11), (12, 11), (12, 12), (11, 12)}
    eyes = box(4, 5, 5, 7) | box(10, 5, 11, 7)
    return [("#5865f2", body | horn), (None, eyes)]


def gmail():
    """M 자만 남긴다. 봉투 면을 칠하고 M 을 뚫으면 흰 면적이 절반을 넘어
    글자가 아니라 테두리 사각형으로 읽힌다."""
    m = box(1, 3, 2, 12) | box(13, 3, 14, 12)
    for i in range(5):                       # V 두 변. 한 줄에 두 칸씩 내려간다
        m |= {(3 + i, 3 + i), (4 + i, 3 + i), (12 - i, 3 + i), (11 - i, 3 + i)}
    m |= box(7, 8, 8, 9)                     # V 바닥
    return [("#ea4335", m)]


def github():
    """얼굴만. 전신(몸·다리·꼬리)을 16칸에 욱여넣으면 머리가 칩을 꽉 채운
    사각형이 되어 고양이로 안 읽힌다. 귀는 삼각형으로 머리 위에 세운다."""
    head = disc(8, 8.5, 5.4)
    ear = (box(4, 1, 5, 1) | box(3, 2, 5, 2) | box(3, 3, 6, 3)
           | box(10, 1, 11, 1) | box(10, 2, 12, 2) | box(9, 3, 12, 3))
    eyes = box(5, 7, 6, 8) | box(9, 7, 10, 8)
    mouth = box(7, 10, 8, 10) | {(6, 11), (9, 11)}
    return [("MONO", head | ear), (None, eyes | mouth)]


CONTACT = [
    ("discord", "@omufrozen", discord, "https://discord.com/users/omufrozen"),
    ("mail", "goenho0613@gmail.com", gmail, "mailto:goenho0613@gmail.com"),
    ("github", "2rami", github, "https://github.com/2rami"),
]
